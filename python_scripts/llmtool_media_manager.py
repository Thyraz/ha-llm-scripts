TOOL_NAME = "llmtool_media_manager"

OPERATIONS = [
    "search",
    "browse_library",
    "play_by_uri",
    "play_by_name",
    "get_queue",
    "transfer_queue",
    "group_join",
    "group_unjoin",
    "group_clear_members",
]

MEDIA_TYPES = ["artist", "album", "audiobook", "playlist", "podcast", "track", "radio"]
DEFAULT_SEARCH_MEDIA_TYPES = ["track", "album", "artist", "playlist", "radio"]
PLAY_BY_NAME_MEDIA_TYPES = ["track", "album", "artist", "playlist", "radio"]
ALBUM_TYPES = ["album", "single", "compilation", "ep"]
ENQUEUE_VALUES = ["play", "replace", "next", "add"]
BOOL_FIELDS = [
    "library_only",
    "favorite",
    "radio_mode",
    "auto_play",
    "ungroup_first",
    "replace_existing",
]

SEARCH_DEFAULT_LIMIT = 20
SEARCH_MAX_LIMIT = 100
BROWSE_DEFAULT_LIMIT = 20
BROWSE_MAX_LIMIT = 100
QUEUE_DEFAULT_LIMIT = 20
QUEUE_MAX_LIMIT = 100
MAX_PLAYBACK_ITEMS = 100

CONFIG_HELPER_ENTITY_ID = "input_text.llmtool_media_manager_music_assistant_config_entry_id"

PARAMETER_NAMES = [
    "query",
    "search_media_types",
    "media_type",
    "artist",
    "album",
    "library_only",
    "favorite",
    "limit",
    "offset",
    "album_type",
    "player_entity_id",
    "media_uris",
    "play_queries",
    "enqueue",
    "radio_mode",
    "source_player_entity_id",
    "target_player_entity_id",
    "auto_play",
    "leader_entity_id",
    "member_entity_ids",
    "ungroup_first",
    "replace_existing",
]

ALLOWLISTS = {
    "search": ["operation", "query", "search_media_types", "artist", "album", "library_only", "limit"],
    "browse_library": ["operation", "query", "media_type", "favorite", "limit", "offset", "album_type"],
    "play_by_uri": ["operation", "player_entity_id", "media_uris", "enqueue", "radio_mode"],
    "play_by_name": ["operation", "player_entity_id", "play_queries", "media_type", "enqueue", "radio_mode"],
    "get_queue": ["operation", "player_entity_id", "limit"],
    "transfer_queue": ["operation", "source_player_entity_id", "target_player_entity_id", "auto_play"],
    "group_join": ["operation", "leader_entity_id", "member_entity_ids", "ungroup_first", "replace_existing"],
    "group_unjoin": ["operation", "member_entity_ids"],
    "group_clear_members": ["operation", "leader_entity_id"],
}

SEARCH_RESPONSE_KEYS = {
    "artist": ["artists", "artist"],
    "album": ["albums", "album"],
    "audiobook": ["audiobooks", "audiobook"],
    "playlist": ["playlists", "playlist"],
    "podcast": ["podcasts", "podcast"],
    "track": ["tracks", "track"],
    "radio": ["radio", "radios"],
}


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
        return default_value


def has_mapping_value(value, key):
    try:
        value[key]
        return True
    except (KeyError, TypeError):
        pass
    try:
        return key in value
    except TypeError:
        return False


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


def append_unique(items, value):
    if value and value not in items:
        items.append(value)


def plural(value, singular, plural_text):
    if value == 1:
        return singular
    return plural_text


def base_meta(operation):
    return {"tool": TOOL_NAME, "operation": operation}


def validation_error(message, data_payload=None, meta_payload=None):
    output["success"] = False
    output["error"] = message
    output["data"] = data_payload or {}
    output["meta"] = meta_payload or {"tool": TOOL_NAME}


def is_present(value):
    if value is None:
        return False
    if value is False:
        return False
    if is_sequence(value):
        for item in value:
            if is_present(item):
                return True
        return False
    text = as_text(value).lower()
    return text not in ["", "false", "off", "no", "0", "none", "unknown", "unavailable"]


def parse_bool_field(field_name):
    value = data.get(field_name)
    if value is True:
        return True, ""
    if value is False or value is None:
        return False, ""

    text = as_text(value).lower()
    if text in ["", "false", "off", "no", "0", "none"]:
        return False, ""
    if text in ["true", "on", "yes", "1"]:
        return True, ""
    return False, "Invalid boolean value. Use true or false."


