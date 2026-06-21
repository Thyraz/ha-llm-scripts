# Home Assistant LLM Scripts

This project defines a reusable script collection for giving Home Assistant Assistants safe, documented LLM tools.

## Language

**LLM Tool**:
A capability intended for an LLM-based Assistant to call through Home Assistant.
_Avoid_: function, plugin, skill

**LLM Tool Script**:
A Home Assistant script exposed to an Assistant as the public entrypoint for an LLM Tool.
_Avoid_: YAML wrapper, wrapper script

**HA-native operation**:
Work done inside an LLM Tool Script using Home Assistant's own script actions, template functions, or integrations.
_Avoid_: backend, service layer

**LLM Tool Python Helper**:
A native Home Assistant `python_script` used by an LLM Tool Script for data shaping or handoff logic that is too awkward in YAML/Jinja.
_Avoid_: backend, worker, integration

**Structured response**:
A mapping returned by an LLM Tool with predictable keys so an Assistant can use the result reliably.
_Avoid_: text blob, raw output

**Assist exposure**:
The user-controlled Home Assistant step that makes an LLM Tool Script available to an Assistant.
_Avoid_: auto expose, storage patching

**Assistant-facing text**:
Text an Assistant may read when choosing, calling, or interpreting an LLM Tool.
_Avoid_: implementation notes, internal docs

**Entity Index**:
An LLM Tool that lets an Assistant discover Home Assistant entities it is allowed to know about before calling other LLM Tools.
_Avoid_: entity registry dump, entity database, search backend

**Long-Term Aggregated Statistics**:
An LLM Tool that returns aggregated Home Assistant long-term statistics for a requested time range.
_Avoid_: Aggregated Longterm History Access, raw state history, history fetcher

**Long-Term Statistics Entity ID**:
An entity ID supplied to Long-Term Aggregated Statistics and passed to Home Assistant as a statistic ID.
_Avoid_: external statistic ID, raw history entity

**Long-Term Statistics Time Range**:
A local Home Assistant time range with a required start time and optional end time used to query Long-Term Aggregated Statistics.
_Avoid_: relative time text, UTC-only range

**Long-Term Statistics Period**:
A grouping choice for Long-Term Aggregated Statistics results, including Home Assistant statistics periods and one total-range aggregate.
_Avoid_: arbitrary interval, sample rate

**Raw Entity History**:
An LLM Tool that returns unaggregated Home Assistant entity state history for a requested time range.
_Avoid_: Short-Term RAW Entity History, raw recorder dump, history fetcher

**Calculator**:
An LLM Tool that performs deterministic arithmetic over values supplied by the Assistant.
_Avoid_: expression engine, history fetcher, statistics backend

**Calculator operation**:
A named arithmetic action the Calculator applies to supplied values.
_Avoid_: operator symbol, expression

**Calculator value**:
A locale-independent decimal number supplied to the Calculator, using `.` as the decimal separator.
_Avoid_: value with unit, localized number

**Calculator precision**:
An optional decimal-place limit for the Calculator result.
_Avoid_: display format, unit conversion

**Date Calculator**:
An LLM Tool that performs deterministic calendar and local-time calculations over dates supplied by the Assistant.
_Avoid_: date function, calendar plugin, time backend

**Date Calculator operation**:
A named calendar or local-time calculation the Date Calculator applies to supplied date values.
_Avoid_: function, mode, command

**Date Calculator segments**:
A comma-separated set of integer calendar/time offsets supplied to the Date Calculator, using keys such as `years`, `months`, `days`, `hours`, `minutes`, and `seconds`.
_Avoid_: object selector, duration object, date patch

**Date Calculator date**:
A local Home Assistant date-time value supplied to or returned by the Date Calculator.
_Avoid_: relative time text, timezone-suffixed timestamp, UTC-only timestamp
