TOOL_NAME = "llmtool_calendar_manager"
DEFAULT_DAYS_AHEAD = 31
MAX_TIME_RANGE_DAYS = 365
SECONDS_PER_DAY = 86400
DEFAULT_LIMIT = 100
MAX_LIMIT = 1000
MAX_DESCRIPTION_LENGTH = 1000

OPERATIONS = ["search_events", "list_upcoming", "list_range"]
EVENT_TYPES = ["all", "all_day", "timed"]
VERBOSITIES = ["compact", "detailed"]


# Small helpers keep the top-level python_script flow readable.
def as_text(value):
    if value is None:
        return ""
    return str(value).strip()


def validation_error(message, data_payload=None, meta_payload=None):
    output["success"] = False
    output["error"] = message
    output["data"] = data_payload or {}
    output["meta"] = meta_payload or {"tool": TOOL_NAME}


def plural(value, singular, plural_text):
    if value == 1:
        return singular
    return plural_text


def mapping_value(value, key):
    try:
        getter = value.get
    except AttributeError:
        return None

    if getter is None:
        return None

    try:
        return getter(key)
    except TypeError:
        return None


def is_calendar_entity_id(value):
    parts = value.split(".")
    if len(parts) != 2:
        return False

    domain = parts[0]
    object_id = parts[1]
    if domain != "calendar" or not object_id:
        return False

    valid_chars = "abcdefghijklmnopqrstuvwxyz0123456789_"
    for char in object_id:
        if char not in valid_chars:
            return False

    return True


def parse_calendar_entity_ids(raw_entity_ids):
    entity_ids = []
    invalid_entity_ids = []
    for part in str(raw_entity_ids or "").split(","):
        entity_id = part.strip()
        if not entity_id:
            continue

        if not is_calendar_entity_id(entity_id):
            invalid_entity_ids.append(entity_id)
        elif entity_id not in entity_ids:
            entity_ids.append(entity_id)

    return entity_ids, invalid_entity_ids


def available_calendar_entity_ids():
    entity_ids = []

    try:
        discovered = hass.states.entity_ids("calendar")
    except TypeError:
        discovered = None
    except AttributeError:
        discovered = None

    if discovered is None:
        try:
            discovered = hass.states.entity_ids()
        except TypeError:
            discovered = []
        except AttributeError:
            discovered = []

    for entity_id in discovered or []:
        entity_id_text = as_text(entity_id)
        if is_calendar_entity_id(entity_id_text) and entity_id_text not in entity_ids:
            entity_ids.append(entity_id_text)

    entity_ids.sort()
    return entity_ids


def calendar_entity_exists(entity_id):
    try:
        state = hass.states.get(entity_id)
    except AttributeError:
        state = None
    return state is not None


def calendar_metadata(entity_id):
    entity = {
        "calendar_entity_id": entity_id,
        "friendly_name": entity_id,
    }

    try:
        state = hass.states.get(entity_id)
    except AttributeError:
        state = None

    if state is None:
        return entity

    attributes = state.attributes or {}
    friendly_name = as_text(mapping_value(attributes, "friendly_name"))
    if friendly_name:
        entity["friendly_name"] = friendly_name

    return entity


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


def has_date_format(value):
    if len(value) != 10:
        return False

    if value[4] != "-" or value[7] != "-":
        return False

    digit_positions = [0, 1, 2, 3, 5, 6, 8, 9]
    for position in digit_positions:
        char = value[position]
        if char < "0" or char > "9":
            return False

    return True


def parse_local_date(value):
    if not has_date_format(value):
        return None

    try:
        return datetime.datetime(
            int(value[0:4]),
            int(value[5:7]),
            int(value[8:10]),
            0,
            0,
            0,
        )
    except ValueError:
        return None


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


def two_digit(value):
    if value < 10:
        return "0{}".format(value)
    return str(value)


def local_time_text(value):
    return "{}-{}-{} {}:{}:{}".format(
        str(value.year).rjust(4, "0"),
        two_digit(value.month),
        two_digit(value.day),
        two_digit(value.hour),
        two_digit(value.minute),
        two_digit(value.second),
    )


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


def add_days(value, days):
    return datetime_from_local_seconds(local_seconds(value) + days * 86400)


