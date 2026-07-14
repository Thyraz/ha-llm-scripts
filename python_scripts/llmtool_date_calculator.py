TOOL_NAME = "llmtool_date_calculator"
TIME_FORMAT = "YYYY-MM-DD HH:MM:SS"
DEFAULT_LIMIT = 366
MAX_LIMIT = 3660

OPERATIONS = [
    "duration_between_dates",
    "date_by_adding_segments",
    "weekday_for_date",
    "next_matching_date",
    "list_calendar_days",
    "epoch_to_date",
    "date_to_epoch",
]

WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

SEGMENT_KEYS = ["years", "months", "days", "hours", "minutes", "seconds"]

PARAMETER_NAMES = [
    "date",
    "date2",
    "segments",
    "month",
    "weekday",
    "day_of_month",
    "hour",
    "minute",
    "second",
    "epoch_time_s",
    "limit",
]

ALLOWLISTS = {
    "duration_between_dates": ["operation", "date", "date2"],
    "date_by_adding_segments": ["operation", "date", "segments"],
    "weekday_for_date": ["operation", "date"],
    "next_matching_date": ["operation", "date", "month", "weekday", "day_of_month", "hour", "minute", "second"],
    "list_calendar_days": ["operation", "date", "date2", "limit"],
    "epoch_to_date": ["operation", "epoch_time_s"],
    "date_to_epoch": ["operation", "date"],
}


# Small helpers keep the top-level python_script flow readable.
def as_text(value):
    if value is None:
        return ""
    return str(value).strip()


def validation_error(message, data_payload=None, meta_payload=None):
    output["success"] = False
    output["error"] = message
    output["data"] = data_payload or {}
    output["meta"] = meta_payload or {"tool": TOOL_NAME, "operation": operation}


def validate_allowlist(operation):
    allowed = ALLOWLISTS.get(operation) or []
    invalid_parameters = []

    for parameter_name in PARAMETER_NAMES:
        if parameter_name not in allowed and as_text(data.get(parameter_name)) != "":
            invalid_parameters.append(parameter_name)

    if invalid_parameters:
        validation_error(
            "Invalid parameters for operation.",
            {
                "operation": operation,
                "invalid_parameters": invalid_parameters,
                "allowed_parameters": allowed,
            },
            {"tool": TOOL_NAME, "operation": operation},
        )


def two_digit(value):
    if value < 10:
        return "0{}".format(value)
    return str(value)


