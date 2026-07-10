# Home Assistant LLM Scripts

Reusable Home Assistant script collection for LLM-based Assistants.

This project exposes Home Assistant scripts as LLM tools. Scripts use HA-native operations first, and call native `python_script` helpers only when YAML/Jinja would become hard to read.

## Status

Current implementation includes:

- `script.llmtool_demo` for install and response-shape validation
- `script.llmtool_entity_index` for safe labeled-entity discovery
- `script.llmtool_long_term_aggregated_statistics` for aggregated long-term statistics
- `script.llmtool_raw_entity_history` for unaggregated raw entity history
- `script.llmtool_calculator` for deterministic arithmetic
- `script.llmtool_date_calculator` for deterministic calendar and local-time calculations
- `script.llmtool_calendar_manager` for reading Home Assistant calendar events
- `script.llmtool_media_manager` for Music Assistant media and media player groups
- optional `script.llmtool_memory_manager` for user-provided long-term memory

## Install

Copy or sync these folders into your Home Assistant config folder:

```text
custom_llm_tools/
  llm_scripts/
  rest_commands/
python_scripts/
```

Create a Home Assistant Long-Lived Access Token and add it to `secrets.yaml`.
Keep the `Bearer ` prefix in the secret value:

```yaml
llmtool_home_assistant_bearer_token: "Bearer <long-lived-access-token>"
```

Add this to `configuration.yaml`:

```yaml
script llm_tools: !include_dir_merge_named custom_llm_tools/llm_scripts/

rest_command: !include_dir_merge_named custom_llm_tools/rest_commands/

python_script:
```

If you already have a `rest_command:` section, do not add a second top-level
`rest_command:` key. Instead, either move your existing REST commands into the
same included directory, or copy the `llmtool_home_assistant_api_get` command from
`custom_llm_tools/rest_commands/raw_entity_history.yaml` into your existing
`rest_command:` mapping.

Reload scripts or restart Home Assistant. For a new or renamed Python Helper,
run `python_script.reload`.

## Demo tool

After install, Home Assistant should expose:

- `script.llmtool_demo`
- `python_script.llmtool_demo`

Run `script.llmtool_demo` from Developer Tools -> Actions:

```yaml
name: Alex
```

Expected response in Developer Tools -> Actions:

```yaml
success: true
answer: "Hello Alex, this came from the LLM Tool Python Helper."
data:
  normalized_name: "Alex"
  helper_message: "Hello Alex, this came from the LLM Tool Python Helper."
meta:
  tool: "llmtool_demo"
  python_helper: "python_script.llmtool_demo"
```

Expected response in Assist tool trace:

```yaml
success: true
result:
  success: true
  answer: "Hello Alex, this came from the LLM Tool Python Helper."
  data:
    normalized_name: "Alex"
    helper_message: "Hello Alex, this came from the LLM Tool Python Helper."
  meta:
    tool: "llmtool_demo"
    python_helper: "python_script.llmtool_demo"
```

Run again with empty or missing `name`; response should use `World`.
Then manually expose `script.llmtool_demo` to Assist and ask the Assistant to
call the demo tool. Inspect Script trace and Conversation trace.

## Entity Index tool

After install, Home Assistant should expose:

- `script.llmtool_entity_index`
- `python_script.llmtool_entity_index`

Entity Index lets an Assistant discover allowed Home Assistant entities by
label and location.

For likely cumulative sensors, compact and detailed results include
`value_hint`. For usage over a time range, follow that hint and use Long-Term
Aggregated Statistics with `aggregation_type: change` instead of answering from
the current state.

Use `verbosity: detailed` when you need operational fields. Detailed climate
entities may include `current_temperature` and `temperature`. Detailed media
players may include `volume_level`, `is_volume_muted`, `media_title`,
`media_album_name`, `shuffle`, `repeat`, and `group_members`.

Supported label names come from:

1. `input_select.llmtool_entity_index_labels` options, when that helper exists.
2. Otherwise all Home Assistant label names except the internal Entity Index
   labels.

