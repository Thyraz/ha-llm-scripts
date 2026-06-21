# Raw Entity History Plan

Status: planning.

## Purpose

Raw Entity History gives an Assistant unaggregated Home Assistant entity state
history for entity IDs discovered through Entity Index. It is not for
long-term aggregated statistics.

## Current decisions

- Tool name: Raw Entity History.
- Script ID: `llmtool_raw_entity_history`.
- Entity after reload: `script.llmtool_raw_entity_history`.
- Python action: `python_script.llmtool_raw_entity_history`.
- REST action: `rest_command.llmtool_raw_entity_history`.
- The public input uses `entity_ids`, because Assist can pass entity IDs from
  Entity Index directly.
- This tool reads raw Home Assistant state history. Long-term aggregated
  statistics are out of scope.
- Raw Entity History uses Home Assistant's REST history API through a
  user-configured `rest_command`.
- The REST API bearer token must live in the user's `secrets.yaml` as
  `llmtool_home_assistant_bearer_token`.
- The secret value includes the `Bearer ` prefix.
- The repo must never store or log the token.
- The documented default REST URL targets `http://localhost:8123`; users may
  adjust it if their Home Assistant install needs a different local URL.
- Parameters are scalar/simple values:
  - `entity_ids`
  - `start_time`
  - `end_time`
  - `limit`
- `entity_ids` is a comma-separated list of Home Assistant entity IDs.
- Entity IDs should normally come from Entity Index.
- Maximum requested entities is 10.
- Invalid entity ID format returns a soft validation failure.
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
- `start_time` is inclusive.
- `end_time` is exclusive.
- The Python Helper converts local input times into URL-safe REST API
  timestamp parameters.
- `limit` is optional.
- Empty `limit` uses the default.
- Default `limit` is 100.
- Minimum `limit` is 1.
- Maximum `limit` is 1000.
- `limit` is a global cap across all returned history entries, not per entity.
- Results preserve requested entity order and chronological order per entity.
- `meta.count` is returned history entries after truncation.
- `meta.total` is matching history entries before truncation.
- Capped responses include `meta.truncated: true`.
- Raw history entries return `changed_at` and `state`.
- `state` remains a Home Assistant state string. The tool does not parse
  numbers, booleans, or units.
- A history entry includes `duration_until_next_change_seconds` only when there
  is a next returned untruncated history entry.
- The last returned entry omits `duration_until_next_change_seconds`.
- If a response is truncated, the final returned entry omits
  `duration_until_next_change_seconds`.
- Entity results include `state_at_start` when Home Assistant returns a state
  active at the start boundary.
- Entity results include `state_at_end` when a last state is known from the
  untruncated entity history.
- Boundary fields include `active_at` to show the query boundary where the state
  was active. `changed_at` remains the time the state originally became active.
- `state_at_end` is derived before truncation, so the summary remains useful
  when `history` is capped.
- Entity results include `friendly_name` and `unit_of_measurement` when
  available.
- Attributes are omitted in v1.
- Domain, area, and device metadata are omitted in v1.
- Add `custom_llm_tools/rest_commands/raw_entity_history.yaml`.
- Users install rest commands with
  `rest_command: !include_dir_merge_named custom_llm_tools/rest_commands/`.
- REST API calls use `minimal_response`, `no_attributes`, and
  `significant_changes_only=0`.
- REST API non-200 responses return soft failures.
- HTTP 401/403 returns an authentication-focused soft failure.
- Other non-200 responses include the status and tell the user to inspect the
  Script trace; response content is not returned.
- Malformed JSON or unexpected REST response shape returns a soft failure.
- If at least one entity has history, return `success: true`.
- If no requested entity has history, return `success: false`.
- `data.entities` contains only entities with returned history.
- `data.missing_entities` contains requested entity IDs with no returned
  history.
- v1 does not distinguish purged history, excluded recorder entities, never
  recorded entities, and entities with no changes in range.
- REST returns one outer list of per-entity histories. The helper maps each
  group back to requested entity order by the first row that includes
  `entity_id`; an unmappable group is treated as an invalid response shape.
