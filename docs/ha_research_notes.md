# Home Assistant Research Notes

Checked: 2026-07-24
Docs version shown by Home Assistant pages: 2026.7.4

Use this file as the source ledger for Home Assistant behavior we rely on. Before substantial changes, re-check official docs, release notes, and source for anything touched here.

## Source policy

- Home Assistant docs and Home Assistant Core source are the primary sources.
- Prefer official docs/source over third-party examples, old forum posts, old model memory, and generated code.
- Third-party repos can inspire checks, but do not copy rules into this repo unless they match our script collection and are confirmed against official sources or real HA testing.
- When checking docs, update the date and Home Assistant docs/source version here.

## Sources checked

- Home Assistant script syntax: https://www.home-assistant.io/docs/scripts/
- Home Assistant Scripts integration: https://www.home-assistant.io/integrations/script/
- Home Assistant Python Scripts integration: https://www.home-assistant.io/integrations/python_script/
- Home Assistant RESTful Command integration: https://www.home-assistant.io/integrations/rest_command/
- Home Assistant REST API: https://developers.home-assistant.io/docs/api/rest/
- Home Assistant Recorder statistics action:
  https://www.home-assistant.io/actions/recorder.get_statistics/
- Home Assistant History integration:
  https://www.home-assistant.io/integrations/history/
- Home Assistant Calendar integration:
  https://www.home-assistant.io/integrations/calendar/
- Home Assistant Calendar get events action:
  https://www.home-assistant.io/actions/calendar.get_events/
- Home Assistant Weather get forecasts action:
  https://www.home-assistant.io/actions/weather.get_forecasts/
- Home Assistant Media player integration:
  https://www.home-assistant.io/integrations/media_player/
- Home Assistant media player join action:
  https://www.home-assistant.io/actions/media_player.join/
- Home Assistant media player unjoin action:
  https://www.home-assistant.io/actions/media_player.unjoin/
- Home Assistant media player shuffle action:
  https://www.home-assistant.io/actions/media_player.shuffle_set/
- Home Assistant media player repeat action:
  https://www.home-assistant.io/actions/media_player.repeat_set/
- Home Assistant Music Assistant integration:
  https://www.home-assistant.io/integrations/music_assistant/
- Home Assistant Music Assistant actions:
  - https://www.home-assistant.io/actions/music_assistant.get_library/
  - https://www.home-assistant.io/actions/music_assistant.search/
  - https://www.home-assistant.io/actions/music_assistant.play_media/
  - https://www.home-assistant.io/actions/music_assistant.get_queue/
  - https://www.home-assistant.io/actions/music_assistant.transfer_queue/
- Home Assistant Core Music Assistant services source:
  `homeassistant/components/music_assistant/services.yaml`
- Deprecated Music Assistant custom integration:
  https://github.com/music-assistant/hass-music-assistant
- Home Assistant Core template helper source:
  `homeassistant/helpers/template.py`
- Home Assistant sensor source:
  `homeassistant/components/sensor/__init__.py`
- Home Assistant sensor long-term statistics developer docs:
  https://developers.home-assistant.io/docs/core/entity/sensor/#long-term-statistics
- Home Assistant sensor presentation rounding developer note:
  https://developers.home-assistant.io/blog/2023/02/08/sensor_presentation_rounding/
- Home Assistant sensor default display precision developer note:
  https://developers.home-assistant.io/blog/2025/05/26/sensor-default-display-precision/
- Home Assistant template functions: https://www.home-assistant.io/template-functions/
- Home Assistant states template function:
  https://www.home-assistant.io/template-functions/states/
- Home Assistant translated state template function:
  https://www.home-assistant.io/template-functions/state_translated/
- Home Assistant label template functions:
  - https://www.home-assistant.io/template-functions/labels/
  - https://www.home-assistant.io/template-functions/label_entities/
  - https://www.home-assistant.io/template-functions/label_id/
  - https://www.home-assistant.io/template-functions/label_name/