def parse_int_field(value, field_name, default_value, min_value, max_value):
    text = as_text(value)
    if not text:
        return default_value, ""

    parsed_text = text
    if "." in parsed_text:
        parts = parsed_text.split(".")
        if len(parts) == 2 and parts[1] == "0":
            parsed_text = parts[0]
        else:
            return None, "Invalid {}. Use an integer from {} to {}.".format(field_name, min_value, max_value)

    if not parsed_text:
        return None, "Invalid {}. Use an integer from {} to {}.".format(field_name, min_value, max_value)

    for char in parsed_text:
        if char < "0" or char > "9":
            return None, "Invalid {}. Use an integer from {} to {}.".format(field_name, min_value, max_value)

    parsed = int(parsed_text)
    if parsed < min_value or parsed > max_value:
        return None, "Invalid {}. Use an integer from {} to {}.".format(field_name, min_value, max_value)

    return parsed, ""


def parse_min_int_field(value, field_name, default_value, min_value):
    text = as_text(value)
    if not text:
        return default_value, ""

    parsed_text = text
    if "." in parsed_text:
        parts = parsed_text.split(".")
        if len(parts) == 2 and parts[1] == "0":
            parsed_text = parts[0]
        else:
            return None, "Invalid {}. Use an integer of {} or more.".format(field_name, min_value)

    if not parsed_text:
        return None, "Invalid {}. Use an integer of {} or more.".format(field_name, min_value)

    for char in parsed_text:
        if char < "0" or char > "9":
            return None, "Invalid {}. Use an integer of {} or more.".format(field_name, min_value)

    parsed = int(parsed_text)
    if parsed < min_value:
        return None, "Invalid {}. Use an integer of {} or more.".format(field_name, min_value)

    return parsed, ""


def time_range_days(start_value, end_value):
    seconds = local_seconds(end_value) - local_seconds(start_value)
    if seconds <= 0:
        return 0

    days = seconds // SECONDS_PER_DAY
    if seconds % SECONDS_PER_DAY:
        days = days + 1

    return days


def validate_time_range(start_value, end_value, meta):
    requested_days = time_range_days(start_value, end_value)
    if requested_days > MAX_TIME_RANGE_DAYS:
        validation_error(
            "Calendar Manager Time Range too long. Use 365 days or less.",
            {
                "max_time_range_days": MAX_TIME_RANGE_DAYS,
                "requested_time_range_days": requested_days,
                "start_time": local_time_text(start_value),
                "end_time": local_time_text(end_value),
            },
            meta,
        )


def parse_calendar_event_time(value):
    text = as_text(value)
    date_value = parse_local_date(text)
    if date_value is not None:
        return date_value, True

    local_value = parse_local_time(text)
    if local_value is not None:
        return local_value, False

    try:
        parsed = dt_util.parse_datetime(text)
    except AttributeError:
        parsed = None
    except TypeError:
        parsed = None
    except ValueError:
        parsed = None

    if parsed is None:
        return None, False

    return local_naive_from_datetime(parsed), False


def title_from_event(row):
    title = as_text(mapping_value(row, "summary"))
    if not title:
        title = as_text(mapping_value(row, "title"))
    return title


def shape_event(row, calendar_entity_id, operation, keyword, event_type, start_text, end_text, verbosity):
    start_raw = mapping_value(row, "start")
    end_raw = mapping_value(row, "end")
    if start_raw is None or end_raw is None:
        return None

    start_value, start_is_date = parse_calendar_event_time(start_raw)
    end_value, end_is_date = parse_calendar_event_time(end_raw)
    if start_value is None or end_value is None:
        return None

    explicit_all_day = mapping_value(row, "all_day")
    if explicit_all_day is True or explicit_all_day is False:
        is_all_day = explicit_all_day
    else:
        is_all_day = start_is_date or end_is_date

    query_start = parse_local_time(start_text)
    query_end = parse_local_time(end_text)
    if query_start is None or query_end is None:
        return None

    if local_seconds(start_value) >= local_seconds(query_end) or local_seconds(end_value) <= local_seconds(query_start):
        return False

    if event_type == "all_day" and not is_all_day:
        return False
    if event_type == "timed" and is_all_day:
        return False

    title = title_from_event(row)
    description = as_text(mapping_value(row, "description"))
    location = as_text(mapping_value(row, "location"))

    if operation == "search_events":
        haystack = "{} {} {}".format(title, description, location).lower()
        if keyword.lower() not in haystack:
            return False

    if is_all_day:
        display_end = datetime_from_local_seconds(local_seconds(end_value) - 1)
        if display_end is None:
            return None
        shaped_event_type = "all_day"
    else:
        display_end = end_value
        shaped_event_type = "timed"

    event = {
        "title": title,
        "event_type": shaped_event_type,
        "start": local_time_text(start_value),
        "end": local_time_text(display_end),
        "location": location or None,
        "_calendar_entity_id": calendar_entity_id,
        "_start_seconds": local_seconds(start_value),
    }

    if verbosity == "detailed":
        if len(description) > MAX_DESCRIPTION_LENGTH:
            event["description"] = description[:MAX_DESCRIPTION_LENGTH]
            event["description_truncated"] = True
        else:
            event["description"] = description or None

    return event


