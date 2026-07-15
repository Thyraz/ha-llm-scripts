import builtins
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "python_scripts" / "llmtool_calendar_manager.py"

LOCAL_TZ = timezone(timedelta(hours=2))


class FakeDtUtil:
    def __init__(self, now=None):
        self.now_value = now or datetime(2026, 6, 22, 12, 0, 0, tzinfo=LOCAL_TZ)

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
    timedelta = None
    timezone = None


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


def run_helper(
    overrides,
    states=None,
    now=None,
    datetime_module=None,
    restricted_builtins=None,
    support_domain_arg=True,
):
    data = {
        "mode": "prepare",
        "operation": "list_upcoming",
        "calendar_entity_ids": "calendar.family",
        "keyword": "",
        "start_time": "",
        "end_time": "",
        "days_ahead": "",
        "limit": "",
        "event_type": "",
        "verbosity": "",
    }
    data.update(overrides)

    output = {}
    exec(
        SCRIPT.read_text(),
        {
            "data": data,
            "output": output,
            "hass": FakeHass(states=states, support_domain_arg=support_domain_arg),
            "dt_util": FakeDtUtil(now=now),
            "datetime": datetime_module or __import__("datetime"),
            "__builtins__": restricted_builtins or builtins.__dict__,
        },
    )
    return output


def shape_payload(payload, overrides=None, states=None, restricted_builtins=None, datetime_module=None):
    data = {
        "mode": "shape",
        "operation": "list_range",
        "calendar_entity_ids": "calendar.family,calendar.garbage",
        "events_response": payload,
        "keyword": "",
        "start_time": "2026-06-22 00:00:00",
        "end_time": "2026-06-25 00:00:00",
        "days_ahead": "31",
        "limit": "100",
        "event_type": "all",
        "verbosity": "compact",
    }
    if overrides:
        data.update(overrides)
    return run_helper(
        data,
        states=states,
        restricted_builtins=restricted_builtins,
        datetime_module=datetime_module,
    )


def event(summary, start, end, description="", location="", all_day=None):
    payload = {
        "summary": summary,
        "start": start,
        "end": end,
    }
    if description:
        payload["description"] = description
    if location:
        payload["location"] = location
    if all_day is not None:
        payload["all_day"] = all_day
    return payload


