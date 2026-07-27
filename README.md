# Home Assistant LLM Scripts

Reusable Home Assistant script collection for LLM-based Assistants.

This project exposes Home Assistant scripts as LLM tools. Scripts use HA-native operations first, and call native `python_script` helpers only when YAML/Jinja would become hard to read.

## Status

Current implementation includes:

- `script.llmtool_demo` for install and response-shape validation
- `script.llmtool_entity_index` for safe labeled-entity discovery
- `script.llmtool_option_selector` for reading and selecting options on input_select/select entities
- `script.llmtool_long_term_aggregated_statistics` for aggregated long-term statistics
- `script.llmtool_raw_entity_history` for unaggregated raw entity history
- `script.llmtool_calculator` for deterministic arithmetic
- `script.llmtool_date_calculator` for deterministic calendar and local-time calculations
- `script.llmtool_calendar_manager` for reading Home Assistant calendar events
- `script.llmtool_weather_forecast` for reading Home Assistant weather forecasts
- `script.llmtool_media_manager` for Music Assistant media, playback mode, and media player groups
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

Returned `state` uses Home Assistant display precision but keeps Home
Assistant's canonical, unlocalized state language. `state_filter` also uses the
canonical state string, such as `on` or `off`.

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

Pass `label_names` as comma-separated text, not a YAML/JSON list.

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

Responses are capped by `limit`, default 50 and maximum 1000. Capped responses
include `meta.truncated: true`, add `data.truncation`, and make `answer` warn
about truncation. Retry with a narrower query or higher limit if needed
entities were not included.

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

## Option Selector tool

After install, Home Assistant should expose:

- `script.llmtool_option_selector`
- `python_script.llmtool_option_selector`

Option Selector reads available options from, and selects one option on,
Home Assistant `input_select.*` and `select.*` entities. Use Entity Index first
if the Assistant does not know the exact entity ID. Do not invent entity IDs.

Supported operations:

- `get_options`
- `select_option`

Operation contracts:

- `get_options`: required `operation`, `entity_id`
- `select_option`: required `operation`, `entity_id`, `desired_option`

Only pass parameters listed for the selected operation. Non-empty parameters
outside that operation contract return a soft failure.

Run `script.llmtool_option_selector` from Developer Tools -> Actions:

```yaml
operation: get_options
entity_id: input_select.house_mode
```

Expected response shape:

```yaml
success: true
answer: "Found 4 options."
data:
  entity_id: input_select.house_mode
  domain: input_select
  friendly_name: House mode
  current: Home
  options:
    - Home
    - Away
    - Sleep
    - Guest
meta:
  tool: llmtool_option_selector
  operation: get_options
  count: 4
```

Call `select_option` only when the user asks to set, change, choose, or select
an option:

```yaml
operation: select_option
entity_id: input_select.house_mode
desired_option: Away
```

`desired_option` resolves to an exact available option before Home Assistant is
called. Exact match wins. If there is no exact match, a case-insensitive unique
match is allowed. Unknown or ambiguous options return a soft failure with
allowed options.

```yaml
success: false
error: "Unknown option. Use data.allowed_options and retry."
data:
  entity_id: input_select.house_mode
  domain: input_select
  friendly_name: House mode
  desired_option: Vacation
  allowed_options:
    - Home
    - Away
meta:
  tool: llmtool_option_selector
  operation: select_option
```

Successful selection reports the requested selection and observed current state:

```yaml
success: true
answer: "Selected Away."
data:
  entity_id: input_select.house_mode
  domain: input_select
  friendly_name: House mode
  previous: Home
  selected: Away
  current: Away
meta:
  tool: llmtool_option_selector
  operation: select_option
```

Some `select.*` entities may update asynchronously, so `current` is useful
evidence, not the success condition.

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
`meta.truncated: true`, add `data.truncation`, and make `answer` warn about
truncation. Retry with a narrower time range, coarser `aggregation_period`, or
fewer entities if needed data was not included.

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
include `meta.truncated: true`, add `data.truncation`, and make `answer` warn
about truncation. Retry with a narrower time range or higher limit if needed
data was not included:

