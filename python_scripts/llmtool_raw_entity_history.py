TOOL_NAME = "llmtool_raw_entity_history"
MAX_ENTITY_IDS = 10
DEFAULT_LIMIT = 100
MAX_LIMIT = 1000
DEFAULT_BASE_URL = "http://localhost:8123"
TRUNCATION_RETRY_HINT = "Retry with a higher limit or narrower time range if needed data was not included."


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


def is_entity_id(value):
    parts = value.split(".")
    if len(parts) != 2:
        return False

    domain = parts[0]
    object_id = parts[1]
    if not domain or not object_id:
        return False

    valid_chars = "abcdefghijklmnopqrstuvwxyz0123456789_"
    for char in domain:
        if char not in valid_chars:
            return False
    for char in object_id:
        if char not in valid_chars:
            return False

    return True


def parse_entity_ids(raw_entity_ids):
    entity_ids = []
    invalid_entity_ids = []
    for part in str(raw_entity_ids or "").split(","):
        entity_id = part.strip()
        if not entity_id:
            continue

        if not is_entity_id(entity_id):
            invalid_entity_ids.append(entity_id)
        elif entity_id not in entity_ids:
            entity_ids.append(entity_id)

    return entity_ids, invalid_entity_ids


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
        parsed = datetime.datetime(
            int(value[0:4]),
            int(value[5:7]),
            int(value[8:10]),
            int(value[11:13]),
            int(value[14:16]),
            int(value[17:19]),
        )
    except ValueError:
        return None

    return parsed


def days_before_year(year):
    previous_year = year - 1
    return (
        previous_year * 365
        + previous_year // 4
        - previous_year // 100
        + previous_year // 400
    )


