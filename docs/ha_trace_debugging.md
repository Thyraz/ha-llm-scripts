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
- `known_label_names`
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

If `known_label_names` is empty, check whether
`input_select.llmtool_entity_index_labels` exists with no options, or with
options that do not resolve to real Home Assistant labels.

If `candidate_entity_ids` is empty while `visibility_label_id` is set, no entity
has the direct `Everywhere` label, or Home Assistant did not reload the updated
script.

`known_label_names` is expected to be a native list in the Script trace. Do not
pipe it through `from_json` again.

`candidate_records_json` is expected to be a JSON string in the Script trace.
The Python Helper `candidates` service data must be a list. If `candidates` is
shown as one quoted string, the `from_json` handoff at the Python Helper action
did not produce a native list.

### Long-Term Aggregated Statistics

Useful trace variables:

- `helper_entity_ids`
- `helper_start_time`
- `helper_end_time`
- `helper_aggregation_type`
- `helper_aggregation_period`
- `long_term_aggregated_statistics_helper`
- `long_term_aggregated_statistics_response`

Useful Python Helper response fields:

- `meta.entity_ids`
- `meta.start_time`
- `meta.end_time`
- `meta.end_time_was_defaulted`
- `meta.aggregation_type`
- `meta.aggregation_period`
- `meta.count`
- `meta.total`
- `meta.truncated`
- `data.entities`
- `data.missing_entities`

Expected recorder model:

- The public `entity_ids` input is passed to recorder as `statistic_ids`.
- For normal Home Assistant recorder-owned sensor statistics, statistic ID and
  entity ID are the same string.
- The helper calls `recorder.get_statistics` with the selected
  `aggregation_type` only.
- `aggregation_period=total` calls recorder with either `5minute` or `hour`,
  then returns `meta.aggregation_period: total`.
- Input and output times are local Home Assistant times in
  `YYYY-MM-DD HH:MM:SS`.

If the helper returns an invalid time format error, check the exact value passed
in the script fields. ISO `T`, timezone suffixes, date-only values, and missing
seconds are intentionally invalid.

If the helper returns no data for an entity that exists, check whether that
entity actually has long-term statistics. Raw state history does not count.

If `meta.truncated` is true, the helper found more value rows than it returned.
Retry with a narrower time range or coarser `aggregation_period`.

If the trace shows a Home Assistant runtime error from `recorder.get_statistics`,
check that recorder is loaded and that Assist-exposed script calls can access
administrator-only recorder actions in the target Home Assistant instance.

### Raw Entity History

Useful trace variables:

- `raw_entity_history_prepare`
- `raw_entity_history_rest`
- `raw_entity_history_payload_json`
- `raw_entity_history_helper`
- `raw_entity_history_response`

Useful Python Helper response fields:

- `meta.entity_ids`
- `meta.start_time`
- `meta.end_time`
- `meta.end_time_was_defaulted`
- `meta.count`
- `meta.total`
- `meta.truncated`
- `meta.limit`
- `data.entities`
- `data.missing_entities`

Expected REST model:

- The public `entity_ids` input is passed to the History REST API as
  `filter_entity_id`.
- The shared REST command is `rest_command.llmtool_home_assistant_api_get`.
- The Raw Entity History `api_path` uses `minimal_response`, `no_attributes`,
  and `significant_changes_only=0`.
- The REST API token comes from `secrets.yaml` as
  `llmtool_home_assistant_bearer_token`.
- The REST base URL defaults to `http://localhost:8123`; if
  `input_text.llmtool_home_assistant_base_url` exists and has a value, the
  script uses that value instead.
- Input and output times are local Home Assistant times in
  `YYYY-MM-DD HH:MM:SS`.
- `state_at_start.active_at` is the requested start time, while
  `state_at_start.changed_at` is when that state originally became active.
- `state_at_end.active_at` is the requested end time, while
  `state_at_end.changed_at` is when that state originally became active.
- History entries include `duration_until_next_change_seconds` only when a next
  returned untruncated history entry exists.

If the helper returns an authentication error, check that
`llmtool_home_assistant_bearer_token` exists in `secrets.yaml`, includes the
`Bearer ` prefix, and uses a valid Long-Lived Access Token.

If the helper returns a non-200 History API error, inspect
`raw_entity_history_rest.status` and confirm
`rest_command.llmtool_home_assistant_api_get` is loaded.

If the helper returns invalid JSON or response shape, inspect
`raw_entity_history_rest.content` and `raw_entity_history_payload_json`.
`raw_entity_history_rest.content` may already be a native list. In that case the
script must not call `from_json` on it before passing it to the Python Helper.
`raw_entity_history_payload_json` may also be stored as a native list after the
intermediate variable step; the helper action data must only call `from_json`
when that variable is still a string.

If the helper raises `TypeError: 'NoneType' object is not callable` while
shaping state rows, check for calling missing methods such as `.get` on native
lists. In native `python_script`, protected attribute access can return `None`
instead of raising `AttributeError`.

If the helper returns no data for an entity that exists, check Recorder
retention, Recorder include/exclude filters, and whether the requested time
range is inside the raw history retention period.

If `meta.truncated` is true, retry with a narrower time range or higher
`limit`.
