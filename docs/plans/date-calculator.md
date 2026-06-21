# Date Calculator Plan

Status: planned. This plan transfers the legacy Date Calculator tool into the
repo's LLM Tool Script, Python Helper, structured response, and scalar parameter
patterns.

## Purpose

Date Calculator gives an Assistant deterministic calendar and local-time
calculations for dates it already has. It does not fetch Home Assistant states,
entities, history, or statistics.

## Current decisions

- Tool name: Date Calculator.
- Script ID: `llmtool_date_calculator`.
- Entity after reload: `script.llmtool_date_calculator`.
- Python action: `python_script.llmtool_date_calculator`.
- Date Calculator is separate from Calculator because calendar math has local
  time, weekday, month, year, and epoch rules.
- Parameters are scalar/simple values:
  - `operation`
  - `date`
  - `date2`
  - `segments`
  - `weekday`
  - `day_of_month`
  - `n`
  - `epoch_time_s`
  - `limit`
- Use `operation`, not `function`.
- Supported operations:
  - `duration_between_dates`
  - `date_by_adding_segments`
  - `weekday_for_date`
  - `date_for_weekday_in_n_weeks`
  - `date_for_day_of_month_in_n_months`
  - `list_calendar_days`
  - `epoch_to_date`
  - `date_to_epoch`
- No operation aliases in v1.
- Dates are local Home Assistant times.
- Date input format is exactly `YYYY-MM-DD HH:MM:SS`.
- Relative time text, timezone suffixes, dates without seconds, and ISO `T`
  separators are invalid.
- Operations that return a date-only calendar result return midnight as
  `YYYY-MM-DD 00:00:00`.
- Use the repo structured response contract:
  - success: `success`, `answer`, `data`, `meta`
  - soft failure: `success`, `error`, `data`, `meta`
- Operation result fields live under `data`.
- `meta` echoes normalized operation and useful normalized inputs.
- Date Calculator uses one LLM Tool Script and one LLM Tool Python Helper.
- No Node-RED, REST command, custom integration, or external service.
- The LLM Tool Script owns fields, helper call, and final structured response.
- The LLM Tool Python Helper owns parsing, validation, calendar math, epoch
  conversion, and response shaping.
- The Python Helper should use native `python_script` style: no imports, simple
  top-level flow, and manual strict date parsing instead of `strptime`.
- Use Home Assistant `dt_util` helpers for local/UTC conversion where needed.
- `segments` is a comma-separated `key=value` string.
- Supported segment keys:
  - `years`
  - `months`
  - `days`
  - `hours`
  - `minutes`
  - `seconds`
- Segment values are integers and may be negative.
- Unknown segment keys return a soft validation failure.
- Missing or empty `segments` is invalid for `date_by_adding_segments`.
- `date_by_adding_segments` clamps invalid target day-of-month values to the
  last valid day of the target month.
- Year addition from Feb 29 to a non-leap year clamps to Feb 28.
- `duration_between_dates` returns exact scalar durations for:
  - `seconds`
  - `minutes`
  - `hours`
  - `days`
  - `weeks`
- `duration_between_dates` returns approximate scalar durations for:
  - `months`, using `days / 30.436875`
  - `years`, using `days / 365.2425`
- `duration_between_dates` also returns `duration_in_segments`.
- `duration_in_segments.sign` is `+` or `-`.
- `duration_in_segments` segment values are unsigned integers.
- Negative durations are represented by `sign: "-"`, not negative segment
  values.
- Segment decomposition walks from the earlier date toward the later date using
  calendar months with clamping, then days, hours, minutes, and seconds.
- `date_to_epoch` treats `date` as local Home Assistant time and returns Unix
  epoch seconds.
- `epoch_to_date` treats `epoch_time_s` as UTC epoch seconds and returns local
  Home Assistant date and weekday.
- `date_for_weekday_in_n_weeks` accepts optional `date` as an anchor.
- Empty `date` for `date_for_weekday_in_n_weeks` means local now.
- The weekday calculation uses the anchor local date and ignores anchor time.
- `date_for_weekday_in_n_weeks` returns midnight.
- `n=0` for `date_for_weekday_in_n_weeks` means the next occurrence including
  today when the weekday matches.
- `date_for_day_of_month_in_n_months` accepts optional `date` as an anchor.
- Empty `date` for `date_for_day_of_month_in_n_months` means local now.
- The day-of-month calculation uses the anchor local date and ignores anchor
  time.
- `date_for_day_of_month_in_n_months` returns midnight.
- If `n=0`, choose this month when `day_of_month >= anchor day`; otherwise
  choose next month.
