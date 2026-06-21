import builtins
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "python_scripts" / "llmtool_raw_entity_history.py"

LOCAL_TZ = timezone(timedelta(hours=2))


class FakeDtUtil:
    def __init__(self, now=None):
        self.now_value = now or datetime(2026, 6, 20, 12, 0, 0, tzinfo=LOCAL_TZ)

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


class FakeState:
    def __init__(self, attributes):
        self.attributes = attributes


class FakeStates:
    def __init__(self, states):
        self.states = states

    def get(self, entity_id):
        return self.states.get(entity_id)


class FakeHass:
    def __init__(self, states=None):
        self.states = FakeStates(states or {})


def run_helper(overrides, states=None, now=None, restricted_builtins=None):
    data = {
        "mode": "prepare",
        "entity_ids": "binary_sensor.window",
        "start_time": "2026-06-20 10:00:00",
        "end_time": "2026-06-20 12:00:00",
        "limit": "",
    }
    data.update(overrides)

    output = {}
    exec(
        SCRIPT.read_text(),
        {
            "data": data,
            "output": output,
            "hass": FakeHass(states=states),
            "dt_util": FakeDtUtil(now=now),
            "datetime": __import__("datetime"),
            "__builtins__": restricted_builtins or builtins.__dict__,
        },
    )
    return output


def row(entity_id, changed_at, state):
    return {
        "entity_id": entity_id,
        "last_changed": changed_at,
        "state": state,
    }


def minimal_row(changed_at, state):
    return {
        "last_changed": changed_at,
        "state": state,
    }


def shape_payload(payload, overrides=None, states=None, restricted_builtins=None):
    data = {
        "mode": "shape",
        "rest_status": "200",
        "history_payload": payload,
        "entity_ids": "binary_sensor.window",
        "start_time": "2026-06-20 10:00:00",
        "end_time": "2026-06-20 12:00:00",
        "end_time_was_defaulted": "False",
        "limit": "100",
    }
    if overrides:
        data.update(overrides)
    return run_helper(data, states=states, restricted_builtins=restricted_builtins)


