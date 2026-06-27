DEFAULT_LIMIT = 50
MAX_LIMIT = 1000


# Small helpers keep the top-level python_script flow readable.
def as_text(value):
    if value is None:
        return ""
    return str(value).strip()


def parse_labels(raw_labels):
    parsed = []
    for part in str(raw_labels or "").split(","):
        label = part.strip()
        if label and label not in parsed:
            parsed.append(label)
    return parsed


def validation_error(message, data_payload=None, meta_payload=None):
    output["success"] = False
    output["error"] = message
    output["data"] = data_payload or {}
    output["meta"] = meta_payload or {}


def normalized_unit(value):
    return as_text(value).lower().replace(" ", "").replace("\u00b3", "3")


def cumulative_value_hint(match):
    if match.get("domain") != "sensor":
        return ""

    state_class = as_text(match.get("state_class")).lower()
    device_class = as_text(match.get("device_class")).lower()
    unit = normalized_unit(match.get("unit_of_measurement"))

    if state_class in ["total", "total_increasing"]:
        return "cumulative; for usage over time use Long-Term Aggregated Statistics with aggregation_type=change"

    if device_class in ["energy", "gas", "water"] and unit in ["wh", "kwh", "mwh", "l", "ml", "m3"]:
        return "cumulative; for usage over time use Long-Term Aggregated Statistics with aggregation_type=change"

    if unit in ["wh", "kwh", "mwh"]:
        return "cumulative; for usage over time use Long-Term Aggregated Statistics with aggregation_type=change"

    return ""


# Normalize script input and internal label names.
known_label_names = data.get("known_labels") or []
visibility_label_name = as_text(data.get("visibility_label")) or "Everywhere"
inside_label_name = as_text(data.get("inside_label")) or "Inside"
outside_label_name = as_text(data.get("outside_label")) or "Outside"

requested_labels = parse_labels(data.get("labels", ""))
location = as_text(data.get("location"))
query_mode = as_text(data.get("query_mode")) or "by_labels"
match_mode = as_text(data.get("match_mode")) or "all"
verbosity = as_text(data.get("verbosity")) or "compact"
state_filter = as_text(data.get("state_filter"))
raw_limit = as_text(data.get("limit"))

valid_locations = ["inside", "outside", "everywhere"]
valid_query_modes = ["by_labels", "all_labeled"]
valid_match_modes = ["all", "any"]
valid_verbosity = ["id_only", "compact", "detailed"]

# Validate caller parameters before touching candidate records.
if location not in valid_locations:
    validation_error(
        "Invalid location. Use inside, outside, or everywhere.",
        {"known_locations": valid_locations},
    )
elif query_mode not in valid_query_modes:
    validation_error(
        "Invalid query_mode. Use by_labels or all_labeled.",
        {"known_query_modes": valid_query_modes},
    )
elif match_mode not in valid_match_modes:
    validation_error(
        "Invalid match_mode. Use all or any.",
        {"known_match_modes": valid_match_modes},
    )
elif verbosity not in valid_verbosity:
    validation_error(
        "Invalid verbosity. Use id_only, compact, or detailed.",
        {"known_verbosity": valid_verbosity},
    )
else:
    limit = DEFAULT_LIMIT
    if raw_limit:
        try:
            limit = int(raw_limit)
        except ValueError:
            validation_error(
                "Invalid limit. Use an integer from 1 to 1000.",
                {"default_limit": DEFAULT_LIMIT, "max_limit": MAX_LIMIT},
            )

    if output.get("success") is not False:
        if limit < 1 or limit > MAX_LIMIT:
            validation_error(
                "Invalid limit. Use an integer from 1 to 1000.",
                {"default_limit": DEFAULT_LIMIT, "max_limit": MAX_LIMIT},
            )

    if output.get("success") is not False:
        unknown_labels = []
        internal_labels = [visibility_label_name, inside_label_name, outside_label_name]
        for label in requested_labels:
            if label in internal_labels or label not in known_label_names:
                unknown_labels.append(label)

        if unknown_labels:
            validation_error(
                "Unknown label name. Use data.known_labels and retry.",
                {
                    "unknown_labels": unknown_labels,
                    "known_labels": known_label_names,
                },
            )

    if output.get("success") is not False and query_mode == "by_labels" and not requested_labels:
        validation_error(
            "query_mode=by_labels requires at least one label name.",
            {"known_labels": known_label_names},
        )

