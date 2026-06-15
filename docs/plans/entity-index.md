# Entity Index Plan

Entity Index is a planned LLM Tool for Assistants. It is not a coding guideline for this repository.

## Purpose

Entity Index helps an Assistant find Home Assistant entities it is allowed to know about before calling other tools.

## Current decisions

- Only manually labeled Home Assistant entities are visible through this tool.
- Unlabeled Home Assistant entities are intentionally invisible to the Assistant.
- The queryable labels are a static allowlist of canonical Home Assistant label IDs.
- Initial allowlist:
  - `PhotovoltaicSystem`
  - `ElectricCar`
  - `TemperatureSensor`
  - `Thermostat`
  - `WaterMeter`
  - `Light`
  - `WindowSensor`
  - `MediaPlayer`
  - `PowerSensor`
  - `EnergySensor`
  - `BatteryLevel`
  - `Selection`
  - `RainSensor`
- Label ID matching is case-sensitive.
- The static allowlist lives in `llmtool_entity_index.yaml` variables and is
  passed to the Python Helper as `known_labels`.
- `inside` and `outside` live as separate internal location-label variables, not
  in the queryable allowlist.
- Future room and house-level labels are queryable labels in the allowlist, not
  new `location` values.
- Tool input accepts label IDs only, not friendly label names.
- Tool input accepts multiple labels as a comma-separated string.
- The user-provided label list must not include `inside` or `outside`; `location` owns those labels.
- `location` is a mandatory parameter with values `inside`, `outside`, or `everywhere`.
- `location=inside` internally adds the existing HA label `inside` as an AND filter.
- `location=outside` internally adds the existing HA label `outside` as an AND filter.
- `location=everywhere` does not add either location label.
- If the requested location label does not exist in Home Assistant, return a successful empty result.
- The Assistant sees `inside` / `outside` / `everywhere` as location choices, not as labels.
- `match_mode=any` applies only to user-provided labels; `location=inside` and
  `location=outside` are always required filters.
- Unknown labels should return `success: false` with an actionable error, `data.unknown_labels`,
  and `data.known_labels` so the Assistant can retry.
- Invalid `location`, `query_mode`, `match_mode`, `verbosity`, non-integer `limit`, or
  `limit > 1000` return `success: false` with an actionable error.
- Missing or empty `limit` uses the default.
- `query_mode` controls scope, such as `by_labels` or `all_labeled`.
- `query_mode=by_labels` requires at least one non-empty label ID.
- `query_mode=all_labeled` returns entities with at least one allowlisted label, not entities with any Home Assistant label.
- `query_mode=all_labeled` ignores `match_mode`.
- `match_mode` controls multi-label matching: `any` or `all`; default is `all`.
- `verbosity` controls result size: `id_only`, `compact`, or `detailed`; default is `compact`.
- `id_only` returns `data.entities` as a list of entity ID strings.
- Success responses always return results under `data.entities`.
- `compact` returns `entity_id`, `friendly_name`, `state`, and `matched_labels`.
- `matched_labels` contains only query-relevant labels that caused the entity to match.
- `matched_labels` excludes `inside` and `outside`; location appears in response metadata.
- `state_filter` is an exact Home Assistant state string.
- Empty or missing `state_filter` means no state filter.
- `unknown` and `unavailable` are included unless `state_filter` excludes them.
- `detailed` adds safe operational fields only: `domain`, `area_id`, `device_id`,
  `unit_of_measurement`, `device_class`, and `state_class` when available.
- `detailed` omits unavailable optional fields and never dumps all attributes.
- `limit` caps returned results; default is 50 and maximum is 1000.
- Response metadata includes `count` for returned results and `total` for total matches before limit.
- Response metadata echoes normalized query parameters, including `query_mode`,
  `labels`, `location`, `effective_labels`, `match_mode`, `state_filter`,
  `verbosity`, and `limit`.
- Capped responses include `meta.truncated: true`.
- Success `answer` is a short count summary; details stay in `data.entities`.
- Results are sorted by `entity_id` ascending.
- The LLM Tool Script handles fields, Home Assistant label template lookup, and
  the final structured response.
- The LLM Tool Script gathers raw candidate records with entity labels, state,
  safe attributes, area ID, and device ID, then passes them to the LLM Tool
  Python Helper.
- The LLM Tool Script gathers one raw candidate shape for all verbosity modes;
  the helper decides which fields to return.
- For `query_mode=by_labels`, the LLM Tool Script gathers candidates from the
  requested labels plus any location label.
- For `query_mode=all_labeled`, the LLM Tool Script gathers candidates from the
  full allowlist plus any location label.
- The LLM Tool Python Helper handles validation, set matching, sorting, limiting,
  and result shaping.

## Research before implementation

- Recheck current Home Assistant label helper behavior.
- Verify exact label IDs/names in a real Home Assistant instance.
- Verify the internal `inside` and `outside` labels exist in the target Home Assistant instance.
- Confirm response size stays useful for Assistants.

## Assistant call scenarios

These examples describe how the Home Assistant LLM Assistant should choose parameters when calling this tool.

- "Lowest room temperature" should use `location=inside` so outside temperature sensors are excluded.
- "Outside temperature" should use `location=outside`.
- Broad inventory questions may use `location=everywhere`.

## Prompt guidance

The plan defines the intended prompt guidance. README should include the
copyable user-facing snippet after implementation. The snippet should tell the
Assistant to call Entity Index before tools that need entity IDs, use label IDs,
choose `location`, and inspect `meta.truncated`.