def parse_int_field(raw_value, field_name, default_value, min_value, max_value):
    text = as_text(raw_value)
    if not text:
        return default_value, ""

    if text.endswith(".0"):
        text = text[:-2]
    if not text:
        return None, "Invalid {}. Use an integer from {} to {}.".format(field_name, min_value, max_value)
    for char in text:
        if char not in "0123456789":
            return None, "Invalid {}. Use an integer from {} to {}.".format(field_name, min_value, max_value)

    value = int(text)
    if value < min_value or value > max_value:
        return None, "Invalid {}. Use an integer from {} to {}.".format(field_name, min_value, max_value)
    return value, ""


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
    if not is_sequence(raw_members):
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


def parse_comma_list(raw_value):
    values = []
    if is_sequence(raw_value):
        for item in raw_value:
            text = as_text(item)
            if text:
                append_unique(values, text)
        return values

    for part in str(raw_value or "").split(","):
        text = part.strip()
        if text:
            append_unique(values, text)
    return values


def parse_newline_list(raw_value):
    values = []
    if is_sequence(raw_value):
        for item in raw_value:
            text = as_text(item)
            if text:
                values.append(text)
        return values

    for line in str(raw_value or "").splitlines():
        text = line.strip()
        if text:
            values.append(text)
    return values


def parse_search_media_types(raw_value):
    media_types = parse_comma_list(raw_value)
    if not media_types:
        media_types = DEFAULT_SEARCH_MEDIA_TYPES[:]

    invalid_media_types = []
    for media_type in media_types:
        if media_type not in MEDIA_TYPES:
            append_unique(invalid_media_types, media_type)
    return media_types, invalid_media_types


def parse_config_entry_ids(raw_value):
    return parse_comma_list(raw_value)


def is_loaded_state(value):
    text = as_text(value).lower()
    return text == "loaded" or text.endswith(".loaded")


def resolve_music_assistant_config_entry(operation):
    helper_config_entry_id = as_text(data.get("helper_config_entry_id"))
    helper_config_entry_loaded = parse_bool_field("helper_config_entry_id_is_music_assistant_loaded")[0]
    config_entry_ids = parse_config_entry_ids(data.get("music_assistant_config_entry_ids"))

    if helper_config_entry_id:
        if helper_config_entry_loaded:
            return helper_config_entry_id, None
        return "", {
            "message": "Music Assistant instance helper is invalid. Ask the user to update input_text.llmtool_media_manager_music_assistant_config_entry_id.",
            "data": {"helper_entity_id": CONFIG_HELPER_ENTITY_ID},
            "meta": base_meta(operation),
        }

    if len(config_entry_ids) == 1:
        return config_entry_ids[0], None

    if len(config_entry_ids) == 0:
        return "", {
            "message": "Music Assistant does not seem to be installed or loaded.",
            "data": {"helper_entity_id": CONFIG_HELPER_ENTITY_ID},
            "meta": base_meta(operation),
        }

    return "", {
        "message": "Music Assistant instance is ambiguous. Ask the user to set input_text.llmtool_media_manager_music_assistant_config_entry_id.",
        "data": {"helper_entity_id": CONFIG_HELPER_ENTITY_ID},
        "meta": base_meta(operation),
    }


def validate_allowlist(operation):
    allowed = ALLOWLISTS.get(operation) or []
    invalid_parameters = []
    for parameter_name in PARAMETER_NAMES:
        if parameter_name not in allowed and is_present(data.get(parameter_name)):
            invalid_parameters.append(parameter_name)

    if invalid_parameters:
        validation_error(
            "Invalid parameters for operation.",
            {
                "operation": operation,
                "invalid_parameters": invalid_parameters,
                "allowed_parameters": allowed,
            },
            base_meta(operation),
        )


def validate_bool_fields(operation):
    for field_name in BOOL_FIELDS:
        _, error = parse_bool_field(field_name)
        if error:
            validation_error(
                error,
                {"parameter": field_name},
                base_meta(operation),
            )
            return


def is_music_assistant_player_flag(field_name):
    return parse_bool_field(field_name)[0]


def validate_music_assistant_player(operation, entity_id, flag_field_name, field_name):
    if not entity_id:
        validation_error(
            "Missing {}. Provide a Music Assistant media_player.* entity ID.".format(field_name),
            {"required": field_name},
            base_meta(operation),
        )
    elif not is_media_player_entity_id(entity_id):
        validation_error(
            "Invalid entity ID. Use Home Assistant media_player.* entity IDs.",
            {"invalid_entity_ids": [entity_id]},
            base_meta(operation),
        )
    elif not is_music_assistant_player_flag(flag_field_name):
        validation_error(
            "Invalid player. Use a Music Assistant media_player.* entity ID.",
            {"invalid_entity_ids": [entity_id]},
            base_meta(operation),
        )


def shape_artist_names(row):
    artists = mapping_value(row, "artists", [])
    names = []
    if is_sequence(artists):
        for artist in artists:
            name = as_text(mapping_value(artist, "name"))
            if name:
                names.append(name)
    return names


