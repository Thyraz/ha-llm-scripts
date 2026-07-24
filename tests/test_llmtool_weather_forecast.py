import builtins
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "python_scripts" / "llmtool_weather_forecast.py"
LOCAL_TZ = timezone(timedelta(hours=2))


class FakeDtUtil:
    def parse_datetime(self, value):
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def as_local(self, value):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(LOCAL_TZ)


class FakeState:
    def __init__(self, attributes=None):
        self.attributes = attributes or {}


class FakeStates:
    def __init__(self, states=None, support_domain_arg=True):
        self.states = states or {}
        self.support_domain_arg = support_domain_arg

    def entity_ids(self, domain=None):
        if domain is not None and not self.support_domain_arg:
            raise TypeError("domain arg unsupported")
        if domain is None:
            return list(self.states.keys())
        return [entity_id for entity_id in self.states if entity_id.startswith(domain + ".")]

    def get(self, entity_id):
        return self.states.get(entity_id)


class FakeHass:
    def __init__(self, states=None, support_domain_arg=True):
        self.states = FakeStates(states=states, support_domain_arg=support_domain_arg)


def run_helper(overrides, states=None, restricted_builtins=None, support_domain_arg=True):
    data = {
        "mode": "prepare",
        "weather_entity_id": "weather.home",
        "forecast_type": "daily",
        "start_time": "2026-07-25 00:00:00",
        "end_time": "2026-07-27 00:00:00",
        "verbosity": "",
        "limit": "",
    }
    data.update(overrides)
    if states is None:
        states = {
            "weather.home": FakeState(
                {
                    "friendly_name": "Home",
                    "temperature_unit": "C",
                    "precipitation_unit": "mm",
                    "pressure_unit": "hPa",
                    "wind_speed_unit": "km/h",
                }
            )
        }
    output = {}
    exec(
        SCRIPT.read_text(),
        {
            "data": data,
            "output": output,
            "hass": FakeHass(states=states, support_domain_arg=support_domain_arg),
            "dt_util": FakeDtUtil(),
            "datetime": __import__("datetime"),
            "__builtins__": restricted_builtins or builtins.__dict__,
        },
    )
    return output


def shape_payload(prepared, forecast_rows, response_key="weather.home", states=None, restricted_builtins=None):
    return run_helper(
        {
            "mode": "shape",
            "prepared": prepared,
            "weather_response": {
                response_key: {
                    "forecast": forecast_rows,
                }
            },
        },
        states=states,
        restricted_builtins=restricted_builtins,
    )


def row(datetime_value, **values):
    result = {"datetime": datetime_value}
    result.update(values)
    return result


