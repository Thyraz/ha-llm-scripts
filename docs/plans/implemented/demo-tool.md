# Demo LLM Tool Plan

Status: implemented and validated with Home Assistant Developer Tools -> Actions and Assist.

This is the first implementation step. It proves the basic workflow before real tools like Entity Index.

## Goal

Create one minimal LLM Tool Script and one LLM Tool Python Helper that prove:

- scalar tool parameters
- YAML script to Python Helper handoff
- Python `output` captured through `response_variable`
- final structured response through `stop` and `response_variable`
- manual Assist exposure

## Files to add

- `custom_llm_tools/llm_scripts/demo.yaml`
- `python_scripts/llmtool_demo.py`
- `python_scripts/services.yaml`
- README install/test notes if missing after implementation

## Tool contract

Script ID: `llmtool_demo`

Entity after reload: `script.llmtool_demo`

Python action: `python_script.llmtool_demo`

Input field:

- `name`
- type: text/scalar string
- required: false
- default behavior: use `World` when empty or missing

Successful response in Developer Tools -> Actions:

```yaml
success: true
answer: "Hello Alex, this came from the LLM Tool Python Helper."
data:
  normalized_name: "Alex"
  helper_message: "Hello Alex, this came from the LLM Tool Python Helper."
meta:
  tool: "llmtool_demo"
  python_helper: "python_script.llmtool_demo"
```

Successful response in Assist tool trace:

```yaml
success: true
result:
  success: true
  answer: "Hello Alex, this came from the LLM Tool Python Helper."
  data:
    normalized_name: "Alex"
    helper_message: "Hello Alex, this came from the LLM Tool Python Helper."
  meta:
    tool: "llmtool_demo"
    python_helper: "python_script.llmtool_demo"
```

Expected validation behavior:

- Keep validation minimal.
- Convert `name` to a string in the Python Helper.
- Strip whitespace.
- If the stripped value is empty, use `World`.
- Do not add broad defensive error handling.

## YAML script guidance

- Use `action: python_script.llmtool_demo`, not legacy `service:`.
- Use native YAML comments for each meaningful section.
- Keep flow readable: input cleanup, helper call, response assembly, stop.
- The LLM Tool Script owns the final structured response.
- The Python Helper only returns helper data through `output`.

## Python helper guidance

- No imports.
- Read input from `data`.
- Write return values to `output`.
- Keep top-level code simple.
- Do not log unless useful for debugging.

## Manual validation

1. Copy/sync `custom_llm_tools/` and `python_scripts/` into Home Assistant config.
2. Ensure `configuration.yaml` contains:

```yaml
script llm_tools: !include_dir_merge_named custom_llm_tools/llm_scripts/

python_script:
```

3. Reload scripts or restart Home Assistant.
4. Confirm `script.llmtool_demo` exists.
5. Confirm `python_script.llmtool_demo` is callable.
6. Run `script.llmtool_demo` from Developer Tools -> Actions with `name=Alex`.
7. Verify structured response includes `success`, `answer`, `data`, and `meta`.
8. Run with empty/missing `name`; verify fallback to `World`.
9. Manually expose `script.llmtool_demo` to Assist.
10. Ask the Assistant to call the demo tool.
11. Verify Conversation trace contains `tool_result.result.answer`.
12. Inspect Script trace and Conversation trace.

## Done when

- The demo works from Developer Tools -> Actions.
- The demo works when exposed to Assist.
- README explains the install and validation steps clearly enough for another user.
- Any HA behavior learned during testing is added to `docs/ha_research_notes.md`.
