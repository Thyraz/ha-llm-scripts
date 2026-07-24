TOOL_NAME = "llmtool_weather_forecast"
DEFAULT_LIMIT = 24
MAX_LIMIT = 168
TRUNCATION_RETRY_HINT = "Retry with a higher limit or narrower Weather Forecast Time Range if needed forecast rows were not included."

FORECAST_TYPES = ["daily", "hourly"]
VERBOSITIES = ["overview", "detailed"]
WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
PRECIPITATION_CONDITIONS = [
    "rainy",
    "pouring",
    "snowy",
    "snowy-rainy",
    "hail",
    "lightning-rainy",
]
WIND_CONDITIONS = ["windy", "windy-variant"]

SUPPORTED_DETAIL_FIELDS = [
    "temperature",
    "templow",
    "apparent_temperature",
    "dew_point",
    "humidity",
    "cloud_coverage",
    "precipitation",
    "precipitation_probability",
    "pressure",
    "uv_index",
    "wind_bearing",
    "wind_gust_speed",
    "wind_speed",
    "is_daytime",
]

NUMERIC_FIELDS = [
    "temperature",
    "templow",
    "apparent_temperature",
    "dew_point",
    "humidity",
    "cloud_coverage",
    "precipitation",
    "precipitation_probability",
    "pressure",
    "uv_index",
    "wind_gust_speed",
    "wind_speed",
]


# Small helpers keep the top-level python_script flow readable.
def as_text(value):
    if value is None:
        return ""
    return str(value).strip()


def mapping_value(value, key, default_value=None):
    try:
        return value[key]
    except (KeyError, TypeError):
        pass

    try:
        getter = value.get
    except AttributeError:
        return default_value

    if getter is None:
        return default_value

    try:
        return getter(key, default_value)
    except TypeError:
        try:
            return getter(key)
        except TypeError:
            return default_value


def is_text_value(value):
    if value is None:
        return False
    try:
        value + ""
        return True
    except TypeError:
        return False


def is_sequence(value):
    if value is None or is_text_value(value):
        return False
    try:
        for _ in value:
            return True
    except TypeError:
        return False
    return True


def validation_error(message, data_payload=None, meta_payload=None):
    output["success"] = False
    output["error"] = message
    output["data"] = data_payload or {}
    output["meta"] = meta_payload or {"tool": TOOL_NAME}


def plural(value, singular, plural_text):
    if value == 1:
        return singular
    return plural_text


def is_weather_entity_id(value):
    parts = value.split(".")
    if len(parts) != 2:
        return False

    domain = parts[0]
    object_id = parts[1]
    if domain != "weather" or not object_id:
        return False

    valid_chars = "abcdefghijklmnopqrstuvwxyz0123456789_"
    for char in object_id:
        if char not in valid_chars:
            return False
    return True


def available_weather_entity_ids():
    entity_ids = []

    try:
        discovered = hass.states.entity_ids("weather")
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
        if is_weather_entity_id(entity_id_text) and entity_id_text not in entity_ids:
            entity_ids.append(entity_id_text)

    entity_ids.sort()
    return entity_ids


def weather_entity_exists(entity_id):
    try:
        state = hass.states.get(entity_id)
    except AttributeError:
        state = None
    return state is not None


def weather_units(entity_id):
    units = {}
    try:
        state = hass.states.get(entity_id)
    except AttributeError:
        state = None

    if state is None:
        return units

    attributes = state.attributes or {}
    for key in [
        "temperature_unit",
        "precipitation_unit",
        "pressure_unit",
        "wind_speed_unit",
    ]:
        value = as_text(mapping_value(attributes, key))
        if value:
            units[key] = value
    return units


def has_date_format(value):
    if len(value) != 10:
        return False
    if value[4] != "-" or value[7] != "-":
        return False
    for position in [0, 1, 2, 3, 5, 6, 8, 9]:
        char = value[position]
        if char < "0" or char > "9":
            return False
    return True


