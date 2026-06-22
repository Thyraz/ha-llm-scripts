# Calendar Manager Plan

Status: implemented and validated with Home Assistant Developer Tools -> Actions and Assist.

This plan defines the first read-only version of Calendar Manager. The tool is
intended to grow write operations later, so the canonical name remains Calendar
Manager even though v1 only reads events.

## Purpose

Calendar Manager lets an Assistant read Home Assistant calendar events from
calendar entities. Future versions may create, update, or delete calendar
events in the same LLM Tool.

## Current decisions

- Tool name: Calendar Manager.
- Script ID: `llmtool_calendar_manager`.
- Entity after reload: `script.llmtool_calendar_manager`.
- Python action: `python_script.llmtool_calendar_manager`.
- Calendar Manager v1 reads events only.
- Calendar Manager remains one LLM Tool so future write operations can share
  the same event language and calendar selection model.
- Parameters are scalar/simple values:
  - `operation`
  - `calendar_entity_ids`
  - `keyword`
  - `start_time`
  - `end_time`
  - `days_ahead`
  - `limit`
  - `event_type`
  - `verbosity`
- Use `operation`, not `function`.
- Supported v1 operations:
  - `search_events`
  - `list_upcoming`
  - `list_range`
- Future write operations may include:
  - `create_event`
  - `update_event`
  - `delete_event`
- `calendar_entity_ids` is a comma-separated list of Home Assistant
  `calendar.*` entity IDs.
- The Assistant should normally get calendar entity IDs from Entity Index or
  from prompt guidance supplied by the user.
- Empty `calendar_entity_ids` means all available `calendar.*` entities.
- Calendar Manager does not use user-facing calendar aliases or pseudonyms.
- Calendar discovery for empty `calendar_entity_ids` belongs in the Python
  Helper, using Home Assistant state data.
- Invalid non-calendar entity IDs return a soft validation failure.
- Supplied calendar entity IDs that do not exist return a soft validation
  failure with `data.unknown_calendar_entity_ids`.
- If no calendar entities are available when `calendar_entity_ids` is empty,
  return a soft validation failure with a setup hint.
- Dates are local Home Assistant times.
- Date input format is exactly `YYYY-MM-DD HH:MM:SS`.
- Relative time text, timezone suffixes, dates without seconds, and ISO `T`
  separators are invalid.
- `start_time` is inclusive.
- `end_time` is exclusive for querying Home Assistant.
- `list_range` requires `start_time` and `end_time`.
- `search_events` accepts optional `start_time` and `end_time`.
- Empty `search_events.start_time` means local now.
- Empty `search_events.end_time` means local now plus `days_ahead`.
- `list_upcoming` uses local now through local now plus `days_ahead`.
- `days_ahead` is optional.
- Empty `days_ahead` uses 31.
- Maximum `days_ahead` is 3660.
- `end_time` before or equal to `start_time` is invalid.
- If Home Assistant returns an ongoing event for the requested range, Calendar
  Manager may include it. The tool does not add a lookback window to force
  ongoing event discovery.
- `search_events` requires non-empty `keyword`.
- Keyword matching is exact case-insensitive substring matching.
- Keyword matching searches title, description, and location.
- No fuzzy matching, stemming, synonym matching, or token mode in v1.
- `event_type` filters returned events.
- `event_type` values:
  - `all`
  - `all_day`
  - `timed`
- Empty `event_type` means `all`.
- `limit` is optional for all read operations.
- Empty `limit` uses 100.
- Maximum `limit` is 1000.
- `limit` is a global cap across all returned events, not per calendar.
- `meta.count` is returned events after truncation.
- `meta.total` is matching events before truncation.
- Capped responses include `meta.truncated: true`.
- `verbosity` controls event detail.
- `verbosity` values:
  - `compact`
  - `detailed`
- Empty `verbosity` means `compact`.
- `compact` returns title, event type, start, end, and location.
- `detailed` adds description.
- Tool description must explicitly say event description is returned only when
  `verbosity=detailed`.