def shape_media_item(row, fallback_media_type):
    media_item = mapping_value(row, "media_item")
    if media_item is None:
        media_item = {}

    name = as_text(mapping_value(row, "name"))
    if not name:
        name = as_text(mapping_value(media_item, "name"))

    uri = as_text(mapping_value(row, "uri"))
    if not uri:
        uri = as_text(mapping_value(row, "media_id"))
    if not uri:
        uri = as_text(mapping_value(media_item, "uri"))

    media_type = as_text(mapping_value(row, "media_type"))
    if not media_type:
        media_type = as_text(mapping_value(media_item, "media_type"))
    if not media_type:
        media_type = fallback_media_type

    item = {
        "name": name,
        "uri": uri,
        "media_type": media_type,
    }

    version = as_text(mapping_value(row, "version"))
    if not version:
        version = as_text(mapping_value(media_item, "version"))
    if version:
        item["version"] = version

    artist_names = shape_artist_names(row)
    if not artist_names:
        artist_names = shape_artist_names(media_item)
    if artist_names:
        item["artist_names"] = artist_names

    album = mapping_value(row, "album")
    if album is None:
        album = mapping_value(media_item, "album")
    album_name = as_text(mapping_value(album, "name"))
    if not album_name:
        album_name = as_text(mapping_value(row, "album_name"))
    if not album_name:
        album_name = as_text(mapping_value(media_item, "album_name"))
    if album_name:
        item["album_name"] = album_name

    duration = mapping_value(row, "duration")
    if duration is None:
        duration = mapping_value(media_item, "duration")
    if duration is None:
        duration = mapping_value(row, "duration_seconds")
    if duration is None:
        duration = mapping_value(media_item, "duration_seconds")
    if duration is not None:
        item["duration_seconds"] = duration

    elapsed = mapping_value(row, "elapsed_seconds")
    if elapsed is None:
        elapsed = mapping_value(row, "elapsed")
    if elapsed is None:
        elapsed = mapping_value(row, "elapsed_time")
    if elapsed is not None:
        item["elapsed_seconds"] = elapsed

    return item


def response_rows_for_media_type(response, media_type):
    keys = SEARCH_RESPONSE_KEYS.get(media_type) or []
    for key in keys:
        rows = mapping_value(response, key)
        if is_sequence(rows):
            return rows
    return []


def item_at(items, index):
    if index < 0:
        return None
    current_index = 0
    for item in items:
        if current_index == index:
            return item
        current_index = current_index + 1
    return None


def queue_payload_from_response(response, player_entity_id):
    by_entity = mapping_value(response, player_entity_id)
    if by_entity is not None:
        return by_entity
    return response


def queue_items_from_payload(queue_payload):
    for key in ["items", "queue_items", "queue"]:
        rows = mapping_value(queue_payload, key)
        if is_sequence(rows):
            return rows
    return []


def operation_prepare_search():
    operation = "search"
    query = as_text(data.get("query"))
    artist = as_text(data.get("artist"))
    album = as_text(data.get("album"))
    library_only = parse_bool_field("library_only")[0]
    limit, limit_error = parse_int_field(data.get("limit"), "limit", SEARCH_DEFAULT_LIMIT, 1, SEARCH_MAX_LIMIT)
    search_media_types, invalid_media_types = parse_search_media_types(data.get("search_media_types"))

    if not query:
        validation_error("Missing query. Provide search text.", {"required": "query"}, base_meta(operation))
    elif limit_error:
        validation_error(limit_error, {"default_limit": SEARCH_DEFAULT_LIMIT, "max_limit": SEARCH_MAX_LIMIT}, base_meta(operation))
    elif invalid_media_types:
        validation_error("Invalid media type.", {"invalid_media_types": invalid_media_types, "known_media_types": MEDIA_TYPES}, base_meta(operation))
    elif (artist or album) and "track" not in search_media_types and "album" not in search_media_types:
        validation_error(
            "artist and album are only valid when search_media_types includes track or album.",
            {"invalid_parameters": ["artist", "album"]},
            base_meta(operation),
        )
    else:
        config_entry_id, config_error = resolve_music_assistant_config_entry(operation)
        if config_error:
            validation_error(config_error["message"], config_error["data"], config_error["meta"])
        else:
            action_data = {
                "config_entry_id": config_entry_id,
                "name": query,
                "media_type": search_media_types,
                "limit": SEARCH_MAX_LIMIT,
                "library_only": library_only,
            }
            if artist:
                action_data["artist"] = artist
            if album:
                action_data["album"] = album
            output["success"] = True
            output["data"] = {
                "operation": operation,
                "action": "music_assistant.search",
                "action_data": action_data,
                "query": query,
                "artist": artist,
                "album": album,
                "search_media_types": search_media_types,
                "library_only": library_only,
                "limit": limit,
                "action_limit": SEARCH_MAX_LIMIT,
            }
            output["meta"] = base_meta(operation)


