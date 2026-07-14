import builtins
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "python_scripts" / "llmtool_date_calculator.py"

LOCAL_TZ = timezone(timedelta(hours=2))


class FakeDtUtil:
    def __init__(self, now=None):
        self.now_value = now or datetime(2026, 6, 21, 12, 0, 0, tzinfo=LOCAL_TZ)

    def now(self):
        return self.now_value

    def as_utc(self, value):
        if value.tzinfo is None:
            value = value.replace(tzinfo=LOCAL_TZ)
        return value.astimezone(timezone.utc)

    def as_local(self, value):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(LOCAL_TZ)

    def as_timestamp(self, value):
        return value.timestamp()

    def utc_from_timestamp(self, value):
        return datetime.fromtimestamp(value, tz=timezone.utc)


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


def restricted_range(*args):
    result = range(*args)
    if len(result) > 1000:
        raise ValueError(
            "To be created range() object would be to large, in RestrictedPython we only allow 1000 elements in a range."
        )
    return result


def run_helper(overrides, now=None, datetime_module=None, restricted_builtins=None):
    data = {
        "operation": "weekday_for_date",
        "date": "",
        "date2": "",
        "segments": "",
        "weekday": "",
        "month": "",
        "day_of_month": "",
        "hour": "",
        "minute": "",
        "second": "",
        "epoch_time_s": "",
        "limit": "",
    }
    data.update(overrides)

    output = {}
    exec(
        SCRIPT.read_text(),
        {
            "data": data,
            "output": output,
            "dt_util": FakeDtUtil(now=now),
            "datetime": datetime_module or __import__("datetime"),
            "__builtins__": restricted_builtins or builtins.__dict__,
        },
    )
    return output


