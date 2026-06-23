# Media Player Group Manager Plan

Status: implemented and validated with Home Assistant Developer Tools -> Actions.

## Purpose

Media Player Group Manager lets an Assistant change Home Assistant media player
groups for supported multiroom audio integrations.

## Current decisions

- Tool name: Media Player Group Manager.
- Script ID: `llmtool_media_player_group_manager`.
- Entity after reload: `script.llmtool_media_player_group_manager`.
- Python action: `python_script.llmtool_media_player_group_manager`.
- The tool mutates media player group state.
- The tool uses Home Assistant native `media_player.join` and
  `media_player.unjoin` actions.
- Integrations that do not support media player grouping may fail at runtime;
  the LLM Tool does not hide those Home Assistant runtime errors.
- Parameters are scalar/simple values:
  - `operation`
  - `leader_entity_id`
  - `member_entity_ids`
  - `ungroup_first`
  - `replace_existing`
- Use `leader_entity_id`, not `master`.
- Use `member_entity_ids`, not `members`.
- No legacy parameter aliases.
- Supported operations:
  - `join`
  - `unjoin`
  - `clear_members`
- No `inspect` operation in v1.
- No public `dry_run` or plan-only mode.
- `leader_entity_id` is a Home Assistant `media_player.*` entity ID.
- `member_entity_ids` is a comma-separated list of Home Assistant
  `media_player.*` entity IDs.
- Media player entity IDs should normally come from Entity Index.
- The Assistant-facing text should not hardcode a specific Entity Index label
  name.
- Invalid entity IDs return a soft validation failure with
  `data.invalid_entity_ids`.
- `join` requires `leader_entity_id`.
- `join` requires at least one final member entity ID different from
  `leader_entity_id`.
- If `leader_entity_id` appears in `member_entity_ids` for `join`, remove it
  from the final members and report it under `data.ignored_member_entity_ids`.
- Duplicate member entity IDs are de-duped while preserving first occurrence
  order and reported under `data.duplicate_member_entity_ids`.
- `join` preserves final member order.
- `unjoin` requires `member_entity_ids`.
- `unjoin` does not accept `leader_entity_id`; pass the player to
  `member_entity_ids` instead.
- `unjoin` supports multiple member entity IDs in one LLM Tool call and unjoins
  them in input order after de-dupe.
- `clear_members` requires `leader_entity_id`.
- `clear_members` rejects `member_entity_ids`.
- `clear_members` reads `state_attr(leader_entity_id, 'group_members')`, removes
  the leader from that list, and unjoins the remaining current members.
- Missing, string, or non-list `group_members` is treated as an empty current
  group.
- `clear_members` preserves current group order when unjoining.
- `clear_members` returns success when there are no current non-leader members.
- `ungroup_first` is valid only for `join`.
- `replace_existing` is valid only for `join`.
- If either flag is true for a non-`join` operation, return a soft validation
  failure with `data.invalid_flags`.
- For `join`, `ungroup_first=true` unjoins the leader and all final members
  before joining.
- For `join`, `replace_existing=true` unjoins current non-leader members from
  the leader group before joining new members.
- `ungroup_first=true` and `replace_existing=true` may be combined.
- Unjoin action targets are de-duped across `ungroup_first` and
  `replace_existing`.
- The LLM Tool Script uses `mode: queued` and `max: 2`.
- The LLM Tool Script owns fields, Home Assistant state reads, native
  `media_player.*` action calls, and final response handoff.
- The LLM Tool Python Helper owns input parsing, validation, action-plan
  shaping, duplicate/self handling, and final structured response shaping.
- Use one Python Helper with a `mode` field:
  - `prepare` validates input and returns an action plan.
  - `shape` turns the executed action plan into the final structured response.
- Do not write logbook entries for every call.
- Do not change Entity Index for this tool.

## Tool contract

Join success:

```yaml
success: true
answer: "Joined 2 media player group members."
data:
  operation: join
  leader_entity_id: media_player.living_room
  joined_member_entity_ids:
    - media_player.kitchen
    - media_player.bedroom
  unjoined_entity_ids: []
  ignored_member_entity_ids: []
  duplicate_member_entity_ids: []
  ungroup_first: false
  replace_existing: false
meta:
  tool: llmtool_media_player_group_manager
  operation: join
  leader_entity_id: media_player.living_room
```

Unjoin success:

```yaml
success: true
answer: "Unjoined 1 media player."
data:
  operation: unjoin
  unjoined_entity_ids:
    - media_player.kitchen
  duplicate_member_entity_ids: []
meta:
  tool: llmtool_media_player_group_manager
  operation: unjoin
```

Clear members success:

```yaml
success: true
answer: "Cleared 2 media player group members."
data:
  operation: clear_members
  leader_entity_id: media_player.living_room
  cleared_member_entity_ids:
    - media_player.kitchen
    - media_player.bedroom
  previous_member_entity_ids:
    - media_player.kitchen
    - media_player.bedroom
meta:
  tool: llmtool_media_player_group_manager
  operation: clear_members
  leader_entity_id: media_player.living_room
```

Validation failure:

```yaml
success: false
error: "Invalid entity ID. Use Home Assistant media_player.* entity IDs."
data:
  invalid_entity_ids:
    - light.kitchen
meta:
  tool: llmtool_media_player_group_manager
  operation: join
```

## Expected soft errors

- Invalid operation.
- Invalid entity ID format or non-media-player domain.
- Missing `leader_entity_id` for `join`.
- Missing `leader_entity_id` for `clear_members`.
- Missing `member_entity_ids` for `join`.
- Missing `member_entity_ids` for `unjoin`.
- `join` member list contains only the leader after cleanup.
- `leader_entity_id` supplied for `unjoin`.
- `member_entity_ids` supplied for `clear_members`.
- `ungroup_first` or `replace_existing` supplied for non-`join` operation.

## Implementation notes

- Add `custom_llm_tools/llm_scripts/media_player_group_manager.yaml`.
- Add `python_scripts/llmtool_media_player_group_manager.py`.
- Add `llmtool_media_player_group_manager` to `python_scripts/services.yaml`.
- Add `tests/test_llmtool_media_player_group_manager.py`.
- Update README status, usage, prompt guidance, validation command, and docs
  links.
- Update `docs/ha_research_notes.md` with media player action facts.
- Use `action: media_player.join` with `target.entity_id` as the leader and
  `data.group_members` as the final members.
- Use `action: media_player.unjoin` with `target.entity_id` for each unjoin
  target.
- Use `stop` with `response_variable`.
- Keep Assistant-facing text focused on operations, media player entity IDs,
  grouping support, response fields, and validation retry behavior.
- Keep implementation details in comments and this plan.
- Do not use imports in the Python Helper.

## Test cases

- Join builds a join action plan.
- Join removes the leader from member entity IDs and reports it.
- Join de-dupes member entity IDs and preserves order.
- Join fails when only the leader remains after cleanup.
- Join with `ungroup_first` plans leader and member unjoins first.
- Join with `replace_existing` plans current non-leader member unjoins.
- Combined `ungroup_first` and `replace_existing` de-dupes unjoin targets.
- Unjoin requires member entity IDs and rejects `leader_entity_id`.
- Clear members rejects explicit member entity IDs.
- Clear members uses current non-leader group members.
- Missing or string current group members behave as an empty group.
- Invalid entity IDs return soft failures.
- Non-`join` flags return soft failures.
- Shape mode returns standard structured responses for each operation.
- Invalid helper mode returns a soft failure.
