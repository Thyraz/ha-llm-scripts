TOOL_NAME = "llmtool_memory_manager"
MEMORY_STORE_ENTITY_ID = "sensor.llm_memory"
SCHEMA_VERSION = 2
TEXT_LIMIT_BYTES = 4096
SOFT_LIMIT_BYTES = 96 * 1024
HARD_LIMIT_BYTES = 120 * 1024
DEFAULT_LIMIT = 10
MAX_LIMIT = 100
SNIPPET_LENGTH = 240

OPERATIONS = [
    "remember",
    "search",
    "read",
    "update",
    "forget",
    "inspect_inventory",
    "list_recent",
    "status",
]
TAG_MATCH_MODES = ["all", "any"]


# Small helpers keep the top-level python_script flow readable.
def as_text(value):
    if value is None:
        return ""
    return str(value).strip()


def as_bool(value):
    if isinstance(value, bool):
        return value
    return as_text(value).lower() in ["true", "1", "yes", "on"]


def plural(value, singular, plural_text):
    if value == 1:
        return singular
    return plural_text


def mapping_value(value, key, default_value=None):
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


def mapping_has_key(value, key):
    try:
        return key in value
    except TypeError:
        return False


def is_mapping(value):
    try:
        getter = value.get
        keys = value.keys
    except AttributeError:
        return False

    return getter is not None and keys is not None


def is_sequence(value):
    if value is None or isinstance(value, str):
        return False

    try:
        for _ in value:
            return True
    except TypeError:
        return False

    return True


def byte_len(value):
    try:
        return len(value.encode("utf-8"))
    except AttributeError:
        return len(str(value))


def is_int_value(value):
    return isinstance(value, int) and not isinstance(value, bool)


def validation_response(message, data_payload=None, meta_payload=None):
    return {
        "success": False,
        "error": message,
        "data": data_payload or {},
        "meta": meta_payload or {"tool": TOOL_NAME},
    }


def success_response(answer, data_payload, meta_payload):
    return {
        "success": True,
        "answer": answer,
        "data": data_payload,
        "meta": meta_payload,
    }


def base_meta(operation):
    return {"tool": TOOL_NAME, "operation": operation}


