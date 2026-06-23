TOOL_NAME = "llmtool_media_player_group_manager"
OPERATIONS = ["join", "unjoin", "clear_members"]


# Small helpers keep the top-level python_script flow readable.
def as_text(value):
    if value is None:
        return ""
    return str(value).strip()


def as_bool(value):
    if value is True:
        return True
    if value is False:
        return False

    text = as_text(value).lower()
    return text == "true" or text == "on" or text == "yes" or text == "1"


def validation_error(message, data_payload=None, meta_payload=None):
    output["success"] = False
    output["error"] = message
    output["data"] = data_payload or {}
    output["meta"] = meta_payload or {"tool": TOOL_NAME}


def plural(value, singular, plural_text):
    if value == 1:
        return singular
    return plural_text


def is_media_player_entity_id(value):
    parts = value.split(".")
    if len(parts) != 2:
        return False

    domain = parts[0]
    object_id = parts[1]
    if domain != "media_player" or not object_id:
        return False

    valid_chars = "abcdefghijklmnopqrstuvwxyz0123456789_"
    for char in object_id:
        if char not in valid_chars:
            return False

    return True


def append_unique(items, value):
    if value and value not in items:
        items.append(value)


def parse_entity_ids(raw_entity_ids):
    entity_ids = []
    invalid_entity_ids = []
    duplicate_entity_ids = []

    for part in str(raw_entity_ids or "").split(","):
        entity_id = part.strip()
        if not entity_id:
            continue

        if not is_media_player_entity_id(entity_id):
            append_unique(invalid_entity_ids, entity_id)
        elif entity_id in entity_ids:
            append_unique(duplicate_entity_ids, entity_id)
        else:
            entity_ids.append(entity_id)

    return entity_ids, invalid_entity_ids, duplicate_entity_ids


def parse_current_group_members(raw_members):
    if raw_members is None or isinstance(raw_members, str):
        return []

    entity_ids = []
    try:
        for raw_member in raw_members:
            entity_id = as_text(raw_member)
            if is_media_player_entity_id(entity_id):
                append_unique(entity_ids, entity_id)
    except TypeError:
        return []

    return entity_ids


def base_meta(operation, leader_entity_id=None):
    meta = {"tool": TOOL_NAME, "operation": operation}
    if leader_entity_id:
        meta["leader_entity_id"] = leader_entity_id
    return meta


def build_prepare_payload(
    operation,
    leader_entity_id,
    member_entity_ids,
    unjoin_entity_ids,
    previous_member_entity_ids,
    ignored_member_entity_ids,
    duplicate_member_entity_ids,
    ungroup_first,
    replace_existing,
):
    join_leader_entity_id = ""
    join_member_entity_ids = []
    if operation == "join":
        join_leader_entity_id = leader_entity_id
        join_member_entity_ids = member_entity_ids

    return {
        "operation": operation,
        "leader_entity_id": leader_entity_id,
        "member_entity_ids": member_entity_ids,
        "join_leader_entity_id": join_leader_entity_id,
        "join_member_entity_ids": join_member_entity_ids,
        "unjoin_entity_ids": unjoin_entity_ids,
        "previous_member_entity_ids": previous_member_entity_ids,
        "ignored_member_entity_ids": ignored_member_entity_ids,
        "duplicate_member_entity_ids": duplicate_member_entity_ids,
        "ungroup_first": ungroup_first,
        "replace_existing": replace_existing,
    }