Optional strict label config:

```yaml
input_select:
  llmtool_entity_index_labels:
    name: LLM Tool Entity Index Labels
    options:
      - LivingRoom
      - TemperatureSensor
      - Thermostat
      - Light
```

Run `script.llmtool_entity_index` from Developer Tools -> Actions:

```yaml
label_names: LivingRoom,Light
location: inside
entity_scope: filtered_by_labels
label_operator: AND
verbosity: compact
limit: 50
```

Expected response shape:

```yaml
success: true
answer: "Found 1 matching entities."
data:
  entities:
    - entity_id: light.living_room
      friendly_name: Living room light
      state: "on"
      matched_labels:
        - LivingRoom
        - Light
meta:
  tool: llmtool_entity_index
  count: 1
  total: 1
  entity_scope: filtered_by_labels
  label_names:
    - LivingRoom
    - Light
  location: inside
  label_operator: AND
  state_filter: ""
  verbosity: compact
  limit: 50
```

For room/floor plus device-type searches, use `label_operator: AND`. Use
`label_operator: OR` only for broad alternatives; it is a shortcut for multiple
Entity Index calls with one label each.

Invalid label names return a soft failure:

```yaml
success: false
error: "Unknown label name. Use data.known_labels and retry."
data:
  unknown_labels:
    - UnknownLabel
  known_labels:
    - TemperatureSensor
meta: {}
```

## Long-Term Aggregated Statistics tool

After install, Home Assistant should expose:

- `script.llmtool_long_term_aggregated_statistics`
- `python_script.llmtool_long_term_aggregated_statistics`

Long-Term Aggregated Statistics returns Home Assistant recorder long-term
statistics for entity IDs the Assistant already knows, usually from Entity
Index. It does not return raw state history.

Supported aggregation types:

- `mean`
- `min`
- `max`
- `change`

Supported aggregation periods:

- `5minute`
- `hour`
- `day`
- `week`
- `month`
- `year`
- `total`

Use local Home Assistant time in exactly this format:

```text
YYYY-MM-DD HH:MM:SS
```

Run `script.llmtool_long_term_aggregated_statistics` from Developer Tools ->
Actions:

```yaml
entity_ids: sensor.living_room_temperature
start_time: "2025-07-30 14:00:00"
end_time: "2025-07-31 14:00:00"
aggregation_type: mean
aggregation_period: hour
```

Expected response shape:

```yaml
success: true
answer: "Found 24 statistics rows."
data:
  entities:
    - entity_id: sensor.living_room_temperature
      friendly_name: Living room temperature
      unit_of_measurement: C
      values:
        - start: "2025-07-30 14:00:00"
          end: "2025-07-30 15:00:00"
          mean: 21.4
  missing_entities: []
meta:
  tool: llmtool_long_term_aggregated_statistics
  entity_ids:
    - sensor.living_room_temperature
  start_time: "2025-07-30 14:00:00"
  end_time: "2025-07-31 14:00:00"
  aggregation_type: mean
  aggregation_period: hour
  count: 24
  total: 24
```

If some requested entities have no statistics in the requested range, the tool
returns available entities and lists the rest under `data.missing_entities`. If
no requested entity has data, it returns a soft failure:

```yaml
success: false
error: "No statistics found for requested entity IDs and time range."
data:
  entities: []
  missing_entities:
    - sensor.unknown_temperature
meta:
  tool: llmtool_long_term_aggregated_statistics
  entity_ids:
    - sensor.unknown_temperature
  start_time: "2025-07-30 14:00:00"
  end_time: "2025-07-31 14:00:00"
  aggregation_type: mean
  aggregation_period: hour
  count: 0
  total: 0
```

Responses are capped at 500 value rows. Capped responses include
`meta.truncated: true`; retry with a narrower time range or coarser
`aggregation_period`.

`aggregation_period=total` returns one value per entity for the whole requested
time range. It is derived from Home Assistant statistics rows. For `mean`, the
result is an unweighted mean of period means.