class RawEntityHistoryHelperTest(unittest.TestCase):
    def test_prepare_builds_rest_url_and_defaults(self):
        result = run_helper({"end_time": "", "limit": ""})

        self.assertTrue(result["success"])
        self.assertEqual(["binary_sensor.window"], result["data"]["entity_ids"])
        self.assertEqual("2026-06-20 12:00:00", result["data"]["end_time"])
        self.assertTrue(result["data"]["end_time_was_defaulted"])
        self.assertEqual(100, result["data"]["limit"])
        self.assertIn("/api/history/period/2026-06-20T10%3A00%3A00%2B02%3A00", result["data"]["history_url"])
        self.assertIn("end_time=2026-06-20T12%3A00%3A00%2B02%3A00", result["data"]["history_url"])
        self.assertIn("filter_entity_id=binary_sensor.window", result["data"]["history_url"])
        self.assertIn("minimal_response", result["data"]["history_url"])
        self.assertIn("no_attributes", result["data"]["history_url"])
        self.assertIn("significant_changes_only=0", result["data"]["history_url"])

    def test_prepare_validation_errors(self):
        invalid_entity = run_helper({"entity_ids": "binary_sensor.window,Light.Bad"})
        too_many = run_helper({"entity_ids": ",".join(["sensor.value_{}".format(index) for index in range(11)])})
        invalid_start = run_helper({"start_time": "2026-06-20T10:00:00"})
        invalid_end = run_helper({"end_time": "2026-06-20 09:00:00"})
        invalid_limit = run_helper({"limit": "1001"})

        self.assertFalse(invalid_entity["success"])
        self.assertEqual(["Light.Bad"], invalid_entity["data"]["invalid_entity_ids"])
        self.assertFalse(too_many["success"])
        self.assertEqual(10, too_many["data"]["max_entity_ids"])
        self.assertFalse(invalid_start["success"])
        self.assertEqual("YYYY-MM-DD HH:MM:SS", invalid_start["data"]["expected_format"])
        self.assertFalse(invalid_end["success"])
        self.assertIn("after start_time", invalid_end["error"])
        self.assertFalse(invalid_limit["success"])
        self.assertEqual(1000, invalid_limit["data"]["max_limit"])

    def test_shape_history_with_boundaries_durations_and_metadata(self):
        states = {
            "binary_sensor.window": FakeState(
                {
                    "friendly_name": "Window",
                }
            )
        }
        payload = [
            [
                row("binary_sensor.window", "2026-06-20T07:30:00+00:00", "off"),
                minimal_row("2026-06-20T09:00:00+00:00", "on"),
                minimal_row("2026-06-20T09:30:00+00:00", "off"),
            ]
        ]

        result = shape_payload(payload, states=states)

        self.assertTrue(result["success"])
        self.assertEqual("Found 3 history entries.", result["answer"])
        self.assertEqual(3, result["meta"]["count"])
        self.assertEqual(3, result["meta"]["total"])
        entity = result["data"]["entities"][0]
        self.assertEqual("Window", entity["friendly_name"])
        self.assertEqual(
            {"changed_at": "2026-06-20 09:30:00", "active_at": "2026-06-20 10:00:00", "state": "off"},
            entity["state_at_start"],
        )
        self.assertEqual(
            {"changed_at": "2026-06-20 11:30:00", "active_at": "2026-06-20 12:00:00", "state": "off"},
            entity["state_at_end"],
        )
        self.assertEqual(
            [
                {
                    "changed_at": "2026-06-20 09:30:00",
                    "state": "off",
                    "duration_until_next_change_seconds": 5400,
                },
                {
                    "changed_at": "2026-06-20 11:00:00",
                    "state": "on",
                    "duration_until_next_change_seconds": 1800,
                },
                {
                    "changed_at": "2026-06-20 11:30:00",
                    "state": "off",
                },
            ],
            entity["history"],
        )

    def test_shape_partial_missing_entities_returns_success(self):
        payload = [
            [
                row("binary_sensor.window", "2026-06-20T08:00:00+00:00", "off"),
            ]
        ]

        result = shape_payload(
            payload,
            overrides={"entity_ids": "binary_sensor.window,binary_sensor.door"},
        )

        self.assertTrue(result["success"])
        self.assertEqual(["binary_sensor.door"], result["data"]["missing_entities"])
        self.assertIn("No raw history found for 1 requested entity", result["answer"])

    def test_shape_no_data_returns_soft_failure(self):
        result = shape_payload([])

        self.assertFalse(result["success"])
        self.assertEqual("No raw history found for requested entity IDs and time range.", result["error"])
        self.assertEqual(["binary_sensor.window"], result["data"]["missing_entities"])
        self.assertEqual(0, result["meta"]["count"])

    def test_truncates_globally_and_keeps_state_at_end_from_untruncated_rows(self):
        payload = [
            [
                row("binary_sensor.window", "2026-06-20T08:00:00+00:00", "off"),
                minimal_row("2026-06-20T08:30:00+00:00", "on"),
                minimal_row("2026-06-20T09:00:00+00:00", "off"),
            ]
        ]

        result = shape_payload(payload, overrides={"limit": "2"})

        self.assertTrue(result["success"])
        self.assertEqual(2, result["meta"]["count"])
        self.assertEqual(3, result["meta"]["total"])
        self.assertTrue(result["meta"]["truncated"])
        entity = result["data"]["entities"][0]
        self.assertTrue(entity["truncated"])
        self.assertEqual(2, len(entity["history"]))
        self.assertNotIn("duration_until_next_change_seconds", entity["history"][-1])
        self.assertEqual("off", entity["state_at_end"]["state"])
        self.assertEqual("2026-06-20 11:00:00", entity["state_at_end"]["changed_at"])

    def test_http_errors_and_invalid_json_return_soft_failures(self):
        auth = shape_payload([], overrides={"rest_status": "401"})
        server = shape_payload([], overrides={"rest_status": "500"})
        invalid_json = shape_payload({"llmtool_invalid_json": True})

        self.assertFalse(auth["success"])
        self.assertIn("authentication failed", auth["error"])
        self.assertEqual(401, auth["data"]["status"])
        self.assertFalse(server["success"])
        self.assertEqual(500, server["data"]["status"])
        self.assertFalse(invalid_json["success"])
        self.assertIn("Invalid History API JSON", invalid_json["error"])

    def test_invalid_response_shape_returns_soft_failure(self):
        result = shape_payload([{"bad": "shape"}])

        self.assertFalse(result["success"])
        self.assertIn("Invalid History API response shape", result["error"])

    def test_restricted_builtins_without_dict_or_list(self):
        restricted = builtins.__dict__.copy()
        restricted.pop("dict")
        restricted.pop("list")

        result = shape_payload(
            [[row("binary_sensor.window", "2026-06-20T08:00:00+00:00", "off")]],
            states={},
            restricted_builtins=restricted,
        )

        self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()