- Use one Python Helper with a `mode` field:
  - `prepare` validates input and builds REST query parameters.
  - `shape` validates the REST response and shapes the final LLM Tool response.
- The LLM Tool Script owns fields, helper calls, REST action call, and final
  structured response.
- The LLM Tool Python Helper owns input parsing, time conversion, REST response
  parsing, state boundary derivation, duration calculation, truncation, and
  response shaping.

## Tool contract

Successful response:

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

No data:

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

Validation failure:

```yaml
success: false
error: "Invalid start_time. Use local time in format YYYY-MM-DD HH:MM:SS."
data:
  expected_format: "YYYY-MM-DD HH:MM:SS"
meta:
  tool: llmtool_raw_entity_history
```

## Expected soft errors

- Missing `entity_ids`.
- Too many entity IDs.
- Invalid entity ID format.
- Missing `start_time`.
- Invalid `start_time` format.
- Invalid `end_time` format.
- `end_time` before or equal to `start_time`.
- Invalid `limit`.
- REST authentication failure.
- REST non-200 response.
- Invalid REST response shape.
- No raw history found for requested entity IDs and time range.

## Implementation notes

- Add `custom_llm_tools/llm_scripts/raw_entity_history.yaml`.
- Add `python_scripts/llmtool_raw_entity_history.py`.
- Add `llmtool_raw_entity_history` to `python_scripts/services.yaml`.
- Add `tests/test_llmtool_raw_entity_history.py`.
- Update README status, install notes, usage, prompt guidance, and validation
  command.
- Raw Entity History setup belongs in the main bundle install docs, not a
  separate optional install section.
- Update `docs/ha_trace_debugging.md` with trace variables for this tool.
- Use `action: python_script.llmtool_raw_entity_history`.
- Use `action: rest_command.llmtool_raw_entity_history`.
- Use `stop` with `response_variable`.
- Keep Assistant-facing text focused on entity IDs, local time format, response
  fields, no-data behavior, truncation, and retry behavior.
- Keep REST token setup in docs only; the token belongs in `secrets.yaml`.

## Test cases

- Parses comma-separated entity IDs and preserves request order.
- Rejects invalid entity ID format.
- Rejects more than 10 entity IDs.
- Rejects missing or invalid `start_time`.
- Rejects invalid `end_time`.
- Rejects `end_time <= start_time`.
- Rejects invalid `limit`.
- Defaults empty `end_time` to local now.
- Defaults empty `limit` to 100.
- Builds REST URL parameters from local times.
- Shapes one entity with multiple history entries.
- Keeps raw state strings unchanged.
- Calculates `duration_until_next_change_seconds` between adjacent entries.
- Omits duration on the last returned entry.
- Omits duration on the final returned entry when truncated.
- Reports `state_at_start`.
- Reports `state_at_end` from untruncated entity history.
- Reports `active_at` on boundary fields.
- Includes friendly name and unit metadata when available.
- Omits attributes.
- Reports partial missing entities while returning success.
- Returns soft failure when all entities are missing.
- Truncates globally over `limit`.
- Reports `meta.count`, `meta.total`, and `meta.truncated`.
- Returns authentication-focused soft failure for HTTP 401/403.
- Returns soft failure for other non-200 responses.
- Returns soft failure for malformed JSON or unexpected REST response shape.

## Manual validation

1. Copy or sync files into Home Assistant config.
2. Add `llmtool_home_assistant_bearer_token` to `secrets.yaml`.
3. Add documented `rest_command.llmtool_raw_entity_history` to
   `configuration.yaml`.
4. Reload scripts or restart Home Assistant.
5. Run `python_script.reload` for the new Python Helper.
6. Confirm `script.llmtool_raw_entity_history` exists.
7. Confirm `python_script.llmtool_raw_entity_history` exists.
8. Confirm `rest_command.llmtool_raw_entity_history` exists.
9. Confirm fields appear in Developer Tools -> Actions.
10. Run successful and failing examples from Developer Tools -> Actions.
11. Check structured response shape.
12. Expose `script.llmtool_raw_entity_history` to Assist.
13. Ask the Assistant to fetch known entity history.
14. Inspect Conversation and Script traces.

## Unresolved questions

None.