## Raw Entity History tool

After install, Home Assistant should expose:

- `script.llmtool_raw_entity_history`
- `python_script.llmtool_raw_entity_history`
- `rest_command.llmtool_home_assistant_api_get`

Raw Entity History returns unaggregated Home Assistant recorder state history
for entity IDs the Assistant already knows, usually from Entity Index. It does
not return long-term aggregated statistics.

Use local Home Assistant time in exactly this format:

```text
YYYY-MM-DD HH:MM:SS
```

Run `script.llmtool_raw_entity_history` from Developer Tools -> Actions:

```yaml
entity_ids: binary_sensor.window
start_time: "2026-06-20 10:00:00"
end_time: "2026-06-20 12:00:00"
limit: 100
```

Expected response shape:

```yaml
success: true
answer: "Found 2 history entries."
data:
  entities:
    - entity_id: binary_sensor.window
      friendly_name: Window
      state_at_start:
        changed_at: "2026-06-20 10:00:00"
        active_at: "2026-06-20 10:00:00"
        state: "off"
      state_at_end:
        changed_at: "2026-06-20 11:00:00"
        active_at: "2026-06-20 12:00:00"
        state: "on"
      history:
        - changed_at: "2026-06-20 10:00:00"
          state: "off"
          duration_until_next_change_seconds: 3600
        - changed_at: "2026-06-20 11:00:00"
          state: "on"
  missing_entities: []
meta:
  tool: llmtool_raw_entity_history
  entity_ids:
    - binary_sensor.window
  start_time: "2026-06-20 10:00:00"
  end_time: "2026-06-20 12:00:00"
  count: 2
  total: 2
  limit: 100
```

Raw history is limited by Recorder retention and filtering. By default, Home
Assistant keeps raw history for 10 days. If no requested entity has raw history
in the range, the tool returns a soft failure:

```yaml
success: false
error: "No raw history found for requested entity IDs and time range."
data:
  entities: []
  missing_entities:
    - binary_sensor.window
meta:
  tool: llmtool_raw_entity_history
  entity_ids:
    - binary_sensor.window
  start_time: "2026-06-20 10:00:00"
  end_time: "2026-06-20 12:00:00"
  count: 0
  total: 0
  limit: 100
```

Responses are capped by `limit`, default 100 and maximum 1000. Capped responses
include `meta.truncated: true`; retry with a narrower time range or higher
limit.

## Calendar Manager tool

After install, Home Assistant should expose:

- `script.llmtool_calendar_manager`
- `python_script.llmtool_calendar_manager`

Calendar Manager reads Home Assistant calendar events from calendar entities.
This version does not create, update, or delete events.

Supported operations:

- `search_events`
- `list_upcoming`
- `list_range`

Pass `calendar_entity_ids` as comma-separated Home Assistant `calendar.*`
entity IDs. Empty `calendar_entity_ids` uses all available `calendar.*`
entities.

Use local Home Assistant time in exactly this format:

```text
YYYY-MM-DD HH:MM:SS
```

Calendar Manager Time Range must be 365 days or less. Longer ranges return a
soft failure before Home Assistant calendar data is queried.

Run `script.llmtool_calendar_manager` from Developer Tools -> Actions:

```yaml
operation: list_upcoming
calendar_entity_ids: calendar.family
days_ahead: 30
limit: 10
event_type: all
verbosity: compact
```

Expected response shape:

```yaml
success: true
answer: "Found 2 calendar events."
data:
  calendars:
    - calendar_entity_id: calendar.family
      friendly_name: Family
      count: 2
      events:
        - title: Dentist
          event_type: timed
          start: "2026-06-24 14:00:00"
          end: "2026-06-24 15:00:00"
          location: Town
        - title: Paper collection
          event_type: all_day
          start: "2026-06-25 00:00:00"
          end: "2026-06-25 23:59:59"
          location:
meta:
  tool: llmtool_calendar_manager
  operation: list_upcoming
  calendar_entity_ids:
    - calendar.family
  start_time: "2026-06-22 12:00:00"
  end_time: "2026-07-22 12:00:00"
  event_type: all
  verbosity: compact
  limit: 10
  count: 2
  total: 2
```