def tags_shape_error(operation):
    if not as_bool(data.get("tags_invalid_shape")):
        return None

    received_type = as_text(data.get("tags_received_type")) or "non-string"
    return validation_response(
        "Invalid tags. Use comma-separated text, not an array/list.",
        {
            "parameter": "tags",
            "expected": "comma-separated text",
            "received": received_type,
            "example": "schedule,kid_one",
        },
        base_meta(operation),
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


def now_text():
    return local_time_text(dt_util.as_local(dt_util.now()))


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


def normalize_key(value):
    text = as_text(value).lower()
    result = ""
    pending_separator = False

    for char in text:
        if ("a" <= char <= "z") or ("0" <= char <= "9"):
            if pending_separator and result:
                result = result + "_"
            result = result + char
            pending_separator = False
        else:
            pending_separator = True

    return result


def parse_tags(raw_tags):
    tags = []
    invalid_tags = []

    for part in str(raw_tags or "").split(","):
        raw_tag = part.strip()
        if not raw_tag:
            continue

        tag = normalize_key(raw_tag)
        if not tag:
            invalid_tags.append(raw_tag)
        elif tag not in tags:
            tags.append(tag)

    return tags, invalid_tags


def parse_limit(raw_limit):
    text = as_text(raw_limit)
    if not text:
        return DEFAULT_LIMIT, ""

    parsed_text = text
    if "." in parsed_text:
        parts = parsed_text.split(".")
        if len(parts) == 2 and parts[1] == "0":
            parsed_text = parts[0]
        else:
            return None, "Invalid limit. Use an integer from 1 to 100."

    if not parsed_text:
        return None, "Invalid limit. Use an integer from 1 to 100."

    for char in parsed_text:
        if char < "0" or char > "9":
            return None, "Invalid limit. Use an integer from 1 to 100."

    limit = int(parsed_text)
    if limit < 1 or limit > MAX_LIMIT:
        return None, "Invalid limit. Use an integer from 1 to 100."

    return limit, ""


def is_memory_id(value):
    text = as_text(value)
    if len(text) != 7 or text[0] != "m":
        return False

    for char in text[1:]:
        if char < "0" or char > "9":
            return False

    return True


def next_memory_id(next_id):
    return "m{}".format(str(next_id).rjust(6, "0"))


def memory_id_number(memory_id):
    if not is_memory_id(memory_id):
        return 0
    return int(memory_id[1:])


def empty_store():
    return {"schema_version": SCHEMA_VERSION, "next_id": 1, "entries": {}}


def store_from_entity():
    try:
        state = hass.states.get(MEMORY_STORE_ENTITY_ID)
    except AttributeError:
        state = None

    if state is None:
        return None, False, validation_response(
            "Memory Store Entity is missing. Create sensor.llm_memory with Variables+History, then retry.",
            {"memory_store_entity_id": MEMORY_STORE_ENTITY_ID},
            {"tool": TOOL_NAME},
        )

    attributes = state.attributes or {}
    if not is_mapping(attributes) or not mapping_has_key(attributes, "memory"):
        return empty_store(), True, None

    memory = mapping_value(attributes, "memory")
    return memory, False, None


def validate_store(memory):
    if not is_mapping(memory):
        return None, validation_response(
            "Malformed memory store. The memory attribute must be a mapping.",
            {"memory_store_entity_id": MEMORY_STORE_ENTITY_ID},
            {"tool": TOOL_NAME},
        )

    schema_version = mapping_value(memory, "schema_version")
    next_id = mapping_value(memory, "next_id")
    entries = mapping_value(memory, "entries")

    if schema_version != SCHEMA_VERSION:
        return None, validation_response(
            "Malformed memory store. Unsupported schema_version.",
            {"expected_schema_version": SCHEMA_VERSION},
            {"tool": TOOL_NAME},
        )
    if not is_int_value(next_id) or next_id < 1:
        return None, validation_response(
            "Malformed memory store. next_id must be a positive integer.",
            {"memory_store_entity_id": MEMORY_STORE_ENTITY_ID},
            {"tool": TOOL_NAME},
        )
    if not is_mapping(entries):
        return None, validation_response(
            "Malformed memory store. entries must be a mapping.",
            {"memory_store_entity_id": MEMORY_STORE_ENTITY_ID},
            {"tool": TOOL_NAME},
        )

    normalized_entries = {}
    max_entry_number = 0
    entry_ids = []
    try:
        for entry_id in entries.keys():
            entry_ids.append(entry_id)
    except TypeError:
        entry_ids = []

    for memory_id in entry_ids:
        memory_id_text = as_text(memory_id)
        entry = mapping_value(entries, memory_id)
        if not is_memory_id(memory_id_text) or not is_mapping(entry):
            return None, validation_response(
                "Malformed memory store. entries must be keyed by Memory ID.",
                {"memory_store_entity_id": MEMORY_STORE_ENTITY_ID},
                {"tool": TOOL_NAME},
            )

        topic = mapping_value(entry, "topic")
        tags = mapping_value(entry, "tags")
        text = mapping_value(entry, "text")
        created_at = mapping_value(entry, "created_at")
        updated_at = mapping_value(entry, "updated_at")

        topic_text = as_text(topic)
        if not topic_text or topic_text != normalize_key(topic_text):
            return None, validation_response(
                "Malformed memory store. Entry topics must be lower_snake text.",
                {"memory_id": memory_id_text},
                {"tool": TOOL_NAME},
            )
        if not is_sequence(tags):
            return None, validation_response(
                "Malformed memory store. Entry tags must be a list.",
                {"memory_id": memory_id_text},
                {"tool": TOOL_NAME},
            )

        normalized_tags = []
        for tag in tags:
            tag_text = as_text(tag)
            if not tag_text or tag_text != normalize_key(tag_text):
                return None, validation_response(
                    "Malformed memory store. Entry tags must be lower_snake text.",
                    {"memory_id": memory_id_text},
                    {"tool": TOOL_NAME},
                )
            if tag_text not in normalized_tags:
                normalized_tags.append(tag_text)

        if not normalized_tags:
            return None, validation_response(
                "Malformed memory store. Entry tags cannot be empty.",
                {"memory_id": memory_id_text},
                {"tool": TOOL_NAME},
            )
        if not isinstance(text, str):
            return None, validation_response(
                "Malformed memory store. Entry text must be text.",
                {"memory_id": memory_id_text},
                {"tool": TOOL_NAME},
            )

        created_at_text = as_text(created_at)
        updated_at_text = as_text(updated_at)
        if not has_strict_time_format(created_at_text) or not has_strict_time_format(updated_at_text):
            return None, validation_response(
                "Malformed memory store. Entry timestamps must use YYYY-MM-DD HH:MM:SS.",
                {"memory_id": memory_id_text},
                {"tool": TOOL_NAME},
            )

        normalized_entries[memory_id_text] = {
            "topic": topic_text,
            "tags": normalized_tags,
            "text": text,
            "created_at": created_at_text,
            "updated_at": updated_at_text,
        }

        entry_number = memory_id_number(memory_id_text)
        if entry_number > max_entry_number:
            max_entry_number = entry_number

    if next_id <= max_entry_number:
        return None, validation_response(
            "Malformed memory store. next_id must be greater than existing Memory IDs.",
            {"next_id": next_id, "max_existing_id": next_memory_id(max_entry_number)},
            {"tool": TOOL_NAME},
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "next_id": next_id,
        "entries": normalized_entries,
    }, None


def json_escape(value):
    result = ""
    for char in value:
        if char == "\\":
            result = result + "\\\\"
        elif char == '"':
            result = result + '\\"'
        elif char == "\n":
            result = result + "\\n"
        elif char == "\r":
            result = result + "\\r"
        elif char == "\t":
            result = result + "\\t"
        elif ord(char) < 32:
            result = result + "\\u{}".format(hex(ord(char))[2:].rjust(4, "0"))
        else:
            result = result + char
    return result


def normalized_json(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return '"' + json_escape(value) + '"'
    if isinstance(value, int) or isinstance(value, float):
        return str(value)
    if is_mapping(value):
        keys = []
        for key in value.keys():
            keys.append(as_text(key))
        keys.sort()

        parts = []
        for key in keys:
            parts.append(normalized_json(key) + ":" + normalized_json(mapping_value(value, key)))
        return "{" + ",".join(parts) + "}"

    parts = []
    for item in value:
        parts.append(normalized_json(item))
    return "[" + ",".join(parts) + "]"


def store_size_bytes(store):
    return byte_len(normalized_json(store))


def clone_store(store):
    cloned_entries = {}
    entries = store["entries"]
    for memory_id in entries:
        entry = entries[memory_id]
        tags = []
        for tag in entry["tags"]:
            tags.append(tag)
        cloned_entries[memory_id] = {
            "topic": entry["topic"],
            "tags": tags,
            "text": entry["text"],
            "created_at": entry["created_at"],
            "updated_at": entry["updated_at"],
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "next_id": store["next_id"],
        "entries": cloned_entries,
    }


def snippet(text):
    one_line = " ".join(as_text(text).split())
    if len(one_line) <= SNIPPET_LENGTH:
        return one_line
    return one_line[: SNIPPET_LENGTH - 3].rstrip() + "..."


def tokenize(value):
    tokens = []
    current = ""
    for char in as_text(value).lower():
        if ("a" <= char <= "z") or ("0" <= char <= "9"):
            current = current + char
        elif current:
            if current not in tokens:
                tokens.append(current)
            current = ""

    if current and current not in tokens:
        tokens.append(current)

    return tokens


def entry_tokens(entry):
    haystack = entry["topic"] + " " + " ".join(entry["tags"]) + " " + entry["text"]
    return tokenize(haystack)


def tags_match(entry_tags, requested_tags, mode):
    if not requested_tags:
        return True

    matched_count = 0
    for tag in requested_tags:
        if tag in entry_tags:
            matched_count = matched_count + 1

    if mode == "any":
        return matched_count > 0
    return matched_count == len(requested_tags)


def query_tokens_match(entry, query_tokens):
    if not query_tokens:
        return True

    tokens = entry_tokens(entry)
    for token in query_tokens:
        if token not in tokens:
            return False
    return True


def sorted_entry_ids_by_updated(entries):
    entry_ids = []
    for memory_id in entries:
        entry_ids.append(memory_id)
    entry_ids.sort(key=lambda memory_id: entries[memory_id]["updated_at"], reverse=True)
    return entry_ids


def entry_summary(memory_id, entry):
    return {
        "memory_id": memory_id,
        "topic": entry["topic"],
        "tags": entry["tags"],
        "snippet": snippet(entry["text"]),
        "updated_at": entry["updated_at"],
    }


def topic_count(store):
    topics = []
    for memory_id in store["entries"]:
        topic = store["entries"][memory_id]["topic"]
        if topic not in topics:
            topics.append(topic)
    return len(topics)


def store_warning_state(size_bytes):
    if size_bytes >= HARD_LIMIT_BYTES:
        return "hard_limit"
    if size_bytes >= SOFT_LIMIT_BYTES:
        return "soft_limit"
    return "ok"


def write_meta(operation, store):
    size_bytes = store_size_bytes(store)
    meta = base_meta(operation)
    meta["store_size_bytes"] = size_bytes
    meta["soft_limit_bytes"] = SOFT_LIMIT_BYTES
    meta["hard_limit_bytes"] = HARD_LIMIT_BYTES
    if size_bytes >= SOFT_LIMIT_BYTES:
        meta["warning"] = "Memory store is near size limit."
    return meta


def ensure_text_limit(text):
    if byte_len(text) > TEXT_LIMIT_BYTES:
        return validation_response(
            "Memory Entry text is too large. Use at most 4 KiB.",
            {"text_size_bytes": byte_len(text), "text_limit_bytes": TEXT_LIMIT_BYTES},
            {"tool": TOOL_NAME},
        )
    return None


def ensure_store_limit(operation, current_store, attempted_store):
    attempted_size = store_size_bytes(attempted_store)
    if attempted_size > HARD_LIMIT_BYTES:
        return validation_response(
            "Memory store is full. Ask the user to review Memory Manager entries and forget old entries before adding more.",
            {
                "store_size_bytes": store_size_bytes(current_store),
                "hard_limit_bytes": HARD_LIMIT_BYTES,
                "attempted_size_bytes": attempted_size,
            },
            base_meta(operation),
        )
    return None


def remember(store):
    meta = base_meta("remember")
    shape_error = tags_shape_error("remember")
    if shape_error:
        return shape_error, None

    topic = normalize_key(data.get("topic"))
    tags, invalid_tags = parse_tags(data.get("tags"))
    text = as_text(data.get("text"))

    if not topic:
        return validation_response("remember requires topic.", {"required": "topic"}, meta), None
    if invalid_tags:
        return validation_response("Invalid Memory Tag. Use short text tags.", {"invalid_tags": invalid_tags}, meta), None
    if not tags:
        return validation_response("remember requires at least one tag.", {"required": "tags"}, meta), None
    if not text:
        return validation_response("remember requires text.", {"required": "text"}, meta), None

    text_error = ensure_text_limit(text)
    if text_error:
        return text_error, None

    new_store = clone_store(store)
    memory_id = next_memory_id(new_store["next_id"])
    timestamp = now_text()
    new_store["entries"][memory_id] = {
        "topic": topic,
        "tags": tags,
        "text": text,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    new_store["next_id"] = new_store["next_id"] + 1

    limit_error = ensure_store_limit("remember", store, new_store)
    if limit_error:
        return limit_error, None

    return success_response(
        "Remembered 1 memory entry.",
        {"memory_id": memory_id, "topic": topic, "tags": tags},
        write_meta("remember", new_store),
    ), new_store


def inspect_inventory(store):
    topics = {}
    for memory_id in store["entries"]:
        entry = store["entries"][memory_id]
        topic = entry["topic"]
        if topic not in topics:
            topics[topic] = {"topic": topic, "count": 0, "tags": []}
        topics[topic]["count"] = topics[topic]["count"] + 1
        for tag in entry["tags"]:
            if tag not in topics[topic]["tags"]:
                topics[topic]["tags"].append(tag)

    result = []
    for topic in topics:
        topics[topic]["tags"].sort()
        result.append(topics[topic])
    result.sort(key=lambda item: item["topic"])

    count = len(result)
    return success_response(
        "Memory inventory has {} memory {}.".format(count, plural(count, "topic", "topics")),
        {"topics": result},
        {
            "tool": TOOL_NAME,
            "operation": "inspect_inventory",
            "topic_count": count,
            "entry_count": len(store["entries"]),
        },
    ), None


def search(store):
    meta = base_meta("search")
    shape_error = tags_shape_error("search")
    if shape_error:
        return shape_error, None

    raw_topic = as_text(data.get("topic"))
    topic = normalize_key(raw_topic) if raw_topic else ""
    tags, invalid_tags = parse_tags(data.get("tags"))
    tag_match_mode = as_text(data.get("tag_match_mode")).lower() or "all"
    query = as_text(data.get("query"))
    query_tokens = tokenize(query)
    limit, limit_error = parse_limit(data.get("limit"))

    if raw_topic and not topic:
        return validation_response("Invalid Memory Topic. Use short topic text.", {"invalid_topic": raw_topic}, meta), None
    if invalid_tags:
        return validation_response("Invalid Memory Tag. Use short text tags.", {"invalid_tags": invalid_tags}, meta), None
    if tag_match_mode not in TAG_MATCH_MODES:
        return validation_response(
            "Invalid tag_match_mode. Use all or any.",
            {"known_tag_match_modes": TAG_MATCH_MODES},
            meta,
        ), None
    if limit_error:
        return validation_response(limit_error, {"default_limit": DEFAULT_LIMIT, "max_limit": MAX_LIMIT}, meta), None
    if not topic and not tags and not query_tokens:
        return validation_response(
            "search requires query, topic, or tags.",
            {"required": "query, topic, or tags"},
            meta,
        ), None

    matches = []
    for memory_id in sorted_entry_ids_by_updated(store["entries"]):
        entry = store["entries"][memory_id]
        if topic and entry["topic"] != topic:
            continue
        if not tags_match(entry["tags"], tags, tag_match_mode):
            continue
        if not query_tokens_match(entry, query_tokens):
            continue
        matches.append(entry_summary(memory_id, entry))

    total = len(matches)
    entries = matches[:limit]
    meta = {
        "tool": TOOL_NAME,
        "operation": "search",
        "count": len(entries),
        "total": total,
        "query": query,
        "topic": topic,
        "tag_match_mode": tag_match_mode,
    }
    if tags:
        meta["tags"] = tags
    if total > limit:
        meta["truncated"] = True

    data_payload = {"entries": entries}
    answer = "Found {} matching memory {}.".format(len(entries), plural(len(entries), "entry", "entries"))
    if total == 0:
        hint = (
            "If you have not already inspected memory inventory for this user request, "
            "call inspect_inventory, choose existing topic/tags, and retry search before saying no memory was found."
        )
        answer = answer + " " + hint
        data_payload["hint"] = hint
        meta["hint"] = hint

    return success_response(
        answer,
        data_payload,
        meta,
    ), None


def read(store):
    memory_id = as_text(data.get("memory_id"))
    meta = base_meta("read")

    if not is_memory_id(memory_id):
        return validation_response("Invalid memory_id. Use a Memory ID such as m000001.", {"required": "memory_id"}, meta), None
    if memory_id not in store["entries"]:
        return validation_response("Unknown Memory ID.", {"memory_id": memory_id}, meta), None

    entry = store["entries"][memory_id]
    return success_response(
        "Read memory entry {}.".format(memory_id),
        {
            "memory_id": memory_id,
            "topic": entry["topic"],
            "tags": entry["tags"],
            "text": entry["text"],
            "created_at": entry["created_at"],
            "updated_at": entry["updated_at"],
        },
        meta,
    ), None


def update(store):
    meta = base_meta("update")
    shape_error = tags_shape_error("update")
    if shape_error:
        return shape_error, None

    memory_id = as_text(data.get("memory_id"))
    raw_topic = as_text(data.get("topic"))
    topic = normalize_key(raw_topic) if raw_topic else ""
    raw_tags = as_text(data.get("tags"))
    tags, invalid_tags = parse_tags(raw_tags)
    text = as_text(data.get("text"))

    if not is_memory_id(memory_id):
        return validation_response("Invalid memory_id. Use a Memory ID such as m000001.", {"required": "memory_id"}, meta), None
    if memory_id not in store["entries"]:
        return validation_response("Unknown Memory ID.", {"memory_id": memory_id}, meta), None
    if raw_topic and not topic:
        return validation_response("Invalid Memory Topic. Use short topic text.", {"invalid_topic": raw_topic}, meta), None
    if invalid_tags:
        return validation_response("Invalid Memory Tag. Use short text tags.", {"invalid_tags": invalid_tags}, meta), None
    if raw_tags and not tags:
        return validation_response("update tags cannot be empty when provided.", {"required": "tags"}, meta), None
    if not text:
        return validation_response("update requires replacement text.", {"required": "text"}, meta), None

    text_error = ensure_text_limit(text)
    if text_error:
        return text_error, None

    new_store = clone_store(store)
    entry = new_store["entries"][memory_id]
    if topic:
        entry["topic"] = topic
    if raw_tags:
        entry["tags"] = tags
    entry["text"] = text
    entry["updated_at"] = now_text()

    limit_error = ensure_store_limit("update", store, new_store)
    if limit_error:
        return limit_error, None

    return success_response(
        "Updated memory entry {}.".format(memory_id),
        {
            "memory_id": memory_id,
            "topic": entry["topic"],
            "tags": entry["tags"],
        },
        write_meta("update", new_store),
    ), new_store


def forget(store):
    memory_id = as_text(data.get("memory_id"))
    meta = base_meta("forget")

    if not is_memory_id(memory_id):
        return validation_response("Invalid memory_id. Use a Memory ID such as m000001.", {"required": "memory_id"}, meta), None
    if memory_id not in store["entries"]:
        return validation_response("Unknown Memory ID.", {"memory_id": memory_id}, meta), None

    new_store = clone_store(store)
    del new_store["entries"][memory_id]

    return success_response(
        "Forgot memory entry {}.".format(memory_id),
        {"memory_id": memory_id},
        write_meta("forget", new_store),
    ), new_store


def list_recent(store):
    limit, limit_error = parse_limit(data.get("limit"))
    meta = base_meta("list_recent")
    if limit_error:
        return validation_response(limit_error, {"default_limit": DEFAULT_LIMIT, "max_limit": MAX_LIMIT}, meta), None

    entries = []
    for memory_id in sorted_entry_ids_by_updated(store["entries"]):
        entries.append(entry_summary(memory_id, store["entries"][memory_id]))

    total = len(entries)
    limited = entries[:limit]
    meta = {
        "tool": TOOL_NAME,
        "operation": "list_recent",
        "count": len(limited),
        "total": total,
        "limit": limit,
    }
    if total > limit:
        meta["truncated"] = True

    return success_response(
        "Found {} recent memory {}.".format(len(limited), plural(len(limited), "entry", "entries")),
        {"entries": limited},
        meta,
    ), None


def status(store):
    size_bytes = store_size_bytes(store)
    entry_count = len(store["entries"])
    topic_total = topic_count(store)
    return success_response(
        "Memory Manager has {} memory {}.".format(entry_count, plural(entry_count, "entry", "entries")),
        {
            "entry_count": entry_count,
            "topic_count": topic_total,
            "store_size_bytes": size_bytes,
            "soft_limit_bytes": SOFT_LIMIT_BYTES,
            "hard_limit_bytes": HARD_LIMIT_BYTES,
            "warning_state": store_warning_state(size_bytes),
        },
        {
            "tool": TOOL_NAME,
            "operation": "status",
            "entry_count": entry_count,
            "topic_count": topic_total,
            "store_size_bytes": size_bytes,
        },
    ), None


def dispatch(operation, store):
    if operation == "remember":
        return remember(store)
    if operation == "search":
        return search(store)
    if operation == "read":
        return read(store)
    if operation == "update":
        return update(store)
    if operation == "forget":
        return forget(store)
    if operation == "inspect_inventory":
        return inspect_inventory(store)
    if operation == "list_recent":
        return list_recent(store)
    if operation == "status":
        return status(store)

    return validation_response(
        "Invalid operation. Use a known Memory Manager operation.",
        {"known_operations": OPERATIONS},
        {"tool": TOOL_NAME, "operation": operation},
    ), None


operation = as_text(data.get("operation")).lower()
response = None
write_memory = None
initialized_empty_store = False

if operation not in OPERATIONS:
    response, write_memory = dispatch(operation, empty_store())
else:
    raw_store, initialized_empty_store, store_error = store_from_entity()
    if store_error:
        response = store_error
    else:
        store, validation_error_result = validate_store(raw_store)
        if validation_error_result:
            response = validation_error_result
        else:
            response, write_memory = dispatch(operation, store)
            if initialized_empty_store and write_memory is None:
                write_memory = store

output["success"] = response["success"]
output["response"] = response
output["write_required"] = write_memory is not None
output["memory_store_entity_id"] = MEMORY_STORE_ENTITY_ID

if write_memory is not None:
    output["write_memory"] = write_memory
