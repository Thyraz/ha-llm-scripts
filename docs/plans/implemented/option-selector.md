# Option Selector

Status: implemented and runtime-validated.

Option Selector replaces a user-specific input/select script with a repo-native
LLM Tool for reading available options from, and selecting one option on,
Home Assistant `input_select.*` and `select.*` entities.

## Decisions

- Tool name: Option Selector, not Select Manager.
- Public script ID: `script.llmtool_option_selector`.
- Operations: `get_options` and `select_option`.
- Supported domains: `input_select.*` and `select.*` only.
- Entity Index is the discovery path when exact entity ID is unknown.
- Exact option match wins; otherwise a case-insensitive unique match is allowed.
- Ambiguous and unknown options return soft failures with allowed options.
- Selecting the current option is allowed.
- `select_option` reports previous, selected, and observed current state after
  the Home Assistant action, but does not make success depend on the observed
  current state.
- Option lists are returned complete; no limit or truncation.
- Option Selector accepts exact supported entity IDs and does not duplicate
  Entity Index visibility labels.

## Validation Checklist

- Helper validates operation contract and unknown operations.
- Helper rejects unsupported entity domains and unknown entity IDs.
- Helper treats existing `unknown` state as an existing entity.
- Helper returns empty-options soft failure.
- Helper resolves exact, case-insensitive, ambiguous, and unknown desired options.
- YAML calls `{{ option_selector_helper.data.domain }}.select_option`.
- README, Prompt overview, `services.yaml`, trace debugging docs, research notes,
  and plan index mention Option Selector.
- Home Assistant runtime test passed for the implemented LLM Tool Script.
