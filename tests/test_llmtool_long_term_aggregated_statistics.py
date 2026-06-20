import builtins
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "python_scripts"
    / "llmtool_long_term_aggregated_statistics.py"
)

LOCAL_TZ = timezone(timedelta(hours=2))


class FakeDtUtil:
    def __init__(self, now=None):
        self.now_value = now or datetime(2025, 7, 30, 16, 0, 0, tzinfo=LOCAL_TZ)

    def now(self):
        return self.now_value

    def parse_datetime(self, value):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def as_utc(self, value):
        if value.tzinfo is None:
            value = value.replace(tzinfo=LOCAL_TZ)
        return value.astimezone(timezone.utc)

    def as_local(self, value):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(LOCAL_TZ)


class GuardedDateTime(datetime):
    @classmethod
    def strptime(cls, value, time_format):
        raise ImportError("Not allowed to import time")

    def strftime(self, time_format):
        raise ImportError("Not allowed to import time")


class GuardedDateTimeModule:
    datetime = GuardedDateTime


class FakeState:
    def __init__(self, attributes):
        self.attributes = attributes


class FakeStates:
    def __init__(self, states):
        self.states = states

    def get(self, entity_id):
        return self.states.get(entity_id)


class FakeServices:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def call(self, domain, service, service_data, blocking=False, return_response=False):
        self.calls.append(
            {
                "domain": domain,
                "service": service,
                "service_data": service_data,
                "blocking": blocking,
                "return_response": return_response,
            }
        )
        response = self.responses[len(self.calls) - 1]
        if callable(response):
            return response(service_data)
        return response


class FakeHass:
    def __init__(self, responses=None, states=None):
        self.services = FakeServices(responses or [{"statistics": {}}])
        self.states = FakeStates(states or {})


def row(start, end, **values):
    payload = {
        "start": start,
        "end": end,
    }
    payload.update(values)
    return payload


def run_helper(
    overrides,
    responses=None,
    states=None,
    now=None,
    datetime_module=None,
    restricted_builtins=None,
):
    data = {
        "entity_ids": "sensor.living_room_temperature",
        "start_time": "2025-07-30 14:00:00",
        "end_time": "2025-07-30 16:00:00",
        "aggregation_type": "mean",
        "aggregation_period": "hour",
    }
    data.update(overrides)

    output = {}
    hass = FakeHass(responses=responses, states=states)
    exec(
        SCRIPT.read_text(),
        {
            "data": data,
            "output": output,
            "hass": hass,
            "dt_util": FakeDtUtil(now=now),
            "datetime": datetime_module or __import__("datetime"),
            "__builtins__": restricted_builtins or builtins.__dict__,
        },
    )
    return output, hass