- Home Assistant area/device template functions:
  - https://www.home-assistant.io/template-functions/area_id/
  - https://www.home-assistant.io/template-functions/device_id/
- Home Assistant conversation integrations:
  - https://www.home-assistant.io/integrations/openai_conversation/
  - https://www.home-assistant.io/integrations/google_generative_ai_conversation/
- Home Assistant Input Select integration:
  - https://www.home-assistant.io/integrations/input_select/
- Home Assistant Core LLM helper source: `homeassistant/helpers/llm.py`
- Home Assistant Core Python script source:
  `homeassistant/components/python_script/__init__.py`
- Home Assistant Core Recorder services source:
  `homeassistant/components/recorder/services.py`
- Home Assistant Core History source:
  `homeassistant/components/history/__init__.py`
- Home Assistant `from_json` template function:
  https://www.home-assistant.io/template-functions/from_json/
- Variables+History custom integration:
  https://github.com/Wibias/hass-variables
- Home Assistant RestoreEntity source:
  `homeassistant/helpers/restore_state.py`

## Verified

- Scripts can run from Assist and other callers.
- Scripts can declare `fields` for UI/tool parameter metadata.
- Action data passed to a script is available as template variables, even when
  not declared under `fields`.
- Current script examples use `action:` for actions. Prefer `action:` over legacy `service:` in new YAML.
- Script `stop` can return a response through `response_variable`; response data must be a mapping.
- Assist exposed-script tools wrap the script action response as `success: true` and `result: <script response>`.
- Native `python_script` files live under `<config>/python_scripts/`.
- Native `python_script` can return data by writing to `output`; callers read it through `response_variable`.
- Native `python_script.reload` reloads available scripts and `services.yaml`; changing an existing Python script does not require that reload.
- `rest_command` returns a dictionary with `status`, `content`, and `headers`; callers can capture it with `response_variable`.
- `rest_command` can expose JSON response content as native Home Assistant
  template data instead of a JSON string. Check whether `content is string`
  before applying `from_json`.
- Home Assistant template functions include JSON serialization filters/functions such as `to_json` and `tojson`.
- Home Assistant `from_json` accepts a `default` value that is returned instead
  of raising a template error when the input is invalid JSON.
- `states(entity_id, rounded=true)` returns numeric states rounded according to
  the entity's display precision, matching Home Assistant UI rounding.
- `states(entity_id, with_unit=true)` appends the unit and implies display
  rounding unless `rounded` is set explicitly.
- `state_translated(entity_id)` returns localized state text for display. Use
  `states(entity_id)` for comparisons because translated state text changes
  with Home Assistant language.
- Home Assistant template state formatting calls sensor presentation rounding
  through `async_rounded_state`, which reads entity registry display precision
  or suggested display precision.
- Entity Index should collect Entity Display State in the LLM Tool Script with
  `states(entity_id, rounded=true)` and keep raw `states(entity_id)` for
  `state_filter`.
- Home Assistant REST API requires bearer token auth and exposes `/api/history/period`.
- `labels()` returns all label IDs when called without an argument.
- `labels(entity_id)` returns labels assigned directly to that entity; device and area labels do not roll up.
- `label_entities(label_id_or_name)` returns entity IDs with the label assigned directly; device and area labels do not roll up.
- `label_entities()` returns an empty list when the label does not match any entities.
- `label_id(label_name)` returns the internal label ID for a friendly label name, returns `None` when missing, and is case-sensitive.
- `label_name(label_id)` returns the friendly label name for an internal label ID and returns `None` when missing.
- LLM Tool parameters should use friendly label names when that is what the HA user sees; resolve to internal IDs inside templates when another helper expects or benefits from IDs.
- Conversation agent Instructions for the official OpenAI and Google Gemini
  integrations are written using Home Assistant templating.
- Input Select helpers define an editable list of options and can be configured
  in the UI or YAML.
