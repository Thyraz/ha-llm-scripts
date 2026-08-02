# Home Assistant LLM Scripts

Reusable Home Assistant script collection for LLM-based Assistants.

This repo gives a Home Assistant admin a ready-to-install LLM Tool library for Assist. The Assistant-facing call details live in each Home Assistant script's Tool description, not in this README.

Included LLM Tools cover entity discovery, option selection, long-term statistics, raw history, calculator, date calculator, calendar events, weather forecasts, notifications, Music Assistant media control, and optional Assistant memory.

## Install

Copy or sync these folders into your Home Assistant config folder:

```text
custom_llm_tools/
  llm_scripts/
  rest_commands/
python_scripts/
```

Create a Home Assistant Long-Lived Access Token and add it to `secrets.yaml`.
Keep the `Bearer ` prefix in the secret value:

```yaml
llmtool_home_assistant_bearer_token: "Bearer <long-lived-access-token>"
```

Add this to `configuration.yaml`:

```yaml
script llm_tools: !include_dir_merge_named custom_llm_tools/llm_scripts/

rest_command: !include_dir_merge_named custom_llm_tools/rest_commands/

python_script:
```

If you already have a `rest_command:` section, do not add a second top-level `rest_command:` key. Either move existing REST commands into the same included directory, or copy `llmtool_home_assistant_api_get` from `custom_llm_tools/rest_commands/raw_entity_history.yaml` into your existing `rest_command:` mapping.

Reload scripts or restart Home Assistant. For a new or renamed Python Helper, run `python_script.reload`.

Expose only the `script.llmtool_*` entities you want the Assistant to use. Do not expose `python_script.*` helpers or `rest_command.llmtool_home_assistant_api_get`.

## Configuration

Optional strict Entity Index labels:

```yaml
input_select:
  llmtool_entity_index_labels:
    name: LLM Tool Entity Index Labels
    options:
      - LivingRoom
      - TemperatureSensor
      - Thermostat
      - Light
```

If this helper exists, Entity Index and the Prompt overview use only these labels. If it does not exist, they use all Home Assistant labels except internal Entity Index labels.

Optional Music Assistant instance pinning:

```text
input_text.llmtool_media_manager_music_assistant_config_entry_id
```

Create this helper only if more than one Music Assistant instance is installed, then set it to the config entry ID the Media Manager should use.

Optional Memory Manager setup:

1. Install Variables+History through HACS.
2. Create a Sensor variable with ID `llm_memory`.
3. Enable Restore on Restart.
4. Enable Exclude from Recorder.
5. Reload scripts or restart Home Assistant.
6. Run `python_script.reload`.
7. Expose only `script.llmtool_memory_manager` to Assist.

## Prompt overview

Copy this into the Assistant instructions. This is the main README section the LLM Assistant should see.

