# Long-Term Aggregated Statistics Plan

Status: implemented with local helper tests. Home Assistant validation pending.

## Purpose

Long-Term Aggregated Statistics gives an Assistant aggregated Home Assistant
long-term statistics for entity IDs discovered through Entity Index. It is not
for raw state history.

## Current decisions

- Tool name: Long-Term Aggregated Statistics.
- Script ID: `llmtool_long_term_aggregated_statistics`.
- Entity after reload: `script.llmtool_long_term_aggregated_statistics`.
- Python action: `python_script.llmtool_long_term_aggregated_statistics`.
- The public input uses `entity_ids`, because Assist can pass entity IDs from
  Entity Index directly.
- Internally, the tool passes those entity IDs to Home Assistant as
  `statistic_ids`.
- For normal Home Assistant recorder-owned sensor statistics, statistic ID and
  entity ID are the same string. External statistics with `domain:statistic`
  IDs are out of scope for v1.
- This tool reads aggregated long-term statistics only. Raw state history is out
  of scope.
- Parameters are scalar/simple values:
  - `entity_ids`
  - `start_time`
  - `end_time`
  - `aggregation_type`
  - `aggregation_period`
- `entity_ids` is a comma-separated list of Home Assistant entity IDs.
- Maximum requested entities is 10.
- Invalid entity ID format returns a soft validation failure.
- The tool does not check current state-machine existence before querying
  recorder, because removed entities may still have long-term statistics.
- `start_time` is required.
- `end_time` is optional. Empty means now.
- If `end_time` is empty, the helper resolves local now once and uses that
  timestamp for the query and response metadata.
- When `end_time` is defaulted, `meta.end_time` echoes the resolved local time
  and `meta.end_time_was_defaulted` is `true`.
- Times are local Home Assistant times.
- Time input format is exactly `YYYY-MM-DD HH:MM:SS`.
- Relative time text, timezone suffixes, dates without seconds, and ISO `T`
  separators are invalid.
- The Python Helper uses Home Assistant `dt_util` helpers to treat naive input
  as local time, convert query times to UTC, and convert response times back to
  local time.
- `start_time` is inclusive.
- `end_time` is exclusive.
- Returned periods follow Home Assistant recorder period boundaries.
- The tool does not pre-align, round, or reject unaligned start/end times.
- `aggregation_type` accepts one value per call:
  - `mean`
  - `min`
  - `max`
  - `change`
- For cumulative counters such as energy, water, and gas meters,
  `aggregation_type=change` returns usage over the requested time range.
- Assistant-facing text should tell the Assistant not to estimate energy or
  fluid usage from current power/flow multiplied by duration when a cumulative
  counter/statistics source exists.
- `sum`, `state`, and `last_reset` are out of scope for v1.
- `aggregation_period` accepts:
  - `5minute`
  - `hour`
  - `day`
  - `week`
  - `month`
  - `year`
  - `total`
- Non-`total` periods return Home Assistant statistics rows as-is for the
  requested aggregation type.
- The helper asks Home Assistant only for the selected `aggregation_type`.
- The helper relies on Home Assistant's always-present `start` and `end` row
  fields.
- `total` returns one value row per entity for the requested time range.
- For `total`, `mean` is the unweighted mean of returned period means.
- For `total`, `min` is the minimum of returned period minimums.
- For `total`, `max` is the maximum of returned period maximums.
- For `total`, `change` uses the sum of returned period changes unless Home
  Assistant returns one row covering the requested range.
- For `total`, the helper queries Home Assistant with `5minute` when the
  requested time range is shorter than 3 hours.
- If a short `total` range returns no `5minute` rows, the helper retries with
  `hour` before reporting no data.
- For `total` ranges of 3 hours or longer, the helper queries Home Assistant
  with `hour`.
- If a `5minute` query returns some rows, the helper uses those rows and does
  not retry with `hour`.
- The README should explain that `total` is derived from Home Assistant period
  rows and that `mean` is an unweighted mean of period means.
- The runtime response should not expose internal `total` derivation details in
  `meta`.
- No public unit-conversion parameter in v1.
- Return current Home Assistant state metadata where useful:
  - `friendly_name`
  - `unit_of_measurement`
- Omit missing entity metadata fields.
- Do not include domain, area, or device metadata in v1.
- The LLM Tool Python Helper calls `recorder.get_statistics` with
  `blocking=True` and `return_response=True`.
- The LLM Tool Script owns fields, helper call, and final structured response.
- The LLM Tool Python Helper owns input parsing, time conversion, recorder
  action call, no-data handling, total aggregation, sorting, truncation, and
  response shaping.
- Let unexpected Home Assistant runtime failures surface as runtime errors.
- Use soft failures for expected validation problems and no-data results.
- If at least one entity has data, return `success: true`.
- If no requested entity has data, return `success: false`.
- `data.entities` contains only entities with returned values.
- `data.missing_entities` contains requested entity IDs with no statistics in
  the requested time range.
- v1 does not distinguish entities with no long-term statistics at all from
  entities with no statistics in the requested time range.