def operation_prepare_browse_library():
    operation = "browse_library"
    media_type = as_text(data.get("media_type"))
    query = as_text(data.get("query"))
    favorite = parse_bool_field("favorite")[0]
    album_type = as_text(data.get("album_type"))
    limit, limit_error = parse_int_field(data.get("limit"), "limit", BROWSE_DEFAULT_LIMIT, 1, BROWSE_MAX_LIMIT)
    offset, offset_error = parse_int_field(data.get("offset"), "offset", 0, 0, 1000000)

    if not media_type:
        validation_error("Missing media_type. Provide one Music Assistant media type.", {"required": "media_type"}, base_meta(operation))
    elif media_type not in MEDIA_TYPES:
        validation_error("Invalid media_type.", {"invalid_media_types": [media_type], "known_media_types": MEDIA_TYPES}, base_meta(operation))
    elif limit_error:
        validation_error(limit_error, {"default_limit": BROWSE_DEFAULT_LIMIT, "max_limit": BROWSE_MAX_LIMIT}, base_meta(operation))
    elif offset_error:
        validation_error(offset_error, {"default_offset": 0}, base_meta(operation))
    elif album_type and media_type != "album":
        validation_error("album_type is only valid when media_type is album.", {"invalid_parameters": ["album_type"]}, base_meta(operation))
    elif album_type and album_type not in ALBUM_TYPES:
        validation_error("Invalid album_type.", {"invalid_album_type": album_type, "known_album_types": ALBUM_TYPES}, base_meta(operation))
    else:
        config_entry_id, config_error = resolve_music_assistant_config_entry(operation)
        if config_error:
            validation_error(config_error["message"], config_error["data"], config_error["meta"])
        else:
            action_data = {
                "config_entry_id": config_entry_id,
                "media_type": media_type,
                "limit": limit,
                "offset": offset,
            }
            if query:
                action_data["search"] = query
            if favorite:
                action_data["favorite"] = True
            if album_type:
                action_data["album_type"] = [album_type]
            output["success"] = True
            output["data"] = {
                "operation": operation,
                "action": "music_assistant.get_library",
                "action_data": action_data,
                "query": query,
                "media_type": media_type,
                "favorite": favorite,
                "limit": limit,
                "offset": offset,
                "album_type": album_type,
            }
            output["meta"] = base_meta(operation)


def operation_prepare_play_by_uri():
    operation = "play_by_uri"
    player_entity_id = as_text(data.get("player_entity_id"))
    media_uris = parse_newline_list(data.get("media_uris"))
    enqueue = as_text(data.get("enqueue")) or "play"
    radio_mode = parse_bool_field("radio_mode")[0]

    if not player_entity_id or not is_media_player_entity_id(player_entity_id) or not is_music_assistant_player_flag("player_entity_id_is_music_assistant"):
        validate_music_assistant_player(operation, player_entity_id, "player_entity_id_is_music_assistant", "player_entity_id")
    elif not media_uris:
        validation_error("Missing media_uris. Provide Music Assistant media URIs from search or library results.", {"required": "media_uris"}, base_meta(operation))
    elif len(media_uris) > MAX_PLAYBACK_ITEMS:
        validation_error("Too many media_uris. Use at most 100 media URIs.", {"max_media_uris": MAX_PLAYBACK_ITEMS}, base_meta(operation))
    elif enqueue not in ENQUEUE_VALUES:
        validation_error("Invalid enqueue. Use play, replace, next, or add.", {"known_enqueue_values": ENQUEUE_VALUES}, base_meta(operation))
    elif radio_mode and len(media_uris) != 1:
        validation_error("radio_mode requires exactly one media URI.", {"uri_count": len(media_uris)}, base_meta(operation))
    else:
        output["success"] = True
        output["data"] = {
            "operation": operation,
            "action": "music_assistant.play_media",
            "target_entity_id": player_entity_id,
            "action_data": {
                "media_id": media_uris,
                "enqueue": enqueue,
                "radio_mode": radio_mode,
            },
            "player_entity_id": player_entity_id,
            "media_uris": media_uris,
            "uri_count": len(media_uris),
            "enqueue": enqueue,
            "radio_mode": radio_mode,
        }
        output["meta"] = base_meta(operation)


