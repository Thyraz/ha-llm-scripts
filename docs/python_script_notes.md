# Python Script Notes

Native Home Assistant `python_script` is useful for small helpers, but it is sandboxed. It is not normal Python.

Source: https://www.home-assistant.io/integrations/python_script/

## Verified behavior

- Files live in `<config>/python_scripts/`.
- Each `.py` file becomes a `python_script.<name>` action.
- Scripts receive input through `data`.
- Scripts return data by writing to `output`.
- Callers capture helper output with `response_variable`.
- `services.yaml` documents Python script actions in the frontend.
- `python_script.reload` reloads available scripts and `services.yaml`.
- Existing script file changes do not require reload.

## Limits

- No imports.
- No external dependencies.
- Sandbox access to `hass` is limited.
- Keep helpers short and synchronous.

## Project use

Use an LLM Tool Python Helper for:

- data shaping that is hard to read in Jinja
- aggregation
- normalizing action responses before returning to the LLM Tool Script

Do not use a Python Helper just because it feels more familiar than YAML. If HA-native operations are clear, keep the work in the LLM Tool Script.

## Return shape

Python Helpers should write simple data to `output`. The LLM Tool Script remains responsible for the final structured response.

Example:

```python
name = data.get("name", "World")

output["normalized_name"] = str(name).strip()
output["message"] = "Hello {}".format(output["normalized_name"] or "World")
```