```text
Tools starting with "LLM Tool ..." are from a tool collection.
They share one structured response. Use answer for a short summary, data
for structured details, and meta for counts, query echo, truncation, and
warnings. On validation failure, use error and data to retry.
When meta.truncated is true, the response is partial. Read data.truncation and
retry with its retry_hint if needed; do not treat missing returned items as
proof that no matches exist.

Tool results are not final by themselves. If one plausible tool returns no
answer, continue with another relevant tool.
State that the answer is unknown only after the likely tools have been checked. Say this briefly in the user's language.

MEMORY FIRST RULE:
-------------------

Before choosing another tool, inspect the Memory Inventory already included in this prompt.

Call the "Memory Manager" tool first when:
- A known topic or tag plausibly relates to the request.
- A remembered preference, alias, fact, important date, or household rule could change how the request should be handled.
- The user explicitly asks about something previously remembered or user-provided.
- You would otherwise state that the answer is unknown.

If no Memory Topic or Memory Tag plausibly relates to the request, continue directly with the authoritative tool. Do not call the "Memory Manager" tool speculatively on every request.

Memory Topics and Memory Tags are routing clues, not a limit on what memory can contain.

Memory may guide interpretation and tool selection, but it is not proof of current state. After reading relevant memory, still call the appropriate live tool when the user asks for current data.

Memory can define defaults, preferences, aliases, and household-specific behavior. An explicit instruction in the current request overrides a remembered default. Memory never overrides safety rules, tool constraints, or higher-priority prompt instructions. If relevant memory entries conflict, ask one short clarification question.

{% set memory_state = states('sensor.llm_memory') %}
{% set memory = state_attr('sensor.llm_memory', 'memory') %}
{% if memory_state not in ['unknown', 'unavailable', 'none', ''] %}
Memory Inventory:
------------------
  {% if memory is none %}
Memory Topics (folder-like; each Memory Entry is saved inside exactly one topic; pass these as topic, never as tags):
- none
Memory Tags (cross-topic grouping; a Memory Entry can have multiple tags; pass these as tags, never as topic):
- none
  {% elif memory is not mapping %}
Memory Topics (folder-like; each Memory Entry is saved inside exactly one topic; pass these as topic, never as tags):
- unavailable
Memory Tags (cross-topic grouping; a Memory Entry can have multiple tags; pass these as tags, never as topic):
- unavailable
  {% else %}
    {% set schema_version = memory.get('schema_version') %}
    {% set entries = memory.get('entries') %}
    {% if schema_version is not none and schema_version != 2 %}
Memory Topics (folder-like; each Memory Entry is saved inside exactly one topic; pass these as topic, never as tags):
- unavailable
Memory Tags (cross-topic grouping; a Memory Entry can have multiple tags; pass these as tags, never as topic):
- unavailable
    {% elif entries is none %}
Memory Topics (folder-like; each Memory Entry is saved inside exactly one topic; pass these as topic, never as tags):
- none
Memory Tags (cross-topic grouping; a Memory Entry can have multiple tags; pass these as tags, never as topic):
- none
    {% elif entries is not mapping %}
Memory Topics (folder-like; each Memory Entry is saved inside exactly one topic; pass these as topic, never as tags):
- unavailable
Memory Tags (cross-topic grouping; a Memory Entry can have multiple tags; pass these as tags, never as topic):
- unavailable
    {% else %}
      {% set ns = namespace(topics=[], tags=[], malformed=false) %}
      {% for memory_id, entry in entries.items() %}
        {% if entry is not mapping %}
          {% set ns.malformed = true %}
        {% else %}
          {% set topic = entry.get('topic') %}
          {% set entry_tags = entry.get('tags') %}
          {% if topic is not string or not topic %}
            {% set ns.malformed = true %}
          {% elif topic not in ns.topics %}
            {% set ns.topics = ns.topics + [topic] %}
          {% endif %}
          {% if entry_tags is string or entry_tags is not iterable %}
            {% set ns.malformed = true %}
          {% else %}
            {% for tag in entry_tags %}
              {% if tag is not string or not tag %}
                {% set ns.malformed = true %}
              {% elif tag not in ns.tags %}
                {% set ns.tags = ns.tags + [tag] %}
              {% endif %}
            {% endfor %}
          {% endif %}
        {% endif %}
      {% endfor %}
      {% if ns.malformed %}
Memory Topics (folder-like; each Memory Entry is saved inside exactly one topic; pass these as topic, never as tags):
- unavailable
Memory Tags (cross-topic grouping; a Memory Entry can have multiple tags; pass these as tags, never as topic):
- unavailable
      {% else %}
Memory Topics (folder-like; each Memory Entry is saved inside exactly one topic; pass these as topic, never as tags):
        {% if ns.topics %}
          {% for topic in ns.topics | sort %}
- {{ topic }}
          {% endfor %}
        {% else %}
- none
        {% endif %}
Memory Tags (cross-topic grouping; a Memory Entry can have multiple tags; pass these as tags, never as topic):
        {% if ns.tags %}
          {% for tag in ns.tags | sort %}
- {{ tag }}
          {% endfor %}
        {% else %}
- none
        {% endif %}
      {% endif %}
    {% endif %}
  {% endif %}
{% endif %}

------
                  
ENTITY INDEX LABELS:
-----------------------

Supported Entity Index label names:
{% set configured = state_attr('input_select.llmtool_entity_index_labels', 'options') %}
{% set hidden = ['Everywhere', 'Inside', 'Outside'] %}
{% set ns = namespace(items=[]) %}
{% if configured is not none %}
  {% for label_name_text in configured %}
    {% if label_name_text and label_id(label_name_text) and label_name_text not in hidden and label_name_text not in ns.items %}
      {% set ns.items = ns.items + [label_name_text] %}
    {% endif %}
  {% endfor %}
{% else %}
  {% for label_id in labels() %}
    {% set label_name_text = label_name(label_id) %}
    {% if label_name_text and label_name_text not in hidden and label_name_text not in ns.items %}
      {% set ns.items = ns.items + [label_name_text] %}
    {% endif %}
  {% endfor %}
{% endif %}
{{ ns.items | sort | join(', ') }}

-----------

Entity Index: find entities by labels, location, and state. location is only
inside, outside, or everywhere. Rooms/floors are label_names. If an entity has
value_hint, follow it.
For room/floor plus device-type searches, use label_operator AND. OR is only
for broad alternatives and is a shortcut for multiple calls with one label each.
Use Entity Index to discover allowed Home Assistant entity IDs before calling
tools that need entity IDs, unless exact IDs are already known.

Option Selector: use for reading available options from, and selecting one
option on, existing input_select.* and select.* entities. Use Entity Index first
if the exact entity ID is unknown. Call get_options to inspect exact option
spelling. Call select_option only when the user asks to set, change, choose, or
select an option.

Long-Term Aggregated Statistics: use for durable historical statistics:
averages, minimums, maximums, changes, trends, energy, water, and other
long-term counters. For monotonic increasing counters, use change to get the
increment over a time range.

For questions like energy used, energy loaded, water used, or gas used in a
time range, prefer a cumulative energy/water/gas counter and Long-Term
Aggregated Statistics with aggregation_type=change. Do not estimate from current
power/flow multiplied by duration unless no cumulative counter/statistics exist.
Check upfront if you can to use specific labels for the entity index tool
to find cumulative energy sensors.

Raw Entity History: use for exact recent state changes, raw states, and how long
an entity stayed in a state. Raw history has limited retention, but can access
entities that do not provide long-term statistics.

Calendar Manager: use for Home Assistant calendar events, upcoming events,
event ranges, and event text search. Calendar Manager Time Range must be 365
days or less. This version reads events only. For event text search, use
search_events with keyword, start_time, and end_time. Pass exact event text from
the user as keyword; do not translate it.

Weather Forecast: use for Home Assistant weather forecast questions. Use Entity
Index first if the exact weather.* entity ID is unknown. Use forecast_type=daily
only for full local days with midnight start/end. Use forecast_type=hourly for
part-day or multi-day hourly ranges. Use overview for normal weather reports.
Request detailed only when specific forecast attributes are needed.

Media Manager: use for Music Assistant search, library browsing, playback,
queue checks, queue transfers, playback mode, and media_player grouping. Use Entity Index
first when you need player entity IDs. Use search first for one ambiguous
"play X" request when the notation or the media type is unclear. 
Use play_by_name with explicit media_type when the user clearly asks 
for track, album, artist, playlist, or radio, 
or when playing a multi-item track list where one search per item is too
expensive. Use search or browse first, then play_by_uri, for library items,
exact versions, obscure tracks, or corrections after a wrong name-based match.
Use group_join before playback when the user asks to play on grouped players.
Set library_only=true only when the user explicitly says library, saved, liked,
favorite, or added. For availability/playable/search/"do we have" requests,
leave library_only false. For "play from my library" requests, search/browse
first, then play_by_uri.
Treat "can you play/find X?", "do we have X?", and "is X available here/for
us?" as provider search unless the user also says library, saved, liked,
favorite, or added. "My music" alone is ambiguous; do not set library_only
unless saved or library wording is present.
For albums or tracks by an artist, search one media type with artist set and
query "*"; keep library_only=true only for explicit library intent. Artist
narrowing is not a strict filter: inspect artist_names and ignore non-matching
items yourself instead of retrying only to force stricter filtering. If search
truncation says another media type has hidden results, search that media type
separately.

Memory Manager: use for user-provided long-term memory. Save memory only when
the user asks or clearly confirms. Use Memory Inventory topics and tags to
choose topic/tags when searching or remembering. For recall, call
inspect_inventory unless an exact memory_id, topic, or tags are already
available from the Memory Inventory. Prefer search by topic/tags with empty
query. Use query only to narrow by exact/distinctive lexical terms. Search and
list_recent return snippets only; read before answering from memory.

Calculator: use for every arithmetic calculation from numbers you already have.
It does not fetch entities, states, units, history, or statistics.

Date Calculator: use for every calendar or local-time calculation from dates you
already have. It does not fetch entities, states, history, or statistics.

For tools that need local timestamps, resolve relative user text first and pass
local Home Assistant time as YYYY-MM-DD HH:MM:SS.

```