def has_strict_time_format(value):
    if len(value) != 19:
        return False
    if value[4] != "-" or value[7] != "-" or value[10] != " ":
        return False
    if value[13] != ":" or value[16] != ":":
        return False
    for position in [0, 1, 2, 3, 5, 6, 8, 9, 11, 12, 14, 15, 17, 18]:
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


def parse_forecast_datetime(value):
    text = as_text(value)
    if not text:
        return None

    local_date = parse_local_date(text)
    if local_date is not None:
        return local_date

    local_time = parse_local_time(text)
    if local_time is not None:
        return local_time

    try:
        parsed = dt_util.parse_datetime(text)
    except AttributeError:
        parsed = None
    except TypeError:
        parsed = None
    except ValueError:
        parsed = None

    if parsed is None:
        return None
    return local_naive_from_datetime(parsed)


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


def local_date_text(value):
    return "{}-{}-{}".format(
        str(value.year).rjust(4, "0"),
        two_digit(value.month),
        two_digit(value.day),
    )


def time_text(value):
    return "{}:{}:{}".format(
        two_digit(value.hour),
        two_digit(value.minute),
        two_digit(value.second),
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


def midnight(value):
    return datetime.datetime(value.year, value.month, value.day, 0, 0, 0)


def weekday_name(value):
    return WEEKDAYS[value.weekday()]


def parse_limit(raw_limit):
    text = as_text(raw_limit)
    if not text:
        return DEFAULT_LIMIT, ""

    if text.endswith(".0"):
        text = text[:-2]
    if not text:
        return None, "Invalid limit. Use an integer from 1 to 168."
    for char in text:
        if char < "0" or char > "9":
            return None, "Invalid limit. Use an integer from 1 to 168."

    limit = int(text)
    if limit < 1 or limit > MAX_LIMIT:
        return None, "Invalid limit. Use an integer from 1 to 168."
    return limit, ""


def normalize_number(value):
    if value is True or value is False or value is None:
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    positive_inf = float("inf")
    if number == positive_inf or number == -positive_inf or number != number:
        return None

    integer_value = int(number)
    if number == integer_value:
        return integer_value
    return number


def shape_field_value(field_name, value):
    if value is None:
        return None

    if field_name in NUMERIC_FIELDS:
        return normalize_number(value)

    if field_name == "is_daytime":
        if value is True or value is False:
            return value
        text = as_text(value).lower()
        if text in ["true", "on", "yes", "1"]:
            return True
        if text in ["false", "off", "no", "0"]:
            return False
        return None

    if field_name == "wind_bearing":
        number = normalize_number(value)
        if number is not None:
            return number
        text = as_text(value)
        if text:
            return text
        return None

    text = as_text(value)
    if text:
        return text
    return None


def wind_speed_to_kmh(value, unit):
    number = normalize_number(value)
    if number is None:
        return None

    normalized_unit = as_text(unit).lower().replace(" ", "")
    if normalized_unit in ["m/s", "mps", "meter/second", "meters/second"]:
        return number * 3.6
    if normalized_unit in ["mph", "mi/h", "miles/hour"]:
        return number * 1.609344
    if normalized_unit in ["kn", "kt", "kts", "knot", "knots"]:
        return number * 1.852
    return number


def has_significant_precipitation(row):
    condition = as_text(mapping_value(row, "condition")).lower()
    precipitation = normalize_number(mapping_value(row, "precipitation"))
    probability = normalize_number(mapping_value(row, "precipitation_probability"))

    if condition in PRECIPITATION_CONDITIONS:
        return True
    if precipitation is not None and precipitation >= 0.1:
        return True
    if probability is not None and probability >= 30:
        return True
    return False


def has_significant_wind(row, units):
    condition = as_text(mapping_value(row, "condition")).lower()
    wind_unit = mapping_value(units, "wind_speed_unit", "")
    wind_speed = wind_speed_to_kmh(mapping_value(row, "wind_speed"), wind_unit)
    gust_speed = wind_speed_to_kmh(mapping_value(row, "wind_gust_speed"), wind_unit)

    if condition in WIND_CONDITIONS:
        return True
    if wind_speed is not None and wind_speed >= 30:
        return True
    if gust_speed is not None and gust_speed >= 45:
        return True
    return False


def add_available_field(target, row, field_name):
    value = shape_field_value(field_name, mapping_value(row, field_name))
    if value is not None:
        target[field_name] = value


def base_row_payload(row, row_time, include_datetime):
    payload = {}
    if include_datetime:
        payload["datetime"] = local_time_text(row_time)
        payload["date"] = local_date_text(row_time)
        payload["weekday"] = weekday_name(row_time)
        payload["time"] = time_text(row_time)

    condition = shape_field_value("condition", mapping_value(row, "condition"))
    if condition is not None:
        payload["condition"] = condition
    add_available_field(payload, row, "temperature")
    return payload


def shape_overview_row(row, row_time, forecast_type, units):
    if forecast_type == "daily":
        payload = {
            "date": local_date_text(row_time),
            "weekday": weekday_name(row_time),
        }
        condition = shape_field_value("condition", mapping_value(row, "condition"))
        if condition is not None:
            payload["condition"] = condition
        add_available_field(payload, row, "temperature")
        add_available_field(payload, row, "templow")
    else:
        payload = {
            "datetime": local_time_text(row_time),
            "time": time_text(row_time),
        }
        condition = shape_field_value("condition", mapping_value(row, "condition"))
        if condition is not None:
            payload["condition"] = condition
        add_available_field(payload, row, "temperature")

    if has_significant_precipitation(row):
        add_available_field(payload, row, "precipitation")
        add_available_field(payload, row, "precipitation_probability")

    if has_significant_wind(row, units):
        add_available_field(payload, row, "wind_speed")
        add_available_field(payload, row, "wind_gust_speed")
        add_available_field(payload, row, "wind_bearing")

    return payload


def shape_detailed_row(row, row_time):
    payload = base_row_payload(row, row_time, True)
    for field_name in SUPPORTED_DETAIL_FIELDS:
        add_available_field(payload, row, field_name)
    return payload


def response_meta(prepared, count, total):
    meta = {
        "tool": TOOL_NAME,
        "weather_entity_id": prepared["weather_entity_id"],
        "forecast_type": prepared["forecast_type"],
        "start_time": prepared["start_time"],
        "end_time": prepared["end_time"],
        "verbosity": prepared["verbosity"],
        "count": count,
        "total": total,
        "limit": prepared["limit"],
    }
    if prepared["units"]:
        meta["units"] = prepared["units"]
    if count < total:
        meta["truncated"] = True
    return meta


def truncation_payload(count, total, limit):
    return {
        "truncated": True,
        "count_returned": count,
        "count_total_before_truncation": total,
        "limit": limit,
        "retry_hint": TRUNCATION_RETRY_HINT,
    }


def prepare_mode():
    weather_entity_id = as_text(data.get("weather_entity_id"))
    forecast_type = as_text(data.get("forecast_type"))
    start_text = as_text(data.get("start_time"))
    end_text = as_text(data.get("end_time"))
    verbosity = as_text(data.get("verbosity")) or "overview"
    raw_limit = as_text(data.get("limit"))
    available_entities = available_weather_entity_ids()
    meta = {"tool": TOOL_NAME, "weather_entity_id": weather_entity_id}

    if not weather_entity_id:
        validation_error(
            "Missing weather_entity_id. Provide an exact Home Assistant weather.* entity ID.",
            {
                "required": "weather_entity_id",
                "available_weather_entity_ids": available_entities,
            },
            meta,
        )
    elif not is_weather_entity_id(weather_entity_id):
        validation_error(
            "Invalid weather_entity_id. Use a Home Assistant weather.* entity ID.",
            {
                "invalid_weather_entity_id": weather_entity_id,
                "available_weather_entity_ids": available_entities,
            },
            meta,
        )
    elif not weather_entity_exists(weather_entity_id):
        validation_error(
            "Unknown weather entity ID. Use an existing Home Assistant weather.* entity ID.",
            {
                "unknown_weather_entity_id": weather_entity_id,
                "available_weather_entity_ids": available_entities,
            },
            meta,
        )
    elif not forecast_type:
        validation_error(
            "Missing forecast_type. Use daily for full local days or hourly for part-day weather.",
            {"known_forecast_types": FORECAST_TYPES},
            meta,
        )
    elif forecast_type not in FORECAST_TYPES:
        validation_error(
            "Invalid forecast_type. Use daily or hourly.",
            {"known_forecast_types": FORECAST_TYPES},
            meta,
        )
    elif verbosity not in VERBOSITIES:
        validation_error(
            "Invalid verbosity. Use overview or detailed.",
            {"known_verbosity": VERBOSITIES},
            meta,
        )
    elif not start_text:
        validation_error(
            "Missing start_time. Use local time in format YYYY-MM-DD HH:MM:SS.",
            {"expected_format": "YYYY-MM-DD HH:MM:SS"},
            meta,
        )
    elif not end_text:
        validation_error(
            "Missing end_time. Use local time in format YYYY-MM-DD HH:MM:SS.",
            {"expected_format": "YYYY-MM-DD HH:MM:SS"},
            meta,
        )

    if output.get("success") is not False:
        start_local = parse_local_time(start_text)
        end_local = parse_local_time(end_text)
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

    if output.get("success") is not False and local_seconds(end_local) <= local_seconds(start_local):
        validation_error(
            "Invalid end_time. Use an end_time after start_time.",
            {
                "start_time": start_text,
                "end_time": end_text,
            },
            meta,
        )

    if output.get("success") is not False and forecast_type == "daily":
        if time_text(start_local) != "00:00:00" or time_text(end_local) != "00:00:00":
            validation_error(
                "Invalid Weather Forecast Time Range. Use daily only for full local days starting and ending at 00:00:00.",
                {
                    "forecast_type": "daily",
                    "required_time": "00:00:00",
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
        output["success"] = True
        output["data"] = {
            "weather_entity_id": weather_entity_id,
            "forecast_type": forecast_type,
            "start_time": local_time_text(start_local),
            "end_time": local_time_text(end_local),
            "verbosity": verbosity,
            "limit": limit,
            "units": weather_units(weather_entity_id),
        }
        output["meta"] = meta


def shape_mode():
    prepared = data.get("prepared")
    weather_response = data.get("weather_response")
    if prepared is None or is_text_value(prepared) or weather_response is None or is_text_value(weather_response):
        validation_error(
            "Invalid Weather Forecast helper handoff. Inspect the Script trace.",
            {},
            {"tool": TOOL_NAME},
        )
        return

    weather_entity_id = as_text(mapping_value(prepared, "weather_entity_id"))
    forecast_type = as_text(mapping_value(prepared, "forecast_type"))
    start_text = as_text(mapping_value(prepared, "start_time"))
    end_text = as_text(mapping_value(prepared, "end_time"))
    verbosity = as_text(mapping_value(prepared, "verbosity")) or "overview"
    limit, limit_error = parse_limit(mapping_value(prepared, "limit"))
    units = mapping_value(prepared, "units", {})
    meta = {"tool": TOOL_NAME, "weather_entity_id": weather_entity_id}

    start_local = parse_local_time(start_text)
    end_local = parse_local_time(end_text)
    if (
        not weather_entity_id
        or forecast_type not in FORECAST_TYPES
        or start_local is None
        or end_local is None
        or verbosity not in VERBOSITIES
        or limit_error
    ):
        validation_error(
            "Invalid Weather Forecast helper handoff. Inspect the Script trace.",
            {},
            meta,
        )
        return

    payload = mapping_value(weather_response, weather_entity_id)
    if payload is None:
        validation_error(
            "Invalid weather.get_forecasts response shape. Expected response keyed by weather entity ID.",
            {"expected": "mapping keyed by weather entity ID"},
            meta,
        )
        return

    forecast_rows = mapping_value(payload, "forecast")
    if forecast_rows is None:
        forecast_rows = []
    if not is_sequence(forecast_rows):
        validation_error(
            "Invalid weather.get_forecasts response shape. Expected a forecast list.",
            {"expected": "forecast list"},
            meta,
        )
        return

    # Normalize, filter, and sort rows before applying the global limit.
    matching_rows = []
    invalid_response = False
    start_seconds = local_seconds(start_local)
    end_seconds = local_seconds(end_local)

    for row in forecast_rows:
        if row is None or is_text_value(row):
            invalid_response = True
            break

        row_time = parse_forecast_datetime(mapping_value(row, "datetime"))
        if row_time is None:
            invalid_response = True
            break

        compare_time = row_time
        if forecast_type == "daily":
            compare_time = midnight(row_time)

        compare_seconds = local_seconds(compare_time)
        if compare_seconds >= start_seconds and compare_seconds < end_seconds:
            matching_rows.append({"row": row, "time": row_time, "compare_time": compare_time})

    if invalid_response:
        validation_error(
            "Invalid weather.get_forecasts response shape. Expected forecast rows with datetime.",
            {"expected": "forecast rows with datetime"},
            meta,
        )
        return

    matching_rows.sort(key=lambda item: local_seconds(item["compare_time"]))
    total = len(matching_rows)
    limited_rows = matching_rows[:limit]
    count = len(limited_rows)

    prepared_payload = {
        "weather_entity_id": weather_entity_id,
        "forecast_type": forecast_type,
        "start_time": start_text,
        "end_time": end_text,
        "verbosity": verbosity,
        "limit": limit,
        "units": units,
    }
    output_meta = response_meta(prepared_payload, count, total)

    if total == 0:
        output["success"] = False
        output["error"] = "No forecast rows found for requested Weather Forecast Time Range."
        output["data"] = {"days": []}
        output["meta"] = output_meta
        return

    days = []
    if forecast_type == "daily":
        for item in limited_rows:
            if verbosity == "detailed":
                days.append(shape_detailed_row(item["row"], item["compare_time"]))
            else:
                days.append(shape_overview_row(item["row"], item["compare_time"], forecast_type, units))
    else:
        grouped = {}
        day_order = []
        for item in limited_rows:
            row_time = item["time"]
            date_key = local_date_text(row_time)
            if date_key not in grouped:
                grouped[date_key] = {
                    "date": date_key,
                    "weekday": weekday_name(row_time),
                    "periods": [],
                }
                day_order.append(date_key)
            if verbosity == "detailed":
                grouped[date_key]["periods"].append(shape_detailed_row(item["row"], row_time))
            else:
                grouped[date_key]["periods"].append(shape_overview_row(item["row"], row_time, forecast_type, units))

        for date_key in day_order:
            days.append(grouped[date_key])

    data_payload = {"days": days}
    if count < total:
        data_payload["truncation"] = truncation_payload(count, total, limit)

    output["success"] = True
    noun = "days"
    if forecast_type == "hourly":
        noun = "periods"
    if count < total:
        output["answer"] = (
            "Found {} of {} forecast {}. Attention: returned data is truncated because "
            "total matching forecast rows ({}) exceeded limit ({}). {}".format(
                count,
                total,
                noun,
                total,
                limit,
                TRUNCATION_RETRY_HINT,
            )
        )
    else:
        output["answer"] = "Found {} forecast {}.".format(count, plural(count, noun[:-1], noun))
    output["data"] = data_payload
    output["meta"] = output_meta


mode = as_text(data.get("mode")) or "prepare"

if mode == "prepare":
    prepare_mode()
elif mode == "shape":
    shape_mode()
else:
    validation_error(
        "Invalid Weather Forecast helper mode. Inspect the Script trace.",
        {"known_modes": ["prepare", "shape"]},
        {"tool": TOOL_NAME},
    )
