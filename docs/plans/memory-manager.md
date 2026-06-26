# Memory Manager Plan

Status: planned. No implementation yet.

## Purpose

Memory Manager lets an Assistant remember user-provided information across conversations. It is optional, separate from the base script install, and should only be exposed to Assist when the user wants Assistant memory.

## Current decisions

- Tool name: Memory Manager.
- Script ID: `llmtool_memory_manager`.
- Entity after reload: `script.llmtool_memory_manager`.
- Python action: `python_script.llmtool_memory_manager`.
- Memory Manager depends on the third-party Variables+History integration.
- Users must create one Variables+History sensor with entity ID `sensor.llm_memory`.
- The Memory Store Entity should use Restore on Restart.
- The Memory Store Entity should use Exclude from Recorder because attributes may be large.
- Memory Manager auto-initializes missing memory attributes.
- The user must manually expose only `script.llmtool_memory_manager` to Assist.
- Existing LLM Tools and the base install path do not depend on Memory Manager.
- Memory Manager uses the Memory Store Entity's `memory` attribute as its store.
- Memory Manager does not use files, SQLite, shell commands, REST commands, add-ons, or custom integrations in v1.
- Memory Manager is not a semantic memory system and does not use embeddings.
- Search is deterministic lexical token search.
- Search does not do fuzzy typo matching in v1.
- Memory Manager has one capped store in v1.
- The soft store warning threshold is 96 KiB.
- The hard store write limit is 120 KiB.
- Store size is measured from normalized memory JSON before a write.
- If a write would exceed the hard limit, return a soft failure and do not write.
- If a write crosses or remains above the soft threshold, return success with warning metadata.
- Each Memory Entry text is capped at 4 KiB.
- `remember` always creates a new Memory Entry.
- Memory Manager does not auto-deduplicate entries.
- `forget` hard-deletes a Memory Entry by ID.
- `update` replaces full entry text by ID.
- `update` may also replace topic and labels.
- If `update` omits topic or labels, keep the existing values.
- Memory IDs are stable strings generated from `next_id`, such as `m000001`.
- Topics and labels normalize to `lower_snake`.
- `remember` requires topic, at least one label, and text.
- The Assistant should call `list_topics` before creating new topics or labels when practical, to reduce near-duplicate organization terms.
- `list_topics` is also the label discovery getter: it returns every known topic with its labels, so there is no separate `list_labels` operation in v1.
- The Assistant should call `list_topics` before broad or ambiguous searches when labels may help narrow the request.
- `search` can filter by topic and labels.
- `search` accepts `label_match_mode=all` or `any`; default is `all`.
- `search`, `list_topics`, and `list_recent` return snippets only.
- `read` returns full text for one Memory Entry.
- Memory Manager does not verify writes after `variable.update_sensor`; Home Assistant runtime errors are allowed to surface if the update action fails.

## Store shape

The `memory` attribute on `sensor.llm_memory` is a mapping:

```yaml
schema_version: 1
next_id: 2
entries:
  m000001:
    topic: school
    labels:
      - schedule
      - kid_one
    text: "School starts at 08:10 on regular weekdays."
    created_at: "2026-06-26 10:15:00"
    updated_at: "2026-06-26 10:15:00"
```

Rules:

- `schema_version` must be `1`.
- `next_id` is the next integer used for Memory ID generation.
- `entries` is keyed by Memory ID.
- Entry fields are `topic`, `labels`, `text`, `created_at`, and `updated_at`.
- The store has no separate label index in v1; labels and topics are derived by scanning entries.
- Malformed stores return an actionable soft failure unless the attribute is missing, in which case the helper initializes an empty v1 store.

## Tool contract

Common fields:

- `operation`: `remember`, `search`, `read`, `update`, `forget`, `list_topics`, `list_recent`, or `status`.
- `memory_id`: Memory ID for `read`, `update`, and `forget`.
- `topic`: required for `remember`, optional for `search` and `update`.
- `labels`: comma-separated Memory Labels. Required for `remember`, optional for `search` and `update`.
- `label_match_mode`: `all` or `any` for multi-label search. Empty means `all`.
- `query`: lexical search text for `search`.
- `text`: Memory Entry text for `remember` and `update`.
- `limit`: optional maximum result count for `search` and `list_recent`.

Successful `remember`:

```yaml
success: true
answer: "Remembered 1 memory entry."
data:
  memory_id: m000001
  topic: school
  labels:
    - schedule
    - kid_one
meta:
  tool: llmtool_memory_manager
  operation: remember
  store_size_bytes: 424
  soft_limit_bytes: 98304
  hard_limit_bytes: 122880
```

Successful `list_topics`:

```yaml
success: true
answer: "Found 2 memory topics."
data:
  topics:
    - topic: school
      count: 3
      labels:
        - schedule
        - kid_one
    - topic: heating
      count: 2
      labels:
        - bedroom
        - preference
meta:
  tool: llmtool_memory_manager
  operation: list_topics
  topic_count: 2
  entry_count: 5
```

Use `list_topics` when the Assistant needs to see available Memory Labels before searching or writing.

Successful `search`:

```yaml
success: true
answer: "Found 1 matching memory entry."
data:
  entries:
    - memory_id: m000001
      topic: school
      labels:
        - schedule
        - kid_one
      snippet: "School starts at 08:10 on regular weekdays."
      updated_at: "2026-06-26 10:15:00"
meta:
  tool: llmtool_memory_manager
  operation: search
  count: 1
  total: 1
  query: school starts today
  topic: school
  label_match_mode: all
```

Successful `read`:

```yaml
success: true
answer: "Read memory entry m000001."
data:
  memory_id: m000001
  topic: school
  labels:
    - schedule
    - kid_one
  text: "School starts at 08:10 on regular weekdays."
  created_at: "2026-06-26 10:15:00"
  updated_at: "2026-06-26 10:15:00"
meta:
  tool: llmtool_memory_manager
  operation: read
```

Store full failure:

```yaml
success: false
error: "Memory store is full. Ask the user to review Memory Manager entries and forget old entries before adding more."
data:
  store_size_bytes: 121900
  hard_limit_bytes: 122880
  attempted_size_bytes: 123100
meta:
  tool: llmtool_memory_manager
  operation: remember
```

## Implementation notes

- Add `custom_llm_tools/llm_scripts/memory_manager.yaml`.
- Add `python_scripts/llmtool_memory_manager.py`.
- Add `llmtool_memory_manager` to `python_scripts/services.yaml`.
- Add `tests/test_llmtool_memory_manager.py`.
- Update README with a separate optional Memory Manager chapter.
- Update README prompt guidance for Memory Manager.
- Update `docs/ha_trace_debugging.md` with Memory Manager trace variables.
- Keep Assistant-facing text clear that Memory Manager is optional.
- Keep Assistant-facing text clear that writes happen only when the user asks to remember something.
- Keep Assistant-facing text clear that the Assistant may search memory when user intent suggests prior personal or home-specific knowledge may matter.
- Use `action: variable.update_sensor` to write the Memory Store Entity.
- Use `replace_attributes: true` and send the full `memory` attribute on writes.
- Use `action: python_script.llmtool_memory_manager` for validation, normalization, search, and response shaping.
- Use `stop` with `response_variable`.
- Do not mention Variables+History internals in Assistant-facing text except in setup errors.

## Assistant call scenarios

- User says "remember that Kid One starts school at 08:10": call `list_topics` if practical, then `remember` with topic `school`, labels such as `schedule,kid_one`, and the remembered text.
- User asks "what do you remember about school?": call `list_topics`, then `search` with topic `school`.
- User asks "when does school start today for Kid One?": call `list_topics` if needed, then `search` with topic `school`, labels `schedule,kid_one`, and query terms from the question. Use `read` for a promising result before answering.
- User says "forget that school time": search if no Memory ID is known, confirm the likely entry in the answer, and call `forget` only when the user intent is explicit.
- User says "update that school starts at 08:20 now": search/read first, then call `update` with the full replacement text.

## Test cases

- Missing Memory Store Entity returns setup soft failure.
- Missing `memory` attribute initializes empty v1 store.
- Valid existing v1 store is accepted.
- Malformed `memory` attribute returns actionable soft failure.
- Invalid operation returns known operations.
- `remember` requires topic, label, and text.
- Topic and labels normalize to `lower_snake`.
- `remember` creates stable IDs and increments `next_id`.
- `remember` rejects text over 4 KiB.
- `remember` rejects writes over 120 KiB normalized store size.
- `remember` succeeds with warning metadata above 96 KiB.
- `list_topics` returns topics, counts, and sorted labels.
- `list_topics` is sufficient for label discovery; no separate label index or label operation exists in v1.
- `list_recent` returns snippets only.
- `search` matches lexical query tokens against text, topic, and labels.
- `search` supports `label_match_mode=all`.
- `search` supports `label_match_mode=any`.
- `search` honors `limit` and reports truncation.
- `read` returns full text by Memory ID.
- `read` returns soft failure for unknown Memory ID.
- `update` replaces text and preserves omitted topic and labels.
- `update` can replace topic and labels.
- `update` enforces entry and store size limits.
- `forget` removes the entry and frees store bytes.
- `status` returns entry count, topic count, store size, soft limit, hard limit, and warning state.
- Native `python_script` restricted-runtime tests pass without imports.

## Manual validation

1. Install Variables+History through HACS.
2. Create a Sensor variable with ID `llm_memory`.
3. Set Restore on Restart to true.
4. Set Exclude from Recorder to true.
5. Copy or sync Memory Manager files into Home Assistant config.
6. Reload scripts or restart Home Assistant.
7. Run `python_script.reload` for the new Python Helper.
8. Confirm `sensor.llm_memory` exists.
9. Confirm `script.llmtool_memory_manager` exists.
10. Run each operation from Developer Tools -> Actions.
11. Restart Home Assistant and confirm memory restores.
12. Expose `script.llmtool_memory_manager` to Assist.
13. Ask the Assistant to remember, search, read, update, and forget a test entry.
14. Inspect Conversation and Script traces.

## Unresolved questions

None.
