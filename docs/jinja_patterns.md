# Home Assistant Jinja Patterns

Home Assistant extends Jinja with custom functions, filters, and tests. Check current docs before adding non-trivial template logic.

Source: https://www.home-assistant.io/template-functions/

## State access

Prefer:

```jinja
{{ states('sensor.example') }}
{{ state_attr('sensor.example', 'friendly_name') }}
```

Avoid:

```jinja
{{ states.sensor.example.state }}
```

## Defaults

Use explicit defaults when converting:

```jinja
{{ states('sensor.temperature') | float(none) }}
{{ count | default(0, true) | int(0) }}
```

## Lists and loops

Jinja loop assignment has scoping rules. Use `namespace()` when a loop needs to build a value used later.

For large transforms, prefer an LLM Tool Python Helper instead of dense YAML/Jinja.

## Serialization

When rendering a list or mapping into a string field, serialize it explicitly.

Prefer `to_json` in this repo for consistency:

```jinja
{{ result | to_json }}
```

For LLM Tool Script to Python Helper handoff, deserialize at the action boundary:

```yaml
data:
  records: "{{ records_json | from_json }}"
```

Do not pass a block-template list/dict directly to a Python Helper and assume it
will stay native. Use `to_json` first, then `from_json`.

Home Assistant also exposes `tojson`; verify current docs before changing style.

## YAML strings

- Quote strings containing `{{ ... }}` when unsure.
- Use `>` for folded prose.
- Use `|` when preserving line breaks matters.
- Keep templates short enough that a Home Assistant user can debug them in Developer Tools.
