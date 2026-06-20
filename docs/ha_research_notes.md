# Home Assistant Research Notes

Checked: 2026-06-19
Docs version shown by Home Assistant pages: 2026.6.3

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
- Home Assistant template functions include JSON serialization filters/functions such as `to_json` and `tojson`.
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
- Native `python_script` cannot access `hass.config`; use exposed `dt_util`
  helpers instead of reading `hass.config.time_zone`.
- `dt_util.as_utc` assumes a naive datetime is in Home Assistant's default time
  zone; `dt_util.as_local` converts UTC datetimes back to the same local time
  zone.
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
- If a requested statistic ID has no statistics, `recorder.get_statistics` does
  not include it in the response.
- Long-term statistics are available for sensors with `state_class` of
  `measurement`, `total`, or `total_increasing`.
- Home Assistant records short-term statistics every 5 minutes and stores
  hourly long-term aggregates. Short-term statistics are purged after a
  configured period, default 10 days. Long-term statistics are not purged.
- Native `python_script` can call actions with `blocking=True` and
  `return_response=True` to retrieve response data.

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