```yaml
success: true
answer: "Found 20 of 132 history entries. Attention: returned data is truncated because total matching data points (132) exceeded limit (20). Retry with a higher limit or narrower time range if needed data was not included."
data:
  truncation:
    truncated: true
    count_returned: 20
    count_total_before_truncation: 132
    limit: 20
    retry_hint: "Retry with a higher limit or narrower time range if needed data was not included."
meta:
  count: 20
  total: 132
  limit: 20
  truncated: true
```

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

Operation contracts:

```yaml
search_events:
  required: operation, keyword, start_time, end_time
  optional: calendar_entity_ids, event_type, verbosity, limit
list_range:
  required: operation, start_time, end_time
  optional: calendar_entity_ids, event_type, verbosity, limit
list_upcoming:
  required: operation
  optional: calendar_entity_ids, days_ahead, event_type, verbosity, limit
```

Only pass parameters listed for the selected operation. Non-empty parameters not
listed for that operation return a soft failure.

Use `search_events` when the user gives event text to find. Pass exact event
text from the user; do not translate it. Always provide a Calendar Manager Time
Range: `start_time` is the start of the range to search, and `end_time` is the
end of that range.

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
include `meta.truncated: true`, add `data.truncation`, and make `answer` warn
about truncation. Retry with a narrower time range or higher limit if needed
events were not included.

## Weather Forecast tool

After install, Home Assistant should expose:

- `script.llmtool_weather_forecast`
- `python_script.llmtool_weather_forecast`

Weather Forecast reads Home Assistant forecasts from one exact `weather.*`
entity. Use Entity Index first if the Assistant does not know the weather
entity ID. This version reads forecasts only.

Supported forecast types:

- `daily`
- `hourly`

This version does not expose `twice_daily`.

Call contract:

```yaml
required: weather_entity_id, forecast_type, start_time, end_time
optional: verbosity, limit
```

Use `forecast_type=daily` for full local days. Use `forecast_type=hourly` for
part-day requests, such as this evening or tomorrow morning, and for multi-day
hourly ranges.

Use local Home Assistant time in exactly this format:

```text
YYYY-MM-DD HH:MM:SS
```

`start_time` is inclusive. `end_time` is exclusive. For
`forecast_type=daily`, both times must use `00:00:00`. Returned forecast days
include `weekday`; Assistants should trust returned weekdays instead of
recalculating them.

`verbosity=overview` is the default. Use it for normal weather reports.
Overview returns baseline forecast data and only includes precipitation or wind
when worth mentioning. It omits pressure, humidity, UV index, cloud coverage,
apparent temperature, and dew point.

Use `verbosity=detailed` only when specific forecast attributes are needed.
Detailed responses return supported Home Assistant forecast fields when the
weather provider supplies them.

Run `script.llmtool_weather_forecast` from Developer Tools -> Actions:

```yaml
weather_entity_id: weather.home
forecast_type: daily
start_time: "2026-07-25 00:00:00"
end_time: "2026-07-27 00:00:00"
verbosity: overview
limit: 24
```

Expected daily response shape:

```yaml
success: true
answer: "Found 2 forecast days."
data:
  days:
    - date: "2026-07-25"
      weekday: Saturday
      condition: rainy
      temperature: 22
      templow: 16
      precipitation: 3.2
      precipitation_probability: 70
    - date: "2026-07-26"
      weekday: Sunday
      condition: partlycloudy
      temperature: 24
      templow: 17
meta:
  tool: llmtool_weather_forecast
  weather_entity_id: weather.home
  forecast_type: daily
  start_time: "2026-07-25 00:00:00"
  end_time: "2026-07-27 00:00:00"
  verbosity: overview
  count: 2
  total: 2
  limit: 24
```

Hourly responses group periods by local day:

```yaml
data:
  days:
    - date: "2026-07-24"
      weekday: Friday
      periods:
        - datetime: "2026-07-24 18:00:00"
          time: "18:00:00"
          condition: rainy
          temperature: 21
          precipitation_probability: 60
```