class LongTermAggregatedStatisticsHelperTest(unittest.TestCase):
    def test_shapes_one_entity_and_calls_recorder(self):
        responses = [
            {
                "statistics": {
                    "sensor.living_room_temperature": [
                        row(
                            "2025-07-30T12:00:00+00:00",
                            "2025-07-30T13:00:00+00:00",
                            mean=21.4,
                        )
                    ]
                }
            }
        ]
        states = {
            "sensor.living_room_temperature": FakeState(
                {
                    "friendly_name": "Living room temperature",
                    "unit_of_measurement": "C",
                }
            )
        }

        result, hass = run_helper({}, responses=responses, states=states)

        self.assertTrue(result["success"])
        self.assertEqual("Found 1 statistics row.", result["answer"])
        self.assertEqual(1, result["meta"]["count"])
        self.assertEqual(1, result["meta"]["total"])
        self.assertEqual("hour", hass.services.calls[0]["service_data"]["period"])
        self.assertEqual(["mean"], hass.services.calls[0]["service_data"]["types"])
        self.assertTrue(hass.services.calls[0]["blocking"])
        self.assertTrue(hass.services.calls[0]["return_response"])
        entity = result["data"]["entities"][0]
        self.assertEqual("sensor.living_room_temperature", entity["entity_id"])
        self.assertEqual("Living room temperature", entity["friendly_name"])
        self.assertEqual("C", entity["unit_of_measurement"])
        self.assertEqual(
            [
                {
                    "start": "2025-07-30 14:00:00",
                    "end": "2025-07-30 15:00:00",
                    "mean": 21.4,
                }
            ],
            entity["values"],
        )

    def test_default_end_time_is_echoed(self):
        result, hass = run_helper(
            {"end_time": ""},
            responses=[
                {
                    "statistics": {
                        "sensor.living_room_temperature": [
                            row(
                                "2025-07-30T12:00:00+00:00",
                                "2025-07-30T13:00:00+00:00",
                                mean=21.4,
                            )
                        ]
                    }
                }
            ],
            now=datetime(2025, 7, 30, 17, 30, 0, tzinfo=LOCAL_TZ),
        )

        self.assertTrue(result["success"])
        self.assertEqual("2025-07-30 17:30:00", result["meta"]["end_time"])
        self.assertTrue(result["meta"]["end_time_was_defaulted"])
        self.assertEqual(
            datetime(2025, 7, 30, 15, 30, 0, tzinfo=timezone.utc),
            hass.services.calls[0]["service_data"]["end_time"],
        )

    def test_time_handling_does_not_use_datetime_format_helpers(self):
        result, _ = run_helper(
            {},
            responses=[
                {
                    "statistics": {
                        "sensor.living_room_temperature": [
                            row(
                                "2025-07-30T12:00:00+00:00",
                                "2025-07-30T13:00:00+00:00",
                                mean=21.4,
                            )
                        ]
                    }
                }
            ],
            datetime_module=GuardedDateTimeModule(),
        )

        self.assertTrue(result["success"])

    def test_restricted_builtins_without_dict_or_list(self):
        restricted = builtins.__dict__.copy()
        restricted.pop("dict")
        restricted.pop("list")

        result, _ = run_helper(
            {},
            responses=[
                {
                    "statistics": {
                        "sensor.living_room_temperature": [
                            row(
                                "2025-07-30T12:00:00+00:00",
                                "2025-07-30T13:00:00+00:00",
                                mean=21.4,
                            )
                        ]
                    }
                }
            ],
            restricted_builtins=restricted,
        )

        self.assertTrue(result["success"])

    def test_validation_errors(self):
        too_many_ids = ",".join(["sensor.value_{}".format(index) for index in range(11)])

        invalid_entity, _ = run_helper({"entity_ids": "sensor.good,light.Bad"})
        too_many, _ = run_helper({"entity_ids": too_many_ids})
        invalid_start, _ = run_helper({"start_time": "2025-07-30T14:00:00"})
        invalid_end, _ = run_helper({"end_time": "2025-07-30 13:00:00"})
        invalid_type, _ = run_helper({"aggregation_type": "sum"})
        invalid_period, _ = run_helper({"aggregation_period": "minute"})

        self.assertFalse(invalid_entity["success"])
        self.assertEqual(["light.Bad"], invalid_entity["data"]["invalid_entity_ids"])
        self.assertFalse(too_many["success"])
        self.assertEqual(10, too_many["data"]["max_entity_ids"])
        self.assertFalse(invalid_start["success"])
        self.assertEqual("YYYY-MM-DD HH:MM:SS", invalid_start["data"]["expected_format"])
        self.assertFalse(invalid_end["success"])
        self.assertIn("after start_time", invalid_end["error"])
        self.assertFalse(invalid_type["success"])
        self.assertIn("mean", invalid_type["data"]["known_aggregation_types"])
        self.assertFalse(invalid_period["success"])
        self.assertIn("total", invalid_period["data"]["known_aggregation_periods"])

    def test_partial_missing_entities_returns_success(self):
        result, _ = run_helper(
            {"entity_ids": "sensor.one,sensor.two"},
            responses=[
                {
                    "statistics": {
                        "sensor.one": [
                            row(
                                "2025-07-30T12:00:00+00:00",
                                "2025-07-30T13:00:00+00:00",
                                mean=1,
                            )
                        ]
                    }
                }
            ],
        )

        self.assertTrue(result["success"])
        self.assertEqual(["sensor.two"], result["data"]["missing_entities"])
        self.assertEqual(["sensor.one"], [item["entity_id"] for item in result["data"]["entities"]])
        self.assertIn("No statistics found for 1 requested entity", result["answer"])

    def test_no_data_returns_soft_failure(self):
        result, _ = run_helper(
            {"entity_ids": "sensor.one,sensor.two"},
            responses=[{"statistics": {}}],
        )

        self.assertFalse(result["success"])
        self.assertEqual("No statistics found for requested entity IDs and time range.", result["error"])
        self.assertEqual(["sensor.one", "sensor.two"], result["data"]["missing_entities"])
        self.assertEqual(0, result["meta"]["count"])

    def test_truncates_globally_and_keeps_entity_with_empty_values(self):
        first_rows = []
        for index in range(500):
            first_rows.append(
                row(
                    "2025-07-30T12:00:00+00:00",
                    "2025-07-30T13:00:00+00:00",
                    mean=index,
                )
            )

        result, _ = run_helper(
            {"entity_ids": "sensor.one,sensor.two"},
            responses=[
                {
                    "statistics": {
                        "sensor.one": first_rows,
                        "sensor.two": [
                            row(
                                "2025-07-30T12:00:00+00:00",
                                "2025-07-30T13:00:00+00:00",
                                mean=999,
                            )
                        ],
                    }
                }
            ],
        )

        self.assertTrue(result["success"])
        self.assertEqual(500, result["meta"]["count"])
        self.assertEqual(501, result["meta"]["total"])
        self.assertTrue(result["meta"]["truncated"])
        self.assertEqual(500, len(result["data"]["entities"][0]["values"]))
        self.assertEqual([], result["data"]["entities"][1]["values"])
        self.assertTrue(result["data"]["entities"][1]["truncated"])
        self.assertEqual([], result["data"]["missing_entities"])

    def test_negative_zero_normalizes_to_zero(self):
        result, _ = run_helper(
            {},
            responses=[
                {
                    "statistics": {
                        "sensor.living_room_temperature": [
                            row(
                                "2025-07-30T12:00:00+00:00",
                                "2025-07-30T13:00:00+00:00",
                                mean=-0.0,
                            )
                        ]
                    }
                }
            ],
        )

        self.assertTrue(result["success"])
        self.assertEqual(0, result["data"]["entities"][0]["values"][0]["mean"])

    def test_total_mean_min_max_and_change(self):
        rows = [
            row("2025-07-30T12:00:00+00:00", "2025-07-30T13:00:00+00:00", mean=10, min=8, max=12, change=2),
            row("2025-07-30T13:00:00+00:00", "2025-07-30T14:00:00+00:00", mean=20, min=18, max=22, change=3),
        ]

        mean_result, _ = run_helper(
            {"aggregation_period": "total", "aggregation_type": "mean"},
            responses=[{"statistics": {"sensor.living_room_temperature": rows}}],
        )
        min_result, _ = run_helper(
            {"aggregation_period": "total", "aggregation_type": "min"},
            responses=[{"statistics": {"sensor.living_room_temperature": rows}}],
        )
        max_result, _ = run_helper(
            {"aggregation_period": "total", "aggregation_type": "max"},
            responses=[{"statistics": {"sensor.living_room_temperature": rows}}],
        )
        change_result, _ = run_helper(
            {"aggregation_period": "total", "aggregation_type": "change"},
            responses=[{"statistics": {"sensor.living_room_temperature": rows}}],
        )

        self.assertEqual(15, mean_result["data"]["entities"][0]["values"][0]["mean"])
        self.assertEqual(8, min_result["data"]["entities"][0]["values"][0]["min"])
        self.assertEqual(22, max_result["data"]["entities"][0]["values"][0]["max"])
        self.assertEqual(5, change_result["data"]["entities"][0]["values"][0]["change"])
        self.assertEqual("total", mean_result["meta"]["aggregation_period"])

    def test_total_short_range_uses_5minute_and_falls_back_to_hour_when_empty(self):
        result, hass = run_helper(
            {"aggregation_period": "total"},
            responses=[
                {"statistics": {}},
                {
                    "statistics": {
                        "sensor.living_room_temperature": [
                            row(
                                "2025-07-30T12:00:00+00:00",
                                "2025-07-30T13:00:00+00:00",
                                mean=21,
                            )
                        ]
                    }
                },
            ],
        )

        self.assertTrue(result["success"])
        self.assertEqual("5minute", hass.services.calls[0]["service_data"]["period"])
        self.assertEqual("hour", hass.services.calls[1]["service_data"]["period"])

    def test_total_short_range_does_not_fallback_when_5minute_has_some_rows(self):
        result, hass = run_helper(
            {"entity_ids": "sensor.one,sensor.two", "aggregation_period": "total"},
            responses=[
                {
                    "statistics": {
                        "sensor.one": [
                            row(
                                "2025-07-30T12:00:00+00:00",
                                "2025-07-30T12:05:00+00:00",
                                mean=1,
                            )
                        ]
                    }
                }
            ],
        )

        self.assertTrue(result["success"])
        self.assertEqual(1, len(hass.services.calls))
        self.assertEqual(["sensor.two"], result["data"]["missing_entities"])

    def test_total_long_range_uses_hour(self):
        result, hass = run_helper(
            {
                "aggregation_period": "total",
                "end_time": "2025-07-30 18:00:00",
            },
            responses=[
                {
                    "statistics": {
                        "sensor.living_room_temperature": [
                            row(
                                "2025-07-30T12:00:00+00:00",
                                "2025-07-30T13:00:00+00:00",
                                mean=21,
                            )
                        ]
                    }
                }
            ],
        )

        self.assertTrue(result["success"])
        self.assertEqual(1, len(hass.services.calls))
        self.assertEqual("hour", hass.services.calls[0]["service_data"]["period"])

    def test_invalid_recorder_response_shape_returns_soft_failure(self):
        result, _ = run_helper({}, responses=[{"bad": {}}])

        self.assertFalse(result["success"])
        self.assertIn("Invalid recorder response shape", result["error"])


if __name__ == "__main__":
    unittest.main()
