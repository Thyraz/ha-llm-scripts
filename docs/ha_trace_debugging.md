# Home Assistant Trace Debugging

Use this workflow when an LLM Tool Script behaves differently in Home Assistant
than the local Python Helper tests.

## General Workflow

The downloaded Script trace JSON is usually enough. Get it from:

Settings -> Automations & scenes -> Scripts -> script three-dot menu -> Traces
-> open the relevant trace -> trace view three-dot menu -> Download trace.

When reporting a Home Assistant-only issue, provide:

1. The Developer Tools -> Actions input.
2. The final script response.
3. The downloaded Script trace JSON file.

No separate Python trace is expected. The Script trace includes the Python Helper
action call, service data passed to the `python_script.*` action, and the helper
response variable.

## Local Checks

The agent can test:

- Python Helper syntax.
- Python Helper filtering and response shaping.
- YAML parse checks.

Local checks do not execute Home Assistant's Jinja environment, label registry,
script variables, or Assist exposure.

## Generic Trace Checks

If pasting selected snippets instead of the full trace file, include:

- Script variables after parameter preparation.
- Script variables after candidate lookup.
- Script variables after candidate record building.
- Service data passed to the `python_script.*` action.
- Python Helper response variable.

Generic failure patterns:

- Helper input arrives as one quoted string when a list/dict was expected: the
  YAML -> Python handoff failed. Check the `_json` variable and the `from_json`
  action data conversion.
- A resolved Home Assistant ID is empty: check exact friendly name spelling,
  internal ID conversion, and whether the script was reloaded.
- Candidate IDs are empty after a valid lookup: the Home Assistant source data
  likely has no matching direct entity labels or the query is too narrow.
- Python Helper returns `success: false`: treat it as an expected validation
  failure. Inspect `error`, `data`, and `meta`.

## Tool-Specific Checks

Add a subsection here for every tool that needs trace variables or runtime
checks beyond the generic workflow.

### Entity Index

Useful trace variables:

- `visibility_label_name`
- `visibility_label_id`
- `inside_label_name`
- `outside_label_name`
- `query_label_source_entity_id`
- `known_label_names_json`
- `location_label_name`
- `location_label_id`
- `match_label_names`
- `candidate_entity_ids`
- `candidate_records_json`

Expected label model:

- Every visible entity has direct entity label `Everywhere`.
- Inside entities also have direct entity label `Inside`.
- Outside entities also have direct entity label `Outside`.
- Query labels are direct entity labels.
- If `input_select.llmtool_entity_index_labels` exists, its options are the
  supported query labels.
- If `input_select.llmtool_entity_index_labels` is missing, all Home Assistant
  labels except the internal visibility/location labels are supported query
  labels.

If `visibility_label_id` is empty, the friendly label name does not match Home
Assistant exactly.

If `known_label_names_json` is empty, check whether
`input_select.llmtool_entity_index_labels` exists with no options, or with
options that do not resolve to real Home Assistant labels.

If `candidate_entity_ids` is empty while `visibility_label_id` is set, no entity
has the direct `Everywhere` label, or Home Assistant did not reload the updated
script.

`candidate_records_json` is expected to be a JSON string in the Script trace.
The Python Helper `candidates` service data must be a list. If `candidates` is
shown as one quoted string, the `from_json` handoff at the Python Helper action
did not produce a native list.