- If `n>0`, first resolve the `n=0` occurrence, then add `n` months.
- Invalid target day-of-month values are clamped to the last valid day of the
  target month.
- `date_for_day_of_month_in_n_months` returns requested `day_of_month`.
- If clamping happens, also return `actual_day_of_month`.
- Weekday input accepts exact English names only:
  - `Monday`
  - `Tuesday`
  - `Wednesday`
  - `Thursday`
  - `Friday`
  - `Saturday`
  - `Sunday`
- Weekday output uses the same spelling.
- Invalid weekday returns a soft validation failure with `data.known_weekdays`.
- `n` is an integer greater than or equal to 0.
- `day_of_month` is an integer from 1 through 31.
- `limit` is used by `list_calendar_days`.
- `limit` default is 366.
- `limit` maximum is 3660.
- Other operations ignore `limit`.
- `list_calendar_days` treats `date` and `date2` as local datetimes, then lists
  local calendar dates.
- `list_calendar_days` is inclusive of both local calendar dates.
- `list_calendar_days` returns at most `limit` days.
- If the full result exceeds `limit`, set `meta.truncated: true`.
- If `date2 < date`, `list_calendar_days` returns a soft validation failure.

## Tool contract

Successful response shape:

```yaml
success: true
answer: "Calculated date."
data: {}
meta:
  tool: llmtool_date_calculator
  operation: weekday_for_date
```

Validation failure shape:

```yaml
success: false
error: "Invalid date. Use local time in format YYYY-MM-DD HH:MM:SS."
data:
  expected_format: "YYYY-MM-DD HH:MM:SS"
meta:
  tool: llmtool_date_calculator
  operation: weekday_for_date
```

## Expected soft errors

- Invalid operation.
- Missing required `date`.
- Missing required `date2`.
- Invalid date format.
- `date2` before `date` for `list_calendar_days`.
- Missing `segments`.
- Invalid segment key.
- Invalid segment value.
- Missing or invalid `weekday`.
- Missing or invalid `day_of_month`.
- Missing or invalid `n`.
- Missing or invalid `epoch_time_s`.
- Invalid `limit`.

## Implementation notes

- Add `custom_llm_tools/llm_scripts/date_calculator.yaml`.
- Add `python_scripts/llmtool_date_calculator.py`.
- Add `llmtool_date_calculator` to `python_scripts/services.yaml`.
- Add `tests/test_llmtool_date_calculator.py`.
- Update README status, usage, prompt guidance, and validation command.
- Update `docs/ha_trace_debugging.md` if Home Assistant trace behavior needs
  tool-specific notes.
- Keep Assistant-facing text focused on operations, required parameters, date
  format, response fields, and validation retry behavior.
- Keep implementation details in comments and this plan.

## Test cases

- Reject invalid operation and return known operations.
- Reject missing required parameters per operation.
- Reject invalid date format.
- Reject ISO `T`, timezone suffixes, date-only values, and missing seconds.
- Return weekday for a valid date.
- Add positive and negative segments.
- Clamp month addition from Jan 31 to February.
- Clamp year addition from Feb 29 to non-leap year.
- Convert local date to epoch seconds.
- Convert epoch seconds to local date.
- Compute positive and negative duration scalar values.
- Compute signed unsigned duration segments.
- Resolve weekday in zero and non-zero weeks from explicit anchor date.
- Default weekday anchor date to local now.
- Resolve day-of-month in zero and non-zero months from explicit anchor date.
- Default day-of-month anchor date to local now.
- Clamp day-of-month result and return `actual_day_of_month`.
- List calendar days inclusively.
- Truncate calendar day list globally and set `meta.truncated`.
- Reject reversed calendar day list range.
- Reject invalid weekdays with `known_weekdays`.
- Reject invalid segment keys and values.
- Reject invalid `n`, `day_of_month`, `epoch_time_s`, and `limit`.
- Run under restricted native `python_script` builtins without imports.

## Manual validation

1. Copy or sync files into Home Assistant config.
2. Reload scripts or restart Home Assistant.
3. Run `python_script.reload` for the new Python Helper.
4. Confirm `script.llmtool_date_calculator` exists.
5. Confirm `python_script.llmtool_date_calculator` exists.
6. Confirm fields appear in Developer Tools -> Actions.
7. Run successful and failing examples from Developer Tools -> Actions.
8. Check structured response shape.
9. Expose `script.llmtool_date_calculator` to Assist.
10. Ask the Assistant to calculate a date and inspect traces.

## Done when

- Local helper tests pass.
- Existing helper tests still pass.
- README documents Date Calculator usage.
- Home Assistant direct script validation succeeds.
- Assist validation succeeds after manual exposure.

## Unresolved questions

- Response examples per operation?
- Implement now?