class WeatherForecastHelperTest(unittest.TestCase):
    def test_prepare_defaults_and_units(self):
        result = run_helper({})

        self.assertTrue(result["success"])
        self.assertEqual("overview", result["data"]["verbosity"])
        self.assertEqual(24, result["data"]["limit"])
        self.assertEqual("C", result["data"]["units"]["temperature_unit"])
        self.assertEqual("km/h", result["data"]["units"]["wind_speed_unit"])

    def test_prepare_weather_entity_validation_with_available_ids(self):
        states = {
            "weather.home": FakeState(),
            "weather.outside": FakeState(),
            "sensor.temperature": FakeState(),
        }

        missing = run_helper({"weather_entity_id": ""}, states=states, support_domain_arg=False)
        invalid = run_helper({"weather_entity_id": "sensor.temperature"}, states=states)
        unknown = run_helper({"weather_entity_id": "weather.garden"}, states=states)

        self.assertFalse(missing["success"])
        self.assertEqual(["weather.home", "weather.outside"], missing["data"]["available_weather_entity_ids"])
        self.assertFalse(invalid["success"])
        self.assertEqual("sensor.temperature", invalid["data"]["invalid_weather_entity_id"])
        self.assertFalse(unknown["success"])
        self.assertEqual("weather.garden", unknown["data"]["unknown_weather_entity_id"])

    def test_prepare_validates_forecast_type_verbosity_time_range_and_limit(self):
        missing_type = run_helper({"forecast_type": ""})
        invalid_type = run_helper({"forecast_type": "twice_daily"})
        invalid_verbosity = run_helper({"verbosity": "compact"})
        invalid_time = run_helper({"start_time": "2026-07-25T00:00:00"})
        reversed_range = run_helper({"end_time": "2026-07-25 00:00:00"})
        partial_daily = run_helper({"start_time": "2026-07-25 06:00:00"})
        invalid_limit = run_helper({"limit": "169"})

        self.assertFalse(missing_type["success"])
        self.assertIn("forecast_type", missing_type["error"])
        self.assertFalse(invalid_type["success"])
        self.assertIn("hourly", invalid_type["data"]["known_forecast_types"])
        self.assertFalse(invalid_verbosity["success"])
        self.assertIn("overview", invalid_verbosity["data"]["known_verbosity"])
        self.assertFalse(invalid_time["success"])
        self.assertEqual("YYYY-MM-DD HH:MM:SS", invalid_time["data"]["expected_format"])
        self.assertFalse(reversed_range["success"])
        self.assertIn("after start_time", reversed_range["error"])
        self.assertFalse(partial_daily["success"])
        self.assertIn("00:00:00", partial_daily["error"])
        self.assertFalse(invalid_limit["success"])

    def test_shape_daily_overview_adds_weekday_and_significant_precipitation_only(self):
        prepared = run_helper({})["data"]
        result = shape_payload(
            prepared,
            [
                row(
                    "2026-07-25T00:00:00+02:00",
                    condition="rainy",
                    temperature=22,
                    templow=16,
                    precipitation=0,
                    precipitation_probability=0,
                    pressure=1012,
                    humidity=90,
                ),
                row(
                    "2026-07-26T00:00:00+02:00",
                    condition="partlycloudy",
                    temperature=24,
                    templow=17,
                    precipitation=0.05,
                    precipitation_probability=20,
                    wind_speed=10,
                    wind_bearing=180,
                ),
            ],
        )

        self.assertTrue(result["success"])
        self.assertEqual("Found 2 forecast days.", result["answer"])
        first = result["data"]["days"][0]
        second = result["data"]["days"][1]
        self.assertEqual("Saturday", first["weekday"])
        self.assertEqual("rainy", first["condition"])
        self.assertEqual(0, first["precipitation"])
        self.assertEqual(0, first["precipitation_probability"])
        self.assertNotIn("pressure", first)
        self.assertNotIn("humidity", first)
        self.assertEqual("Sunday", second["weekday"])
        self.assertNotIn("precipitation", second)
        self.assertNotIn("wind_speed", second)
        self.assertNotIn("wind_bearing", second)

    def test_shape_hourly_overview_groups_days_and_reports_significant_wind(self):
        prepared = run_helper(
            {
                "forecast_type": "hourly",
                "start_time": "2026-07-24 21:00:00",
                "end_time": "2026-07-25 03:00:00",
            },
            states={
                "weather.home": FakeState({"wind_speed_unit": "mph"}),
            },
        )["data"]
        result = shape_payload(
            prepared,
            [
                row("2026-07-24T19:00:00+00:00", condition="cloudy", temperature=20, wind_speed=10),
                row("2026-07-24T20:00:00+00:00", condition="cloudy", temperature=19, wind_speed=20, wind_bearing="SW"),
                row("2026-07-24T21:00:00+00:00", condition="windy", temperature=18, wind_speed=5, wind_bearing=240),
                row("2026-07-25T00:00:00+00:00", condition="cloudy", temperature=17),
            ],
        )

        self.assertTrue(result["success"])
        self.assertEqual(4, result["meta"]["count"])
        self.assertEqual(["2026-07-24", "2026-07-25"], [day["date"] for day in result["data"]["days"]])
        self.assertEqual("Friday", result["data"]["days"][0]["weekday"])
        first_day_periods = result["data"]["days"][0]["periods"]
        self.assertNotIn("wind_speed", first_day_periods[0])
        self.assertEqual(20, first_day_periods[1]["wind_speed"])
        self.assertEqual("SW", first_day_periods[1]["wind_bearing"])
        self.assertEqual(5, first_day_periods[2]["wind_speed"])
        self.assertEqual(240, first_day_periods[2]["wind_bearing"])

    def test_shape_detailed_returns_supported_fields_and_omits_unknown(self):
        prepared = run_helper({"verbosity": "detailed"})["data"]
        result = shape_payload(
            prepared,
            [
                row(
                    "2026-07-25",
                    condition="sunny",
                    temperature=23,
                    templow=13,
                    apparent_temperature=25,
                    dew_point=12,
                    humidity=50,
                    cloud_coverage=20,
                    precipitation=0,
                    precipitation_probability=0,
                    pressure=1015,
                    uv_index=6,
                    wind_bearing=90,
                    wind_gust_speed=30,
                    wind_speed=15,
                    is_daytime=True,
                    provider_extra="hidden",
                )
            ],
        )

        self.assertTrue(result["success"])
        day = result["data"]["days"][0]
        self.assertEqual("2026-07-25 00:00:00", day["datetime"])
        self.assertEqual("Saturday", day["weekday"])
        self.assertEqual("00:00:00", day["time"])
        self.assertEqual(25, day["apparent_temperature"])
        self.assertEqual(1015, day["pressure"])
        self.assertTrue(day["is_daytime"])
        self.assertNotIn("provider_extra", day)

    def test_shape_truncates_by_rows_not_days(self):
        prepared = run_helper(
            {
                "forecast_type": "hourly",
                "start_time": "2026-07-24 00:00:00",
                "end_time": "2026-07-25 00:00:00",
                "limit": "2",
            }
        )["data"]
        result = shape_payload(
            prepared,
            [
                row("2026-07-24T00:00:00+02:00", condition="cloudy"),
                row("2026-07-24T01:00:00+02:00", condition="cloudy"),
                row("2026-07-24T02:00:00+02:00", condition="cloudy"),
            ],
        )

        self.assertTrue(result["success"])
        self.assertEqual(2, result["meta"]["count"])
        self.assertEqual(3, result["meta"]["total"])
        self.assertTrue(result["meta"]["truncated"])
        self.assertEqual(2, len(result["data"]["days"][0]["periods"]))
        self.assertEqual(2, result["data"]["truncation"]["count_returned"])
        self.assertIn("Attention: returned data is truncated", result["answer"])

    def test_shape_empty_and_invalid_responses_are_soft_failures(self):
        prepared = run_helper({})["data"]
        empty = shape_payload(prepared, [])
        missing_key = shape_payload(prepared, [], response_key="weather.other")
        string_response = run_helper(
            {
                "mode": "shape",
                "prepared": prepared,
                "weather_response": "not a mapping",
            }
        )
        missing_datetime = shape_payload(prepared, [{"condition": "sunny"}])

        self.assertFalse(empty["success"])
        self.assertIn("No forecast rows", empty["error"])
        self.assertEqual(0, empty["meta"]["total"])
        self.assertFalse(missing_key["success"])
        self.assertIn("keyed by weather entity ID", missing_key["error"])
        self.assertFalse(string_response["success"])
        self.assertIn("helper handoff", string_response["error"])
        self.assertFalse(missing_datetime["success"])
        self.assertIn("datetime", missing_datetime["error"])

    def test_restricted_runtime_does_not_require_iter_or_isinstance_builtins(self):
        restricted = builtins.__dict__.copy()
        restricted.pop("iter", None)
        restricted["isinstance"] = None

        prepared = run_helper({}, restricted_builtins=restricted)["data"]
        result = shape_payload(
            prepared,
            [row("2026-07-25T00:00:00+02:00", condition="sunny", temperature=23)],
            restricted_builtins=restricted,
        )

        self.assertTrue(result["success"])
        self.assertEqual("Saturday", result["data"]["days"][0]["weekday"])


if __name__ == "__main__":
    unittest.main()