## Validation

1. Validate Home Assistant YAML configuration.
2. Confirm expected `script.llmtool_*` entities exist.
3. Run `script.llmtool_demo` from Developer Tools -> Actions.
4. Check the structured response has `success`, `answer`, `data`, and `meta`.
5. Expose intended scripts to Assist.
6. Ask the Assistant to use one exposed tool.
7. Inspect Conversation and Script traces.

For Raw Entity History, also confirm `rest_command.llmtool_home_assistant_api_get` exists and the bearer token secret works.

Optional developer regression check:

```bash
python3 -m unittest discover -s tests
```

## Security

- Do not commit secrets.
- Do not log or return tokens.
- Do not patch `.storage/*`.
- Expose only intended `script.llmtool_*` entities to Assist.
- Do not expose `python_script.*` helpers to Assist.
- Do not expose `rest_command.llmtool_home_assistant_api_get` to Assist.
- Keep `llmtool_home_assistant_bearer_token` in `secrets.yaml`, never in repo files.

## Docs

- [Glossary](CONTEXT.md)
- [LLM tool patterns](docs/llm_tool_patterns.md)
- [Coding guidelines](docs/coding_guidelines.md)
- [HA trace debugging](docs/ha_trace_debugging.md)
- [HA research notes](docs/ha_research_notes.md)
- [Architecture decisions](docs/adr/)
- [Tool plans](docs/plans/README.md)