Responses are capped by `limit`, default 24 and maximum 168. Capped responses
include `meta.truncated: true`, add `data.truncation`, and make `answer` warn
about truncation. Retry with a narrower Weather Forecast Time Range or higher
limit if needed forecast rows were not included.

## Media Manager tool

After install, Home Assistant should expose:

- `script.llmtool_media_manager`
- `python_script.llmtool_media_manager`

Media Manager searches Music Assistant, browses the user's Music Assistant
library, plays by Music Assistant media URI or by name, reads and transfers
Music Assistant queues, sets playback mode, and manages Home Assistant media
player groups.

Supported operations:

- `search`
- `browse_library`
- `play_by_uri`
- `play_by_name`
- `get_queue`
- `transfer_queue`
- `set_playback_mode`
- `group_join`
- `group_unjoin`
- `group_clear_members`

Use Entity Index first when you need Home Assistant `media_player.*` entity IDs.
Use `search` first for a single ambiguous "play X" request when the notation or the 
media type is unclear. Use `play_by_name` when the user clearly asks for a track, album,
artist, playlist, or radio station, or when playing a multi-item track list
where one search per item would be too expensive. Use search or browse first,
then `play_by_uri`, for library items, exact versions, obscure tracks, or
corrections after a wrong name-based match.

Use `library_only: true` only when the user explicitly says library, saved,
liked, favorite, or added. For availability, playable, "do we have", or general
search requests, leave `library_only` false so Music Assistant can search
connected providers. Use `browse_library` only for explicit library intent, not
for general available media. Treat "can you play/find X?", "do we have X?", and
"is X available here/for us?" as provider search unless the user also says
library, saved, liked, favorite, or added. "My music" alone is ambiguous; do
not set `library_only` unless saved or library wording is present.

Operation contracts:

- `search`: required `operation`, `query`; optional `search_media_types`, `artist`, `album`, `library_only`, `limit`
- `browse_library`: required `operation`, `media_type`; optional `query`, `favorite`, `limit`, `offset`, `album_type`
- `play_by_uri`: required `operation`, `player_entity_id`, `media_uris`; optional `enqueue`, `radio_mode`
- `play_by_name`: required `operation`, `player_entity_id`, `play_queries`, `media_type`; optional `enqueue`, `radio_mode`
- `get_queue`: required `operation`, `player_entity_id`; optional `limit`
- `transfer_queue`: required `operation`, `source_player_entity_id`, `target_player_entity_id`; optional `auto_play`
- `set_playback_mode`: required `operation`, `player_entity_id`, and at least one of `shuffle_mode`, `repeat`; optional `shuffle_mode`, `repeat`
- `group_join`: required `operation`, `leader_entity_id`, `member_entity_ids`; optional `ungroup_first`, `replace_existing`
- `group_unjoin`: required `operation`, `member_entity_ids`
- `group_clear_members`: required `operation`, `leader_entity_id`

Playback `enqueue` defaults to `replace`. Use `replace` for normal play
requests, `next` for play-next requests, `add` for add-to-queue requests, and
`play` only for explicit Music Assistant native play behavior.

Playback mode uses `shuffle_mode: on|off` and `repeat: off|all|one`. Use
`repeat: one` for "repeat this song" and `repeat: all` for "loop the
queue/playlist". `set_playback_mode` reports the requested change, not verified
final player state.

Only pass parameters listed for the selected operation. Non-empty parameters
outside that operation contract return a soft failure.

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

Responses capped by `limit` include `meta.truncated: true`, add
`data.truncation`, and make `answer` warn about truncation. Search truncation
can hide later requested media types when earlier types consume the global
limit; if a media type has `count_total_before_truncation > 0` but
`count_returned: 0`, search that media type separately.

For albums or tracks by an artist, use `search` with the artist name in
`artist` and `query: "*"`. Keep `library_only: true` only when the user asks
for saved, liked, favorite, added, or library media:

```yaml
operation: search
query: "*"
search_media_types: album
artist: Dillon
library_only: true
limit: 100
```

