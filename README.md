# Home Assistant LLM Scripts

Reusable Home Assistant script collection for LLM-based Assistants.

This project exposes Home Assistant scripts as LLM tools. Scripts use HA-native operations first, and call native `python_script` helpers only when YAML/Jinja would become hard to read.

## Status

First implementation is a demo LLM Tool Script that proves:

- scalar tool parameters
- script to Python Helper handoff
- `output` captured through `response_variable`
- final structured response through `stop` and `response_variable`
- manual Assist exposure

## Install

Copy or sync these folders into your Home Assistant config folder:

```text
custom_llm_tools/
  llm_scripts/
python_scripts/
```

Add this to `configuration.yaml`:

```yaml
script llm_tools: !include_dir_merge_named custom_llm_tools/llm_scripts/

python_script:
```

Reload scripts or restart Home Assistant. For a new or renamed Python Helper,
run `python_script.reload`.

## Demo tool

After install, Home Assistant should expose:

- `script.llmtool_demo`
- `python_script.llmtool_demo`

Run `script.llmtool_demo` from Developer Tools -> Actions:

```yaml
name: Alex
```

Expected response in Developer Tools -> Actions:

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

Expected response in Assist tool trace:

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

Run again with empty or missing `name`; response should use `World`.
Then manually expose `script.llmtool_demo` to Assist and ask the Assistant to
call the demo tool. Inspect Script trace and Conversation trace.

## LLM tool response format

Tools return a structured response in Developer Tools -> Actions:

```yaml
success: true
answer: "Short summary for the Assistant."
data: {}
meta: {}
```

Assist tool traces wrap that payload under `result`.

Expected validation failures return:

```yaml
success: false
error: "Short actionable error."
data: {}
meta: {}
```

## Prompt guidance

Tell your Assistant that these tools share one response format. It should use `answer` for the short summary, `data` for structured details, and `meta` for counts/query echo.

## Docs

- [Glossary](CONTEXT.md)
- [HA research notes](docs/ha_research_notes.md)
- [LLM tool patterns](docs/llm_tool_patterns.md)
- [Jinja patterns](docs/jinja_patterns.md)
- [Python script notes](docs/python_script_notes.md)
- [Coding guidelines](docs/coding_guidelines.md)
- [Architecture decisions](docs/adr/0001-ha-native-llm-tool-scripts.md)
- [Tool plans](docs/plans/README.md)
- [Demo tool plan](docs/plans/implemented/demo-tool.md)
- [Entity Index plan](docs/plans/entity-index.md)

## Security

- Do not commit secrets.
- Do not log or return tokens.
- Do not patch `.storage/*`.
- Expose only intended `script.llmtool_*` entities to Assist.

## Validation

For every tool:

1. Validate YAML configuration.
2. Confirm `script.llmtool_*` exists.
3. Confirm fields appear in Developer Tools -> Actions.
4. Run the script directly.
5. Check structured response.
6. Expose the script to Assist.
7. Ask the Assistant to use it.
8. Inspect Conversation and Script traces.
