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

**Tool description**:
Assistant-facing text attached to one LLM Tool Script that explains how to call that tool.
_Avoid_: prompt snippet, README overview, implementation notes

**Prompt overview**:
Short Assistant prompt text that explains which LLM Tools are available and when to use each one.
_Avoid_: full tool manual, call reference, implementation notes

**Entity Index**:
An LLM Tool that lets an Assistant discover Home Assistant entities it is allowed to know about before calling other LLM Tools.
_Avoid_: entity registry dump, entity database, search backend

**Entity Index entity scope**:
The Entity Index choice between filtering by supplied `label_names` or returning all Entity Index-visible entities.
_Avoid_: query mode, search mode

**Entity Index label operator**:
The `AND` or `OR` operator that controls whether Entity Index requires all supplied `label_names` or at least one supplied `label_names` value to match.
_Avoid_: match mode, label matching mode

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

**Cumulative Sensor**:
A sensor whose current state is an accumulated total; usage over a time range is the change in that total, not the current state itself.
_Avoid_: current usage value, instant consumption, meter reading as period usage

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

**Date Calculator matching date**:
A Date Calculator date selected by matching supplied calendar and optional time parts against an anchor date.
_Avoid_: next date with segments, recurrence engine, cron expression

**Calendar Manager**:
An LLM Tool that lets an Assistant work with Home Assistant calendar events.
_Avoid_: Calendar Query Tool, calendar plugin, calendar backend

**Calendar Manager Calendar Entity ID**:
A Home Assistant `calendar.*` entity ID supplied to Calendar Manager to choose event sources.
_Avoid_: calendar name, calendar alias, calendar pseudonym

**Calendar Manager Time Range**:
A local Home Assistant time span used by Calendar Manager to query calendar events.
_Avoid_: search timeout, response timeout, calendar retention

**Calendar Manager event**:
A Home Assistant calendar event returned or managed by Calendar Manager.
_Avoid_: appointment object, reminder item, calendar row

**Calendar Manager operation**:
A named calendar-event action the Calendar Manager applies, such as reading upcoming events or searching events.
_Avoid_: function, mode, command

**Calendar Manager event type**:
A Calendar Manager filter that selects all events, all-day events, or timed events.
_Avoid_: all_day boolean, calendar state

**Media Manager**:
An LLM Tool that lets an Assistant control music playback, queues, and media player groups.
_Avoid_: Media Player Group Manager, Music Library Search, speaker group tool

**Music Assistant Instance**:
The Music Assistant server whose library and connected providers the Media Manager searches or browses.
_Avoid_: hardcoded beta ID, stable integration ID

**Music Assistant media URI**:
A Music Assistant result identifier selected from search or library results and later supplied to Media Manager `play_by_uri`.
_Avoid_: plain text play query, guessed media ID, URL, media ID

**Music Assistant play query**:
A plain-text media request supplied to Media Manager `play_by_name`, usually written as `artist - title` for track playback.
_Avoid_: Music Assistant media URI, search result, media ID

**Music Assistant Player Entity ID**:
A Home Assistant `media_player.*` entity ID belonging to Music Assistant and supplied to Media Manager playback or queue operations.
_Avoid_: speaker name, room name, raw player name

**Music Assistant queue**:
The ordered playback queue owned by a Music Assistant player.
_Avoid_: media player attributes, now-playing state blob

**Music Assistant library**:
The user's saved, liked, or added Music Assistant media collection.
_Avoid_: streaming catalog, provider search results

**Music Assistant provider search**:
A Music Assistant search across connected music providers outside the user's saved library.
_Avoid_: library search, global Home Assistant search

**Music Assistant grouped search**:
A Music Assistant search response organized by requested media types, used when the Assistant should inspect several media categories before choosing what to play.
_Avoid_: paginated library browse, single-type list

**Media Manager operation**:
A named media action the Media Manager applies, such as searching, browsing the library, playing media, reading a queue, transferring a queue, or changing media player groups.
_Avoid_: function, mode, command

**Memory Manager**:
An optional LLM Tool that lets an Assistant store, find, update, and forget user-provided long-term memory.
_Avoid_: memory database, cabinet, drawer, hyperindex

**Memory Store Entity**:
A Home Assistant entity that owns the durable memory state used by Memory Manager.
_Avoid_: storage backend, database table, variable helper

**Memory Entry**:
One remembered item in Memory Manager, with text plus organization metadata.
_Avoid_: drawer, note blob, raw text chunk

**Memory Topic**:
A broad user-meaningful area that groups Memory Entries, such as school or heating.
_Avoid_: chapter, folder, namespace

**Memory Tag**:
A short tag attached to a Memory Entry inside a Memory Topic to make retrieval more precise.
_Avoid_: Memory Label, category, Home Assistant label, entity label

**Memory Inventory**:
The available Memory Topics and Memory Tags an Assistant inspects before choosing how to search or store Memory Entries.
_Avoid_: topic list, memory dump, full memory listing

**Memory First rule**:
A tool-selection rule where an Assistant checks Memory Manager before other LLM Tools or an "I don't know" answer when a request may involve remembered user-provided knowledge.
_Avoid_: memory gate, always use memory, recall trigger

**Memory Manager operation**:
A named memory action the Memory Manager applies, such as remembering, searching, reading, updating, forgetting, inspecting inventory, listing recent entries, or reporting status.
_Avoid_: function, mode, command
