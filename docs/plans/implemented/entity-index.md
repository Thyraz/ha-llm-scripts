# Entity Index Plan

Status: implemented. Local validation covered YAML parsing, Python syntax, and
direct helper simulations. Full Home Assistant validation still needs a target
instance with the expected labels.

Label name correction checked against Home Assistant docs on 2026-06-16.

## Purpose

Entity Index helps an Assistant find Home Assistant entities it is allowed to know about before calling other tools.

## Current decisions

- Only manually labeled Home Assistant entities are visible through this tool.
- Unlabeled Home Assistant entities are intentionally invisible to the Assistant.
- Every returned entity must have the direct entity label `Everywhere`.
- `Everywhere` is an internal visibility label, not a public query label.
- The queryable labels are discovered at runtime as friendly Home Assistant
  label names.
- If `input_select.llmtool_entity_index_labels` exists, its options are the
  explicit query label allowlist.
- Explicit helper options are used only when they resolve to real Home Assistant
  labels.
- If `input_select.llmtool_entity_index_labels` is missing, Entity Index falls
  back to all Home Assistant label names except internal visibility/location
  labels.
- If `input_select.llmtool_entity_index_labels` exists but has no options,
  Entity Index uses no query labels and returns validation errors for
  `entity_scope=filtered_by_labels`.
- Friendly label name matching is case-sensitive because `label_id(label_name)` is case-sensitive.
- The LLM Tool Script resolves friendly label names to internal label IDs with
  `label_id()` before calling `label_entities()`.
- Internal label IDs and internal visibility/location labels are implementation
  details and should not appear in Assistant-facing text.
- The LLM Tool Script passes the runtime query label list to the Python Helper
  as `known_labels`.
- `Inside` and `Outside` live as separate location-label name variables, not
  in the query label source.
- Entity labels representing rooms or floors are queryable labels in the label
  source, not new `location` values.
- Entity labels representing rooms or floors are not Home Assistant area labels
  for this tool, and should not become separate `area`, `room`, or `floor`
  parameters.
- Tool input accepts friendly label names only, not internal label IDs.
- Tool input accepts multiple label names as a comma-separated string in
  `label_names`.
- The user-provided `label_names` value must not include `Everywhere`, `Inside`,
  or `Outside`; `location` owns the location labels and visibility is always required.
- `location` is a mandatory parameter with values `inside`, `outside`, or `everywhere`.
- `location=inside` internally requires `Everywhere` and the existing HA label named `Inside`.
- `location=outside` internally requires `Everywhere` and the existing HA label named `Outside`.
- `location=everywhere` requires `Everywhere` and does not add either location label.
- If the requested location label does not exist in Home Assistant, return a successful empty result.
- The Assistant sees `inside` / `outside` / `everywhere` as location choices, not as labels.
- `label_operator=OR` applies only to user-provided labels; `location=inside` and
  `location=outside` are always required filters.
- `label_operator=OR` is for broad alternative searches and is a shortcut for
  multiple Entity Index calls with one label each.
- For room or floor plus device type, the Assistant should use `label_operator=AND`.
- Unknown labels should return `success: false` with an actionable error, `data.unknown_labels`,
  and `data.known_labels` so the Assistant can retry.
- Invalid `location`, `entity_scope`, `label_operator`, `verbosity`, non-integer
  `limit`, `limit < 1`, or `limit > 1000` return `success: false` with an
  actionable error.
- Missing or empty `limit` uses the default.
- `entity_scope` controls scope: `filtered_by_labels` or `all`.
- `entity_scope=filtered_by_labels` requires at least one non-empty label name.
- `entity_scope=all` returns visible entities even if they have no query label.
- `entity_scope=all` rejects `label_names` and `label_operator`.
- `label_operator` controls multi-label matching: `AND` or `OR`; default is `AND`.
- `label_operator` comparison is case-insensitive.
- `verbosity` controls result size: `id_only`, `compact`, or `detailed`; default is `compact`.
- `id_only` returns `data.entities` as a list of entity ID strings.
- Success responses always return results under `data.entities`.
- `compact` returns `entity_id`, `friendly_name`, `state`, and `matched_labels`.
- `compact` and `detailed` add `value_hint` only when the entity state is likely
  cumulative and period usage should be read through Long-Term Aggregated
  Statistics with `aggregation_type=change`.
- `matched_labels` contains only query-relevant labels that caused the entity to match.
- `matched_labels` excludes `Everywhere`, `Inside`, and `Outside`; location appears in response metadata.
- `state_filter` is an exact Home Assistant state string.
- Empty or missing `state_filter` means no state filter.
- `unknown` and `unavailable` are included unless `state_filter` excludes them.
- `detailed` adds safe operational fields only: `domain`, `area_id`, `device_id`,
  `unit_of_measurement`, `device_class`, and `state_class` when available.
- For `climate.*`, `detailed` may also include `current_temperature` and
  `temperature`.
- For `media_player.*`, `detailed` may also include `volume_level`,
  `is_volume_muted`, `media_title`, `media_album_name`, `shuffle`, `repeat`,
  and `group_members`.
- `detailed` omits unavailable optional fields and never dumps all attributes.
- Cumulative sensor hints use Home Assistant metadata such as
  `state_class=total`, `state_class=total_increasing`, and energy/water/gas
  unit metadata.
- `limit` caps returned results; default is 50 and maximum is 1000.
- Response metadata includes `count` for returned results and `total` for total matches before limit.
- Response metadata echoes normalized public query parameters, including
  `entity_scope`, `label_names`, `location`, `label_operator`, `state_filter`,
  `verbosity`, and `limit`.
- Runtime responses must not expose hidden visibility/location labels through
  `answer`, `error`, `data`, or `meta`.
- Capped responses include `meta.truncated: true`.
- Success `answer` is a short count summary; details stay in `data.entities`.
- Results are sorted by `entity_id` ascending.
- The LLM Tool Script handles fields, Home Assistant label name-to-ID lookup, and
  the final structured response.
- The LLM Tool Script gathers raw candidate records with entity labels, state,
  safe attributes, area ID, and device ID, then passes them to the LLM Tool
  Python Helper.
- The LLM Tool Script gathers one raw candidate shape for all verbosity modes;
  the helper decides which fields to return.
- The LLM Tool Script gathers candidates from the `Everywhere` visibility label,
  then marks query and location matches for the helper.
- For `entity_scope=filtered_by_labels`, the helper filters visible candidates by the
  requested query labels plus any location label.
- For `entity_scope=all`, the helper returns visible candidates matching
  the location filter.
- The LLM Tool Python Helper handles validation, set matching, sorting, limiting,
  and result shaping.

## Research before implementation

- Recheck current Home Assistant label helper behavior.
- Verify exact friendly label names in a real Home Assistant instance.
- Verify the friendly visibility/location label names `Everywhere`, `Inside`,
  and `Outside` exist in the target Home Assistant instance.
- Confirm response size stays useful for Assistants.

## Assistant call scenarios

These examples describe how the Home Assistant LLM Assistant should choose parameters when calling this tool.

- "Lowest room temperature" should use `location=inside` so outside temperature sensors are excluded.
- "Outside temperature" should use `location=outside`.
- Broad inventory questions may use `location=everywhere`.
- Broad inventory should use `entity_scope=all` and no labels.

## Prompt overview

README should include the same runtime query label source as the script, tell
the Assistant to call Entity Index before tools that need entity IDs, mention
that rooms and floors are `label_names`, and leave detailed call rules to the
Tool description.