def build_meta(
    operation,
    calendar_entity_ids,
    start_text,
    end_text,
    event_type,
    verbosity,
    limit,
    count,
    total,
    days_ahead,
):
    meta = {
        "tool": TOOL_NAME,
        "operation": operation,
        "calendar_entity_ids": calendar_entity_ids,
        "start_time": start_text,
        "end_time": end_text,
        "event_type": event_type,
        "verbosity": verbosity,
        "limit": limit,
        "count": count,
        "total": total,
    }

    if days_ahead is not None:
        meta["days_ahead"] = days_ahead
    if count < total:
        meta["truncated"] = True

    return meta


def prepare_mode():
    operation = as_text(data.get("operation"))
    raw_calendar_entity_ids = as_text(data.get("calendar_entity_ids"))
    keyword = as_text(data.get("keyword"))
    raw_start_time = as_text(data.get("start_time"))
    raw_end_time = as_text(data.get("end_time"))
    raw_days_ahead = as_text(data.get("days_ahead"))
    raw_limit = as_text(data.get("limit"))
    event_type = as_text(data.get("event_type")) or "all"
    verbosity = as_text(data.get("verbosity")) or "compact"

    meta = {"tool": TOOL_NAME, "operation": operation}

    if operation not in OPERATIONS:
        validation_error(
            "Invalid operation. Use a known Calendar Manager operation.",
            {"known_operations": OPERATIONS},
            meta,
        )

    if output.get("success") is not False and event_type not in EVENT_TYPES:
        validation_error(
            "Invalid event_type. Use all, all_day, or timed.",
            {"known_event_types": EVENT_TYPES},
            meta,
        )

    if output.get("success") is not False and verbosity not in VERBOSITIES:
        validation_error(
            "Invalid verbosity. Use compact or detailed.",
            {"known_verbosity": VERBOSITIES},
            meta,
        )

    if output.get("success") is not False:
        limit, limit_error = parse_int_field(raw_limit, "limit", DEFAULT_LIMIT, 1, MAX_LIMIT)
        if limit_error:
            validation_error(
                limit_error,
                {"default_limit": DEFAULT_LIMIT, "max_limit": MAX_LIMIT},
                meta,
            )

    if output.get("success") is not False:
        days_ahead, days_ahead_error = parse_min_int_field(
            raw_days_ahead,
            "days_ahead",
            DEFAULT_DAYS_AHEAD,
            1,
        )
        if days_ahead_error:
            validation_error(
                days_ahead_error,
                {"default_days_ahead": DEFAULT_DAYS_AHEAD, "max_time_range_days": MAX_TIME_RANGE_DAYS},
                meta,
            )

    if output.get("success") is not False:
        calendar_entity_ids, invalid_calendar_entity_ids = parse_calendar_entity_ids(raw_calendar_entity_ids)
        if invalid_calendar_entity_ids:
            validation_error(
                "Invalid calendar_entity_ids. Use comma-separated calendar.* entity IDs.",
                {"invalid_calendar_entity_ids": invalid_calendar_entity_ids},
                meta,
            )
        elif not calendar_entity_ids:
            calendar_entity_ids = available_calendar_entity_ids()
            if not calendar_entity_ids:
                validation_error(
                    "No calendar entities found. Provide calendar_entity_ids or enable calendar entities.",
                    {"required": "calendar_entity_ids"},
                    meta,
                )
        else:
            unknown_calendar_entity_ids = []
            for entity_id in calendar_entity_ids:
                if not calendar_entity_exists(entity_id):
                    unknown_calendar_entity_ids.append(entity_id)
            if unknown_calendar_entity_ids:
                validation_error(
                    "Unknown calendar entity ID. Use existing Home Assistant calendar.* entity IDs.",
                    {"unknown_calendar_entity_ids": unknown_calendar_entity_ids},
                    meta,
                )

    if output.get("success") is not False and operation == "search_events" and not keyword:
        validation_error(
            "Missing keyword. Provide a keyword for search_events.",
            {"required": "keyword"},
            meta,
        )

    if output.get("success") is not False:
        now_local = local_naive_from_datetime(dt_util.now())
        if operation == "list_range":
            if not raw_start_time:
                validation_error(
                    "Missing start_time. Use local time in format YYYY-MM-DD HH:MM:SS.",
                    {"expected_format": "YYYY-MM-DD HH:MM:SS"},
                    meta,
                )
            elif not raw_end_time:
                validation_error(
                    "Missing end_time. Use local time in format YYYY-MM-DD HH:MM:SS.",
                    {"expected_format": "YYYY-MM-DD HH:MM:SS"},
                    meta,
                )
            else:
                start_local = parse_local_time(raw_start_time)
                end_local = parse_local_time(raw_end_time)
                if start_local is None:
                    validation_error(
                        "Invalid start_time. Use local time in format YYYY-MM-DD HH:MM:SS.",
                        {"expected_format": "YYYY-MM-DD HH:MM:SS"},
                        meta,
                    )
                elif end_local is None:
                    validation_error(
                        "Invalid end_time. Use local time in format YYYY-MM-DD HH:MM:SS.",
                        {"expected_format": "YYYY-MM-DD HH:MM:SS"},
                        meta,
                    )
        elif operation == "search_events":
            if raw_start_time:
                start_local = parse_local_time(raw_start_time)
                if start_local is None:
                    validation_error(
                        "Invalid start_time. Use local time in format YYYY-MM-DD HH:MM:SS.",
                        {"expected_format": "YYYY-MM-DD HH:MM:SS"},
                        meta,
                    )
            else:
                start_local = now_local

            if output.get("success") is not False:
                if raw_end_time:
                    end_local = parse_local_time(raw_end_time)
                    if end_local is None:
                        validation_error(
                            "Invalid end_time. Use local time in format YYYY-MM-DD HH:MM:SS.",
                            {"expected_format": "YYYY-MM-DD HH:MM:SS"},
                            meta,
                        )
                else:
                    end_local = add_days(now_local, days_ahead)
        else:
            start_local = now_local
            end_local = add_days(now_local, days_ahead)

    if output.get("success") is not False:
        if end_local is None or local_seconds(end_local) <= local_seconds(start_local):
            validation_error(
                "Invalid end_time. Use an end_time after start_time.",
                {
                    "start_time": local_time_text(start_local),
                    "end_time": local_time_text(end_local) if end_local is not None else "",
                },
                meta,
            )

    if output.get("success") is not False and days_ahead > MAX_TIME_RANGE_DAYS:
        validation_error(
            "Calendar Manager Time Range too long. Use 365 days or less.",
            {
                "max_time_range_days": MAX_TIME_RANGE_DAYS,
                "requested_time_range_days": days_ahead,
                "start_time": local_time_text(start_local),
                "end_time": local_time_text(end_local),
            },
            meta,
        )

    if output.get("success") is not False:
        validate_time_range(start_local, end_local, meta)

    if output.get("success") is not False:
        start_text = local_time_text(start_local)
        end_text = local_time_text(end_local)
        output["success"] = True
        output["data"] = {
            "operation": operation,
            "calendar_entity_ids": calendar_entity_ids,
            "keyword": keyword,
            "start_time": start_text,
            "end_time": end_text,
            "days_ahead": days_ahead,
            "limit": limit,
            "event_type": event_type,
            "verbosity": verbosity,
        }
        output["meta"] = meta