- In `detailed`, description is capped at 1000 characters.
- If description is capped, the event includes `description_truncated: true`.
- Returned data is grouped by calendar.
- Calendar groups are sorted by `calendar_entity_id`.
- Events within each calendar group are sorted oldest to newest.
- Counts in `meta` are global across all calendar groups.
- Calendar groups include:
  - `calendar_entity_id`
  - `friendly_name`
  - `count`
  - `events`
- Event shape uses:
  - `title`
  - `event_type`
  - `start`
  - `end`
  - `location`
  - `description` only in `detailed`
- Events omit calendar identity because the response is grouped by calendar.
- All-day events return `event_type: all_day`.
- Timed events return `event_type: timed`.
- Home Assistant calendar all-day event ends are exclusive, but Calendar
  Manager returns all-day event `end` as an Assistant-facing inclusive local
  `23:59:59` on the final day.
- Timed event `end` is the normal local end time.
- Empty search/list results are successful responses with count 0.
- Validation and setup issues return soft failures.
- Use one Python Helper with a `mode` field:
  - `prepare` validates input, resolves calendars, and builds the time window.
  - `shape` validates and shapes `calendar.get_events` response data.
- The LLM Tool Script owns fields, helper calls, `calendar.get_events`, and the
  final structured response.
- The LLM Tool Python Helper owns parsing, validation, calendar discovery,
  keyword/event-type filtering, sorting, grouping, truncation, description
  capping, and response shaping.
- The LLM Tool Script calls `calendar.get_events` with explicit
  `target.entity_id` and captures its response variable.
- Calendar Manager does not need a REST command.
- No ADR for the all-day inclusive end decision yet. Capture it in this plan,
  comments, and user-facing docs. Revisit when write operations are designed.

## Tool contract

Successful response:

```yaml
success: true
answer: "Found 3 calendar events."
data:
  calendars:
    - calendar_entity_id: calendar.abfall
      friendly_name: Garbage
      count: 1
      events:
        - title: "Paper collection"
          event_type: all_day
          start: "2026-06-23 00:00:00"
          end: "2026-06-23 23:59:59"
          location: null
    - calendar_entity_id: calendar.gemeinsam
      friendly_name: Family
      count: 2
      events:
        - title: "Dentist"
          event_type: timed
          start: "2026-06-24 14:00:00"
          end: "2026-06-24 15:00:00"
          location: "Town"
meta:
  tool: llmtool_calendar_manager
  operation: search_events
  calendar_entity_ids:
    - calendar.abfall
    - calendar.gemeinsam
  start_time: "2026-06-22 12:00:00"
  end_time: "2027-06-22 12:00:00"
  event_type: all
  verbosity: compact
  limit: 100
  count: 3
  total: 3
```

Empty result:

```yaml
success: true
answer: "Found 0 calendar events."
data:
  calendars: []
meta:
  tool: llmtool_calendar_manager
  operation: search_events
  calendar_entity_ids:
    - calendar.gemeinsam
  start_time: "2026-06-22 12:00:00"
  end_time: "2027-06-22 12:00:00"
  event_type: all
  verbosity: compact
  limit: 100
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
  tool: llmtool_calendar_manager
  operation: list_range
```

## Expected soft errors

- Invalid operation.
- Invalid calendar entity ID format.
- Unknown supplied calendar entity ID.
- No available calendar entities.
- Missing `keyword` for `search_events`.
- Missing `start_time` for `list_range`.
- Missing `end_time` for `list_range`.
- Invalid `start_time` format.
- Invalid `end_time` format.
- `end_time` before or equal to `start_time`.
- Invalid `days_ahead`.
- Invalid `limit`.
- Invalid `event_type`.
- Invalid `verbosity`.
- Invalid Calendar Manager helper handoff.
- Invalid `calendar.get_events` response shape.

## Implementation notes