Use `verbosity=detailed` when event descriptions are needed. Detailed
descriptions are capped for response size and may include
`description_truncated: true`.

All-day event `end` is returned as the final local day at `23:59:59`, not Home
Assistant's exclusive all-day end.

Responses are capped by `limit`, default 100 and maximum 1000. Capped responses
include `meta.truncated: true`; retry with a narrower time range or higher
limit.

## Media Manager tool

After install, Home Assistant should expose:

- `script.llmtool_media_manager`
- `python_script.llmtool_media_manager`

Media Manager searches Music Assistant, browses the user's Music Assistant
library, plays by Music Assistant media URI or by name, reads and transfers
Music Assistant queues, and manages Home Assistant media player groups.

Supported operations:

- `search`
- `browse_library`
- `play_by_uri`
- `play_by_name`
- `get_queue`
- `transfer_queue`
- `group_join`
- `group_unjoin`
- `group_clear_members`

Use Entity Index first when you need Home Assistant `media_player.*` entity IDs.
Use `play_by_name` for ordinary voice requests to play one or more well-known
tracks by artist/title. Use search or browse first, then `play_by_uri`, for
library items, exact versions, obscure tracks, or corrections after a wrong
name-based match.

If more than one Music Assistant instance is installed, create this helper and
set it to the config entry ID to use:

```yaml
input_text.llmtool_media_manager_music_assistant_config_entry_id
```

Run `script.llmtool_media_manager` from Developer Tools -> Actions:

```yaml
operation: search
query: Bohemian Rhapsody
search_media_types: track
limit: 5
```

Expected response shape:

```yaml
success: true
answer: "Found 1 media item."
data:
  results:
    - media_type: track
      count: 1
      total: 1
      items:
        - name: Bohemian Rhapsody
          uri: spotify://track/example
          media_type: track
          artist_names:
            - Queen
          album_name: A Night at the Opera
meta:
  tool: llmtool_media_manager
  operation: search
  query: Bohemian Rhapsody
  search_media_types:
    - track
  library_only: false
  limit: 5
  count: 1
  total: 1
```

Then play selected URIs:

```yaml
operation: play_by_uri
player_entity_id: media_player.kitchen
media_uris: |-
  spotify://track/example
enqueue: play
```

Fast name-based playback:

```yaml
operation: play_by_name
player_entity_id: media_player.kitchen
play_queries: |-
  Lady Gaga - Aura
  Queen - Don't Stop Me Now
media_type: track
enqueue: play
```

To group players before playback:

```yaml
operation: group_join
leader_entity_id: media_player.living_room
member_entity_ids: media_player.kitchen,media_player.bedroom
replace_existing: true
```

Validation issues return soft failures with `error`, `data`, and `meta` so the
Assistant can retry.

## Memory Manager tool

Memory Manager is optional. Use it only when you want Assistant memory.

Before exposing it to Assist:

1. Install Variables+History through HACS.
2. Create a Sensor variable with ID `llm_memory`.
3. Enable Restore on Restart.
4. Enable Exclude from Recorder.
5. Reload scripts or restart Home Assistant.
6. Run `python_script.reload`.

After setup, Home Assistant should expose:

- `script.llmtool_memory_manager`
- `python_script.llmtool_memory_manager`
- `sensor.llm_memory`

Expose only `script.llmtool_memory_manager` to Assist.

Supported operations:

- `remember`
- `search`
- `read`
- `update`
- `forget`
- `inspect_inventory`
- `list_recent`
- `status`

Run `script.llmtool_memory_manager` from Developer Tools -> Actions:

```yaml
operation: remember
topic: school
tags: schedule,kid_one
text: School starts at 08:10 on regular weekdays.
```