- `area_id(entity_id)` returns the area ID for an entity or `None`.
- `device_id(entity_id)` returns the device ID for an entity or `None`.
- `integration_entities(entry_name)` returns entity IDs for an integration
  domain, or for a config entry when `entry_name` matches that config entry's
  title.
- `config_entry_id(entity_id)` returns the config entry ID for an entity.
- `config_entry_attr(config_entry_id, attr_name)` returns selected config entry
  fields including `domain`, `title`, `state`, `source`, and `disabled_by`.
- Home Assistant config entry IDs are generated when not explicitly supplied;
  Music Assistant config flow sets a stable server unique ID, but this is not
  the same as the action-facing config entry ID.
- Native `python_script` can read state machine data through `hass.states.entity_ids`,
  `hass.states.all`, `hass.states.get`, `hass.states.is_state`, and
  `hass.states.is_state_attr`.
- Native `python_script` exposes `datetime`, `time`, and selected `dt_util`
  helpers including `now`, `parse_datetime`, `as_utc`, and `as_local`.
- Native `python_script` protected attribute access can return `None` for
  missing methods, such as `.get` on a list. Avoid calling `.get` on values that
  may be lists or non-mappings; use guarded item access instead.
- Raw Entity History parses REST timestamps manually into epoch seconds and uses
  `dt_util.utc_from_timestamp` for local rendering. This keeps REST timestamp
  shaping independent from optional datetime parsing helpers and constructors in
  the native `python_script` sandbox.
- Native `python_script` cannot access `hass.config`; use exposed `dt_util`
  helpers instead of reading `hass.config.time_zone`.
- `dt_util.as_utc` assumes a naive datetime is in Home Assistant's default time
  zone; `dt_util.as_local` converts UTC datetimes back to the same local time
  zone.
- In native `python_script`, `datetime.datetime.strptime` and
  `datetime.datetime.strftime` can trigger a blocked import and fail with
  `ImportError: Not allowed to import time`; parse and format strict timestamp
  fields manually or use exposed `dt_util` helpers.
- Native `python_script` does not expose every Python type constructor as a
  named builtin. Avoid checks such as `isinstance(value, dict)` or
  `isinstance(value, list)` in helpers; use existing local type boundaries or
  simple method-shape checks instead.
- Complex block-template results can arrive in native action data as strings.
  For list/dict handoff to a Python Helper, serialize with `to_json`, then pass
  it through `from_json` at the action boundary.
- Script trace from 2026-06-17 showed a simple list rendered with `to_json` in a
  script variable can be stored as a native list. Do not call `from_json` on a
  value that the trace already shows as a list/dict.
- Before serializing entity records for a Python Helper, convert enum-like
  attributes such as `unit_of_measurement` and `state_class` to strings.
- `recorder.get_statistics` retrieves long-term statistics for one or more
  statistic IDs and returns data through a response variable.
- `recorder.get_statistics` accepts entities or statistics as statistic IDs. For
  Home Assistant recorder-owned sensor statistics, the statistic ID is the
  entity ID. External statistics can use a separate `domain:statistic` ID
  format.
- `recorder.get_statistics` is registered as an administrator-only action.
- `recorder.get_statistics` accepts `start_time`, optional `end_time`,
  `statistic_ids`, `period`, `types`, and optional `units`.
- `recorder.get_statistics` periods are `5minute`, `hour`, `day`, `week`,
  `month`, and `year`.
- `recorder.get_statistics` types are `change`, `last_reset`, `max`, `mean`,
  `min`, `state`, and `sum`.
- `recorder.get_statistics` response data is keyed by statistic ID under
  `statistics`; each row includes `start` and `end`, plus requested value types
  when present.
- `recorder.get_statistics` formats returned `start` and `end` as UTC ISO
  datetime strings.
- If a requested statistic ID has no statistics, `recorder.get_statistics` does
  not include it in the response.