class CalendarManagerHelperTest(unittest.TestCase):
    def test_prepare_discovers_all_calendar_entities_and_defaults(self):
        states = {
            "calendar.garbage": FakeState({"friendly_name": "Garbage"}),
            "calendar.family": FakeState({"friendly_name": "Family"}),
            "light.kitchen": FakeState(),
        }

        result = run_helper(
            {"calendar_entity_ids": "", "operation": "list_upcoming"},
            states=states,
            support_domain_arg=False,
        )

        self.assertTrue(result["success"])
        self.assertEqual(["calendar.family", "calendar.garbage"], result["data"]["calendar_entity_ids"])
        self.assertEqual("2026-06-22 12:00:00", result["data"]["start_time"])
        self.assertEqual("2026-07-23 12:00:00", result["data"]["end_time"])
        self.assertEqual(31, result["data"]["days_ahead"])
        self.assertEqual(100, result["data"]["limit"])
        self.assertEqual("all", result["data"]["event_type"])
        self.assertEqual("compact", result["data"]["verbosity"])

    def test_prepare_validation_errors(self):
        states = {"calendar.family": FakeState()}

        invalid_operation = run_helper({"operation": "list"}, states=states)
        invalid_calendar = run_helper({"calendar_entity_ids": "sensor.bad"}, states=states)
        unknown_calendar = run_helper({"calendar_entity_ids": "calendar.unknown"}, states=states)
        no_calendars = run_helper({"calendar_entity_ids": ""}, states={})
        missing_keyword = run_helper({"operation": "search_events", "keyword": ""}, states=states)
        missing_range = run_helper({"operation": "list_range", "start_time": "", "end_time": ""}, states=states)
        invalid_start = run_helper(
            {"operation": "list_range", "start_time": "2026-06-22T00:00:00", "end_time": "2026-06-23 00:00:00"},
            states=states,
        )
        reversed_range = run_helper(
            {"operation": "list_range", "start_time": "2026-06-23 00:00:00", "end_time": "2026-06-22 00:00:00"},
            states=states,
        )
        too_long_range = run_helper(
            {"operation": "list_range", "start_time": "2026-01-01 00:00:00", "end_time": "2027-01-02 00:00:00"},
            states=states,
        )
        invalid_days = run_helper({"days_ahead": "366"}, states=states)
        invalid_limit = run_helper({"limit": "1001"}, states=states)
        invalid_event_type = run_helper({"event_type": "holiday"}, states=states)
        invalid_verbosity = run_helper({"verbosity": "full"}, states=states)

        self.assertFalse(invalid_operation["success"])
        self.assertIn("search_events", invalid_operation["data"]["known_operations"])
        self.assertFalse(invalid_calendar["success"])
        self.assertEqual(["sensor.bad"], invalid_calendar["data"]["invalid_calendar_entity_ids"])
        self.assertFalse(unknown_calendar["success"])
        self.assertEqual(["calendar.unknown"], unknown_calendar["data"]["unknown_calendar_entity_ids"])
        self.assertFalse(no_calendars["success"])
        self.assertFalse(missing_keyword["success"])
        self.assertFalse(missing_range["success"])
        self.assertFalse(invalid_start["success"])
        self.assertEqual("YYYY-MM-DD HH:MM:SS", invalid_start["data"]["expected_format"])
        self.assertFalse(reversed_range["success"])
        self.assertIn("after start_time", reversed_range["error"])
        self.assertFalse(too_long_range["success"])
        self.assertEqual(365, too_long_range["data"]["max_time_range_days"])
        self.assertEqual(366, too_long_range["data"]["requested_time_range_days"])
        self.assertFalse(invalid_days["success"])
        self.assertEqual("Calendar Manager Time Range too long. Use 365 days or less.", invalid_days["error"])
        self.assertEqual(366, invalid_days["data"]["requested_time_range_days"])
        self.assertFalse(invalid_limit["success"])
        self.assertFalse(invalid_event_type["success"])
        self.assertFalse(invalid_verbosity["success"])

    def test_prepare_rejects_parameters_outside_operation_contract(self):
        states = {"calendar.family": FakeState()}

        list_range_keyword = run_helper(
            {
                "operation": "list_range",
                "keyword": "dentist",
                "start_time": "2026-06-22 00:00:00",
                "end_time": "2026-06-23 00:00:00",
            },
            states=states,
        )
        list_range_days_ahead = run_helper(
            {
                "operation": "list_range",
                "days_ahead": "10",
                "start_time": "2026-06-22 00:00:00",
                "end_time": "2026-06-23 00:00:00",
            },
            states=states,
        )
        list_upcoming_range = run_helper(
            {
                "operation": "list_upcoming",
                "start_time": "2026-06-22 00:00:00",
                "end_time": "2026-06-23 00:00:00",
            },
            states=states,
        )

        self.assertFalse(list_range_keyword["success"])
        self.assertEqual(["keyword"], list_range_keyword["data"]["invalid_parameters"])
        self.assertIn("start_time", list_range_keyword["data"]["allowed_parameters"])
        self.assertFalse(list_range_days_ahead["success"])
        self.assertEqual(["days_ahead"], list_range_days_ahead["data"]["invalid_parameters"])
        self.assertFalse(list_upcoming_range["success"])
        self.assertEqual(["start_time", "end_time"], list_upcoming_range["data"]["invalid_parameters"])

    def test_prepare_search_requires_and_accepts_explicit_range(self):
        states = {"calendar.family": FakeState()}

        missing_start = run_helper(
            {
                "operation": "search_events",
                "keyword": "dentist",
                "end_time": "2026-06-24 00:00:00",
            },
            states=states,
        )
        missing_end = run_helper(
            {
                "operation": "search_events",
                "keyword": "dentist",
                "start_time": "2026-06-23 00:00:00",
            },
            states=states,
        )
        invalid_days_ahead = run_helper(
            {
                "operation": "search_events",
                "keyword": "dentist",
                "start_time": "2026-06-23 00:00:00",
                "end_time": "2026-06-24 00:00:00",
                "days_ahead": "10",
            },
            states=states,
        )
        explicit = run_helper(
            {
                "operation": "search_events",
                "keyword": "dentist",
                "start_time": "2026-06-23 00:00:00",
                "end_time": "2026-06-24 00:00:00",
            },
            states=states,
        )

        self.assertFalse(missing_start["success"])
        self.assertIn("Calendar Manager Time Range", missing_start["error"])
        self.assertFalse(missing_end["success"])
        self.assertIn("Calendar Manager Time Range", missing_end["error"])
        self.assertFalse(invalid_days_ahead["success"])
        self.assertEqual(["days_ahead"], invalid_days_ahead["data"]["invalid_parameters"])
        self.assertTrue(explicit["success"])
        self.assertEqual("2026-06-23 00:00:00", explicit["data"]["start_time"])
        self.assertEqual("2026-06-24 00:00:00", explicit["data"]["end_time"])
        self.assertEqual("", explicit["data"]["days_ahead"])
        self.assertNotIn("days_ahead", explicit["meta"])

    def test_prepare_accepts_exact_365_day_range(self):
        states = {"calendar.family": FakeState()}

        result = run_helper(
            {
                "operation": "list_range",
                "start_time": "2026-01-01 00:00:00",
                "end_time": "2027-01-01 00:00:00",
            },
            states=states,
        )

        self.assertTrue(result["success"])

    def test_shape_groups_timed_and_all_day_events(self):
        states = {
            "calendar.family": FakeState({"friendly_name": "Family"}),
            "calendar.garbage": FakeState({"friendly_name": "Garbage"}),
        }
        payload = {
            "calendar.family": {
                "events": [
                    event(
                        "Dentist",
                        "2026-06-24T12:00:00+00:00",
                        "2026-06-24T13:00:00+00:00",
                        description="Teeth",
                        location="Town",
                    )
                ]
            },
            "calendar.garbage": {
                "events": [
                    event("Paper collection", "2026-06-23", "2026-06-24"),
                ]
            },
        }

        result = shape_payload(payload, states=states)

        self.assertTrue(result["success"])
        self.assertEqual("Found 2 calendar events.", result["answer"])
        self.assertEqual(2, result["meta"]["count"])
        self.assertEqual(2, result["meta"]["total"])
        self.assertEqual(["calendar.family", "calendar.garbage"], result["meta"]["calendar_entity_ids"])
        self.assertEqual(
            ["calendar.family", "calendar.garbage"],
            [item["calendar_entity_id"] for item in result["data"]["calendars"]],
        )
        family_event = result["data"]["calendars"][0]["events"][0]
        garbage_event = result["data"]["calendars"][1]["events"][0]
        self.assertEqual("timed", family_event["event_type"])
        self.assertEqual("2026-06-24 14:00:00", family_event["start"])
        self.assertEqual("2026-06-24 15:00:00", family_event["end"])
        self.assertEqual("Town", family_event["location"])
        self.assertNotIn("description", family_event)
        self.assertEqual("all_day", garbage_event["event_type"])
        self.assertEqual("2026-06-23 00:00:00", garbage_event["start"])
        self.assertEqual("2026-06-23 23:59:59", garbage_event["end"])

    def test_shape_keyword_detailed_description_cap(self):
        states = {"calendar.family": FakeState({"friendly_name": "Family"})}
        long_description = "Dentist " + ("x" * 1100)
        payload = {
            "calendar.family": {
                "events": [
                    event(
                        "Checkup",
                        "2026-06-24T12:00:00+00:00",
                        "2026-06-24T13:00:00+00:00",
                        description=long_description,
                        location="Town",
                    ),
                    event(
                        "Other",
                        "2026-06-24T14:00:00+00:00",
                        "2026-06-24T15:00:00+00:00",
                        description="No match",
                    ),
                ]
            },
        }

        result = shape_payload(
            payload,
            overrides={
                "operation": "search_events",
                "calendar_entity_ids": "calendar.family",
                "keyword": "dentist",
                "verbosity": "detailed",
            },
            states=states,
        )

        self.assertTrue(result["success"])
        self.assertEqual(1, result["meta"]["count"])
        shaped = result["data"]["calendars"][0]["events"][0]
        self.assertEqual(1000, len(shaped["description"]))
        self.assertTrue(shaped["description_truncated"])

    def test_shape_event_type_filter_and_global_truncation(self):
        states = {
            "calendar.family": FakeState(),
            "calendar.garbage": FakeState(),
        }
        payload = {
            "calendar.family": {
                "events": [
                    event("Late timed", "2026-06-24T14:00:00+00:00", "2026-06-24T15:00:00+00:00"),
                    event("Early timed", "2026-06-23T08:00:00+00:00", "2026-06-23T09:00:00+00:00"),
                ]
            },
            "calendar.garbage": {
                "events": [
                    event("All day", "2026-06-23", "2026-06-24"),
                    event("Middle timed", "2026-06-23T12:00:00+00:00", "2026-06-23T13:00:00+00:00"),
                ]
            },
        }

        timed = shape_payload(payload, overrides={"event_type": "timed", "limit": "2"}, states=states)
        all_day = shape_payload(payload, overrides={"event_type": "all_day"}, states=states)

        self.assertTrue(timed["success"])
        self.assertEqual(2, timed["meta"]["count"])
        self.assertEqual(3, timed["meta"]["total"])
        self.assertTrue(timed["meta"]["truncated"])
        self.assertIn("Attention: returned data is truncated", timed["answer"])
        self.assertEqual(2, timed["data"]["truncation"]["count_returned"])
        self.assertEqual(3, timed["data"]["truncation"]["count_total_before_truncation"])
        self.assertEqual(1, timed["data"]["truncation"]["by_calendar_entity_id"]["calendar.family"]["count_returned"])
        self.assertEqual(
            2,
            timed["data"]["truncation"]["by_calendar_entity_id"]["calendar.family"]["count_total_before_truncation"],
        )
        returned_titles = []
        for calendar in timed["data"]["calendars"]:
            for shaped_event in calendar["events"]:
                returned_titles.append(shaped_event["title"])
        self.assertEqual(["Early timed", "Middle timed"], sorted(returned_titles))
        self.assertTrue(all_day["success"])
        self.assertEqual(1, all_day["meta"]["count"])
        self.assertEqual("All day", all_day["data"]["calendars"][0]["events"][0]["title"])

    def test_shape_includes_overlapping_events_and_empty_success(self):
        states = {"calendar.family": FakeState()}
        payload = {
            "calendar.family": {
                "events": [
                    event("Ongoing", "2026-06-21T23:00:00+00:00", "2026-06-22T01:00:00+00:00"),
                    event("Outside", "2026-06-25T00:00:00+00:00", "2026-06-25T01:00:00+00:00"),
                ]
            },
        }

        overlapping = shape_payload(
            payload,
            overrides={
                "calendar_entity_ids": "calendar.family",
                "start_time": "2026-06-22 00:00:00",
                "end_time": "2026-06-22 04:00:00",
            },
            states=states,
        )
        empty = shape_payload(
            payload,
            overrides={
                "calendar_entity_ids": "calendar.family",
                "operation": "search_events",
                "keyword": "missing",
            },
            states=states,
        )

        self.assertTrue(overlapping["success"])
        self.assertEqual(["Ongoing"], [item["title"] for item in overlapping["data"]["calendars"][0]["events"]])
        self.assertTrue(empty["success"])
        self.assertEqual("Found 0 calendar events.", empty["answer"])
        self.assertEqual([], empty["data"]["calendars"])

    def test_shape_invalid_response_shape_returns_soft_failure(self):
        missing_calendar = shape_payload({"calendar.family": {"events": []}}, states={"calendar.family": FakeState()})
        events_string = shape_payload(
            {
                "calendar.family": {"events": "bad"},
                "calendar.garbage": {"events": []},
            },
            states={"calendar.family": FakeState(), "calendar.garbage": FakeState()},
        )
        bad_row = shape_payload(
            {
                "calendar.family": {"events": [{"summary": "Bad"}]},
                "calendar.garbage": {"events": []},
            },
            states={"calendar.family": FakeState(), "calendar.garbage": FakeState()},
        )

        self.assertFalse(missing_calendar["success"])
        self.assertFalse(events_string["success"])
        self.assertFalse(bad_row["success"])

    def test_restricted_runtime_without_imports_or_datetime_format_helpers(self):
        restricted = builtins.__dict__.copy()
        restricted.pop("__import__", None)
        restricted.pop("dict", None)
        restricted.pop("list", None)

        states = {"calendar.family": FakeState()}
        payload = {
            "calendar.family": {
                "events": [
                    event("All day", "2026-06-23", "2026-06-24"),
                ]
            }
        }

        result = shape_payload(
            payload,
            overrides={"calendar_entity_ids": "calendar.family"},
            states=states,
            restricted_builtins=restricted,
            datetime_module=GuardedDateTimeModule(),
        )

        self.assertTrue(result["success"])
        self.assertEqual("2026-06-23 23:59:59", result["data"]["calendars"][0]["events"][0]["end"])


if __name__ == "__main__":
    unittest.main()