Expected response shape:

```yaml
success: true
answer: "Remembered 1 memory entry."
data:
  memory_id: m000001
  topic: school
  tags:
    - schedule
    - kid_one
meta:
  tool: llmtool_memory_manager
  operation: remember
  store_size_bytes: 424
  soft_limit_bytes: 98304
  hard_limit_bytes: 122880
```

Use `inspect_inventory` to see the Memory Inventory: existing Memory Topics and
Memory Tags. It is only an index/discovery operation; do not use it by itself
to answer memory recall questions.

```yaml
operation: inspect_inventory
```

Before search or remember, call `inspect_inventory` first unless the user gives
an exact `memory_id`, exact known topic/tags, or you already called
`inspect_inventory` for this user request. For recall, choose existing topic and
tags from the Memory Inventory, then `search`, then `read`.

Use `search` for snippets, then `read` for full text. Snippets are for choosing
candidates, not factual answers. Do not guess Memory IDs. Search results include
`memory_id`; pass that ID to `read`, `update`, or `forget`.

```yaml
operation: search
topic: school
tags: schedule,kid_one
tag_match_mode: all
limit: 5
```

Omit `query` when listing by `topic` or `tags`. Query-only search is also
valid for distinctive names or terms when no Memory Topic or Memory Tag is
known, but topic and tags keep results smaller when available. Empty `query`
plus empty `topic` plus empty `tags` is invalid; use `list_recent` only for
broad browsing, recent-memory checks, or debugging when search scope is unknown.
For example, `search` with `topic: school` and no `query` lists school Memory
Entry snippets. `search` with `tags: kid_one` and no `query` lists `kid_one`
Memory Entry snippets across topics.

`remember` always creates a new Memory Entry. `update` replaces full text by
Memory ID and keeps omitted topic or tags unchanged. `forget` hard-deletes a
Memory Entry by Memory ID. After finding a candidate by `search`, use `read`
before `update` or ambiguous `forget` so you can confirm the full Memory Entry.
If search returns multiple plausible entries for `update` or `forget`, ask the
user to choose before changing memory unless the user's wording clearly
identifies one result. If the user gives an exact `memory_id`, you can use it
directly. `forget` is destructive; call it only when the user explicitly asks
or confirms.

Each Memory Entry text is capped at 4 KiB. The store warns above 96 KiB and
rejects writes above 120 KiB. Search is deterministic lexical token search, not
semantic or fuzzy search.

## Calculator tool

After install, Home Assistant should expose:

- `script.llmtool_calculator`
- `python_script.llmtool_calculator`

Calculator performs arithmetic over values the Assistant already has. It does
not fetch entities, states, units, or history.

Supported operations:

- `sum`
- `difference`
- `product`
- `quotient`
- `minimum`
- `maximum`
- `average`

Run `script.llmtool_calculator` from Developer Tools -> Actions:

```yaml
operation: average
values: 21.5,22,20.8
precision: 1
```

Expected response shape:

```yaml
success: true
answer: "Result: 21.4."
data:
  result: 21.4
  raw_result: 21.433333333333334
  values:
    - 21.5
    - 22
    - 20.8
meta:
  tool: llmtool_calculator
  operation: average
  value_count: 3
  precision: 1
```

Use decimal numbers without units. Use `.` as decimal separator, independent of
locale settings. Commas separate values.

Invalid values return a soft failure:

```yaml
success: false
error: "Invalid Calculator value. Use decimal numbers with '.' as decimal separator."
data:
  invalid_values:
    - token: "21 C"
      position: 2
  expected: "Comma-separated decimal numbers without units. Commas separate values; use '.' for decimals."
meta:
  tool: llmtool_calculator
```

## Date Calculator tool

After install, Home Assistant should expose:

- `script.llmtool_date_calculator`
- `python_script.llmtool_date_calculator`

Date Calculator performs deterministic calendar and local-time calculations over
dates the Assistant already has. It does not fetch entities, states, history, or
statistics.

