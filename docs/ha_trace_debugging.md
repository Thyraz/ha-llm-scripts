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

### Calendar Manager

Useful trace variables:

- `calendar_manager_prepare`
- `calendar_manager_events`
- `calendar_manager_events_json`
- `calendar_manager_helper`
- `calendar_manager_response`

Useful Python Helper response fields:

- `meta.operation`
- `meta.calendar_entity_ids`
- `meta.start_time`
- `meta.end_time`
- `meta.event_type`
- `meta.verbosity`
- `meta.count`
- `meta.total`
- `meta.truncated`
- `data.calendars`

Expected calendar model:

- The public `calendar_entity_ids` input is passed to `calendar.get_events` as
  target calendar entity IDs.
- Empty `calendar_entity_ids` is resolved by the Python Helper to all available
  `calendar.*` entities before `calendar.get_events` is called.
- Input and output times are local Home Assistant times in
  `YYYY-MM-DD HH:MM:SS`.
- Calendar Manager Time Range is capped at 365 days. Longer ranges return a
  soft failure before `calendar.get_events`.
- `calendar.get_events` returns a mapping keyed by calendar entity ID, with an
  `events` list under each key.
- Home Assistant event `end` values are exclusive. Calendar Manager returns
  all-day event `end` as the Assistant-facing final local day at `23:59:59`.
- Event descriptions are returned only when `verbosity=detailed`.

If the helper returns an unknown calendar entity ID error, check whether the
calendar entity exists and whether Entity Index or the Assistant prompt supplied
the right `calendar.*` ID.

If `calendar_manager_events` is missing a requested calendar key, inspect
`calendar.get_events` target handling in the Script trace.

If `calendar_manager_events_json` arrives at the helper as one quoted string,
the YAML -> Python handoff failed. Check the `from_json` action data conversion.

If `meta.truncated` is true, retry with a narrower time range, a higher limit,
or more specific calendar IDs.

### Media Player Group Manager

Useful trace variables:

- `media_player_group_current_members_json`
- `media_player_group_prepare`
- `media_player_group_helper`
- `media_player_group_response`

Useful Python Helper response fields:

- `meta.operation`
- `meta.leader_entity_id`
- `data.join_member_entity_ids`
- `data.unjoin_entity_ids`
- `data.previous_member_entity_ids`
- `data.ignored_member_entity_ids`
- `data.duplicate_member_entity_ids`
- `data.joined_member_entity_ids`
- `data.cleared_member_entity_ids`

Expected media player group model:

- The public `leader_entity_id` input is passed to `media_player.join` as
  `target.entity_id`.
- The public `member_entity_ids` input is passed to `media_player.join` as
  `data.group_members` for `join`.
- `unjoin` and `clear_members` call `media_player.unjoin` with one target entity
  at a time.
- `clear_members` and `join` with `replace_existing=true` read
  `state_attr(leader_entity_id, 'group_members')` before any actions run.
- Missing or string `group_members` is treated as an empty current group.

If the script raises a Home Assistant runtime error from `media_player.join` or
`media_player.unjoin`, check whether the target integration supports media
player grouping.

If `replace_existing` or `clear_members` does not clear expected members,
inspect `media_player_group_current_members_json` and verify whether the media
player integration exposes `group_members` on the leader entity.

### Memory Manager

Useful trace variables:

- `memory_manager_helper`
- `memory_manager_response`

Useful Python Helper response fields:

- `write_required`
- `memory_store_entity_id`
- `response.success`
- `response.data`
- `response.meta`
- `write_memory.schema_version`
- `write_memory.next_id`
- `write_memory.entries`

Expected memory model:

- The Memory Store Entity is `sensor.llm_memory`.
- The durable store lives in the Memory Store Entity's `memory` attribute.
- Missing `memory` attribute initializes an empty v2 store.
- Write operations call `variable.update_sensor` with `replace_attributes:
  true` and a full `memory` attribute.
- The sensor state is set to the current Memory Entry count on writes.
- `remember`, `update`, and `forget` write the store.
- `search` and `list_recent` return snippets only.
- `read` returns full text for one Memory Entry.
- Search is deterministic lexical token search, not semantic or fuzzy search.

If the helper returns a setup failure, confirm `sensor.llm_memory` exists and is
a Variables+History Sensor variable.

If the helper returns a malformed store failure, inspect
`sensor.llm_memory.attributes.memory`; manual edits may have broken
`schema_version`, `next_id`, `entries`, or entry fields such as `topic` and
`tags`.

If `variable.update_sensor` raises a Home Assistant runtime error, confirm the
Variables+History integration is installed and exposes that action.

If `write_memory` is shown as one quoted string under action data, the YAML ->
Python handoff or `variable.update_sensor` attribute templating needs runtime
inspection in the Script trace.
