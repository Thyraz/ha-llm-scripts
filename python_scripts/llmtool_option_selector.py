TOOL_NAME = "llmtool_option_selector"

OPERATIONS = ["get_options", "select_option"]
DOMAINS = ["input_select", "select"]

PARAMETER_NAMES = ["entity_id", "desired_option"]
ALLOWLISTS = {
    "get_options": ["operation", "entity_id"],
    "select_option": ["operation", "entity_id", "desired_option"],
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


def plural(value, singular, plural_text):
    if value == 1:
        return singular
    return plural_text


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


def entity_domain(entity_id):
    parts = entity_id.split(".")
    if len(parts) != 2:
        return ""
    return parts[0]


def is_valid_entity_id(entity_id):
    parts = entity_id.split(".")
    if len(parts) != 2:
        return False

    domain = parts[0]
    object_id = parts[1]
    if domain not in DOMAINS or not object_id:
        return False

    valid_chars = "abcdefghijklmnopqrstuvwxyz0123456789_"
    for char in object_id:
        if char not in valid_chars:
            return False

    return True


def entity_metadata(entity_id, state):
    attributes = state.attributes or {}
    friendly_name = as_text(mapping_value(attributes, "friendly_name")) or entity_id
    return {
        "entity_id": entity_id,
        "domain": entity_domain(entity_id),
        "friendly_name": friendly_name,
        "current": as_text(state.state),
    }


def normalize_options(raw_options):
    options = []
    if not is_sequence(raw_options):
        return options

    for option in raw_options:
        option_text = as_text(option)
        if option_text:
            options.append(option_text)

    return options


def resolve_desired_option(desired_option, options):
    exact_matches = []
    lower_matches = []
    desired_option_lower = desired_option.lower()

    for option in options:
        if option == desired_option:
            exact_matches.append(option)
        elif option.lower() == desired_option_lower:
            lower_matches.append(option)

    if len(exact_matches) == 1:
        return exact_matches[0], [], ""
    if len(exact_matches) > 1:
        return "", exact_matches, "ambiguous"
    if len(lower_matches) == 1:
        return lower_matches[0], [], ""
    if len(lower_matches) > 1:
        return "", lower_matches, "ambiguous"
    return "", [], "unknown"


# Normalize caller input.
operation = as_text(data.get("operation"))
entity_id = as_text(data.get("entity_id"))
desired_option = as_text(data.get("desired_option"))

meta = {"tool": TOOL_NAME, "operation": operation}

# Validate the public operation contract before reading entity data.
if operation not in OPERATIONS:
    validation_error(
        "Invalid operation. Use a known Option Selector operation.",
        {"known_operations": OPERATIONS},
        meta,
    )

if output.get("success") is not False:
    validate_allowlist(operation)

if output.get("success") is not False:
    if not entity_id:
        validation_error(
            "Missing entity_id. Provide an existing input_select.* or select.* entity ID.",
            {"expected_domains": DOMAINS},
            meta,
        )
    elif not is_valid_entity_id(entity_id):
        validation_error(
            "Invalid entity_id. Provide an existing input_select.* or select.* entity ID.",
            {"expected_domains": DOMAINS, "received": entity_id},
            meta,
        )

if output.get("success") is not False:
    state = hass.states.get(entity_id)
    if state is None:
        validation_error(
            "Unknown entity_id. Provide an existing input_select.* or select.* entity ID.",
            {"expected_domains": DOMAINS, "received": entity_id},
            meta,
        )

if output.get("success") is not False:
    entity = entity_metadata(entity_id, state)
    options = normalize_options(mapping_value(state.attributes or {}, "options"))

    if not options:
        validation_error(
            "Entity has no selectable options.",
            {
                "entity_id": entity["entity_id"],
                "domain": entity["domain"],
                "friendly_name": entity["friendly_name"],
                "current": entity["current"],
                "options": [],
            },
            meta,
        )

if output.get("success") is not False and operation == "select_option":
    if not desired_option:
        validation_error(
            "Missing desired_option. Provide one available option.",
            {
                "entity_id": entity["entity_id"],
                "domain": entity["domain"],
                "friendly_name": entity["friendly_name"],
                "allowed_options": options,
            },
            meta,
        )
    else:
        selected, matching_options, match_error = resolve_desired_option(desired_option, options)
        if match_error == "ambiguous":
            validation_error(
                "Ambiguous option. Use exact option.",
                {
                    "entity_id": entity["entity_id"],
                    "domain": entity["domain"],
                    "friendly_name": entity["friendly_name"],
                    "desired_option": desired_option,
                    "matching_options": matching_options,
                    "allowed_options": options,
                },
                meta,
            )
        elif match_error == "unknown":
            validation_error(
                "Unknown option. Use data.allowed_options and retry.",
                {
                    "entity_id": entity["entity_id"],
                    "domain": entity["domain"],
                    "friendly_name": entity["friendly_name"],
                    "desired_option": desired_option,
                    "allowed_options": options,
                },
                meta,
            )

if output.get("success") is not False:
    if operation == "get_options":
        output["success"] = True
        output["answer"] = "Found {} {}.".format(len(options), plural(len(options), "option", "options"))
        output["data"] = {
            "entity_id": entity["entity_id"],
            "domain": entity["domain"],
            "friendly_name": entity["friendly_name"],
            "current": entity["current"],
            "options": options,
        }
        output["meta"] = {
            "tool": TOOL_NAME,
            "operation": operation,
            "count": len(options),
        }
    else:
        output["success"] = True
        output["answer"] = "Resolved option."
        output["data"] = {
            "entity_id": entity["entity_id"],
            "domain": entity["domain"],
            "friendly_name": entity["friendly_name"],
            "previous": entity["current"],
            "selected": selected,
        }
        output["meta"] = {
            "tool": TOOL_NAME,
            "operation": operation,
        }