- Add `custom_llm_tools/llm_scripts/calendar_manager.yaml`.
- Add `python_scripts/llmtool_calendar_manager.py`.
- Add `llmtool_calendar_manager` to `python_scripts/services.yaml`.
- Add `tests/test_llmtool_calendar_manager.py`.
- Update README status, usage, prompt guidance, and validation command.
- Update `docs/ha_research_notes.md` with Home Assistant calendar docs checked
  for `calendar.get_events`.
- Update `docs/ha_trace_debugging.md` with Calendar Manager trace variables.
- Keep Assistant-facing text focused on operations, calendar entity IDs, local
  time format, event type, verbosity, description behavior, truncation, and
  retry behavior.
- Keep implementation details in comments and this plan.
- Do not mention calendar pseudonyms or user-specific calendar names in repo
  owned Assistant-facing text.
- Use `action: python_script.llmtool_calendar_manager`.
- Use `action: calendar.get_events`.
- Use `stop` with `response_variable`.

## Test cases

- Reject invalid operation and return known operations.
- Parse comma-separated calendar entity IDs and remove duplicates.
- Reject non-`calendar.*` entity IDs.
- Reject unknown supplied calendar entity IDs.
- Discover all `calendar.*` entity IDs when `calendar_entity_ids` is empty.
- Return setup soft failure when no calendar entities exist.
- Reject missing keyword for `search_events`.
- Reject missing range fields for `list_range`.
- Reject invalid date format.
- Reject ISO `T`, timezone suffixes, date-only values, and missing seconds.
- Reject `end_time <= start_time`.
- Default `search_events` range to now through now plus `days_ahead`.
- Default `list_upcoming` range to now through now plus `days_ahead`.
- Validate `days_ahead`, default 31, maximum 3660.
- Validate `limit`, default 100, maximum 1000.
- Validate `event_type`.
- Validate `verbosity`.
- Build `calendar.get_events` helper data with target calendar IDs and local
  time window.
- Shape one timed event.
- Shape one all-day event with inclusive final-day `end`.
- Infer all-day events from date-only Home Assistant event times.
- Filter by `event_type=all_day`.
- Filter by `event_type=timed`.
- Match keyword across title, description, and location.
- Match keyword case-insensitively.
- Do not fuzzy-match keyword typos.
- Include overlapping events for explicit ranges.
- Sort events oldest to newest inside each calendar.
- Sort calendar groups by `calendar_entity_id`.
- Group response data by calendar.
- Include description only for `verbosity=detailed`.
- Cap detailed descriptions at 1000 characters and set
  `description_truncated`.
- Return success with empty results.
- Truncate globally over `limit`.
- Report `meta.count`, `meta.total`, and `meta.truncated`.
- Return soft failure for invalid helper handoff.
- Return soft failure for invalid `calendar.get_events` response shape.
- Run under restricted native `python_script` builtins without imports.

## Manual validation

1. Copy or sync files into Home Assistant config.
2. Reload scripts or restart Home Assistant.
3. Run `python_script.reload` for the new Python Helper.
4. Confirm `script.llmtool_calendar_manager` exists.
5. Confirm `python_script.llmtool_calendar_manager` exists.
6. Confirm fields appear in Developer Tools -> Actions.
7. Run `list_upcoming` against one known calendar entity.
8. Run `list_upcoming` with empty `calendar_entity_ids` and confirm all
   calendar entities are targeted.
9. Run `search_events` with a keyword known to match a title, description, and
   location.
10. Run `list_range` with an all-day event and confirm returned `end` is the
    final day at `23:59:59`.
11. Run successful and failing examples from Developer Tools -> Actions.
12. Check structured response shape.
13. Expose `script.llmtool_calendar_manager` to Assist.
14. Ask the Assistant to read upcoming calendar events and inspect traces.

## Done when

- Local helper tests pass.
- Existing helper tests still pass.
- README documents Calendar Manager usage and prompt guidance.
- Home Assistant direct script validation succeeds.
- Assist validation succeeds after manual exposure.

## Unresolved questions

None.