Supported operations:

- `duration_between_dates`
- `date_by_adding_segments`
- `weekday_for_date`
- `next_matching_date`
- `list_calendar_days`
- `epoch_to_date`
- `date_to_epoch`

Use local Home Assistant time in exactly this format:

```text
YYYY-MM-DD HH:MM:SS
```

Run `script.llmtool_date_calculator` from Developer Tools -> Actions:

```yaml
operation: date_by_adding_segments
date: "2025-01-31 10:00:00"
segments: months=1,days=2
```

Expected response shape:

```yaml
success: true
answer: "Calculated date."
data:
  new_date: "2025-03-02 10:00:00"
  weekday: Sunday
  epoch_time_s: 1740906000
  segments:
    years: 0
    months: 1
    days: 2
    hours: 0
    minutes: 0
    seconds: 0
meta:
  tool: llmtool_date_calculator
  operation: date_by_adding_segments
  date: "2025-01-31 10:00:00"
```

For `date_by_adding_segments`, pass `segments` as comma-separated integer
`key=value` pairs. Supported keys are `years`, `months`, `days`, `hours`,
`minutes`, and `seconds`. Month/year results clamp to the last valid day of the
target month when needed.

Use `next_matching_date` for recurring calendar dates such as birthdays,
anniversaries, the next Friday 13th, or the next Tuesday in December. Pass any
combination of `month`, `day_of_month`, and `weekday`; month alone is too broad.
Optional `hour`, `minute`, and `second` set the returned time. Empty `date`
means now.

For `list_calendar_days`, optional `limit` defaults to 366 and maximum is 3660.
Capped responses include `meta.truncated: true`.

## LLM tool response format

Tools return a structured response in Developer Tools -> Actions:

```yaml
success: true
answer: "Short summary for the Assistant."
data: {}
meta: {}
```

Assist tool traces wrap that payload under `result`.

Expected validation failures return:

```yaml
success: false
error: "Short actionable error."
data: {}
meta: {}
```

## Prompt overview

Use this compact overview in the Assistant instructions. Detailed call rules,
parameters, examples, and retry behavior live in each Tool description.