- Long-term statistics are available for sensors with `state_class` of
  `measurement`, `total`, or `total_increasing`.
- Home Assistant records short-term statistics every 5 minutes and stores
  hourly long-term aggregates. Short-term statistics are purged after a
  configured period, default 10 days. Long-term statistics are not purged.
- Native `python_script` can call actions with `blocking=True` and
  `return_response=True` to retrieve response data.
- Home Assistant History depends on Recorder. If Recorder excludes an entity,
  history is not available for that entity.
- By default, Recorder stores raw history for 10 days; users can change the
  retention period, trading storage usage for longer full-resolution history.
- Official Recorder actions include `recorder.get_statistics` for long-term
  statistics, but no documented action for raw entity history.
- Home Assistant raw entity history is available through the REST API
  `/api/history/period/<timestamp>` with `filter_entity_id`, `end_time`,
  `minimal_response`, `no_attributes`, and `significant_changes_only`.
- Home Assistant History REST defaults `significant_changes_only` to enabled;
  callers must pass `significant_changes_only=0` to request all recorded state
  changes.
- Home Assistant history websocket source exposes `history/history_during_period`,
  but LLM Tool Scripts have no native websocket action and native
  `python_script` cannot import a websocket client.
- Home Assistant calendar entities expose whether there is an active event
  through entity state, but event details are read through calendar actions.
- Home Assistant Calendar docs list `calendar.create_event` and
  `calendar.get_events`; some calendar integrations support writing events.
- `calendar.get_events` reads events on one or more calendars within a date
  range and returns response data through a response variable.
- `calendar.get_events` accepts `start_date_time`, `end_date_time`, or
  `duration`; `end_date_time` is exclusive and cannot be used together with
  `duration`.
- `calendar.get_events` requires a target. It can target calendar entities,
  devices, areas, floors, or labels. Calendar Manager uses explicit calendar
  entity IDs.
- `calendar.get_events` response data is keyed by calendar entity ID; each
  value contains an `events` list.
- Calendar event response rows include `summary`, optional `description`,
  `start`, `end`, and optional `location`. Event `end` is exclusive.
- `weather.get_forecasts` reads forecast data from weather entities and returns
  response data through a response variable.
- `weather.get_forecasts` requires a forecast `type` in YAML. Documented
  values are `daily`, `hourly`, and `twice_daily`.
- Weather entities only support the forecast types supplied by their
  integration.
- `weather.get_forecasts` response data is keyed by weather entity ID; each
  value contains a `forecast` list.
- Weather forecast rows include `datetime`; documented forecast fields include
  `is_daytime`, `condition`, `apparent_temperature`, `temperature`, `templow`,
  `dew_point`, `humidity`, `cloud_coverage`, `precipitation`,
  `precipitation_probability`, `pressure`, `uv_index`, `wind_bearing`,
  `wind_gust_speed`, and `wind_speed`. Weather providers may omit fields they
  do not supply.
- `media_player.join` groups media players together for synchronous playback on
  supported multiroom audio systems.
- `media_player.join` uses the target media player as the player others follow,
  and accepts required `group_members` in action data.
- `media_player.unjoin` removes a target media player from a player group.
- `media_player.unjoin` has no additional YAML options beyond the target.
- Media player grouping actions only work on integrations that support player
  groups.
- `media_player.shuffle_set` targets media player entities and requires
  `shuffle`, a boolean.
- `media_player.repeat_set` targets media player entities and requires
  `repeat`, with documented values `off`, `all`, and `one`.
- Shuffle and repeat actions only work on media players that support those
  playback modes.
- The official Home Assistant Music Assistant integration provides
  `music_assistant.get_library`, `music_assistant.search`,
  `music_assistant.play_media`, `music_assistant.get_queue`, and
  `music_assistant.transfer_queue`.
- The deprecated Music Assistant custom integration should not be targeted for
  new LLM Tools.