if output.get("success") is not False:
    # Convert public query choices into the matching rules used below.
    if location == "inside":
        location_label = inside_label_name
    elif location == "outside":
        location_label = outside_label_name
    else:
        location_label = ""

    if query_mode == "all_labeled":
        required_match_labels = []
        reported_match_labels = []
        for label in known_label_names:
            reported_match_labels.append(label)
    else:
        required_match_labels = []
        reported_match_labels = []
        for label in requested_labels:
            required_match_labels.append(label)
            reported_match_labels.append(label)

    candidates = data.get("candidates") or []
    if isinstance(candidates, str):
        validation_error(
            "Invalid candidate handoff. Candidate records arrived as a string; inspect candidate_records_json and the from_json action handoff in the Script trace.",
            {"expected": "list", "received": "string"},
            {
                "query_mode": query_mode,
                "label_names": requested_labels,
                "location": location,
            },
        )

if output.get("success") is not False:
    # Filter HA-collected candidates by visibility, location, labels, and state.
    matches = []
    for candidate in candidates:
        if "entity_id" not in candidate:
            continue

        entity_id = as_text(candidate["entity_id"])
        if not entity_id:
            continue

        if "visibility_matched" not in candidate or not candidate["visibility_matched"]:
            continue

        candidate_matched_labels = []
        if "matched_labels" in candidate:
            for label in candidate["matched_labels"] or []:
                candidate_matched_labels.append(label)

        if location_label and ("location_matched" not in candidate or not candidate["location_matched"]):
            continue

        state = ""
        if "state" in candidate:
            state = as_text(candidate["state"])

        if state_filter and state != state_filter:
            continue

        required_labels_found = []
        for label in required_match_labels:
            if label in candidate_matched_labels and label not in required_labels_found:
                required_labels_found.append(label)

        if query_mode == "by_labels" and match_mode == "all":
            if len(required_labels_found) != len(required_match_labels):
                continue
        elif query_mode == "by_labels" and not required_labels_found:
            continue

        matched_labels = []
        for label in reported_match_labels:
            if label in candidate_matched_labels and label not in matched_labels:
                matched_labels.append(label)

        shaped = {
            "entity_id": entity_id,
            "friendly_name": as_text(candidate["friendly_name"]) or entity_id,
            "state": state,
            "matched_labels": matched_labels,
            "domain": as_text(candidate["domain"]),
        }

        for optional_field in [
            "area_id",
            "device_id",
            "unit_of_measurement",
            "device_class",
            "state_class",
        ]:
            optional_value = ""
            if optional_field in candidate:
                optional_value = as_text(candidate[optional_field])
            if optional_value:
                shaped[optional_field] = optional_value

        matches.append(shaped)

    # Sort, limit, and shape the final response for Assist.
    matches.sort(key=lambda item: item["entity_id"])
    total = len(matches)
    limited_matches = matches[:limit]

    if verbosity == "id_only":
        entities = []
        for match in limited_matches:
            entities.append(match["entity_id"])
    else:
        entities = []
        for match in limited_matches:
            entity = {
                "entity_id": match["entity_id"],
                "friendly_name": match["friendly_name"],
                "state": match["state"],
                "matched_labels": match["matched_labels"],
            }

            if verbosity == "detailed":
                for detail_field in [
                    "domain",
                    "area_id",
                    "device_id",
                    "unit_of_measurement",
                    "device_class",
                    "state_class",
                ]:
                    if detail_field in match:
                        entity[detail_field] = match[detail_field]

            value_hint = cumulative_value_hint(match)
            if value_hint:
                entity["value_hint"] = value_hint

            entities.append(entity)

    meta = {
        "tool": "llmtool_entity_index",
        "count": len(entities),
        "total": total,
        "query_mode": query_mode,
        "label_names": requested_labels,
        "location": location,
        "match_mode": match_mode,
        "state_filter": state_filter,
        "verbosity": verbosity,
        "limit": limit,
    }

    if total > limit:
        meta["truncated"] = True

    output["success"] = True
    output["answer"] = "Found {} matching entities.".format(len(entities))
    output["data"] = {"entities": entities}
    output["meta"] = meta