```text
Tools starting with "LLM Tool ..." are from a tool collection.
They share one structured response. Use answer for a short summary, data
for structured details, and meta for counts, query echo, truncation, and
warnings. On validation failure, use error and data to retry.

Tool results are not final by themselves. If one plausible tool returns no
answer, continue with another relevant tool before saying you do not know. Use
"I don't know" only after the likely tools were checked.

MEMORY FIRST RULE:
-------------------
Before using other tools or saying "I don't know", check whether Memory Manager
remembered something relevant to the request.
Users can save any user-provided knowledge in memory. Do not treat tool names,
live entity names, examples, Known Memory Topics, or Known Memory Tags as limits
on what may be remembered.
If Memory Manager has no matching Memory Entry, continue with the logically
matching tool.

{% set memory_state = states('sensor.llm_memory') %}
{% set memory = state_attr('sensor.llm_memory', 'memory') %}
{% if memory_state not in ['unknown', 'unavailable', 'none', ''] %}
Memory Inventory:
  {% if memory is none %}
Known Memory Topics: none
Known Memory Tags: none
  {% elif memory is not mapping %}
Known Memory Topics: unavailable
Known Memory Tags: unavailable
  {% else %}
    {% set schema_version = memory.get('schema_version') %}
    {% set entries = memory.get('entries') %}
    {% if schema_version is not none and schema_version != 2 %}
Known Memory Topics: unavailable
Known Memory Tags: unavailable
    {% elif entries is none %}
Known Memory Topics: none
Known Memory Tags: none
    {% elif entries is not mapping %}
Known Memory Topics: unavailable
Known Memory Tags: unavailable
    {% else %}
      {% set ns = namespace(topics=[], tags=[], malformed=false) %}
      {% for memory_id, entry in entries.items() %}
        {% if entry is not mapping %}
          {% set ns.malformed = true %}
        {% else %}
          {% set topic = entry.get('topic') %}
          {% set entry_tags = entry.get('tags') %}
          {% if topic is not string or not topic %}
            {% set ns.malformed = true %}
          {% elif topic not in ns.topics %}
            {% set ns.topics = ns.topics + [topic] %}
          {% endif %}
          {% if entry_tags is string or entry_tags is not iterable %}
            {% set ns.malformed = true %}
          {% else %}
            {% for tag in entry_tags %}
              {% if tag is not string or not tag %}
                {% set ns.malformed = true %}
              {% elif tag not in ns.tags %}
                {% set ns.tags = ns.tags + [tag] %}
              {% endif %}
            {% endfor %}
          {% endif %}
        {% endif %}
      {% endfor %}
      {% if ns.malformed %}
Known Memory Topics: unavailable
Known Memory Tags: unavailable
      {% else %}
Known Memory Topics: {{ (ns.topics | sort | join(', ')) if ns.topics else 'none' }}
Known Memory Tags: {{ (ns.tags | sort | join(', ')) if ns.tags else 'none' }}
      {% endif %}
    {% endif %}
  {% endif %}
{% endif %}

Known Memory Topics and Known Memory Tags are clues for choosing a Memory
Manager call, not a complete list of what memory may contain. They are not
Memory Entries. Call Memory Manager to search and read before answering from
memory.

Use Entity Index to discover allowed Home Assistant entity IDs before calling
tools that need entity IDs, unless exact IDs are already known.

Supported Entity Index label names:
{% set configured = state_attr('input_select.llmtool_entity_index_labels', 'options') %}
{% set hidden = ['Everywhere', 'Inside', 'Outside'] %}
{% set ns = namespace(items=[]) %}
{% if configured is not none %}
  {% for label_name_text in configured %}
    {% if label_name_text and label_id(label_name_text) and label_name_text not in hidden and label_name_text not in ns.items %}
      {% set ns.items = ns.items + [label_name_text] %}
    {% endif %}
  {% endfor %}
{% else %}
  {% for label_id in labels() %}
    {% set label_name_text = label_name(label_id) %}
    {% if label_name_text and label_name_text not in hidden and label_name_text not in ns.items %}
      {% set ns.items = ns.items + [label_name_text] %}
    {% endif %}
  {% endfor %}
{% endif %}
{{ ns.items | sort | join(', ') }}

-----------

Entity Index: find entities by labels, location, and state. location is only
inside, outside, or everywhere. Rooms/floors are label_names. If an entity has
value_hint, follow it.
For room/floor plus device-type searches, use label_operator AND. OR is only
for broad alternatives and is a shortcut for multiple calls with one label each.

Long-Term Aggregated Statistics: use for durable historical statistics:
averages, minimums, maximums, changes, trends, energy, water, and other
long-term counters. For monotonic increasing counters, use change to get the
increment over a time range.

For questions like energy used, energy loaded, water used, or gas used in a
time range, prefer a cumulative energy/water/gas counter and Long-Term
Aggregated Statistics with aggregation_type=change. Do not estimate from current
power/flow multiplied by duration unless no cumulative counter/statistics exist.
Check upfront if you can to use specific labels for the entity index tool
to find cumulative energy sensors.

Raw Entity History: use for exact recent state changes, raw states, and how long
an entity stayed in a state. Raw history has limited retention, but can access
entities that do not provide long-term statistics.

Calendar Manager: use for Home Assistant calendar events, upcoming events,
event ranges, and event text search. Calendar Manager Time Range must be 365
days or less. This version reads events only.

Media Manager: use for Music Assistant search, library browsing, playback,
queue checks, queue transfers, and media_player grouping. Use Entity Index
first when you need player entity IDs. Use play_by_name for ordinary voice
requests to play one or more well-known tracks by artist/title. Use search or
browse first, then play_by_uri, for library items, exact versions, obscure
tracks, or corrections after a wrong name-based match. Use group_join before
playback when the user asks to play on grouped players.

Memory Manager: use for user-provided long-term memory. Save memory only when
the user asks or clearly confirms. Use Known Memory Topics and Known Memory Tags
to choose topic/tags when searching or remembering. For recall, call
inspect_inventory unless an exact memory_id, topic, or tags are already
available. Search and list_recent return snippets only; read before answering
from memory.

Calculator: use for every arithmetic calculation from numbers you already have.
It does not fetch entities, states, units, history, or statistics.

Date Calculator: use for every calendar or local-time calculation from dates you
already have. It does not fetch entities, states, history, or statistics.

For tools that need local timestamps, resolve relative user text first and pass
local Home Assistant time as YYYY-MM-DD HH:MM:SS.

```