def operation_prepare_play_by_name():
    operation = "play_by_name"
    player_entity_id = as_text(data.get("player_entity_id"))
    play_queries = parse_newline_list(data.get("play_queries"))
    media_type = as_text(data.get("media_type"))
    enqueue = as_text(data.get("enqueue")) or "play"
    radio_mode = parse_bool_field("radio_mode")[0]

    if not player_entity_id or not is_media_player_entity_id(player_entity_id) or not is_music_assistant_player_flag("player_entity_id_is_music_assistant"):
        validate_music_assistant_player(operation, player_entity_id, "player_entity_id_is_music_assistant", "player_entity_id")
    elif not play_queries:
        validation_error("Missing play_queries. Provide one or more Music Assistant play queries.", {"required": "play_queries"}, base_meta(operation))
    elif not media_type:
        validation_error(
            "Missing media_type. Provide track, album, artist, playlist, or radio.",
            {"required": "media_type", "known_media_types": PLAY_BY_NAME_MEDIA_TYPES},
            base_meta(operation),
        )
    elif len(play_queries) > MAX_PLAYBACK_ITEMS:
        validation_error("Too many play_queries. Use at most 100 play queries.", {"max_play_queries": MAX_PLAYBACK_ITEMS}, base_meta(operation))
    elif media_type not in PLAY_BY_NAME_MEDIA_TYPES:
        validation_error("Invalid media_type for play_by_name.", {"invalid_media_types": [media_type], "known_media_types": PLAY_BY_NAME_MEDIA_TYPES}, base_meta(operation))
    elif enqueue not in ENQUEUE_VALUES:
        validation_error("Invalid enqueue. Use play, replace, next, or add.", {"known_enqueue_values": ENQUEUE_VALUES}, base_meta(operation))
    elif radio_mode and len(play_queries) != 1:
        validation_error("radio_mode requires exactly one play query.", {"query_count": len(play_queries)}, base_meta(operation))
    else:
        output["success"] = True
        output["data"] = {
            "operation": operation,
            "action": "music_assistant.play_media",
            "target_entity_id": player_entity_id,
            "action_data": {
                "media_id": play_queries,
                "media_type": media_type,
                "enqueue": enqueue,
                "radio_mode": radio_mode,
            },
            "player_entity_id": player_entity_id,
            "play_queries": play_queries,
            "query_count": len(play_queries),
            "media_type": media_type,
            "enqueue": enqueue,
            "radio_mode": radio_mode,
        }
        output["meta"] = base_meta(operation)


def operation_prepare_get_queue():
    operation = "get_queue"
    player_entity_id = as_text(data.get("player_entity_id"))
    limit, limit_error = parse_int_field(data.get("limit"), "limit", QUEUE_DEFAULT_LIMIT, 1, QUEUE_MAX_LIMIT)

    if not player_entity_id or not is_media_player_entity_id(player_entity_id) or not is_music_assistant_player_flag("player_entity_id_is_music_assistant"):
        validate_music_assistant_player(operation, player_entity_id, "player_entity_id_is_music_assistant", "player_entity_id")
    elif limit_error:
        validation_error(limit_error, {"default_limit": QUEUE_DEFAULT_LIMIT, "max_limit": QUEUE_MAX_LIMIT}, base_meta(operation))
    else:
        output["success"] = True
        output["data"] = {
            "operation": operation,
            "action": "music_assistant.get_queue",
            "target_entity_id": player_entity_id,
            "action_data": {},
            "player_entity_id": player_entity_id,
            "limit": limit,
        }
        output["meta"] = base_meta(operation)


def operation_prepare_transfer_queue():
    operation = "transfer_queue"
    source_player_entity_id = as_text(data.get("source_player_entity_id"))
    target_player_entity_id = as_text(data.get("target_player_entity_id"))
    auto_play = True
    if data.get("auto_play") is not None and as_text(data.get("auto_play")):
        auto_play = parse_bool_field("auto_play")[0]

    if not source_player_entity_id or not is_media_player_entity_id(source_player_entity_id) or not is_music_assistant_player_flag("source_player_entity_id_is_music_assistant"):
        validate_music_assistant_player(operation, source_player_entity_id, "source_player_entity_id_is_music_assistant", "source_player_entity_id")
    elif not target_player_entity_id or not is_media_player_entity_id(target_player_entity_id) or not is_music_assistant_player_flag("target_player_entity_id_is_music_assistant"):
        validate_music_assistant_player(operation, target_player_entity_id, "target_player_entity_id_is_music_assistant", "target_player_entity_id")
    else:
        output["success"] = True
        output["data"] = {
            "operation": operation,
            "action": "music_assistant.transfer_queue",
            "target_entity_id": target_player_entity_id,
            "action_data": {
                "source_player": source_player_entity_id,
                "auto_play": auto_play,
            },
            "source_player_entity_id": source_player_entity_id,
            "target_player_entity_id": target_player_entity_id,
            "auto_play": auto_play,
        }
        output["meta"] = base_meta(operation)