def prepare_mode():
    operation = as_text(data.get("operation")).lower()
    leader_entity_id = as_text(data.get("leader_entity_id"))
    raw_member_entity_ids = as_text(data.get("member_entity_ids"))
    ungroup_first = as_bool(data.get("ungroup_first"))
    replace_existing = as_bool(data.get("replace_existing"))

    member_entity_ids, invalid_member_entity_ids, duplicate_member_entity_ids = parse_entity_ids(raw_member_entity_ids)
    current_group_members = parse_current_group_members(data.get("current_group_members"))
    previous_member_entity_ids = []
    for entity_id in current_group_members:
        if entity_id != leader_entity_id:
            previous_member_entity_ids.append(entity_id)

    meta = base_meta(operation, leader_entity_id)

    if operation not in OPERATIONS:
        validation_error(
            "Invalid operation. Use a known Media Player Group Manager operation.",
            {"known_operations": OPERATIONS},
            meta,
        )

    if output.get("success") is not False and leader_entity_id and not is_media_player_entity_id(leader_entity_id):
        validation_error(
            "Invalid entity ID. Use Home Assistant media_player.* entity IDs.",
            {"invalid_entity_ids": [leader_entity_id]},
            meta,
        )

    if output.get("success") is not False:
        invalid_flags = []
        if operation != "join" and ungroup_first:
            invalid_flags.append("ungroup_first")
        if operation != "join" and replace_existing:
            invalid_flags.append("replace_existing")
        if invalid_flags:
            validation_error(
                "Invalid flags. ungroup_first and replace_existing are only valid for join.",
                {"invalid_flags": invalid_flags},
                meta,
            )

    if output.get("success") is not False and invalid_member_entity_ids:
        validation_error(
            "Invalid entity ID. Use Home Assistant media_player.* entity IDs.",
            {"invalid_entity_ids": invalid_member_entity_ids},
            meta,
        )

    if output.get("success") is not False and operation == "unjoin" and leader_entity_id:
        validation_error(
            "leader_entity_id is not used for unjoin. Pass players to member_entity_ids.",
            {"invalid_parameters": ["leader_entity_id"]},
            meta,
        )

    if output.get("success") is not False and operation == "clear_members" and member_entity_ids:
        validation_error(
            "Do not provide member_entity_ids for clear_members.",
            {"invalid_parameters": ["member_entity_ids"]},
            meta,
        )

    if output.get("success") is not False and operation == "join" and not leader_entity_id:
        validation_error(
            "Missing leader_entity_id. Provide a media_player.* entity ID for join.",
            {"required": "leader_entity_id"},
            meta,
        )

    if output.get("success") is not False and operation == "clear_members" and not leader_entity_id:
        validation_error(
            "Missing leader_entity_id. Provide a media_player.* entity ID for clear_members.",
            {"required": "leader_entity_id"},
            meta,
        )

    if output.get("success") is not False and operation == "unjoin" and not member_entity_ids:
        validation_error(
            "Missing member_entity_ids. Provide media_player.* entity IDs to unjoin.",
            {"required": "member_entity_ids"},
            meta,
        )

    ignored_member_entity_ids = []
    final_member_entity_ids = []
    if output.get("success") is not False:
        if operation == "join":
            for entity_id in member_entity_ids:
                if entity_id == leader_entity_id:
                    append_unique(ignored_member_entity_ids, entity_id)
                else:
                    final_member_entity_ids.append(entity_id)
        else:
            final_member_entity_ids = member_entity_ids

    if output.get("success") is not False and operation == "join" and not final_member_entity_ids:
        validation_error(
            "join requires at least one member_entity_id different from leader_entity_id.",
            {
                "required": "member_entity_ids",
                "ignored_member_entity_ids": ignored_member_entity_ids,
                "duplicate_member_entity_ids": duplicate_member_entity_ids,
            },
            meta,
        )

    if output.get("success") is not False:
        unjoin_entity_ids = []
        if operation == "join":
            if ungroup_first:
                append_unique(unjoin_entity_ids, leader_entity_id)
                for entity_id in final_member_entity_ids:
                    append_unique(unjoin_entity_ids, entity_id)
            if replace_existing:
                for entity_id in previous_member_entity_ids:
                    append_unique(unjoin_entity_ids, entity_id)
        elif operation == "unjoin":
            for entity_id in final_member_entity_ids:
                append_unique(unjoin_entity_ids, entity_id)
        else:
            for entity_id in previous_member_entity_ids:
                append_unique(unjoin_entity_ids, entity_id)

        output["success"] = True
        output["data"] = build_prepare_payload(
            operation,
            leader_entity_id,
            final_member_entity_ids,
            unjoin_entity_ids,
            previous_member_entity_ids,
            ignored_member_entity_ids,
            duplicate_member_entity_ids,
            ungroup_first,
            replace_existing,
        )
        output["meta"] = meta


def shape_mode():
    operation = as_text(data.get("operation")).lower()
    leader_entity_id = as_text(data.get("leader_entity_id"))
    join_member_entity_ids, _, _ = parse_entity_ids(data.get("join_member_entity_ids"))
    unjoin_entity_ids, _, _ = parse_entity_ids(data.get("unjoin_entity_ids"))
    previous_member_entity_ids, _, _ = parse_entity_ids(data.get("previous_member_entity_ids"))
    ignored_member_entity_ids, _, _ = parse_entity_ids(data.get("ignored_member_entity_ids"))
    duplicate_member_entity_ids, _, _ = parse_entity_ids(data.get("duplicate_member_entity_ids"))
    ungroup_first = as_bool(data.get("ungroup_first"))
    replace_existing = as_bool(data.get("replace_existing"))

    meta = base_meta(operation, leader_entity_id)

    if operation not in OPERATIONS:
        validation_error(
            "Invalid Media Player Group Manager helper handoff. Inspect the Script trace.",
            {},
            {"tool": TOOL_NAME, "operation": operation},
        )

    if output.get("success") is not False and operation == "join":
        count = len(join_member_entity_ids)
        payload = {
            "operation": operation,
            "leader_entity_id": leader_entity_id,
            "joined_member_entity_ids": join_member_entity_ids,
            "unjoined_entity_ids": unjoin_entity_ids,
            "ignored_member_entity_ids": ignored_member_entity_ids,
            "duplicate_member_entity_ids": duplicate_member_entity_ids,
            "ungroup_first": ungroup_first,
            "replace_existing": replace_existing,
        }
        if previous_member_entity_ids:
            payload["previous_member_entity_ids"] = previous_member_entity_ids

        output["success"] = True
        output["answer"] = "Joined {} media player group {}.".format(
            count,
            plural(count, "member", "members"),
        )
        output["data"] = payload
        output["meta"] = meta

    if output.get("success") is not False and operation == "unjoin":
        count = len(unjoin_entity_ids)
        output["success"] = True
        output["answer"] = "Unjoined {} media {}.".format(
            count,
            plural(count, "player", "players"),
        )
        output["data"] = {
            "operation": operation,
            "unjoined_entity_ids": unjoin_entity_ids,
            "duplicate_member_entity_ids": duplicate_member_entity_ids,
        }
        output["meta"] = meta

    if output.get("success") is not False and operation == "clear_members":
        count = len(unjoin_entity_ids)
        output["success"] = True
        output["answer"] = "Cleared {} media player group {}.".format(
            count,
            plural(count, "member", "members"),
        )
        output["data"] = {
            "operation": operation,
            "leader_entity_id": leader_entity_id,
            "cleared_member_entity_ids": unjoin_entity_ids,
            "previous_member_entity_ids": previous_member_entity_ids,
        }
        output["meta"] = meta


mode = as_text(data.get("mode")) or "prepare"

if mode == "prepare":
    prepare_mode()
elif mode == "shape":
    shape_mode()
else:
    validation_error(
        "Invalid Media Player Group Manager helper mode. Inspect the Script trace.",
        {"known_modes": ["prepare", "shape"]},
        {"tool": TOOL_NAME},
    )
