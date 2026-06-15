# Home Assistant Research Notes

Checked: 2026-06-15
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
- Home Assistant template functions: https://www.home-assistant.io/template-functions/
- Home Assistant label template functions:
  - https://www.home-assistant.io/template-functions/labels/
  - https://www.home-assistant.io/template-functions/label_entities/
  - https://www.home-assistant.io/template-functions/label_id/
- Home Assistant area/device template functions:
  - https://www.home-assistant.io/template-functions/area_id/
  - https://www.home-assistant.io/template-functions/device_id/
- Home Assistant Core LLM helper source: `homeassistant/helpers/llm.py`
- Home Assistant Core Python script source:
  `homeassistant/components/python_script/__init__.py`

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
- `area_id(entity_id)` returns the area ID for an entity or `None`.
- `device_id(entity_id)` returns the device ID for an entity or `None`.
- Native `python_script` can read state machine data through `hass.states.entity_ids`,
  `hass.states.all`, `hass.states.get`, `hass.states.is_state`, and
  `hass.states.is_state_attr`.

## Assumptions

- Exposed scripts remain the simplest public interface for this project.
- LLM integrations handle structured script responses best when the response includes a short `answer` plus structured `data`.
- Scalar fields are safer for LLM tool calls than complex selector output until tested across Assist integrations.

## Risks

- Assist tool schema generation from script fields may differ between LLM integrations.
- `success: false` is a soft error convention for the Assistant, not a Home Assistant runtime error.
- History access through REST commands needs careful token handling with `secrets.yaml`.
