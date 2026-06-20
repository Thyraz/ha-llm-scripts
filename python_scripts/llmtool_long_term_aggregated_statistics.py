TOOL_NAME = "llmtool_long_term_aggregated_statistics"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_ENTITY_IDS = 10
MAX_RESPONSE_ROWS = 500
TOTAL_SHORT_RANGE_SECONDS = 3 * 60 * 60

AGGREGATION_TYPES = ["mean", "min", "max", "change"]
AGGREGATION_PERIODS = ["5minute", "hour", "day", "week", "month", "year", "total"]


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
        parsed = dt_util.parse_datetime(value)
    else:
        parsed = value

    if parsed is None:
        return ""

    return local_time_text(dt_util.as_local(parsed))


def normalize_number(value):
    if value == 0:
        return 0
    return value


def is_number(value):
    return isinstance(value, int) or isinstance(value, float)


def call_recorder_statistics(period, start_time, end_time, entity_ids, aggregation_type):
    service_data = {
        "start_time": start_time,
        "end_time": end_time,
        "statistic_ids": entity_ids,
        "period": period,
        "types": [aggregation_type],
    }

    return hass.services.call(
        "recorder",
        "get_statistics",
        service_data,
        blocking=True,
        return_response=True,
    )


def statistics_payload_from_response(response):
    try:
        statistics = response.get("statistics")
    except AttributeError:
        return None

    try:
        statistics.get
    except AttributeError:
        return None

    return statistics


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


def shape_period_rows(rows, aggregation_type):
    values = []
    for row in rows:
        try:
            value = row.get(aggregation_type)
            start_value = row.get("start")
            end_value = row.get("end")
        except AttributeError:
            return None

        if value is None:
            continue

        if not is_number(value):
            return None

        start_text = local_text_from_datetime(start_value)
        end_text = local_text_from_datetime(end_value)
        if not start_text or not end_text:
            return None

        values.append(
            {
                "start": start_text,
                "end": end_text,
                aggregation_type: normalize_number(value),
            }
        )

    values.sort(key=lambda item: item["start"])
    return values


def shape_total_rows(rows, aggregation_type, start_text, end_text):
    collected_values = []
    for row in rows:
        try:
            value = row.get(aggregation_type)
        except AttributeError:
            return None

        if value is None:
            continue

        if not is_number(value):
            return None

        collected_values.append(value)

    if not collected_values:
        return []

    if aggregation_type == "mean":
        result_value = sum(collected_values) / len(collected_values)
    elif aggregation_type == "min":
        result_value = min(collected_values)
    elif aggregation_type == "max":
        result_value = max(collected_values)
    else:
        result_value = sum(collected_values)

    return [
        {
            "start": start_text,
            "end": end_text,
            aggregation_type: normalize_number(result_value),
        }
    ]


def build_entities(statistics_payload, entity_ids, aggregation_type, aggregation_period, start_text, end_text):
    entities = []
    missing_entities = []

    for entity_id in entity_ids:
        rows = statistics_payload.get(entity_id) or []

        if aggregation_period == "total":
            values = shape_total_rows(rows, aggregation_type, start_text, end_text)
        else:
            values = shape_period_rows(rows, aggregation_type)

        if values is None:
            return None, None

        if values:
            entity = entity_metadata(entity_id)
            entity["values"] = values
            entities.append(entity)
        else:
            missing_entities.append(entity_id)

    return entities, missing_entities


def value_row_count(entities):
    count = 0
    for entity in entities:
        count = count + len(entity["values"])
    return count


def truncate_entities(entities):
    remaining = MAX_RESPONSE_ROWS
    truncated_entities = []

    for entity in entities:
        values = entity["values"]
        entity_copy = {}
        for key in entity:
            if key != "values":
                entity_copy[key] = entity[key]

        if remaining >= len(values):
            kept_values = values
            remaining = remaining - len(values)
        elif remaining > 0:
            kept_values = values[:remaining]
            entity_copy["truncated"] = True
            remaining = 0
        else:
            kept_values = []
            entity_copy["truncated"] = True

        entity_copy["values"] = kept_values
        truncated_entities.append(entity_copy)

    return truncated_entities


def build_meta(entity_ids, start_text, end_text, aggregation_type, aggregation_period, count, total, end_time_was_defaulted):
    meta = {
        "tool": TOOL_NAME,
        "entity_ids": entity_ids,
        "start_time": start_text,
        "end_time": end_text,
        "aggregation_type": aggregation_type,
        "aggregation_period": aggregation_period,
        "count": count,
        "total": total,
    }

    if end_time_was_defaulted:
        meta["end_time_was_defaulted"] = True
    if count < total:
        meta["truncated"] = True

    return meta


def success_answer(count, total, missing_count):
    if count < total:
        answer = "Found {} of {} statistics {}.".format(
            count,
            total,
            plural(total, "row", "rows"),
        )
    else:
        answer = "Found {} statistics {}.".format(
            count,
            plural(count, "row", "rows"),
        )

    if missing_count:
        answer = answer + " No statistics found for {} requested {}.".format(
            missing_count,
            plural(missing_count, "entity", "entities"),
        )

    return answer