def build_group_prepare_payload(
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
    if operation == "group_join":
        join_leader_entity_id = leader_entity_id
        join_member_entity_ids = member_entity_ids

    return {
        "operation": operation,
        "action": "group",
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


def operation_prepare_group(operation):
    leader_entity_id = as_text(data.get("leader_entity_id"))
    raw_member_entity_ids = as_text(data.get("member_entity_ids"))
    ungroup_first = parse_bool_field("ungroup_first")[0]
    replace_existing = parse_bool_field("replace_existing")[0]
    member_entity_ids, invalid_member_entity_ids, duplicate_member_entity_ids = parse_entity_ids(raw_member_entity_ids)
    current_group_members = parse_current_group_members(data.get("current_group_members"))
    previous_member_entity_ids = []
    for entity_id in current_group_members:
        if entity_id != leader_entity_id:
            previous_member_entity_ids.append(entity_id)

    meta = base_meta(operation)
    if leader_entity_id:
        meta["leader_entity_id"] = leader_entity_id

    if leader_entity_id and not is_media_player_entity_id(leader_entity_id):
        validation_error("Invalid entity ID. Use Home Assistant media_player.* entity IDs.", {"invalid_entity_ids": [leader_entity_id]}, meta)
    elif invalid_member_entity_ids:
        validation_error("Invalid entity ID. Use Home Assistant media_player.* entity IDs.", {"invalid_entity_ids": invalid_member_entity_ids}, meta)
    elif operation != "group_join" and (ungroup_first or replace_existing):
        invalid_flags = []
        if ungroup_first:
            invalid_flags.append("ungroup_first")
        if replace_existing:
            invalid_flags.append("replace_existing")
        validation_error("Invalid flags. ungroup_first and replace_existing are only valid for group_join.", {"invalid_flags": invalid_flags}, meta)
    elif operation == "group_join" and not leader_entity_id:
        validation_error("Missing leader_entity_id. Provide a media_player.* entity ID for group_join.", {"required": "leader_entity_id"}, meta)
    elif operation == "group_clear_members" and not leader_entity_id:
        validation_error("Missing leader_entity_id. Provide a media_player.* entity ID for group_clear_members.", {"required": "leader_entity_id"}, meta)
    elif operation == "group_unjoin" and not member_entity_ids:
        validation_error("Missing member_entity_ids. Provide media_player.* entity IDs to unjoin.", {"required": "member_entity_ids"}, meta)
    else:
        ignored_member_entity_ids = []
        final_member_entity_ids = []
        if operation == "group_join":
            for entity_id in member_entity_ids:
                if entity_id == leader_entity_id:
                    append_unique(ignored_member_entity_ids, entity_id)
                else:
                    final_member_entity_ids.append(entity_id)
        else:
            final_member_entity_ids = member_entity_ids

        if operation == "group_join" and not final_member_entity_ids:
            validation_error(
                "group_join requires at least one member_entity_id different from leader_entity_id.",
                {
                    "required": "member_entity_ids",
                    "ignored_member_entity_ids": ignored_member_entity_ids,
                    "duplicate_member_entity_ids": duplicate_member_entity_ids,
                },
                meta,
            )
        else:
            unjoin_entity_ids = []
            if operation == "group_join":
                if ungroup_first:
                    append_unique(unjoin_entity_ids, leader_entity_id)
                    for entity_id in final_member_entity_ids:
                        append_unique(unjoin_entity_ids, entity_id)
                if replace_existing:
                    for entity_id in previous_member_entity_ids:
                        append_unique(unjoin_entity_ids, entity_id)
            elif operation == "group_unjoin":
                for entity_id in final_member_entity_ids:
                    append_unique(unjoin_entity_ids, entity_id)
            else:
                for entity_id in previous_member_entity_ids:
                    append_unique(unjoin_entity_ids, entity_id)

            output["success"] = True
            output["data"] = build_group_prepare_payload(
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


def prepare_mode():
    operation = as_text(data.get("operation")).lower()
    if operation not in OPERATIONS:
        validation_error(
            "Invalid operation. Use a known Media Manager operation.",
            {"known_operations": OPERATIONS},
            {"tool": TOOL_NAME, "operation": operation},
        )
        return

    validate_allowlist(operation)
    if output.get("success") is False:
        return

    validate_bool_fields(operation)
    if output.get("success") is False:
        return

    if operation == "search":
        operation_prepare_search()
    elif operation == "browse_library":
        operation_prepare_browse_library()
    elif operation == "play_by_uri":
        operation_prepare_play_by_uri()
    elif operation == "play_by_name":
        operation_prepare_play_by_name()
    elif operation == "get_queue":
        operation_prepare_get_queue()
    elif operation == "transfer_queue":
        operation_prepare_transfer_queue()
    else:
        operation_prepare_group(operation)


def shape_search(prepared, action_response):
    search_media_types = prepared["search_media_types"]
    limit = prepared["limit"]
    action_limit = prepared["action_limit"]
    remaining = limit
    results = []
    count_by_media_type = {}
    total_by_media_type = {}
    count = 0
    total = 0
    action_limit_hit = False

    for media_type in search_media_types:
        rows = response_rows_for_media_type(action_response, media_type)
        type_total = len(rows)
        total = total + type_total
        total_by_media_type[media_type] = type_total
        if type_total >= action_limit:
            action_limit_hit = True

        type_items = []
        if remaining > 0:
            take = type_total
            if take > remaining:
                take = remaining
            index = 0
            for row in rows:
                if index >= take:
                    break
                type_items.append(shape_media_item(row, media_type))
                index = index + 1
            remaining = remaining - take

        count_by_media_type[media_type] = len(type_items)
        count = count + len(type_items)
        results.append(
            {
                "media_type": media_type,
                "count": len(type_items),
                "total": type_total,
                "items": type_items,
            }
        )

    meta = {
        "tool": TOOL_NAME,
        "operation": "search",
        "query": prepared["query"],
        "search_media_types": search_media_types,
        "library_only": prepared["library_only"],
        "limit": limit,
        "count": count,
        "total": total,
        "count_by_media_type": count_by_media_type,
        "total_by_media_type": total_by_media_type,
    }
    if prepared["artist"]:
        meta["artist"] = prepared["artist"]
    if prepared["album"]:
        meta["album"] = prepared["album"]
    if count < total or action_limit_hit:
        meta["truncated"] = True

    output["success"] = True
    if count < total:
        output["answer"] = "Found {} of {} returned media {}.".format(count, total, plural(total, "item", "items"))
    else:
        output["answer"] = "Found {} media {}.".format(count, plural(count, "item", "items"))
    output["data"] = {"results": results}
    output["meta"] = meta


def shape_browse_library(prepared, action_response):
    rows = mapping_value(action_response, "items", [])
    if not is_sequence(rows):
        rows = []

    items = []
    for row in rows:
        items.append(shape_media_item(row, prepared["media_type"]))

    count = len(items)
    meta = {
        "tool": TOOL_NAME,
        "operation": "browse_library",
        "media_type": prepared["media_type"],
        "limit": prepared["limit"],
        "offset": prepared["offset"],
        "count": count,
    }
    if prepared["query"]:
        meta["query"] = prepared["query"]
    if prepared["favorite"]:
        meta["favorite"] = True
    if prepared["album_type"]:
        meta["album_type"] = prepared["album_type"]
    if count == prepared["limit"]:
        meta["truncated"] = True
        meta["next_offset"] = prepared["offset"] + count

    output["success"] = True
    output["answer"] = "Found {} library {}.".format(count, plural(count, "item", "items"))
    output["data"] = {"media_type": prepared["media_type"], "items": items}
    output["meta"] = meta


def shape_play_by_uri(prepared):
    output["success"] = True
    output["answer"] = "Sent {} media {} to {}.".format(
        prepared["uri_count"],
        plural(prepared["uri_count"], "URI", "URIs"),
        prepared["player_entity_id"],
    )
    output["data"] = {
        "player_entity_id": prepared["player_entity_id"],
        "media_uris": prepared["media_uris"],
        "uri_count": prepared["uri_count"],
        "enqueue": prepared["enqueue"],
        "radio_mode": prepared["radio_mode"],
    }
    output["meta"] = {
        "tool": TOOL_NAME,
        "operation": "play_by_uri",
        "player_entity_id": prepared["player_entity_id"],
        "uri_count": prepared["uri_count"],
        "enqueue": prepared["enqueue"],
    }


def shape_play_by_name(prepared):
    output["success"] = True
    output["answer"] = "Sent {} play {} to {}.".format(
        prepared["query_count"],
        plural(prepared["query_count"], "query", "queries"),
        prepared["player_entity_id"],
    )
    output["data"] = {
        "player_entity_id": prepared["player_entity_id"],
        "play_queries": prepared["play_queries"],
        "query_count": prepared["query_count"],
        "media_type": prepared["media_type"],
        "enqueue": prepared["enqueue"],
        "radio_mode": prepared["radio_mode"],
    }
    output["meta"] = {
        "tool": TOOL_NAME,
        "operation": "play_by_name",
        "player_entity_id": prepared["player_entity_id"],
        "query_count": prepared["query_count"],
        "media_type": prepared["media_type"],
        "enqueue": prepared["enqueue"],
        "match_precision": "name_based",
    }


def shape_get_queue(prepared, action_response):
    player_entity_id = prepared["player_entity_id"]
    limit = prepared["limit"]
    queue_payload = queue_payload_from_response(action_response, player_entity_id)
    rows = queue_items_from_payload(queue_payload)

    item_count = mapping_value(queue_payload, "item_count")
    if item_count is None:
        item_count = mapping_value(queue_payload, "items_count")
    if item_count is None:
        item_count = len(rows)

    current_index = mapping_value(queue_payload, "current_index")
    if current_index is None:
        current_index = mapping_value(queue_payload, "current_item_index")
    if current_index is None:
        current_index = 0

    current_item = mapping_value(queue_payload, "current_item")
    if current_item is None:
        current_item = item_at(rows, current_index)
    next_item = mapping_value(queue_payload, "next_item")
    if next_item is None:
        next_item = item_at(rows, current_index + 1)

    shaped_items = []
    index = 0
    for row in rows:
        if index >= current_index and len(shaped_items) < limit:
            shaped_items.append(shape_media_item(row, as_text(mapping_value(row, "media_type"))))
        index = index + 1

    data_payload = {
        "player_entity_id": player_entity_id,
        "active": mapping_value(queue_payload, "active"),
        "current_index": current_index,
        "item_count": item_count,
        "items": shaped_items,
    }
    if current_item is not None:
        data_payload["current_item"] = shape_media_item(current_item, as_text(mapping_value(current_item, "media_type")))
    if next_item is not None:
        data_payload["next_item"] = shape_media_item(next_item, as_text(mapping_value(next_item, "media_type")))

    meta = {
        "tool": TOOL_NAME,
        "operation": "get_queue",
        "player_entity_id": player_entity_id,
        "limit": limit,
        "count": len(shaped_items),
        "total": item_count,
    }
    remaining_item_count = item_count
    try:
        remaining_item_count = item_count - current_index
    except TypeError:
        remaining_item_count = item_count
    if len(shaped_items) < remaining_item_count:
        meta["truncated"] = True

    output["success"] = True
    output["answer"] = "Queue has {} media {}.".format(item_count, plural(item_count, "item", "items"))
    output["data"] = data_payload
    output["meta"] = meta


def shape_transfer_queue(prepared):
    output["success"] = True
    output["answer"] = "Transferred queue from {} to {}.".format(
        prepared["source_player_entity_id"],
        prepared["target_player_entity_id"],
    )
    output["data"] = {
        "source_player_entity_id": prepared["source_player_entity_id"],
        "target_player_entity_id": prepared["target_player_entity_id"],
        "auto_play": prepared["auto_play"],
    }
    output["meta"] = {"tool": TOOL_NAME, "operation": "transfer_queue"}


def shape_group(prepared):
    operation = prepared["operation"]
    leader_entity_id = prepared["leader_entity_id"]
    join_member_entity_ids = prepared["join_member_entity_ids"]
    unjoin_entity_ids = prepared["unjoin_entity_ids"]
    previous_member_entity_ids = prepared["previous_member_entity_ids"]
    ignored_member_entity_ids = prepared["ignored_member_entity_ids"]
    duplicate_member_entity_ids = prepared["duplicate_member_entity_ids"]
    ungroup_first = prepared["ungroup_first"]
    replace_existing = prepared["replace_existing"]

    meta = base_meta(operation)
    if leader_entity_id:
        meta["leader_entity_id"] = leader_entity_id

    if operation == "group_join":
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
        output["answer"] = "Joined {} media player group {}.".format(count, plural(count, "member", "members"))
        output["data"] = payload
        output["meta"] = meta
    elif operation == "group_unjoin":
        count = len(unjoin_entity_ids)
        output["success"] = True
        output["answer"] = "Unjoined {} media {}.".format(count, plural(count, "player", "players"))
        output["data"] = {
            "operation": operation,
            "unjoined_entity_ids": unjoin_entity_ids,
            "duplicate_member_entity_ids": duplicate_member_entity_ids,
        }
        output["meta"] = meta
    else:
        count = len(unjoin_entity_ids)
        output["success"] = True
        output["answer"] = "Cleared {} media player group {}.".format(count, plural(count, "member", "members"))
        output["data"] = {
            "operation": operation,
            "leader_entity_id": leader_entity_id,
            "cleared_member_entity_ids": unjoin_entity_ids,
            "previous_member_entity_ids": previous_member_entity_ids,
        }
        output["meta"] = meta


def shape_mode():
    prepared = data.get("prepared")
    action_response = data.get("action_response") or {}
    if prepared is None or is_text_value(prepared):
        validation_error(
            "Invalid Media Manager helper handoff. Inspect the Script trace.",
            {},
            {"tool": TOOL_NAME},
        )
        return

    operation = as_text(mapping_value(prepared, "operation"))
    if operation == "search":
        shape_search(prepared, action_response)
    elif operation == "browse_library":
        shape_browse_library(prepared, action_response)
    elif operation == "play_by_uri":
        shape_play_by_uri(prepared)
    elif operation == "play_by_name":
        shape_play_by_name(prepared)
    elif operation == "get_queue":
        shape_get_queue(prepared, action_response)
    elif operation == "transfer_queue":
        shape_transfer_queue(prepared)
    elif operation in ["group_join", "group_unjoin", "group_clear_members"]:
        shape_group(prepared)
    else:
        validation_error(
            "Invalid Media Manager helper handoff. Inspect the Script trace.",
            {},
            {"tool": TOOL_NAME, "operation": operation},
        )


mode = as_text(data.get("mode")) or "prepare"

if mode == "prepare":
    prepare_mode()
elif mode == "shape":
    shape_mode()
else:
    validation_error(
        "Invalid Media Manager helper mode. Inspect the Script trace.",
        {"known_modes": ["prepare", "shape"]},
        {"tool": TOOL_NAME},
    )