def shape_mode():
    operation = as_text(data.get("operation"))
    raw_calendar_entity_ids = as_text(data.get("calendar_entity_ids"))
    keyword = as_text(data.get("keyword"))
    start_text = as_text(data.get("start_time"))
    end_text = as_text(data.get("end_time"))
    event_type = as_text(data.get("event_type")) or "all"
    verbosity = as_text(data.get("verbosity")) or "compact"
    days_ahead, days_ahead_error = parse_int_field(
        data.get("days_ahead"),
        "days_ahead",
        DEFAULT_DAYS_AHEAD,
        1,
        MAX_TIME_RANGE_DAYS,
    )
    limit, limit_error = parse_int_field(data.get("limit"), "limit", DEFAULT_LIMIT, 1, MAX_LIMIT)

    meta = {"tool": TOOL_NAME, "operation": operation}
    calendar_entity_ids, invalid_calendar_entity_ids = parse_calendar_entity_ids(raw_calendar_entity_ids)

    if (
        operation not in OPERATIONS
        or invalid_calendar_entity_ids
        or not calendar_entity_ids
        or days_ahead_error
        or limit_error
        or event_type not in EVENT_TYPES
        or verbosity not in VERBOSITIES
        or parse_local_time(start_text) is None
        or parse_local_time(end_text) is None
    ):
        validation_error(
            "Invalid Calendar Manager helper handoff. Inspect the Script trace.",
            {},
            meta,
        )

    if output.get("success") is not False:
        events_response = data.get("events_response")
        if isinstance(events_response, str):
            validation_error(
                "Invalid calendar.get_events response shape. Expected a mapping keyed by calendar entity ID.",
                {"expected": "mapping"},
                meta,
            )

    if output.get("success") is not False:
        # Shape all events before truncation so global limits are deterministic.
        all_events = []
        invalid_response = False

        for calendar_entity_id in calendar_entity_ids:
            payload = mapping_value(events_response, calendar_entity_id)
            if payload is None:
                invalid_response = True
                break

            events = mapping_value(payload, "events")
            if events is None:
                events = []
            if isinstance(events, str):
                invalid_response = True
                break

            for row in events:
                if isinstance(row, str):
                    invalid_response = True
                    break

                shaped = shape_event(
                    row,
                    calendar_entity_id,
                    operation,
                    keyword,
                    event_type,
                    start_text,
                    end_text,
                    verbosity,
                )

                if shaped is None:
                    invalid_response = True
                    break
                if shaped is not False:
                    all_events.append(shaped)

            if invalid_response:
                break

        if invalid_response:
            validation_error(
                "Invalid calendar.get_events response shape. Inspect calendar.get_events response in Script trace.",
                {"expected": "mapping keyed by calendar entity ID with events arrays"},
                meta,
            )

    if output.get("success") is not False:
        all_events.sort(
            key=lambda item: "{} {}".format(
                str(item["_start_seconds"]).rjust(20, "0"),
                item["_calendar_entity_id"],
            )
        )
        total = len(all_events)
        limited_events = all_events[:limit]

        grouped = {}
        for event in limited_events:
            calendar_entity_id = event["_calendar_entity_id"]
            if calendar_entity_id not in grouped:
                grouped[calendar_entity_id] = []
            grouped[calendar_entity_id].append(event)

        calendars = []
        sorted_calendar_entity_ids = []
        for calendar_entity_id in grouped:
            sorted_calendar_entity_ids.append(calendar_entity_id)
        sorted_calendar_entity_ids.sort()

        for calendar_entity_id in sorted_calendar_entity_ids:
            calendar = calendar_metadata(calendar_entity_id)
            events = []
            grouped[calendar_entity_id].sort(key=lambda item: item["_start_seconds"])
            for event in grouped[calendar_entity_id]:
                public_event = {}
                for key in event:
                    if not key.startswith("_"):
                        public_event[key] = event[key]
                events.append(public_event)

            calendar["count"] = len(events)
            calendar["events"] = events
            calendars.append(calendar)

        count = len(limited_events)
        response_meta = build_meta(
            operation,
            calendar_entity_ids,
            start_text,
            end_text,
            event_type,
            verbosity,
            limit,
            count,
            total,
            days_ahead,
        )

        output["success"] = True
        output["answer"] = "Found {} calendar {}.".format(
            count,
            plural(count, "event", "events"),
        )
        output["data"] = {"calendars": calendars}
        output["meta"] = response_meta


mode = as_text(data.get("mode"))

if mode == "prepare":
    prepare_mode()
elif mode == "shape":
    shape_mode()
else:
    validation_error(
        "Invalid Calendar Manager helper mode. Inspect the Script trace.",
        {"known_modes": ["prepare", "shape"]},
        {"tool": TOOL_NAME},
    )