def is_leap_year(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def days_before_month(year, month):
    month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    total = 0
    for index in range(month - 1):
        total = total + month_days[index]
    if month > 2 and is_leap_year(year):
        total = total + 1
    return total


def utc_timestamp_from_parts(year, month, day, hour, minute, second, microsecond, offset_seconds):
    days = (
        days_before_year(year)
        - days_before_year(1970)
        + days_before_month(year, month)
        + day
        - 1
    )
    timestamp = days * 86400 + hour * 3600 + minute * 60 + second
    timestamp = timestamp - offset_seconds
    if microsecond:
        timestamp = timestamp + microsecond / 1000000.0
    return timestamp


def parse_rest_timestamp(value):
    text = as_text(value)
    if len(text) < 20:
        return None

    if text[4] != "-" or text[7] != "-" or text[10] != "T":
        return None
    if text[13] != ":" or text[16] != ":":
        return None

    try:
        year = int(text[0:4])
        month = int(text[5:7])
        day = int(text[8:10])
        hour = int(text[11:13])
        minute = int(text[14:16])
        second = int(text[17:19])
    except ValueError:
        return None

    fraction_end = 19
    microsecond = 0
    if len(text) > 19 and text[19] == ".":
        fraction_end = 20
        fraction = ""
        while fraction_end < len(text):
            char = text[fraction_end]
            if char < "0" or char > "9":
                break
            fraction = fraction + char
            fraction_end = fraction_end + 1

        if not fraction:
            return None

        microsecond = int((fraction + "000000")[0:6])

    suffix = text[fraction_end:]
    if suffix == "Z":
        offset_seconds = 0
    elif len(suffix) == 6 and (suffix[0] == "+" or suffix[0] == "-") and suffix[3] == ":":
        try:
            offset_hours = int(suffix[1:3])
            offset_minutes = int(suffix[4:6])
        except ValueError:
            return None

        offset_seconds = offset_hours * 3600 + offset_minutes * 60
        if suffix[0] == "-":
            offset_seconds = -offset_seconds
    else:
        return None

    try:
        datetime.datetime(year, month, day, hour, minute, second, microsecond)
    except ValueError:
        return None

    return utc_timestamp_from_parts(
        year,
        month,
        day,
        hour,
        minute,
        second,
        microsecond,
        offset_seconds,
    )


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


def local_text_from_datetime(value):
    if isinstance(value, str):
        parsed = parse_rest_timestamp(value)
    else:
        parsed = value

    if parsed is None:
        return ""
    if isinstance(parsed, int) or isinstance(parsed, float):
        parsed = dt_util.utc_from_timestamp(parsed)

    return local_time_text(dt_util.as_local(parsed))


def iso_offset_text(value):
    local_value = dt_util.as_local(value)
    offset = local_value.utcoffset()
    offset_seconds = 0
    if offset is not None:
        offset_seconds = int(offset.total_seconds())

    sign = "+"
    if offset_seconds < 0:
        sign = "-"
        offset_seconds = -offset_seconds

    offset_hours = offset_seconds // 3600
    offset_minutes = (offset_seconds % 3600) // 60

    return "{}T{}:{}:{}{}{}:{}".format(
        "{}-{}-{}".format(
            str(local_value.year).rjust(4, "0"),
            two_digit(local_value.month),
            two_digit(local_value.day),
        ),
        two_digit(local_value.hour),
        two_digit(local_value.minute),
        two_digit(local_value.second),
        sign,
        two_digit(offset_hours),
        two_digit(offset_minutes),
    )


def url_encode(value):
    result = ""
    safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~"
    hex_chars = "0123456789ABCDEF"

    for char in value:
        if char in safe:
            result = result + char
        else:
            ordinal = ord(char)
            result = result + "%" + hex_chars[(ordinal // 16) % 16] + hex_chars[ordinal % 16]

    return result


def parse_limit(raw_limit):
    raw_limit = as_text(raw_limit)
    if not raw_limit:
        return DEFAULT_LIMIT, None

    precision_text = raw_limit
    if "." in precision_text:
        parts = precision_text.split(".")
        if len(parts) == 2 and parts[1] == "0":
            precision_text = parts[0]
        else:
            return None, "Invalid limit. Use an integer from 1 to 1000."

    if not precision_text:
        return None, "Invalid limit. Use an integer from 1 to 1000."

    for char in precision_text:
        if char < "0" or char > "9":
            return None, "Invalid limit. Use an integer from 1 to 1000."

    limit = int(precision_text)
    if limit < 1 or limit > MAX_LIMIT:
        return None, "Invalid limit. Use an integer from 1 to 1000."

    return limit, None


def clean_base_url(value):
    base_url = as_text(value) or DEFAULT_BASE_URL
    return base_url.rstrip("/")


def build_meta(entity_ids, start_text, end_text, count, total, limit, end_time_was_defaulted):
    meta = {
        "tool": TOOL_NAME,
        "entity_ids": entity_ids,
        "start_time": start_text,
        "end_time": end_text,
        "count": count,
        "total": total,
        "limit": limit,
    }

    if end_time_was_defaulted:
        meta["end_time_was_defaulted"] = True
    if count < total:
        meta["truncated"] = True

    return meta


def as_bool(value):
    if value is True:
        return True
    text = as_text(value).lower()
    return text == "true" or text == "1" or text == "yes"


def entity_metadata(entity_id):
    entity = {"entity_id": entity_id}
    state = hass.states.get(entity_id)
    if state is None:
        return entity

    attributes = state.attributes or {}
    friendly_name = as_text(attributes.get("friendly_name"))
    unit_of_measurement = as_text(attributes.get("unit_of_measurement"))

    if friendly_name:
        entity["friendly_name"] = friendly_name
    if unit_of_measurement:
        entity["unit_of_measurement"] = unit_of_measurement

    return entity


def normalize_duration(seconds):
    if seconds < 0:
        seconds = 0
    integer_value = int(seconds)
    if seconds == integer_value:
        return integer_value
    return round(seconds, 3)


def row_value(row, key):
    try:
        return row[key]
    except (KeyError, TypeError):
        return None


def optional_mapping_value(value, key):
    try:
        return value[key]
    except (KeyError, TypeError):
        return None


def shape_history_row(row):
    raw_changed_at = as_text(row_value(row, "last_changed"))
    state = as_text(row_value(row, "state"))
    changed_at_timestamp = parse_rest_timestamp(raw_changed_at)

    if changed_at_timestamp is None or state == "":
        return None

    return {
        "changed_at_timestamp": changed_at_timestamp,
        "entry": {
            "changed_at": local_text_from_datetime(changed_at_timestamp),
            "state": state,
        },
    }


def shape_boundary(entry, active_at):
    return {
        "changed_at": entry["changed_at"],
        "active_at": active_at,
        "state": entry["state"],
    }


def group_entity_id(group):
    entity_id = ""
    for row in group:
        row_entity_id = as_text(row_value(row, "entity_id"))
        if row_entity_id:
            entity_id = row_entity_id
            break
    return entity_id


def prepare_mode():
    base_url = clean_base_url(data.get("base_url"))
    raw_entity_ids = as_text(data.get("entity_ids"))
    raw_start_time = as_text(data.get("start_time"))
    raw_end_time = as_text(data.get("end_time"))
    raw_limit = as_text(data.get("limit"))

    meta = {"tool": TOOL_NAME}
    entity_ids, invalid_entity_ids = parse_entity_ids(raw_entity_ids)

    if not entity_ids and not invalid_entity_ids:
        validation_error(
            "Missing entity_ids. Provide comma-separated Home Assistant entity IDs.",
            {"required": "entity_ids"},
            meta,
        )
    elif invalid_entity_ids:
        validation_error(
            "Invalid entity ID. Use Home Assistant entity IDs such as sensor.example.",
            {"invalid_entity_ids": invalid_entity_ids},
            meta,
        )
    elif len(entity_ids) > MAX_ENTITY_IDS:
        validation_error(
            "Too many entity IDs. Use at most 10 entity IDs.",
            {"max_entity_ids": MAX_ENTITY_IDS, "entity_count": len(entity_ids)},
            meta,
        )
    elif not raw_start_time:
        validation_error(
            "Missing start_time. Use local time in format YYYY-MM-DD HH:MM:SS.",
            {"expected_format": "YYYY-MM-DD HH:MM:SS"},
            meta,
        )

    if output.get("success") is not False:
        start_local = parse_local_time(raw_start_time)
        if start_local is None:
            validation_error(
                "Invalid start_time. Use local time in format YYYY-MM-DD HH:MM:SS.",
                {"expected_format": "YYYY-MM-DD HH:MM:SS"},
                meta,
            )

    if output.get("success") is not False:
        end_time_was_defaulted = False
        if raw_end_time:
            end_local = parse_local_time(raw_end_time)
            if end_local is None:
                validation_error(
                    "Invalid end_time. Use local time in format YYYY-MM-DD HH:MM:SS.",
                    {"expected_format": "YYYY-MM-DD HH:MM:SS"},
                    meta,
                )
        else:
            end_time_was_defaulted = True
            end_local = dt_util.now()

    if output.get("success") is not False:
        start_utc = dt_util.as_utc(start_local)
        end_utc = dt_util.as_utc(end_local)

        if end_utc <= start_utc:
            validation_error(
                "Invalid end_time. Use an end_time after start_time.",
                {
                    "start_time": raw_start_time,
                    "end_time": raw_end_time,
                },
                meta,
            )

    if output.get("success") is not False:
        limit, limit_error = parse_limit(raw_limit)
        if limit_error:
            validation_error(
                limit_error,
                {"default_limit": DEFAULT_LIMIT, "max_limit": MAX_LIMIT},
                meta,
            )

    if output.get("success") is not False:
        start_text = local_text_from_datetime(start_utc)
        end_text = local_text_from_datetime(end_utc)
        start_url = url_encode(iso_offset_text(start_utc))
        end_url = url_encode(iso_offset_text(end_utc))
        entity_ids_url = url_encode(",".join(entity_ids))
        api_path = (
            "history/period/"
            + start_url
            + "?end_time="
            + end_url
            + "&filter_entity_id="
            + entity_ids_url
            + "&minimal_response"
            + "&no_attributes"
            + "&significant_changes_only=0"
        )

        output["success"] = True
        output["data"] = {
            "base_url": base_url,
            "api_path": api_path,
            "entity_ids": entity_ids,
            "start_time": start_text,
            "end_time": end_text,
            "end_time_was_defaulted": end_time_was_defaulted,
            "limit": limit,
        }
        output["meta"] = meta


def shape_mode():
    rest_status = as_text(data.get("rest_status"))
    entity_ids, invalid_entity_ids = parse_entity_ids(data.get("entity_ids"))
    start_text = as_text(data.get("start_time"))
    end_text = as_text(data.get("end_time"))
    end_time_was_defaulted = as_bool(data.get("end_time_was_defaulted"))
    limit, limit_error = parse_limit(data.get("limit"))

    if invalid_entity_ids or not entity_ids or limit_error:
        validation_error(
            "Invalid Raw Entity History helper handoff. Inspect the Script trace.",
            {},
            {"tool": TOOL_NAME},
        )

    if output.get("success") is not False:
        start_local = parse_local_time(start_text)
        end_local = parse_local_time(end_text)
        if start_local is None or end_local is None:
            validation_error(
                "Invalid Raw Entity History helper time handoff. Inspect the Script trace.",
                {},
                {"tool": TOOL_NAME},
            )

    if output.get("success") is not False:
        start_utc = dt_util.as_utc(start_local)
        end_utc = dt_util.as_utc(end_local)
        start_timestamp = dt_util.as_timestamp(start_utc)
        base_meta = build_meta(
            entity_ids,
            start_text,
            end_text,
            0,
            0,
            limit,
            end_time_was_defaulted,
        )

        if rest_status == "401" or rest_status == "403":
            validation_error(
                "History API authentication failed. Check llmtool_home_assistant_bearer_token in secrets.yaml.",
                {"status": int(rest_status)},
                base_meta,
            )
        elif rest_status != "200":
            status_value = 0
            if rest_status:
                try:
                    status_value = int(rest_status)
                except ValueError:
                    status_value = 0
            validation_error(
                "History API request failed. Inspect rest_command.llmtool_home_assistant_api_get in the Script trace.",
                {"status": status_value},
                base_meta,
            )

    if output.get("success") is not False:
        history_payload = data.get("history_payload")
        invalid_json = optional_mapping_value(history_payload, "llmtool_invalid_json")

        if invalid_json:
            validation_error(
                "Invalid History API JSON response. Inspect rest_command.llmtool_home_assistant_api_get content in the Script trace.",
                {"expected": "JSON array"},
                base_meta,
            )

    if output.get("success") is not False:
        try:
            group_total = len(history_payload)
        except TypeError:
            group_total = -1

        if group_total < 0 or isinstance(history_payload, str):
            validation_error(
                "Invalid History API response shape. Expected an array of entity history arrays.",
                {"expected": "array of arrays"},
                base_meta,
            )

    if output.get("success") is not False:
        groups_by_entity_id = {}
        for group in history_payload:
            if isinstance(group, str):
                validation_error(
                    "Invalid History API response shape. Expected each entity history group to be an array.",
                    {"expected": "array of state rows"},
                    base_meta,
                )
                break

            entity_id = group_entity_id(group)
            if not entity_id or entity_id not in entity_ids or entity_id in groups_by_entity_id:
                validation_error(
                    "Invalid History API response shape. Could not map history group to requested entity ID.",
                    {"expected": "each group includes a requested entity_id"},
                    base_meta,
                )
                break

            groups_by_entity_id[entity_id] = group

    if output.get("success") is not False:
        # Shape all rows before truncation so state_at_end stays useful.
        entities = []
        missing_entities = []
        total = 0

        for entity_id in entity_ids:
            group = groups_by_entity_id.get(entity_id) or []
            shaped_rows = []

            for row in group:
                shaped_row = shape_history_row(row)
                if shaped_row is None:
                    validation_error(
                        "Invalid History API response shape. Expected state rows with last_changed and state.",
                        {"expected": "state rows with last_changed and state"},
                        base_meta,
                    )
                    break
                shaped_rows.append(shaped_row)

            if output.get("success") is False:
                break

            shaped_rows.sort(key=lambda item: item["changed_at_timestamp"])
            if not shaped_rows:
                missing_entities.append(entity_id)
                continue

            total = total + len(shaped_rows)
            entity = entity_metadata(entity_id)

            first_row = shaped_rows[0]
            last_row = shaped_rows[-1]

            if first_row["changed_at_timestamp"] <= start_timestamp:
                entity["state_at_start"] = shape_boundary(first_row["entry"], start_text)

            entity["state_at_end"] = shape_boundary(last_row["entry"], end_text)
            entity["history_source_rows"] = shaped_rows
            entities.append(entity)

    if output.get("success") is not False:
        remaining = limit
        response_entities = []

        for entity in entities:
            source_rows = entity["history_source_rows"]
            entity_copy = {}
            for key in entity:
                if key != "history_source_rows":
                    entity_copy[key] = entity[key]

            history_entries = []
            kept_count = 0
            for index in range(len(source_rows)):
                if remaining <= 0:
                    break

                entry = {}
                for key in source_rows[index]["entry"]:
                    entry[key] = source_rows[index]["entry"][key]

                if index + 1 < len(source_rows) and remaining > 1:
                    duration = (
                        source_rows[index + 1]["changed_at_timestamp"]
                        - source_rows[index]["changed_at_timestamp"]
                    )
                    entry["duration_until_next_change_seconds"] = normalize_duration(duration)

                history_entries.append(entry)
                kept_count = kept_count + 1
                remaining = remaining - 1

            if kept_count < len(source_rows):
                entity_copy["truncated"] = True

            entity_copy["history"] = history_entries
            response_entities.append(entity_copy)

        count = 0
        for entity in response_entities:
            count = count + len(entity["history"])

        response_meta = build_meta(
            entity_ids,
            start_text,
            end_text,
            count,
            total,
            limit,
            end_time_was_defaulted,
        )

        if total == 0:
            output["success"] = False
            output["error"] = "No raw history found for requested entity IDs and time range."
            output["data"] = {
                "entities": [],
                "missing_entities": missing_entities,
            }
            output["meta"] = response_meta
        else:
            data_payload = {
                "entities": response_entities,
                "missing_entities": missing_entities,
            }
            answer = "Found {} history {}.".format(
                count,
                plural(count, "entry", "entries"),
            )
            if count < total:
                answer = "Found {} of {} history {}.".format(
                    count,
                    total,
                    plural(total, "entry", "entries"),
                )
                data_payload["truncation"] = {
                    "truncated": True,
                    "count_returned": count,
                    "count_total_before_truncation": total,
                    "limit": limit,
                    "retry_hint": TRUNCATION_RETRY_HINT,
                }
                answer = (
                    answer
                    + " Attention: returned data is truncated because total matching data points ({}) exceeded limit ({}). {}".format(
                        total,
                        limit,
                        TRUNCATION_RETRY_HINT,
                    )
                )
            if missing_entities:
                answer = answer + " No raw history found for {} requested {}.".format(
                    len(missing_entities),
                    plural(len(missing_entities), "entity", "entities"),
                )

            output["success"] = True
            output["answer"] = answer
            output["data"] = data_payload
            output["meta"] = response_meta


mode = as_text(data.get("mode"))

if mode == "prepare":
    prepare_mode()
elif mode == "shape":
    shape_mode()
else:
    validation_error(
        "Invalid Raw Entity History helper mode. Inspect the Script trace.",
        {"known_modes": ["prepare", "shape"]},
        {"tool": TOOL_NAME},
    )