`artist` narrows Music Assistant search; it is not a strict filter and may
return partial or similar artist names. Before answering "albums by X" or
"tracks by X", inspect returned `artist_names` and answer only from matching
results. Do not retry only to force a stricter artist filter; self-filter
returned items.

Then play selected URIs:

```yaml
operation: play_by_uri
player_entity_id: media_player.kitchen
media_uris: |-
  spotify://track/example
enqueue: replace
```

For "play from my library/saved/favorites" requests, search with
`library_only: true` or browse the library first, then play the selected URI
with `play_by_uri`. `play_by_name` is fine for general "play X" requests when
the media type is known.

Fast name-based playback:

```yaml
operation: play_by_name
player_entity_id: media_player.kitchen
play_queries: |-
  Lady Gaga - Aura
  Queen - Don't Stop Me Now
media_type: track
enqueue: replace
```

Radio by name:

```yaml
operation: play_by_name
player_entity_id: media_player.buro
play_queries: SWR3
media_type: radio
enqueue: replace
```

Set playback mode:

```yaml
operation: set_playback_mode
player_entity_id: media_player.kitchen
shuffle_mode: "on"
repeat: "all"
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

Operation contracts:

- `remember`: required `operation`, `topic`, `tags`, `text`
- `search`: required `operation` plus at least one of `query`, `topic`, `tags`; optional `query`, `topic`, `tags`, `tag_match_mode`, `limit`; prefer topic/tags, query-only is for exact/distinctive terms
- `read`: required `operation`, `memory_id`
- `update`: required `operation`, `memory_id`, `text`; optional `topic`, `tags`
- `forget`: required `operation`, `memory_id`
- `inspect_inventory`: required `operation`
- `list_recent`: required `operation`; optional `limit`
- `status`: required `operation`

Only pass parameters listed for the selected operation. Non-empty parameters
outside that operation contract return a soft failure.

Run `script.llmtool_memory_manager` from Developer Tools -> Actions:

```yaml
operation: remember
topic: school
tags: schedule,kid_one
text: School starts at 08:10 on regular weekdays.
```

Pass `tags` as comma-separated text, not a YAML/JSON list.

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

Use `search` for snippets, then `read` for full text. Search is primarily a
filter by known Memory Topic and/or known Memory Tags. Query text is optional
lexical token narrowing, not semantic search. Use query-only search only when
the user asks to search memories for an exact or distinctive term. Snippets are
for choosing candidates, not factual answers. Do not guess Memory IDs. Search
results include `memory_id`; pass that ID to `read`, `update`, or `forget`.

```yaml
operation: search
topic: school
tags: schedule,kid_one
tag_match_mode: all
limit: 5
```

Omit `query` when listing by `topic` or `tags`. Query-only search is valid only
for exact or distinctive terms the user asks to find in memory. Empty `query`
plus empty `topic` plus empty `tags` is invalid; use `list_recent` only for
broad browsing, recent-memory checks, or debugging when search scope is unknown.
For example, `search` with `topic: school` and no `query` lists school Memory
Entry snippets. `search` with `tags: kid_one` and no `query` lists `kid_one`
Memory Entry snippets across topics.

If `search` uses an unknown topic or tag, the tool returns a soft failure with
`known_topics`, `known_tags`, and whether a Memory Topic was accidentally used
as a tag or a Memory Tag was accidentally used as topic.

Search and `list_recent` responses capped by `limit` include
`meta.truncated: true`, add `data.truncation`, and make `answer` warn about
truncation. Retry with a higher limit or narrower memory search scope if
needed entries were not included.

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

Operation contracts:

- `duration_between_dates`: required `operation`, `date`, `date2`
- `date_by_adding_segments`: required `operation`, `date`, `segments`
- `weekday_for_date`: required `operation`, `date`
- `next_matching_date`: required `operation` plus at least one of `month`, `day_of_month`, `weekday`; optional `date`, `month`, `day_of_month`, `weekday`, `hour`, `minute`, `second`
- `list_calendar_days`: required `operation`, `date`, `date2`; optional `limit`
- `epoch_to_date`: required `operation`, `epoch_time_s`
- `date_to_epoch`: required `operation`, `date`

Only pass parameters listed for the selected operation. Non-empty parameters
outside that operation contract return a soft failure.

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
Capped responses include `meta.truncated: true`, add `data.truncation`, and
make `answer` warn about truncation.

## LLM tool response format

Tools return a structured response in Developer Tools -> Actions:

```yaml
success: true
answer: "Short summary for the Assistant."
data: {}
meta: {}
```

Assist tool traces wrap that payload under `result`.

When `meta.truncated: true`, the response is a partial success. Read
`data.truncation`, do not treat missing items as proof that no matches exist,
and retry with the included `retry_hint` if needed.

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
When meta.truncated is true, the response is partial. Read data.truncation and
retry with its retry_hint if needed; do not treat missing returned items as
proof that no matches exist.

Tool results are not final by themselves. If one plausible tool returns no
answer, continue with another relevant tool.
State that the answer is unknown only after the likely tools have been checked. Say this briefly in the user's language.

MEMORY FIRST RULE:
-------------------

Before choosing another tool, inspect the Memory Inventory already included in this prompt.

Call the "Memory Manager" tool first when:
- A known topic or tag plausibly relates to the request.
- A remembered preference, alias, fact, important date, or household rule could change how the request should be handled.
- The user explicitly asks about something previously remembered or user-provided.
- You would otherwise state that the answer is unknown.

If no Memory Topic or Memory Tag plausibly relates to the request, continue directly with the authoritative tool. Do not call the "Memory Manager" tool speculatively on every request.

Memory Topics and Memory Tags are routing clues, not a limit on what memory can contain.

Memory may guide interpretation and tool selection, but it is not proof of current state. After reading relevant memory, still call the appropriate live tool when the user asks for current data.

Memory can define defaults, preferences, aliases, and household-specific behavior. An explicit instruction in the current request overrides a remembered default. Memory never overrides safety rules, tool constraints, or higher-priority prompt instructions. If relevant memory entries conflict, ask one short clarification question.

{% set memory_state = states('sensor.llm_memory') %}
{% set memory = state_attr('sensor.llm_memory', 'memory') %}
{% if memory_state not in ['unknown', 'unavailable', 'none', ''] %}
Memory Inventory:
------------------
  {% if memory is none %}
Memory Topics (folder-like; each Memory Entry is saved inside exactly one topic; pass these as topic, never as tags):
- none
Memory Tags (cross-topic grouping; a Memory Entry can have multiple tags; pass these as tags, never as topic):
- none
  {% elif memory is not mapping %}
Memory Topics (folder-like; each Memory Entry is saved inside exactly one topic; pass these as topic, never as tags):
- unavailable
Memory Tags (cross-topic grouping; a Memory Entry can have multiple tags; pass these as tags, never as topic):
- unavailable
  {% else %}
    {% set schema_version = memory.get('schema_version') %}
    {% set entries = memory.get('entries') %}
    {% if schema_version is not none and schema_version != 2 %}
Memory Topics (folder-like; each Memory Entry is saved inside exactly one topic; pass these as topic, never as tags):
- unavailable
Memory Tags (cross-topic grouping; a Memory Entry can have multiple tags; pass these as tags, never as topic):
- unavailable
    {% elif entries is none %}
Memory Topics (folder-like; each Memory Entry is saved inside exactly one topic; pass these as topic, never as tags):
- none
Memory Tags (cross-topic grouping; a Memory Entry can have multiple tags; pass these as tags, never as topic):
- none
    {% elif entries is not mapping %}
Memory Topics (folder-like; each Memory Entry is saved inside exactly one topic; pass these as topic, never as tags):
- unavailable
Memory Tags (cross-topic grouping; a Memory Entry can have multiple tags; pass these as tags, never as topic):
- unavailable
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
Memory Topics (folder-like; each Memory Entry is saved inside exactly one topic; pass these as topic, never as tags):
- unavailable
Memory Tags (cross-topic grouping; a Memory Entry can have multiple tags; pass these as tags, never as topic):
- unavailable
      {% else %}
Memory Topics (folder-like; each Memory Entry is saved inside exactly one topic; pass these as topic, never as tags):
        {% if ns.topics %}
          {% for topic in ns.topics | sort %}
- {{ topic }}
          {% endfor %}
        {% else %}
- none
        {% endif %}
Memory Tags (cross-topic grouping; a Memory Entry can have multiple tags; pass these as tags, never as topic):
        {% if ns.tags %}
          {% for tag in ns.tags | sort %}
- {{ tag }}
          {% endfor %}
        {% else %}
- none
        {% endif %}
      {% endif %}
    {% endif %}
  {% endif %}
{% endif %}

------
                  
ENTITY INDEX LABELS:
-----------------------

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
Use Entity Index to discover allowed Home Assistant entity IDs before calling
tools that need entity IDs, unless exact IDs are already known.

Option Selector: use for reading available options from, and selecting one
option on, existing input_select.* and select.* entities. Use Entity Index first
if the exact entity ID is unknown. Call get_options to inspect exact option
spelling. Call select_option only when the user asks to set, change, choose, or
select an option. desired_option exact match wins; otherwise a
case-insensitive unique match is allowed.

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
days or less. This version reads events only. For event text search, use
search_events with keyword, start_time, and end_time. Pass exact event text from
the user as keyword; do not translate it.

Weather Forecast: use for Home Assistant weather forecast questions. Use Entity
Index first if the exact weather.* entity ID is unknown. Use forecast_type=daily
only for full local days with midnight start/end. Use forecast_type=hourly for
part-day or multi-day hourly ranges. Use overview for normal weather reports.
Request detailed only when specific forecast attributes are needed.

Media Manager: use for Music Assistant search, library browsing, playback,
queue checks, queue transfers, playback mode, and media_player grouping. Use Entity Index
first when you need player entity IDs. Use search first for one ambiguous
"play X" request when the notation or the media type is unclear. 
Use play_by_name with explicit media_type when the user clearly asks 
for track, album, artist, playlist, or radio, 
or when playing a multi-item track list where one search per item is too
expensive. Use search or browse first, then play_by_uri, for library items,
exact versions, obscure tracks, or corrections after a wrong name-based match.
Use group_join before playback when the user asks to play on grouped players.
Set library_only=true only when the user explicitly says library, saved, liked,
favorite, or added. For availability/playable/search/"do we have" requests,
leave library_only false. For "play from my library" requests, search/browse
first, then play_by_uri.
Treat "can you play/find X?", "do we have X?", and "is X available here/for
us?" as provider search unless the user also says library, saved, liked,
favorite, or added. "My music" alone is ambiguous; do not set library_only
unless saved or library wording is present.
For albums or tracks by an artist, search one media type with artist set and
query "*"; keep library_only=true only for explicit library intent. Artist
narrowing is not a strict filter: inspect artist_names and ignore non-matching
items yourself instead of retrying only to force stricter filtering. If search
truncation says another media type has hidden results, search that media type
separately.

Memory Manager: use for user-provided long-term memory. Save memory only when
the user asks or clearly confirms. Use Memory Inventory topics and tags to
choose topic/tags when searching or remembering. For recall, call
inspect_inventory unless an exact memory_id, topic, or tags are already
available from the Memory Inventory. Prefer search by topic/tags with empty
query. Use query only to narrow by exact/distinctive lexical terms. Search and
list_recent return snippets only; read before answering from memory.

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
- [Option Selector plan](docs/plans/implemented/option-selector.md)
- [Memory Manager plan](docs/plans/implemented/memory-manager.md)
- [Media Manager plan](docs/plans/implemented/media-manager.md)
- [Weather Forecast plan](docs/plans/implemented/weather-forecast.md)
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

For Option Selector helper regression checks:

```bash
python3 tests/test_llmtool_option_selector.py
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

For Weather Forecast helper regression checks:

```bash
python3 tests/test_llmtool_weather_forecast.py
```

For Media Manager helper regression checks:

```bash
python3 tests/test_llmtool_media_manager.py
```

For Memory Manager helper regression checks:

```bash
python3 tests/test_llmtool_memory_manager.py
```
