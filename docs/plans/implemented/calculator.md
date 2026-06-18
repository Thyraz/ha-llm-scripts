# Calculator Plan

Status: implemented and validated with Home Assistant Developer Tools -> Actions.

## Purpose

Calculator gives an Assistant a deterministic arithmetic LLM Tool for values it
already has. It does not fetch Home Assistant states, entities, or history.

## Current decisions

- Script ID: `llmtool_calculator`.
- Entity after reload: `script.llmtool_calculator`.
- Python action: `python_script.llmtool_calculator`.
- Calculator is a pure arithmetic tool over caller-supplied values.
- History access and entity state lookup are out of scope for this tool.
- The Assistant must pass plain numeric values, not entity IDs, states with
  units, or expressions.
- Parameters are scalar/simple values:
  - `operation`
  - `values`
  - `precision`
- `operation` uses semantic names only:
  - `sum`
  - `difference`
  - `product`
  - `quotient`
  - `minimum`
  - `maximum`
  - `average`
- Operator symbols and aliases are not accepted in v1.
- `values` is a comma-separated string of Calculator values.
- Calculator values are strict locale-independent decimal numbers.
- `.` is the decimal separator, independent of the user's locale settings.
- Units, words, empty values, `unknown`, `unavailable`, `nan`, `inf`,
  `infinity`, and scientific notation are invalid.
- Commas always delimit values. Localized decimal commas and thousands
  separators are not interpreted as part of a number.
- Accept examples: `1`, `-1`, `1.5`, `.5`, `1.`.
- Maximum value count is 1000.
- Order matters for `difference` and `quotient`.
- `sum`, `product`, `minimum`, `maximum`, and `average` require at least one
  value.
- `difference` and `quotient` require at least two values.
- `average` with one value is valid and returns that value.
- `quotient` returns a soft validation failure if any divisor is zero.
- `precision` is optional.
- Empty `precision` returns the natural normalized numeric result.
- `precision` accepts integers from 0 to 10.
- When `precision` is supplied, `data.result` and `answer` use the rounded
  result, and `data.raw_result` contains the unrounded result.
- `data.result` is a number, not a string.
- Any result equal to zero is normalized to `0`, not `-0.0`.
- The LLM Tool Script owns fields, helper call, and final structured response.
- The LLM Tool Python Helper owns parsing, validation, arithmetic, rounding, and
  response shaping.

## Tool contract

Successful response:

```yaml
success: true
answer: "Result: 6."
data:
  result: 6
  values:
    - 1
    - 2
    - 3
meta:
  tool: llmtool_calculator
  operation: sum
  value_count: 3
```

Rounded response:

```yaml
success: true
answer: "Result: 3.33."
data:
  result: 3.33
  raw_result: 3.3333333333333335
  values:
    - 10
    - 3
meta:
  tool: llmtool_calculator
  operation: quotient
  value_count: 2
  precision: 2
```

Validation failure:

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

## Implementation notes

- Add `custom_llm_tools/llm_scripts/calculator.yaml`.
- Add `python_scripts/llmtool_calculator.py`.
- Add `llmtool_calculator` to `python_scripts/services.yaml`.
- Add `tests/test_llmtool_calculator.py`.
- Update README status, tool section, prompt guidance, and validation command.
- Use `action: python_script.llmtool_calculator`.
- Use `stop` with `response_variable`.
- Keep Assistant-facing text focused on valid operations, decimal format,
  response fields, and validation retry behavior.
- Keep implementation details in comments and this plan.
- Do not use imports in the Python Helper.

## Test cases

- Sum multiple values.
- Difference preserves order.
- Product multiple values.
- Quotient preserves order.
- Minimum and maximum.
- Average one and many values.
- Precision rounding includes `raw_result`.
- Empty precision omits `raw_result`.
- Negative zero normalizes to `0`.
- Invalid operation returns known operations.
- Missing values returns arity error.
- Too few values for `difference` and `quotient`.
- Invalid decimal tokens include 1-based positions.
- Decimal comma is treated as a value separator, not a decimal separator.
- Units are rejected.
- Scientific notation is rejected.
- Division by zero returns soft failure.
- More than 1000 values returns soft failure.

## Manual validation

1. Copy or sync files into Home Assistant config.
2. Reload scripts or restart Home Assistant.
3. Run `python_script.reload` for the new Python Helper.
4. Confirm `script.llmtool_calculator` exists.
5. Confirm `python_script.llmtool_calculator` exists.
6. Confirm fields appear in Developer Tools -> Actions.
7. Run successful and failing examples from Developer Tools -> Actions.
8. Check structured response shape.
9. Expose `script.llmtool_calculator` to Assist.
10. Ask the Assistant to calculate with known values.
11. Inspect Conversation and Script traces.

## Done when

- Local helper tests pass.
- Existing Entity Index helper tests still pass.
- README documents Calculator usage.
- Home Assistant direct script validation succeeds.
- Assist validation succeeds after manual exposure.

## Unresolved questions

None.
