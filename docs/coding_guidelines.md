# Coding Guidelines

Keep the code easy to read. Prefer clear, boring control flow over defensive handling for errors that are unlikely and not useful to users.

## General

- Optimize for the next Home Assistant user reading the file.
- Validate expected user mistakes; do not guard every impossible branch.
- Keep names explicit and consistent with `CONTEXT.md`.
- Prefer small, direct scripts over clever abstractions.
- Keep secrets out of repo files, logs, comments, and responses.
- Do not invent entity IDs, labels, areas, floors, devices, or action names. Use values from the user, HA docs, or a verified HA instance.

## YAML LLM Tool Scripts

- Use native YAML comments freely. Comments are preserved in YAML files, unlike scripts edited through the Home Assistant GUI.
- Comment each non-obvious step: input cleanup, HA-native operation, helper call, response assembly.
- Prefer readable `variables`, `choose`, and sequential actions.
- Use `action:` for Home Assistant actions in new YAML, not legacy `service:`.
- Avoid complex nested templates when a Python Helper would be easier to understand.
- Return a structured response with `stop` and `response_variable`.

## Python Helpers

- Use simple top-level code; native `python_script` is not normal Python.
- Do not use imports.
- Use `output` for return data.
- Use `logger.info()` / `logger.warning()` only for useful debugging.
- Avoid broad defensive wrappers that hide useful failure signals during testing.

## Docs

- Mark HA facts as `verified`, `assumption`, or `risk` in `docs/ha_research_notes.md`.
- Record researched HA docs version and date.
- Move temporary planning notes into stable docs, then delete the temporary file.