def is_leap_year(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def days_in_month(year, month):
    month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if month == 2 and is_leap_year(year):
        return 29
    return month_days[month - 1]


def days_before_year(year):
    previous_year = year - 1
    return (
        previous_year * 365
        + previous_year // 4
        - previous_year // 100
        + previous_year // 400
    )


def days_before_month(year, month):
    total = 0
    for current_month in range(1, month):
        total = total + days_in_month(year, current_month)
    return total


def day_number(value):
    return days_before_year(value.year) + days_before_month(value.year, value.month) + value.day - 1


def local_seconds(value):
    return (
        day_number(value) * 86400
        + value.hour * 3600
        + value.minute * 60
        + value.second
    )


def date_from_day_number(number):
    if number < 0 or number > day_number(datetime.datetime(9999, 12, 31, 0, 0, 0)):
        return None

    low = 1
    high = 9999
    year = 1
    while low <= high:
        middle = (low + high) // 2
        if days_before_year(middle) <= number:
            year = middle
            low = middle + 1
        else:
            high = middle - 1

    day_of_year = number - days_before_year(year)
    month = 1
    while month <= 12:
        month_length = days_in_month(year, month)
        if day_of_year < month_length:
            return year, month, day_of_year + 1
        day_of_year = day_of_year - month_length
        month = month + 1

    return None


def datetime_from_local_seconds(seconds):
    if seconds < 0:
        return None

    day = seconds // 86400
    remaining = seconds % 86400
    date_parts = date_from_day_number(day)
    if date_parts is None:
        return None

    hour = remaining // 3600
    remaining = remaining % 3600
    minute = remaining // 60
    second = remaining % 60

    try:
        return datetime.datetime(
            date_parts[0],
            date_parts[1],
            date_parts[2],
            hour,
            minute,
            second,
        )
    except ValueError:
        return None


def local_time_text(value):
    return "{}-{}-{} {}:{}:{}".format(
        str(value.year).rjust(4, "0"),
        two_digit(value.month),
        two_digit(value.day),
        two_digit(value.hour),
        two_digit(value.minute),
        two_digit(value.second),
    )


def local_date_text(value):
    return "{}-{}-{}".format(
        str(value.year).rjust(4, "0"),
        two_digit(value.month),
        two_digit(value.day),
    )


def local_text_from_datetime(value):
    local_value = dt_util.as_local(value)
    return local_time_text(local_value)


def local_naive_from_datetime(value):
    local_value = dt_util.as_local(value)
    return datetime.datetime(
        local_value.year,
        local_value.month,
        local_value.day,
        local_value.hour,
        local_value.minute,
        local_value.second,
    )


def has_strict_time_format(value):
    if len(value) != 19:
        return False

    if value[4] != "-" or value[7] != "-" or value[10] != " ":
        return False
    if value[13] != ":" or value[16] != ":":
        return False

    digit_positions = [0, 1, 2, 3, 5, 6, 8, 9, 11, 12, 14, 15, 17, 18]
    for position in digit_positions:
        char = value[position]
        if char < "0" or char > "9":
            return False

    return True


def parse_local_time(value):
    if not has_strict_time_format(value):
        return None

    try:
        return datetime.datetime(
            int(value[0:4]),
            int(value[5:7]),
            int(value[8:10]),
            int(value[11:13]),
            int(value[14:16]),
            int(value[17:19]),
        )
    except ValueError:
        return None


def parse_required_date(value, field_name):
    text = as_text(value)
    if not text:
        validation_error(
            "Missing {}. Use local time in format YYYY-MM-DD HH:MM:SS.".format(field_name),
            {"expected_format": TIME_FORMAT},
        )
        return None

    parsed = parse_local_time(text)
    if parsed is None:
        validation_error(
            "Invalid {}. Use local time in format YYYY-MM-DD HH:MM:SS.".format(field_name),
            {"expected_format": TIME_FORMAT},
        )
        return None

    return parsed


def parse_int_field(value, field_name, min_value=None, max_value=None, required=True):
    text = as_text(value)
    if not text:
        if required:
            validation_error(
                "Missing {}. Use an integer.".format(field_name),
                {"required": field_name},
            )
        return None

    parsed_text = text
    if "." in parsed_text:
        parts = parsed_text.split(".")
        if len(parts) == 2 and parts[1] == "0":
            parsed_text = parts[0]
        else:
            validation_error(
                "Invalid {}. Use an integer.".format(field_name),
                {"field": field_name},
            )
            return None

    if parsed_text == "":
        validation_error(
            "Invalid {}. Use an integer.".format(field_name),
            {"field": field_name},
        )
        return None

    sign = ""
    digits = parsed_text
    if digits[0] == "-":
        sign = "-"
        digits = digits[1:]

    if not digits:
        validation_error(
            "Invalid {}. Use an integer.".format(field_name),
            {"field": field_name},
        )
        return None

    for char in digits:
        if char < "0" or char > "9":
            validation_error(
                "Invalid {}. Use an integer.".format(field_name),
                {"field": field_name},
            )
            return None

    parsed = int(sign + digits)
    if min_value is not None and parsed < min_value:
        validation_error(
            "Invalid {}. Use an integer greater than or equal to {}.".format(field_name, min_value),
            {"min": min_value},
        )
        return None
    if max_value is not None and parsed > max_value:
        validation_error(
            "Invalid {}. Use an integer less than or equal to {}.".format(field_name, max_value),
            {"max": max_value},
        )
        return None

    return parsed


def parse_limit(value):
    limit = parse_int_field(value, "limit", 1, MAX_LIMIT, False)
    if output.get("success") is False:
        return None
    if limit is None:
        return DEFAULT_LIMIT
    return limit


def parse_optional_int_field(value, field_name, min_value=None, max_value=None):
    text = as_text(value)
    if not text:
        return None
    return parse_int_field(value, field_name, min_value, max_value, True)


def normalize_number(value):
    if value == 0:
        return 0

    integer_value = int(value)
    if value == integer_value:
        return integer_value

    return value


def weekday_index(value):
    return value.weekday()


def weekday_name(value):
    return WEEKDAYS[weekday_index(value)]


def parse_weekday(value):
    text = as_text(value)
    if text not in WEEKDAYS:
        validation_error(
            "Invalid weekday. Use an exact English weekday name.",
            {"known_weekdays": WEEKDAYS},
        )
        return None
    return WEEKDAYS.index(text)


def empty_segments():
    return {
        "years": 0,
        "months": 0,
        "days": 0,
        "hours": 0,
        "minutes": 0,
        "seconds": 0,
    }


def parse_segments(value):
    text = as_text(value)
    if not text:
        validation_error(
            "Missing segments. Use comma-separated key=value pairs.",
            {"known_segment_keys": SEGMENT_KEYS},
        )
        return None

    segments = empty_segments()
    unknown_keys = []
    invalid_segments = []

    for raw_part in text.split(","):
        part = raw_part.strip()
        if not part:
            continue

        pieces = part.split("=")
        if len(pieces) != 2:
            invalid_segments.append({"key": part, "value": ""})
            continue

        key = pieces[0].strip()
        raw_value = pieces[1].strip()
        if key not in SEGMENT_KEYS:
            unknown_keys.append(key)
            continue

        parsed_value = raw_value
        if "." in parsed_value:
            value_parts = parsed_value.split(".")
            if len(value_parts) == 2 and value_parts[1] == "0":
                parsed_value = value_parts[0]
            else:
                invalid_segments.append({"key": key, "value": raw_value})
                continue

        sign = ""
        digits = parsed_value
        if digits.startswith("-"):
            sign = "-"
            digits = digits[1:]

        if not digits:
            invalid_segments.append({"key": key, "value": raw_value})
            continue

        valid = True
        for char in digits:
            if char < "0" or char > "9":
                valid = False
        if not valid:
            invalid_segments.append({"key": key, "value": raw_value})
            continue

        segments[key] = segments[key] + int(sign + digits)

    if unknown_keys:
        validation_error(
            "Invalid segments. Use known segment keys.",
            {"unknown_segment_keys": unknown_keys, "known_segment_keys": SEGMENT_KEYS},
        )
        return None

    if invalid_segments:
        validation_error(
            "Invalid segments. Use integer segment values.",
            {"invalid_segments": invalid_segments, "known_segment_keys": SEGMENT_KEYS},
        )
        return None

    non_zero = False
    for key in SEGMENT_KEYS:
        if segments[key] != 0:
            non_zero = True

    if not non_zero:
        validation_error(
            "Invalid segments. Provide at least one non-zero segment.",
            {"known_segment_keys": SEGMENT_KEYS},
        )
        return None

    return segments


def add_months(value, month_delta):
    month_index = value.year * 12 + value.month - 1 + month_delta
    year = month_index // 12
    month = month_index % 12 + 1

    if year < 1 or year > 9999:
        return None

    day = value.day
    max_day = days_in_month(year, month)
    if day > max_day:
        day = max_day

    try:
        return datetime.datetime(year, month, day, value.hour, value.minute, value.second)
    except ValueError:
        return None


def add_segments(value, segments):
    month_delta = segments["years"] * 12 + segments["months"]
    current = add_months(value, month_delta)
    if current is None:
        return None

    second_delta = (
        segments["days"] * 86400
        + segments["hours"] * 3600
        + segments["minutes"] * 60
        + segments["seconds"]
    )
    return datetime_from_local_seconds(local_seconds(current) + second_delta)


def midnight(value):
    return datetime.datetime(value.year, value.month, value.day, 0, 0, 0)


def success_meta(extra=None):
    meta = {"tool": TOOL_NAME, "operation": operation}
    if extra:
        for key in extra:
            meta[key] = extra[key]
    return meta


def success_response(answer, data_payload, meta_payload=None):
    output["success"] = True
    output["answer"] = answer
    output["data"] = data_payload
    output["meta"] = meta_payload or success_meta()


def shape_date_payload(value, key_name):
    utc_value = dt_util.as_utc(value)
    epoch_value = normalize_number(dt_util.as_timestamp(utc_value))
    return {
        key_name: local_time_text(value),
        "weekday": weekday_name(value),
        "epoch_time_s": epoch_value,
    }


def date_matches_parts(value, month_value, day_of_month_value, weekday_value):
    if month_value is not None and value.month != month_value:
        return False
    if day_of_month_value is not None and value.day != day_of_month_value:
        return False
    if weekday_value is not None and weekday_index(value) != weekday_value:
        return False
    return True


def duration_segments_between(start_value, end_value):
    sign = "+"
    earlier = start_value
    later = end_value

    if local_seconds(end_value) < local_seconds(start_value):
        sign = "-"
        earlier = end_value
        later = start_value

    month_delta = (later.year - earlier.year) * 12 + later.month - earlier.month
    candidate = add_months(earlier, month_delta)
    while month_delta > 0 and candidate is not None and local_seconds(candidate) > local_seconds(later):
        month_delta = month_delta - 1
        candidate = add_months(earlier, month_delta)
    while True:
        next_candidate = add_months(earlier, month_delta + 1)
        if next_candidate is None or local_seconds(next_candidate) > local_seconds(later):
            break
        month_delta = month_delta + 1
        candidate = next_candidate

    if candidate is None:
        candidate = earlier
        month_delta = 0

    remaining = local_seconds(later) - local_seconds(candidate)
    weeks = remaining // 604800
    remaining = remaining % 604800
    days = remaining // 86400
    remaining = remaining % 86400
    hours = remaining // 3600
    remaining = remaining % 3600
    minutes = remaining // 60
    seconds = remaining % 60

    return {
        "sign": sign,
        "years": month_delta // 12,
        "months": month_delta % 12,
        "weeks": weeks,
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "seconds": seconds,
    }


operation = as_text(data.get("operation"))
date_text = as_text(data.get("date"))
date2_text = as_text(data.get("date2"))

if operation not in OPERATIONS:
    validation_error(
        "Invalid operation. Use a known Date Calculator operation.",
        {"known_operations": OPERATIONS},
        {"tool": TOOL_NAME, "operation": operation},
    )

if output.get("success") is not False:
    validate_allowlist(operation)

if output.get("success") is not False and operation == "weekday_for_date":
    date_value = parse_required_date(date_text, "date")
    if output.get("success") is not False:
        success_response(
            "Calculated weekday.",
            {
                "date": local_time_text(date_value),
                "weekday": weekday_name(date_value),
            },
            success_meta({"date": local_time_text(date_value)}),
        )

if output.get("success") is not False and operation == "date_by_adding_segments":
    date_value = parse_required_date(date_text, "date")
    if output.get("success") is not False:
        segments = parse_segments(data.get("segments"))
    if output.get("success") is not False:
        new_date = add_segments(date_value, segments)
        if new_date is None:
            validation_error(
                "Date calculation result is out of supported range.",
                {"supported_years": "1..9999"},
            )
    if output.get("success") is not False:
        payload = shape_date_payload(new_date, "new_date")
        payload["segments"] = segments
        success_response(
            "Calculated date.",
            payload,
            success_meta({"date": local_time_text(date_value), "segments": segments}),
        )

if output.get("success") is not False and operation == "date_to_epoch":
    date_value = parse_required_date(date_text, "date")
    if output.get("success") is not False:
        payload = shape_date_payload(date_value, "date")
        success_response(
            "Converted date to epoch seconds.",
            payload,
            success_meta({"date": local_time_text(date_value)}),
        )

if output.get("success") is not False and operation == "epoch_to_date":
    epoch_time_s = parse_int_field(data.get("epoch_time_s"), "epoch_time_s", None, None, True)
    if output.get("success") is not False:
        date_value = local_naive_from_datetime(dt_util.utc_from_timestamp(epoch_time_s))
        payload = shape_date_payload(date_value, "date")
        success_response(
            "Converted epoch seconds to date.",
            payload,
            success_meta({"epoch_time_s": epoch_time_s}),
        )

if output.get("success") is not False and operation == "duration_between_dates":
    date_value = parse_required_date(date_text, "date")
    if output.get("success") is not False:
        date2_value = parse_required_date(date2_text, "date2")
    if output.get("success") is not False:
        start_epoch = dt_util.as_timestamp(dt_util.as_utc(date_value))
        end_epoch = dt_util.as_timestamp(dt_util.as_utc(date2_value))
        seconds = end_epoch - start_epoch
        days = seconds / 86400
        duration = {
            "seconds": normalize_number(seconds),
            "minutes": normalize_number(seconds / 60),
            "hours": normalize_number(seconds / 3600),
            "days": normalize_number(days),
            "weeks": normalize_number(days / 7),
            "months": normalize_number(days / 30.436875),
            "years": normalize_number(days / 365.2425),
        }
        success_response(
            "Calculated duration.",
            {
                "duration": duration,
                "duration_in_segments": duration_segments_between(date_value, date2_value),
            },
            success_meta(
                {
                    "date": local_time_text(date_value),
                    "date2": local_time_text(date2_value),
                }
            ),
        )

if output.get("success") is not False and operation == "next_matching_date":
    date_was_defaulted = False
    if date_text:
        anchor = parse_required_date(date_text, "date")
    else:
        date_was_defaulted = True
        anchor = local_naive_from_datetime(dt_util.now())
    if output.get("success") is not False:
        month_value = parse_optional_int_field(data.get("month"), "month", 1, 12)
    if output.get("success") is not False:
        day_of_month_value = parse_optional_int_field(data.get("day_of_month"), "day_of_month", 1, 31)
    if output.get("success") is not False:
        weekday_value = None
        raw_weekday = as_text(data.get("weekday"))
        if raw_weekday:
            weekday_value = parse_weekday(raw_weekday)
    if output.get("success") is not False:
        hour_value = parse_optional_int_field(data.get("hour"), "hour", 0, 23)
    if output.get("success") is not False:
        minute_value = parse_optional_int_field(data.get("minute"), "minute", 0, 59)
    if output.get("success") is not False:
        second_value = parse_optional_int_field(data.get("second"), "second", 0, 59)
    if output.get("success") is not False:
        if (
            month_value is None
            and day_of_month_value is None
            and weekday_value is None
        ):
            validation_error(
                "Missing matching date parts. Provide month, day_of_month, or weekday.",
                {"required_any": ["month", "day_of_month", "weekday"]},
            )
        elif month_value is not None and day_of_month_value is None and weekday_value is None:
            validation_error(
                "Invalid matching date parts. month alone is too broad; add day_of_month or weekday.",
                {"required_with_month": ["day_of_month", "weekday"]},
            )
    if output.get("success") is not False:
        if hour_value is None:
            hour_value = 0
        if minute_value is None:
            minute_value = 0
        if second_value is None:
            second_value = 0

        anchor_day = day_number(anchor)
        anchor_seconds = local_seconds(anchor)
        target_date = None
        days_from_anchor = None
        offset = 0
        while offset <= MAX_LIMIT:
            date_parts = date_from_day_number(anchor_day + offset)
            if date_parts is None:
                break
            candidate = datetime.datetime(
                date_parts[0],
                date_parts[1],
                date_parts[2],
                hour_value,
                minute_value,
                second_value,
            )
            if date_matches_parts(candidate, month_value, day_of_month_value, weekday_value):
                if local_seconds(candidate) >= anchor_seconds:
                    target_date = candidate
                    days_from_anchor = offset
                    break
            offset = offset + 1

        if target_date is None:
            validation_error(
                "No matching date found in the supported search horizon.",
                {"search_horizon_days": MAX_LIMIT},
            )
    if output.get("success") is not False:
        matched_parts = {
            "hour": hour_value,
            "minute": minute_value,
            "second": second_value,
        }
        if month_value is not None:
            matched_parts["month"] = month_value
        if day_of_month_value is not None:
            matched_parts["day_of_month"] = day_of_month_value
        if weekday_value is not None:
            matched_parts["weekday"] = WEEKDAYS[weekday_value]

        meta = success_meta({"date": local_time_text(anchor), "matched_parts": matched_parts})
        if date_was_defaulted:
            meta["date_was_defaulted"] = True

        success_response(
            "Calculated matching date.",
            {
                "date": local_time_text(target_date),
                "weekday": weekday_name(target_date),
                "days_from_anchor": days_from_anchor,
                "matched_parts": matched_parts,
            },
            meta,
        )

if output.get("success") is not False and operation == "list_calendar_days":
    date_value = parse_required_date(date_text, "date")
    if output.get("success") is not False:
        date2_value = parse_required_date(date2_text, "date2")
    if output.get("success") is not False:
        limit = parse_limit(data.get("limit"))
    if output.get("success") is not False:
        if local_seconds(date2_value) < local_seconds(date_value):
            validation_error(
                "Invalid date2. Use a date2 after or equal to date.",
                {
                    "date": local_time_text(date_value),
                    "date2": local_time_text(date2_value),
                },
            )
    if output.get("success") is not False:
        start_day = day_number(date_value)
        end_day = day_number(date2_value)
        total = end_day - start_day + 1
        count = total
        if count > limit:
            count = limit

        days = []
        offset = 0
        while offset < count:
            date_parts = date_from_day_number(start_day + offset)
            current = datetime.datetime(date_parts[0], date_parts[1], date_parts[2], 0, 0, 0)
            days.append(
                {
                    "date": local_date_text(current),
                    "weekday": weekday_name(current),
                }
            )
            offset = offset + 1

        meta = success_meta(
            {
                "date": local_time_text(date_value),
                "date2": local_time_text(date2_value),
                "count": count,
                "total": total,
                "limit": limit,
            }
        )
        if count < total:
            meta["truncated"] = True
        success_response(
            "Listed {} calendar days.".format(count),
            {"days": days},
            meta,
        )