- Entity result order follows requested `entity_ids`.
- Values sort by `start` ascending.
- `missing_entities` follows requested order.
- Response rows are capped at 500 total value rows across all entities for
  non-`total` requests.
- The 500-row cap is global across the whole response, not per entity.
- Truncation preserves requested entity order and value start order.
- If an entity has rows before truncation but none after truncation, keep the
  entity entry with `values: []` and `truncated: true`.
- If an entity has some rows removed by truncation, set `truncated: true` on
  that entity entry.
- Truncated entities are not listed in `missing_entities`.
- If truncation happens, `meta.truncated` is `true`, `data.truncation` is
  present, and `answer` warns about truncation.
- `data.truncation.by_entity_id` reports returned and total row counts by
  entity.
- `meta.count` is returned value rows after truncation.
- `meta.total` is matching result value rows before truncation.
- For `aggregation_period=total`, `meta.total` counts result rows, not internal
  source rows.
- No public `limit` field in v1.
- Return numbers as Home Assistant gives them, except derived `total` values may
  use Python float math.
- Do not round by default.
- No `precision` parameter in v1.
- Normalize `-0.0` to `0`.

## Tool contract

Successful response:

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

Partial success:

```yaml
success: true
answer: "Found 24 statistics rows. No statistics found for 1 requested entity."
data:
  entities:
    - entity_id: sensor.living_room_temperature
      values:
        - start: "2025-07-30 14:00:00"
          end: "2025-07-30 15:00:00"
          mean: 21.4
  missing_entities:
    - sensor.unknown_temperature
meta:
  tool: llmtool_long_term_aggregated_statistics
  entity_ids:
    - sensor.living_room_temperature
    - sensor.unknown_temperature
  start_time: "2025-07-30 14:00:00"
  end_time: "2025-07-31 14:00:00"
  aggregation_type: mean
  aggregation_period: hour
  count: 24
  total: 24
```

No data:

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

Validation failure:

```yaml
success: false
error: "Invalid start_time. Use local time in format YYYY-MM-DD HH:MM:SS."
data:
  expected_format: "YYYY-MM-DD HH:MM:SS"
meta:
  tool: llmtool_long_term_aggregated_statistics
```

## Expected soft errors

- Missing `entity_ids`.
- Too many entity IDs.
- Invalid entity ID format.
- Missing `start_time`.
- Invalid `start_time` format.
- Invalid `end_time` format.
- `end_time` before or equal to `start_time`.
- Invalid `aggregation_type`.
- Invalid `aggregation_period`.
- No statistics found for requested entity IDs and time range.
- Invalid recorder response shape.

## Implementation notes

- Add `custom_llm_tools/llm_scripts/long_term_aggregated_statistics.yaml`.
- Add `python_scripts/llmtool_long_term_aggregated_statistics.py`.
- Add `llmtool_long_term_aggregated_statistics` to `python_scripts/services.yaml`.
- Add `tests/test_llmtool_long_term_aggregated_statistics.py`.
- Update README status, usage, prompt guidance, and validation command.
- Update `docs/ha_trace_debugging.md` with trace variables for this tool.
- Use `action: python_script.llmtool_long_term_aggregated_statistics`.
- Use `stop` with `response_variable`.
- Keep Assistant-facing text focused on entity IDs, local time format,
  aggregation choices, response fields, no-data behavior, and retry behavior.

## Test cases

- Parses comma-separated entity IDs and preserves request order.
- Rejects invalid entity ID format.
- Rejects more than 10 entity IDs.
- Rejects missing or invalid `start_time`.
- Rejects invalid `end_time`.
- Rejects `end_time <= start_time`.
- Rejects invalid aggregation type.
- Rejects invalid aggregation period.
- Shapes one entity with one value row.
- Shapes multiple entities grouped under `data.entities`.
- Reports partial missing entities while returning success.
- Returns soft failure when all entities are missing.
- Truncates non-`total` responses over 500 value rows.
- Reports `meta.count`, `meta.total`, and `meta.truncated`.
- Reports visible truncation warning in `answer`.
- Reports `data.truncation` with returned count, total-before-truncation count,
  limit, by-entity counts, and retry hint.
- Preserves Home Assistant row numeric values without rounding.
- Normalizes `-0.0` to `0`.
- Computes `total` mean, min, max, and change.
- Converts response timestamps to local formatted strings.

## Manual validation

1. Copy or sync files into Home Assistant config.
2. Reload scripts or restart Home Assistant.
3. Run `python_script.reload` for the new Python Helper.
4. Confirm `script.llmtool_long_term_aggregated_statistics` exists.
5. Confirm `python_script.llmtool_long_term_aggregated_statistics` exists.
6. Confirm fields appear in Developer Tools -> Actions.
7. Run successful and failing examples from Developer Tools -> Actions.
8. Check structured response shape.
9. Expose `script.llmtool_long_term_aggregated_statistics` to Assist.
10. Ask the Assistant to fetch known temperature statistics.
11. Inspect Conversation and Script traces.

## Unresolved questions

None.
