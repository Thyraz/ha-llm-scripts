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

## Tool descriptions

Each LLM Tool Script description should say:

- when to use the tool
- what each parameter means
- what response format to expect
- important safety limits

## Prompt guidance

README should include a short prompt snippet for each non-demo LLM Tool. Demo
tools are validation-only and do not need operational prompt snippets. A later
`examples/assistant_prompt.md` can provide a full copyable version.

The prompt should tell the Assistant:

- these tools share the same response format
- use `answer` for a short summary
- use `data` for structured details
- use `meta` for counts and query echo
- when to call each non-demo tool
- how to choose important parameters
- how to react to validation errors or truncated results
