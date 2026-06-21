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
      - TemperatureSensor
      - Thermostat
      - Light
```

Run `script.llmtool_entity_index` from Developer Tools -> Actions:

```yaml
label_names: TemperatureSensor,Thermostat
location: inside
query_mode: by_labels
match_mode: any
verbosity: compact
limit: 50
```

Expected response shape:

```yaml
success: true
answer: "Found 3 matching entities."
data:
  entities:
    - entity_id: sensor.living_room_temperature
      friendly_name: Living room temperature
      state: "21.5"
      matched_labels:
        - TemperatureSensor
meta:
  tool: llmtool_entity_index
  count: 3
  total: 3
  query_mode: by_labels
  label_names:
    - TemperatureSensor
    - Thermostat
  location: inside
  match_mode: any
  state_filter: ""
  verbosity: compact
  limit: 50
```

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

## Prompt guidance

Tell your Assistant that these tools share one response format. It should use `answer` for the short summary, `data` for structured details, and `meta` for counts/query echo.

For Entity Index, tell your Assistant:

```text
Before calling LLM tools that need Home Assistant entity IDs, call Entity Index.
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

Pass label_names as a comma-separated string. Always choose location: inside,
outside, or everywhere.
Entity labels representing rooms or floors have to be passed as label_names, not
as location. Location only accepts inside, outside, or everywhere.
Use query_mode=by_labels for targeted lookup and all_labeled for inventory.
Use meta.truncated to decide whether to retry with a narrower query or higher
limit. On success, read data.entities. On validation failure, use error and data
to retry.
```

For Long-Term Aggregated Statistics, tell your Assistant:

```text
Use Long-Term Aggregated Statistics when the user asks about aggregated
long-term history, trends, averages, minimums, maximums, or changes for known
Home Assistant entities. It does not fetch raw state history.

If you do not already know the exact entity IDs, call Entity Index first. Then
pass entity_ids as a comma-separated string of entity IDs from Entity Index. Use
at most 10 entity IDs.

Pass start_time and optional end_time as local Home Assistant times in exactly
this format: YYYY-MM-DD HH:MM:SS. Resolve relative user requests like
"yesterday" or "last week" yourself before calling the tool. Empty end_time
means now. Do not pass relative time text or timezone suffixes.

Choose aggregation_type from: mean, min, max, change. Use mean for average
questions, min for lowest, max for highest, and change for increase/decrease
over the time range.

Choose aggregation_period from: 5minute, hour, day, week, month, year, total.
Use total when the user wants one value for the whole requested time range. Use
hour/day/week/month/year when the user asks for a timeline or comparison over
time.

On success, read data.entities[].values. Each value has start and end local
times plus the requested aggregation_type. If data.missing_entities is not
empty, tell the user those requested entities had no statistics for the
requested time range. Use meta.truncated to decide whether to retry with a
narrower time range or coarser aggregation_period. On validation failure, use
error and data to retry.
```

For Raw Entity History, tell your Assistant:

```text
Use Raw Entity History when the user asks for exact recent state history,
state changes, or how long an entity stayed in a raw Home Assistant state. It
does not fetch long-term aggregated statistics.

If you do not already know the exact entity IDs, call Entity Index first. Then
pass entity_ids as a comma-separated string of entity IDs from Entity Index. Use
at most 10 entity IDs.

Pass start_time and optional end_time as local Home Assistant times in exactly
this format: YYYY-MM-DD HH:MM:SS. Resolve relative user requests like
"today", "yesterday", or "last night" yourself before calling the tool. Empty
end_time means now. Do not pass relative time text or timezone suffixes.

Use limit to cap returned history entries when the time range may contain many
changes. Empty limit means 100. Maximum limit is 1000.

On success, read data.entities[].history. Each entry has changed_at and state,
and may have duration_until_next_change_seconds when another returned entry
follows. state_at_start and state_at_end show the state active at the requested
range boundaries when known. If data.missing_entities is not empty, tell the
user those requested entities had no raw history for the requested time range.
Use meta.truncated to decide whether to retry with a narrower time range or
higher limit. On validation failure, use error and data to retry.
```

For Calculator, tell your Assistant:

```text
Use Calculator when arithmetic must be calculated exactly from values you
already have. It does not fetch entities, states, units, or history.

Choose operation from: sum, difference, product, quotient, minimum, maximum,
average.

Pass values as a comma-separated string of decimal numbers without units. Use
"." as decimal separator, independent of locale settings. Commas separate
values. For difference and quotient, value order matters.

Use precision only when the user asks for rounded output, or rounded output is
more useful. On success, read data.result. If precision was used, data.raw_result
contains the unrounded result. On validation failure, use error and data to
retry.
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
- [Tool plans](docs/plans/README.md)
- [Long-Term Aggregated Statistics plan](docs/plans/implemented/long-term-aggregated-statistics.md)
- [Raw Entity History plan](docs/plans/implemented/raw-entity-history.md)
- [Calculator plan](docs/plans/implemented/calculator.md)
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

For Long-Term Aggregated Statistics helper regression checks:

```bash
python3 tests/test_llmtool_long_term_aggregated_statistics.py
```

For Raw Entity History helper regression checks:

```bash
python3 tests/test_llmtool_raw_entity_history.py
```
