# LLM Tool Patterns

## Runtime model

An LLM Tool Script is the public Home Assistant script exposed to Assist. It should use HA-native operations first: script actions, template functions, state reads, and integrations such as `rest_command`.

Use an LLM Tool Python Helper only when YAML/Jinja would be hard to read or when a response needs heavier data shaping.

## Naming

- LLM Tool Script IDs use `llmtool_` prefix.
- Python Helper filenames match the action name, for example `python_scripts/llmtool_demo.py`.
- Use lowercase letters and underscores.
- Avoid generic names such as `calendar_lookup`.

## Parameters

- Prefer scalar strings, booleans, and simple enum strings.
- Prefer comma-separated strings over list selectors until LLM tool parameter behavior is tested.
- Keep descriptions precise; the Assistant sees them as tool guidance.
- Do not ask the Assistant to guess Home Assistant IDs. Use explicit parameters, documented examples, or a purpose-built lookup tool.
- Tool descriptions should describe usable parameters, allowed public values,
  response fields, examples, and retry behavior for one tool. Keep
  implementation details out.
- Prompt overviews should help the Assistant choose the right tool. Do not make
  them full call references.
- For user-specific allowed values that must survive repo updates, prefer a
  user-owned Home Assistant helper/source that both the prompt template and the
  LLM Tool Script read. Do not hardcode those values in repo-owned scripts.

## Response schema

Home Assistant Assist wraps exposed script responses as:

```yaml
success: true
result:
  success: true
  answer: "Short summary for the Assistant."
  data: {}
  meta: {}
```

So the LLM Tool Script should return the structured payload as the script response. The Assistant will place it under `result`.

Success:

```yaml
success: true
answer: "Short summary for the Assistant."
data:
  result: []
meta:
  count: 0
```

Failure:

```yaml
success: false
error: "Short actionable error."
data: {}
meta: {}
```

Rules:

- `answer` is short. Put structured payload in `data`.
- Omit `error` on success.
- Include `meta` when it helps the Assistant retry or explain the result.
- Use soft failures (`success: false`) for expected validation problems.
- Reserve Home Assistant runtime errors for real unexpected failures.
- Use `stop: ""` with `response_variable`.

## Script-helper handoff

For structured data from an LLM Tool Script to a Python Helper, make the type
boundary explicit.

Pattern:

```yaml
- variables:
    records_json: >
      {% set ns = namespace(items=[]) %}
      ...
      {{ ns.items | to_json }}

- action: python_script.llmtool_example
  data:
    records: "{{ records_json | from_json }}"
  response_variable: helper_result
```

Rules:

- Use this pattern for lists or mappings. Do not rely on block-template output
  being preserved as native list/dict action data.
- Check the Script trace. If a script variable already appears as a native
  list/dict, pass it directly and do not call `from_json` again.
- If a script variable appears as a JSON string, deserialize it with `from_json`
  at the Python Helper action boundary.
- Keep handoff records JSON-compatible: strings, numbers, booleans, lists,
  mappings, and null-like empty values.
- Convert enum-like Home Assistant objects to strings before `to_json`, such as
  units, device classes, and state classes.
- Give intermediate variables a `_json` suffix when they intentionally hold
  serialized data.
- In the Python Helper, validate expected handoff shape. If a list/dict arrives
  as a string, return a soft failure with an actionable error instead of
  returning an empty success.
- The Python Helper should return data through `output`; the LLM Tool Script
  still owns the final structured response returned to Assist.

## Tool descriptions

Each LLM Tool Script description should say:

- when to use the tool
- exact workflow once the Assistant chose the tool
- what each parameter means and when to pass it
- what response format to expect
- how to handle validation failures, truncation, or empty results
- important safety limits
- one or two concrete call examples for non-trivial tools

Do not mention hidden filters, internal IDs, helper handoff details, or
implementation labels in Assistant-facing descriptions. Put those details in
YAML comments, plans, debugging docs, or research notes.

Short negative guidance is allowed when it addresses an observed Assistant
failure and does not expose implementation details. Example: "Entity labels
representing rooms or floors are label_names, not location values."

For non-trivial tools, include one call example and one response example when
the Assistant must inspect nested response data. Small realtime models often do
better with concrete, human-like examples than abstract placeholders. Use
plausible values such as `LivingRoom` rather than placeholders such as
`RoomLabel`, and explicitly say that example values may need replacement with
real supported values.

Do not over-compress tool descriptions for realtime smart-home models. More
human-like parameter descriptions can be useful when they explain how parameters
interact, or when to use them.

## Prompt overviews

README should include one compact Prompt overview covering the non-demo LLM
Tools. Demo tools are validation-only and do not need operational prompt text. A
later `examples/assistant_prompt.md` can provide a full copyable version.

The Prompt overview should tell the Assistant:

- these tools share the same response format
- use `answer` for a short summary
- use `data` for structured details
- use `meta` for counts and query echo
- when to call each non-demo tool
- main tool-to-tool flow, such as Entity Index before tools that need entity IDs
- key safety rules that affect tool choice, such as write/destructive memory operations

Prompt overview entries should normally describe what a tool is good for, not
how to call it. Add extra tool-selection hints only for observed small-model
failure modes where the Assistant repeatedly chooses the wrong tool or workflow.

The Prompt overview should not duplicate full parameter lists, call examples,
or detailed retry rules. Those belong in Tool descriptions. Short negative
guidance is allowed only for repeated observed mistakes.