class DateCalculatorHelperTest(unittest.TestCase):
    def test_weekday_for_date(self):
        result = run_helper({"operation": "weekday_for_date", "date": "2026-06-21 09:30:00"})

        self.assertTrue(result["success"])
        self.assertEqual("Sunday", result["data"]["weekday"])
        self.assertEqual("2026-06-21 09:30:00", result["data"]["date"])
        self.assertEqual("weekday_for_date", result["meta"]["operation"])

    def test_invalid_operation_returns_known_operations(self):
        result = run_helper({"operation": "weekday", "date": "2026-06-21 09:30:00"})

        self.assertFalse(result["success"])
        self.assertIn("weekday_for_date", result["data"]["known_operations"])

    def test_operation_contract_rejects_extra_parameters(self):
        weekday_extra = run_helper(
            {
                "operation": "weekday_for_date",
                "date": "2026-06-21 09:30:00",
                "segments": "days=1",
            }
        )
        epoch_extra = run_helper(
            {
                "operation": "epoch_to_date",
                "epoch_time_s": "0",
                "date": "1970-01-01 02:00:00",
            }
        )
        next_match_extra = run_helper(
            {
                "operation": "next_matching_date",
                "weekday": "Monday",
                "limit": "10",
            }
        )

        self.assertFalse(weekday_extra["success"])
        self.assertEqual(["segments"], weekday_extra["data"]["invalid_parameters"])
        self.assertIn("date", weekday_extra["data"]["allowed_parameters"])
        self.assertFalse(epoch_extra["success"])
        self.assertEqual(["date"], epoch_extra["data"]["invalid_parameters"])
        self.assertFalse(next_match_extra["success"])
        self.assertEqual(["limit"], next_match_extra["data"]["invalid_parameters"])

    def test_rejects_invalid_date_formats(self):
        iso = run_helper({"operation": "weekday_for_date", "date": "2026-06-21T09:30:00"})
        date_only = run_helper({"operation": "weekday_for_date", "date": "2026-06-21"})
        timezone_suffix = run_helper({"operation": "weekday_for_date", "date": "2026-06-21 09:30:00+02:00"})

        self.assertFalse(iso["success"])
        self.assertFalse(date_only["success"])
        self.assertFalse(timezone_suffix["success"])
        self.assertEqual("YYYY-MM-DD HH:MM:SS", iso["data"]["expected_format"])

    def test_date_by_adding_segments_clamps_month_and_year(self):
        month_result = run_helper(
            {
                "operation": "date_by_adding_segments",
                "date": "2025-01-31 10:00:00",
                "segments": "months=1",
            }
        )
        year_result = run_helper(
            {
                "operation": "date_by_adding_segments",
                "date": "2024-02-29 10:00:00",
                "segments": "years=1",
            }
        )

        self.assertTrue(month_result["success"])
        self.assertEqual("2025-02-28 10:00:00", month_result["data"]["new_date"])
        self.assertEqual("Friday", month_result["data"]["weekday"])
        self.assertEqual("2025-02-28 10:00:00", year_result["data"]["new_date"])

    def test_date_by_adding_segments_handles_negative_time_segments(self):
        result = run_helper(
            {
                "operation": "date_by_adding_segments",
                "date": "2025-03-01 00:00:30",
                "segments": "seconds=-31",
            }
        )

        self.assertTrue(result["success"])
        self.assertEqual("2025-02-28 23:59:59", result["data"]["new_date"])

    def test_segment_validation_errors(self):
        base = {"operation": "date_by_adding_segments", "date": "2025-01-31 10:00:00"}
        missing = run_helper({**base, "segments": ""})
        unknown = run_helper({**base, "segments": "fortnights=1"})
        invalid = run_helper({**base, "segments": "days=1.5"})

        self.assertFalse(missing["success"])
        self.assertFalse(unknown["success"])
        self.assertEqual(["fortnights"], unknown["data"]["unknown_segment_keys"])
        self.assertFalse(invalid["success"])
        self.assertEqual([{"key": "days", "value": "1.5"}], invalid["data"]["invalid_segments"])

    def test_epoch_conversion_uses_local_time(self):
        date_to_epoch = run_helper(
            {"operation": "date_to_epoch", "date": "1970-01-01 02:00:00"}
        )
        epoch_to_date = run_helper({"operation": "epoch_to_date", "epoch_time_s": "0"})

        self.assertTrue(date_to_epoch["success"])
        self.assertEqual(0, date_to_epoch["data"]["epoch_time_s"])
        self.assertTrue(epoch_to_date["success"])
        self.assertEqual("1970-01-01 02:00:00", epoch_to_date["data"]["date"])
        self.assertEqual("Thursday", epoch_to_date["data"]["weekday"])

    def test_duration_between_dates_shapes_scalar_and_segments(self):
        result = run_helper(
            {
                "operation": "duration_between_dates",
                "date": "2025-01-01 00:00:00",
                "date2": "2026-03-15 01:02:03",
            }
        )
        negative = run_helper(
            {
                "operation": "duration_between_dates",
                "date": "2026-03-15 01:02:03",
                "date2": "2025-01-01 00:00:00",
            }
        )

        self.assertTrue(result["success"])
        self.assertEqual(37846923, result["data"]["duration"]["seconds"])
        self.assertAlmostEqual(62.57758432539683, result["data"]["duration"]["weeks"])
        self.assertEqual(
            {
                "sign": "+",
                "years": 1,
                "months": 2,
                "weeks": 2,
                "days": 0,
                "hours": 1,
                "minutes": 2,
                "seconds": 3,
            },
            result["data"]["duration_in_segments"],
        )
        self.assertEqual("-", negative["data"]["duration_in_segments"]["sign"])
        self.assertEqual(-37846923, negative["data"]["duration"]["seconds"])

    def test_next_matching_date_finds_weekday_and_skips_past_time_today(self):
        today_future = run_helper(
            {
                "operation": "next_matching_date",
                "date": "2026-06-21 15:00:00",
                "weekday": "Sunday",
                "hour": "16",
            }
        )
        today_past = run_helper(
            {
                "operation": "next_matching_date",
                "date": "2026-06-21 15:00:00",
                "weekday": "Sunday",
                "hour": "10",
            }
        )

        self.assertEqual("2026-06-21 16:00:00", today_future["data"]["date"])
        self.assertEqual(0, today_future["data"]["days_from_anchor"])
        self.assertEqual("2026-06-28 10:00:00", today_past["data"]["date"])
        self.assertEqual(7, today_past["data"]["days_from_anchor"])

    def test_next_matching_date_defaults_anchor_to_now(self):
        result = run_helper(
            {
                "operation": "next_matching_date",
                "date": "",
                "weekday": "Saturday",
            }
        )

        self.assertTrue(result["success"])
        self.assertEqual("2026-06-27 00:00:00", result["data"]["date"])
        self.assertEqual(6, result["data"]["days_from_anchor"])
        self.assertTrue(result["meta"]["date_was_defaulted"])

    def test_next_matching_date_finds_day_month_and_leap_day(self):
        birthday = run_helper(
            {
                "operation": "next_matching_date",
                "date": "2026-06-21 15:00:00",
                "month": "6",
                "day_of_month": "5",
            }
        )
        leap_day = run_helper(
            {
                "operation": "next_matching_date",
                "date": "2026-06-21 15:00:00",
                "month": "2",
                "day_of_month": "29",
            }
        )

        self.assertEqual("2027-06-05 00:00:00", birthday["data"]["date"])
        self.assertEqual({"month": 6, "day_of_month": 5, "hour": 0, "minute": 0, "second": 0}, birthday["data"]["matched_parts"])
        self.assertEqual("2028-02-29 00:00:00", leap_day["data"]["date"])
        self.assertEqual("Tuesday", leap_day["data"]["weekday"])

    def test_next_matching_date_finds_combined_weekday_and_day(self):
        friday_13 = run_helper(
            {
                "operation": "next_matching_date",
                "date": "2026-06-21 15:00:00",
                "weekday": "Friday",
                "day_of_month": "13",
            }
        )
        december_tuesday = run_helper(
            {
                "operation": "next_matching_date",
                "date": "2026-06-21 15:00:00",
                "month": "12",
                "weekday": "Tuesday",
            }
        )

        self.assertEqual("2026-11-13 00:00:00", friday_13["data"]["date"])
        self.assertEqual("Friday", friday_13["data"]["weekday"])
        self.assertEqual("2026-12-01 00:00:00", december_tuesday["data"]["date"])
        self.assertEqual("Tuesday", december_tuesday["data"]["weekday"])

    def test_list_calendar_days_inclusive_and_truncated(self):
        result = run_helper(
            {
                "operation": "list_calendar_days",
                "date": "2026-06-20 10:00:00",
                "date2": "2026-06-22 09:00:00",
                "limit": "2",
            }
        )

        self.assertTrue(result["success"])
        self.assertEqual(
            [
                {"date": "2026-06-20", "weekday": "Saturday"},
                {"date": "2026-06-21", "weekday": "Sunday"},
            ],
            result["data"]["days"],
        )
        self.assertEqual(2, result["meta"]["count"])
        self.assertEqual(3, result["meta"]["total"])
        self.assertTrue(result["meta"]["truncated"])

    def test_list_calendar_days_rejects_reversed_range(self):
        result = run_helper(
            {
                "operation": "list_calendar_days",
                "date": "2026-06-22 09:00:00",
                "date2": "2026-06-20 10:00:00",
            }
        )

        self.assertFalse(result["success"])
        self.assertIn("after or equal", result["error"])

    def test_scalar_validation_errors(self):
        weekday = run_helper(
            {"operation": "next_matching_date", "weekday": "Funday"}
        )
        month = run_helper(
            {"operation": "next_matching_date", "month": "13", "day_of_month": "1"}
        )
        day = run_helper(
            {"operation": "next_matching_date", "day_of_month": "32"}
        )
        hour = run_helper(
            {"operation": "next_matching_date", "weekday": "Monday", "hour": "24"}
        )
        too_vague = run_helper(
            {"operation": "next_matching_date", "month": "12"}
        )
        epoch = run_helper({"operation": "epoch_to_date", "epoch_time_s": "1.5"})
        limit = run_helper(
            {
                "operation": "list_calendar_days",
                "date": "2026-06-20 10:00:00",
                "date2": "2026-06-22 09:00:00",
                "limit": "3661",
            }
        )

        self.assertFalse(weekday["success"])
        self.assertIn("Monday", weekday["data"]["known_weekdays"])
        self.assertFalse(month["success"])
        self.assertFalse(day["success"])
        self.assertFalse(hour["success"])
        self.assertFalse(too_vague["success"])
        self.assertFalse(epoch["success"])
        self.assertFalse(limit["success"])

    def test_restricted_runtime_without_imports_or_datetime_format_helpers(self):
        restricted = builtins.__dict__.copy()
        restricted.pop("__import__", None)
        restricted.pop("dict", None)
        restricted.pop("list", None)

        result = run_helper(
            {
                "operation": "date_by_adding_segments",
                "date": "2025-01-31 10:00:00",
                "segments": "months=1,seconds=1",
            },
            datetime_module=GuardedDateTimeModule(),
            restricted_builtins=restricted,
        )

        self.assertTrue(result["success"])
        self.assertEqual("2025-02-28 10:00:01", result["data"]["new_date"])

    def test_restricted_runtime_does_not_create_large_ranges(self):
        restricted = builtins.__dict__.copy()
        restricted["range"] = restricted_range

        next_day_29 = run_helper(
            {
                "operation": "next_matching_date",
                "date": "",
                "day_of_month": "29",
            },
            restricted_builtins=restricted,
        )
        long_list = run_helper(
            {
                "operation": "list_calendar_days",
                "date": "2026-01-01 00:00:00",
                "date2": "2029-12-31 00:00:00",
                "limit": "1100",
            },
            restricted_builtins=restricted,
        )

        self.assertTrue(next_day_29["success"])
        self.assertEqual("2026-06-29 00:00:00", next_day_29["data"]["date"])
        self.assertTrue(long_list["success"])
        self.assertEqual(1100, len(long_list["data"]["days"]))


if __name__ == "__main__":
    unittest.main()