- Music Assistant search and library actions require `config_entry_id`.
- Music Assistant search and library actions use `config_entry_id` to retrieve
  the loaded Music Assistant client.
- Music Assistant `play_media`, `get_queue`, and `transfer_queue` are platform
  entity actions targeting Music Assistant media player entities, so the target
  entity supplies the Music Assistant instance context.
- `music_assistant.search` searches the Music Assistant library and connected
  providers, returns result lists grouped by media type, and supports `name`,
  optional `media_type`, optional `artist`, optional `album`, `limit`, and
  `library_only`. The `artist` and `album` fields are combined into the search
  query before calling Music Assistant search; they are helper fields for a
  more precise query, not separate result filters.
- `music_assistant.get_library` returns an `items` list plus pagination/query
  echo fields. It supports `media_type`, `favorite`, `search`, `limit`,
  `offset`, `order_by`, `album_type`, and `album_artists_only`.
- `music_assistant.get_library` `album_type` applies only when `media_type` is
  `album`; supported values are `album`, `single`, `compilation`, `ep`, and
  `unknown`.
- `music_assistant.get_library` `album_artists_only` applies only when
  `media_type` is `artist`.
- Music Assistant search and library item results include URIs that can be
  passed to `music_assistant.play_media`.
- `music_assistant.play_media` targets Music Assistant `media_player.*`
  entities, accepts one or more `media_id` values, optional `media_type`,
  optional `artist`, optional `album`, `enqueue`, `radio_mode`, and `username`.
- `music_assistant.get_queue` targets Music Assistant `media_player.*`
  entities and returns queue details keyed by entity ID.
- `music_assistant.transfer_queue` targets the destination Music Assistant
  player and accepts optional `source_player` plus `auto_play`. If
  `source_player` is omitted, Music Assistant uses the first playing player.
- Variables+History v3.5.7 creates variable entities as `sensor.*`,
  `binary_sensor.*`, or `device_tracker.*`.
- Variables+History supports UI-created sensor variables and YAML-created
  sensor variables. YAML-created variables cannot be edited through the
  integration UI.
- Variables+History sensor variables support initial attributes, Restore on
  Restart, Force Update, and Exclude from Recorder.
- Variables+History documentation recommends Exclude from Recorder for variable
  attributes larger than 16 KiB to prevent Recorder errors.
- Variables+History exposes `variable.update_sensor` for sensor variables. It
  can update the state value, update attributes, and replace or merge existing
  attributes.
- Variables+History defaults `replace_attributes` to false. Memory Manager
  should use `replace_attributes: true` when writing the full memory attribute
  so deleted entries do not remain as stale top-level attributes.
- Variables+History sensor variables extend Home Assistant `RestoreSensor`, and
  Home Assistant restore state is stored separately from Recorder. This supports
  the Memory Manager plan to use Restore on Restart while excluding the Memory
  Store Entity from Recorder, but it still needs manual validation in a real
  Home Assistant instance.

## Assumptions

- Exposed scripts remain the simplest public interface for this project.
- LLM integrations handle structured script responses best when the response includes a short `answer` plus structured `data`.
- Scalar fields are safer for LLM tool calls than complex selector output until tested across Assist integrations.
- Script descriptions and field descriptions should be treated as static UI/tool
  metadata, not as rendered templates.

## Risks

- Assist tool schema generation from script fields may differ between LLM integrations.
- `success: false` is a soft error convention for the Assistant, not a Home Assistant runtime error.
- History access through REST commands needs careful token handling with `secrets.yaml`.
- The permission behavior of exposed Assist scripts that call administrator-only
  actions needs validation in a real Home Assistant instance.
- Media Manager group operations use `state_attr(leader_entity_id,
  'group_members')` as the current group snapshot for replace and clear
  planning; this needs validation across real media player integrations.
- Music Assistant `get_library` exposes `album_type` as a multi-select/list
  action field; Media Manager accepts one value and sends it as a one-item list.
