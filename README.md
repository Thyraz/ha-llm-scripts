# Home Assistant LLM Scripts

Reusable Home Assistant script collection for LLM-based Assistants.

This project exposes Home Assistant scripts as LLM tools. Scripts use HA-native operations first, and call native `python_script` helpers only when YAML/Jinja would become hard to read.

## Status

Current implementation includes:

- `script.llmtool_demo` for install and response-shape validation
- `script.llmtool_entity_index` for safe labeled-entity discovery
- `script.llmtool_calculator` for deterministic arithmetic

## Install

Copy or sync these folders into your Home Assistant config folder:

```text
custom_llm_tools/
  llm_scripts/
python_scripts/
```

Add this to `configuration.yaml`:

```yaml
script llm_tools: !include_dir_merge_named custom_llm_tools/llm_scripts/

python_script:
```

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
- [Tool plans](docs/plans/README.md)
- [Calculator plan](docs/plans/implemented/calculator.md)
- [Demo tool plan](docs/plans/implemented/demo-tool.md)
- [Entity Index plan](docs/plans/implemented/entity-index.md)

## Security

- Do not commit secrets.
- Do not log or return tokens.
- Do not patch `.storage/*`.
- Expose only intended `script.llmtool_*` entities to Assist.

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

For Entity Index helper regression checks:

```bash
python3 tests/test_llmtool_entity_index.py
```

For Calculator helper regression checks:

```bash
python3 tests/test_llmtool_calculator.py
```