# Normalize caller input.
raw_entity_ids = as_text(data.get("entity_ids"))
raw_start_time = as_text(data.get("start_time"))
raw_end_time = as_text(data.get("end_time"))
aggregation_type = as_text(data.get("aggregation_type"))
aggregation_period = as_text(data.get("aggregation_period"))

meta = {"tool": TOOL_NAME}

# Validate scalar parameters before calling recorder.
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
elif aggregation_type not in AGGREGATION_TYPES:
    validation_error(
        "Invalid aggregation_type. Use mean, min, max, or change.",
        {"known_aggregation_types": AGGREGATION_TYPES},
        meta,
    )
elif aggregation_period not in AGGREGATION_PERIODS:
    validation_error(
        "Invalid aggregation_period. Use a known Long-Term Statistics Period.",
        {"known_aggregation_periods": AGGREGATION_PERIODS},
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
    start_text = local_text_from_datetime(start_utc)
    end_text = local_text_from_datetime(end_utc)

    query_period = aggregation_period
    if aggregation_period == "total":
        duration_seconds = (end_utc - start_utc).total_seconds()
        if duration_seconds < TOTAL_SHORT_RANGE_SECONDS:
            query_period = "5minute"
        else:
            query_period = "hour"

    # Fetch and shape recorder statistics.
    recorder_response = call_recorder_statistics(
        query_period,
        start_utc,
        end_utc,
        entity_ids,
        aggregation_type,
    )
    statistics_payload = statistics_payload_from_response(recorder_response)

    if statistics_payload is None:
        full_meta = build_meta(
            entity_ids,
            start_text,
            end_text,
            aggregation_type,
            aggregation_period,
            0,
            0,
            end_time_was_defaulted,
        )
        validation_error(
            "Invalid recorder response shape. Inspect recorder.get_statistics response in Script trace.",
            {"expected": "mapping with statistics mapping"},
            full_meta,
        )

if output.get("success") is not False:
    entities, missing_entities = build_entities(
        statistics_payload,
        entity_ids,
        aggregation_type,
        aggregation_period,
        start_text,
        end_text,
    )

    if entities is None:
        full_meta = build_meta(
            entity_ids,
            start_text,
            end_text,
            aggregation_type,
            aggregation_period,
            0,
            0,
            end_time_was_defaulted,
        )
        validation_error(
            "Invalid recorder response shape. Inspect recorder.get_statistics response in Script trace.",
            {"expected": "statistics rows with start, end, and requested value type"},
            full_meta,
        )

if (
    output.get("success") is not False
    and aggregation_period == "total"
    and query_period == "5minute"
    and value_row_count(entities) == 0
):
    # Short total queries prefer 5-minute data but retry hourly data if needed.
    recorder_response = call_recorder_statistics(
        "hour",
        start_utc,
        end_utc,
        entity_ids,
        aggregation_type,
    )
    statistics_payload = statistics_payload_from_response(recorder_response)

    if statistics_payload is None:
        full_meta = build_meta(
            entity_ids,
            start_text,
            end_text,
            aggregation_type,
            aggregation_period,
            0,
            0,
            end_time_was_defaulted,
        )
        validation_error(
            "Invalid recorder response shape. Inspect recorder.get_statistics response in Script trace.",
            {"expected": "mapping with statistics mapping"},
            full_meta,
        )

    if output.get("success") is not False:
        entities, missing_entities = build_entities(
            statistics_payload,
            entity_ids,
            aggregation_type,
            aggregation_period,
            start_text,
            end_text,
        )

        if entities is None:
            full_meta = build_meta(
                entity_ids,
                start_text,
                end_text,
                aggregation_type,
                aggregation_period,
                0,
                0,
                end_time_was_defaulted,
            )
            validation_error(
                "Invalid recorder response shape. Inspect recorder.get_statistics response in Script trace.",
                {"expected": "statistics rows with start, end, and requested value type"},
                full_meta,
            )

if output.get("success") is not False:
    total = value_row_count(entities)

    if aggregation_period == "total":
        response_entities = entities
        count = total
    else:
        response_entities = truncate_entities(entities)
        count = value_row_count(response_entities)

    response_meta = build_meta(
        entity_ids,
        start_text,
        end_text,
        aggregation_type,
        aggregation_period,
        count,
        total,
        end_time_was_defaulted,
    )

    if total == 0:
        output["success"] = False
        output["error"] = "No statistics found for requested entity IDs and time range."
        output["data"] = {
            "entities": [],
            "missing_entities": missing_entities,
        }
        output["meta"] = response_meta
    else:
        output["success"] = True
        output["answer"] = success_answer(count, total, len(missing_entities))
        output["data"] = {
            "entities": response_entities,
            "missing_entities": missing_entities,
        }
        output["meta"] = response_meta
