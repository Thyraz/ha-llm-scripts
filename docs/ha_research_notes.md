# Home Assistant Research Notes

Checked: 2026-06-20
Docs version shown by Home Assistant pages: 2026.6.4

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
- Home Assistant sensor long-term statistics developer docs:
  https://developers.home-assistant.io/docs/core/entity/sensor/#long-term-statistics
- Home Assistant template functions: https://www.home-assistant.io/template-functions/
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
- Native `python_script` can read state machine data through `hass.states.entity_ids`,
  `hass.states.all`, `hass.states.get`, `hass.states.is_state`, and
  `hass.states.is_state_attr`.
- Native `python_script` exposes `datetime`, `time`, and selected `dt_util`
  helpers including `now`, `parse_datetime`, `as_utc`, and `as_local`.
- Raw Entity History trace from 2026-06-21 showed a native `python_script`
  `TypeError: 'NoneType' object is not callable` when shaping REST timestamp
  rows with `dt_util.parse_datetime`. Parse strict REST timestamps manually in
  that helper.
- Native `python_script` source allows `datetime.timedelta` but does not expose
  `datetime.timezone`. Avoid timezone constructors in helpers; use timestamps
  and `dt_util.utc_from_timestamp` when shaping REST API timestamps.
- Native `python_script` protected attribute access can return `None` for
  missing methods, such as `.get` on a list. Avoid calling `.get` on values that
  may be lists or non-mappings; use guarded item access instead.
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