## Docs

- [Glossary](CONTEXT.md)
- [HA research notes](docs/ha_research_notes.md)
- [LLM tool patterns](docs/llm_tool_patterns.md)
- [Jinja patterns](docs/jinja_patterns.md)
- [Python script notes](docs/python_script_notes.md)
- [Coding guidelines](docs/coding_guidelines.md)
- [HA trace debugging](docs/ha_trace_debugging.md)
- [Architecture decisions](docs/adr/0001-ha-native-llm-tool-scripts.md)
- [Raw Entity History REST decision](docs/adr/0002-raw-entity-history-rest-command.md)
- [Memory Manager storage decision](docs/adr/0003-optional-memory-manager-uses-variables-history.md)
- [Tool plans](docs/plans/README.md)
- [Memory Manager plan](docs/plans/implemented/memory-manager.md)
- [Media Manager plan](docs/plans/media-manager.md)
- [Calendar Manager plan](docs/plans/implemented/calendar-manager.md)
- [Long-Term Aggregated Statistics plan](docs/plans/implemented/long-term-aggregated-statistics.md)
- [Raw Entity History plan](docs/plans/implemented/raw-entity-history.md)
- [Calculator plan](docs/plans/implemented/calculator.md)
- [Date Calculator plan](docs/plans/implemented/date-calculator.md)
- [Demo tool plan](docs/plans/implemented/demo-tool.md)
- [Entity Index plan](docs/plans/implemented/entity-index.md)

## Security

- Do not commit secrets.
- Do not log or return tokens.
- Do not patch `.storage/*`.
- Expose only intended `script.llmtool_*` entities to Assist.
- Do not expose `rest_command.llmtool_home_assistant_api_get` to Assist; it is
  shared internal plumbing for LLM Tool Scripts.
- Keep `llmtool_home_assistant_bearer_token` in `secrets.yaml`, never in repo
  files.

## Validation

For every tool:

1. Validate YAML configuration.
2. Confirm `script.llmtool_*` exists.
3. Confirm fields appear in Developer Tools -> Actions.
4. Run the script directly.
5. Check structured response.
6. Expose the script to Assist.
7. Ask the Assistant to use it.
8. Inspect Conversation and Script traces.

For Raw Entity History, also confirm `rest_command.llmtool_home_assistant_api_get`
exists and the bearer token secret works.

For Entity Index helper regression checks:

```bash
python3 tests/test_llmtool_entity_index.py
```

For Calculator helper regression checks:

```bash
python3 tests/test_llmtool_calculator.py
```

For Date Calculator helper regression checks:

```bash
python3 tests/test_llmtool_date_calculator.py
```

For Long-Term Aggregated Statistics helper regression checks:

```bash
python3 tests/test_llmtool_long_term_aggregated_statistics.py
```

For Raw Entity History helper regression checks:

```bash
python3 tests/test_llmtool_raw_entity_history.py
```

For Calendar Manager helper regression checks:

```bash
python3 tests/test_llmtool_calendar_manager.py
```

For Media Manager helper regression checks:

```bash
python3 tests/test_llmtool_media_manager.py
```

For Memory Manager helper regression checks:

```bash
python3 tests/test_llmtool_memory_manager.py
```
