# Media Manager Plan

Status: implemented in repo and validated in Home Assistant.

## Purpose

Media Manager lets an Assistant search Music Assistant, browse the user's Music
Assistant library, play by Music Assistant media URI or by name, inspect and
transfer Music Assistant queues, set playback mode, and change Home Assistant
media player groups.

## Current decisions

- Tool name: Media Manager.
- Script ID: `llmtool_media_manager`.
- Entity after reload: `script.llmtool_media_manager`.
- Python action: `python_script.llmtool_media_manager`.
- Media Manager replaces Media Player Group Manager as a breaking change.
- Old Media Player Group Manager script, Python Helper, services entry, tests,
  README section, plan doc, and Prompt overview text are removed.
- No compatibility shim and no legacy operation aliases.
- Media Manager remains one LLM Tool so search, library browsing, playback,
  queue, queue transfer, and grouping share player and Music Assistant Instance
  language.
- Use Entity Index to find media player entity IDs. Media Manager does not add
  a player discovery operation.
- Use one Python Helper with a `mode` field:
  - `prepare` validates input and resolved Music Assistant Instance handoff
    data where needed, and builds the action plan.
  - `shape` validates and shapes Home Assistant action responses.
- The LLM Tool Script owns fields, Home Assistant state reads, Home Assistant
  action calls, and final structured response handoff.
- The LLM Tool Python Helper owns parsing, validation, action-plan shaping,
  duplicate/self handling for grouping, and response shaping.
- Music Assistant search and library actions need a Music Assistant Instance.
- Resolve the Music Assistant Instance in this order:
  1. Use `input_text.llmtool_media_manager_music_assistant_config_entry_id` when
     it exists and is non-empty.
  2. Otherwise discover loaded Music Assistant config entries from
     `media_player.*` entities using `config_entry_id()` and
     `config_entry_attr()`.
  3. If exactly one Music Assistant config entry is found, use it.
  4. If no Music Assistant config entry is found, return a soft setup failure.
  5. If multiple Music Assistant config entries are found, return a soft setup
     failure that tells the Assistant to tell the user to configure the helper.
- If the helper contains an invalid, unloaded, or non-Music-Assistant config
  entry ID, return a soft setup failure and do not auto-fallback.
- Successful Media Manager responses do not expose Music Assistant config entry
  IDs or config-entry-source metadata.
- Music Assistant Instance setup soft failures include the helper entity ID and
  a user-actionable setup message, but do not include config entry IDs in the
  Assistant-facing response.
- `play_by_uri`, `play_by_name`, `get_queue`, and `transfer_queue` use Music
  Assistant media player entities as targets and do not need a separate config
  entry ID.
- `play_by_uri`, `play_by_name`, `get_queue`, and `transfer_queue` validate
  that supplied `media_player.*` entity IDs belong to Music Assistant when Home
  Assistant template config-entry functions can determine that.
- Grouping operations accept generic Home Assistant `media_player.*` entity IDs
  and are not limited to Music Assistant players.
- Supported operations:
  - `search`
  - `browse_library`
  - `play_by_uri`
  - `play_by_name`
  - `get_queue`
  - `transfer_queue`
  - `set_playback_mode`
  - `group_join`
  - `group_unjoin`
  - `group_clear_members`
- Supported Music Assistant media types:
  - `artist`
  - `album`
  - `audiobook`
  - `playlist`
  - `podcast`
  - `track`
  - `radio`
- Do not expose Music Assistant `folder` media type in Media Manager.
- `search` uses `music_assistant.search`.
- `search` requires `query`.
- `search_media_types` is comma-separated and can include multiple media types.
- Empty `search_media_types` means `track,album,artist,playlist,radio`.
- `search` supports `library_only`.
- Use `library_only=true` only when the user explicitly says library, saved,
  liked, favorite, or added.
- Leave `library_only` false for general availability, playable, find, search,
  "do we have", "is this available here/for us", or "can you play/find"
  requests.
- "Do we have X?" and "Is X available here/for us?" mean provider search unless
  the user also says library, saved, liked, favorite, or added.
- "Can you play/find X?" means provider search unless the user also says
  library, saved, liked, favorite, or added.
- "My music" is ambiguous and is not enough for library intent by itself. "My
  Spotify" or "my music services" means connected provider context, not saved
  library.
- Empty or false `library_only` searches Music Assistant and connected
  providers; it does not exclude library items.
- `search` supports optional `artist` and `album` to make a query more precise.
  These are not strict filters and may return partial or similar artist/album
  matches.
- `search.artist` and `search.album` are valid only when `search_media_types`
  includes `track` or `album`.
- For "albums by artist" and "tracks by artist" requests, the Assistant should
  search one media type with `artist` set and `query: "*"`.
- Keep `library_only=true` with artist narrowing only for explicit library
  intent.
- The Assistant must inspect returned `artist_names` before answering from
  artist-narrowed results because `artist` is not a strict post-filter.
- The Assistant must not retry only to force stricter `artist` or `album`
  filtering; it must self-filter returned items.
- `browse_library` uses `music_assistant.get_library`.
- Use `browse_library` only for explicit library, saved, liked, favorite, or
  added media requests.
- Do not use `browse_library` for general available or playable media; use
  `search` with `library_only=false`.
- `browse_library` requires single `media_type`.
- `browse_library` uses `query` as the optional library search text and maps it
  to the Home Assistant action's `search` field.
- `browse_library` supports `favorite`, `limit`, `offset`, and `album_type`.
- `favorite=true` filters to favorite library items. Empty or false applies no
  favorite filter.
- Empty `browse_library.limit` means 20.
- Maximum `browse_library.limit` is 100.
- Empty `browse_library.offset` means 0.
- `album_type` is valid only when `operation=browse_library` and
  `media_type=album`.
- Media Manager accepts one `album_type` value and sends it to Home Assistant as
  the one-item list expected by `music_assistant.get_library`.
- `album_type` values:
  - `album`
  - `single`
  - `compilation`
  - `ep`
- Do not expose Music Assistant `unknown` album type in Media Manager.
- Search and library item shape:
  - `name`
  - `uri`
  - `media_type`
  - `version` only when non-empty
  - `artist_names` when available
  - `album_name` when available
- Do not include item `favorite`, `explicit`, or `image` fields.
- `search` `limit` is a global cap across all returned search items, not a
  per-media-type display cap.
- Empty `search.limit` means 20.
- Maximum `search.limit` is 100.
- Search result groups are emitted for every requested media type, even when
  global truncation leaves a group with no returned items.
- Search global truncation preserves requested media-type order and item order
  inside each media type.
- Search response data uses ordered result groups:
  - `data.results[].media_type`
  - `data.results[].count`
  - `data.results[].total`
  - `data.results[].items`
- Search response metadata includes:
  - `operation`
  - `query`
  - `artist` only when provided
  - `album` only when provided
  - `search_media_types`
  - `library_only`
  - `limit`
  - `count`
  - `total`
  - `count_by_media_type`
  - `total_by_media_type`
  - `truncated` when matching returned action rows exceed `limit`
- Truncated search responses add `data.truncation`, including
  `count_returned`, `count_total_before_truncation`, `limit`,
  `by_media_type`, and `retry_hint`.
- Artist- or album-narrowed search responses add `data.search_guidance`
  explaining that narrowing is not strict and the Assistant must self-filter
  returned items.
- `data.truncation.by_media_type` marks `hidden_by_global_limit: true` when a
  media type had matching returned rows but no items were returned because the
  global search limit was consumed by earlier media types.
- Browse-library response data uses:
  - `data.media_type`
  - `data.items`
- Truncated browse-library responses add `data.truncation`, including
  `count_returned`, `limit`, `next_offset`, and `retry_hint`.
- Browse-library response metadata includes:
  - `operation`
  - `query` only when provided
  - `favorite` only when provided
  - `media_type`
  - `album_type` only when provided
  - `limit`
  - `offset`
  - `next_offset`
  - `count`
  - `truncated` when returned count equals `limit`
- Do not add `truncation_possible`; use `meta.truncated` plus
  `data.truncation`.
- Use `search` first for one ambiguous "play X" request when the media type is
  unclear.
- Use `play_by_name` when the user clearly asks for a track, album, artist,
  playlist, or radio station.
- Use `play_by_name` for multi-item track lists, including user-provided or
  web-found lists, where searching once per item would be too expensive and an
  occasional wrong or missing name-based match is acceptable.
- Use `search` or `browse_library` then `play_by_uri` when the user asks for
  library items, exact versions, obscure tracks, or corrects a wrong song.
- For "play from my library/saved/favorites" requests, search or browse the
  library first, then call `play_by_uri` with selected URIs.
- For general "play X" requests, `play_by_name` is acceptable when the media
  type is clear.
- If the user says the played song is wrong after `play_by_name`, search for
  the intended item and retry with `play_by_uri`.
- `play_by_uri` and `play_by_name` use `music_assistant.play_media`.
- `play_by_uri` requires `player_entity_id`.
- `play_by_uri` requires newline-separated `media_uris` containing Music
  Assistant media URIs from prior search or library results.
- `play_by_uri` supports multiple `media_uris` and preserves order.
- `play_by_uri` accepts at most 100 media URIs.
- `play_by_uri` uses selected Music Assistant media URIs and does not expose a
  separate `media_type` field for playback.
- `play_by_name` requires `player_entity_id`.
- `play_by_name` requires newline-separated `play_queries`.
- `play_by_name` requires `media_type`.
- `play_by_name` queries should usually be written as `artist - title` for
  track playback.
- `play_by_name` supports multiple `play_queries` and sends them in one
  `music_assistant.play_media` action.
- `play_by_name` accepts at most 100 play queries.
- `play_by_name.media_type` supports `track`, `album`, `artist`, `playlist`,
  and `radio`.
- `play_by_name` does not support `library_only`; use search or
  `browse_library` then `play_by_uri` for library playback.
- `play_by_uri` and `play_by_name` support `enqueue`.
- `enqueue` values:
  - `replace`
  - `next`
  - `add`
  - `play`
- Empty `enqueue` means `replace`.
- Use `replace` for normal play requests.
- Use `add` only when the user asks to add to the queue.
- Use `next` only when the user asks to play next.
- Use `play` only for explicit Music Assistant native play behavior.
- Do not expose `replace_next`.
- `play_by_uri` and `play_by_name` support `radio_mode`.
- Empty `radio_mode` means `false`.
- `radio_mode=true` requires exactly one media URI or play query.
- Do not expose Music Assistant `username` in v1.
- `get_queue` uses `music_assistant.get_queue`.
- `get_queue` requires `player_entity_id`.
- `get_queue` is the source for "what is playing?" and "what plays next?"
  questions.
- Do not read raw media player attributes for now-playing answers.
- `get_queue` supports `limit` for returned queue items.
- Empty `get_queue.limit` means 20.
- Maximum `get_queue.limit` is 100.
- `get_queue` returns current item, next item, capped queue items, item count,
  current index, and available queue playback state fields.
- `get_queue` `items` starts with the current queue item and continues forward.
- Truncated `get_queue` responses add `data.truncation`, including
  `count_returned`, `count_total_before_truncation`, `limit`, and `retry_hint`.
- `transfer_queue` uses `music_assistant.transfer_queue`.
- `transfer_queue` requires `source_player_entity_id`.
- `transfer_queue` requires `target_player_entity_id`.
- `auto_play` is optional for `transfer_queue`.
- Empty `auto_play` means `true`.
- Media Manager intentionally rejects Music Assistant's implicit first-playing
  player behavior when `source_player` is omitted.
- `set_playback_mode` uses Home Assistant native `media_player.shuffle_set` and
  `media_player.repeat_set` actions.
- `set_playback_mode` targets one generic Home Assistant `media_player.*`
  entity ID.
- `set_playback_mode` requires at least one of `shuffle_mode` or `repeat`.
- `shuffle_mode` values:
  - `on`
  - `off`
- `repeat` values:
  - `off`
  - `all`
  - `one`
- `set_playback_mode` may set both shuffle and repeat in one operation.
- `set_playback_mode` does not verify final player state. The response reports
  the requested playback mode change.
- Media Manager does not pre-check shuffle/repeat support. Unsupported player
  failures surface as Home Assistant runtime errors in Script trace.
- Use Entity Index detailed to read current media player `shuffle` and
  `repeat` state before or after a playback mode change.
- Grouping operations use Home Assistant native `media_player.join` and
  `media_player.unjoin` actions.
- Grouping operations keep the existing Media Player Group Manager semantics.
- Media Manager does not combine grouping and playback in one operation. The
  Assistant should call a grouping operation first, then search/playback.
- `group_join` requires `leader_entity_id`.
- `group_join` requires at least one final member entity ID different from
  `leader_entity_id`.
- `group_unjoin` requires `member_entity_ids`.
- `group_clear_members` requires `leader_entity_id`.
- `group_clear_members` reads `state_attr(leader_entity_id, 'group_members')`,
  removes the leader from that list, and unjoins the remaining current members.
- `ungroup_first` and `replace_existing` are valid only for `group_join`.
- Parameters are scalar/simple values:
  - `operation`
  - `query`
  - `search_media_types`
  - `media_type`
  - `artist`
  - `album`
  - `library_only`
  - `favorite`
  - `limit`
  - `offset`
  - `album_type`
  - `player_entity_id`
  - `media_uris`
  - `play_queries`
  - `enqueue`
  - `radio_mode`
  - `shuffle_mode`
  - `repeat`
  - `source_player_entity_id`
  - `target_player_entity_id`
  - `auto_play`
  - `leader_entity_id`
  - `member_entity_ids`
  - `ungroup_first`
  - `replace_existing`
- Boolean fields accept common Home Assistant/script values:
  `true`, `on`, `yes`, and `1` mean true; `false`, `off`, `no`, `0`, and empty
  mean false.
- Invalid parameter combinations return soft failures instead of being ignored.
- Empty `search` and `browse_library` results are successful responses with
  `count: 0`.
- Unexpected Home Assistant action failures surface as runtime errors. Media
  Manager soft failures are for validation and setup issues before action calls.
- Each operation uses a strict parameter allowlist. Non-empty parameters outside
  that operation's allowlist return a soft failure with `invalid_parameters`,
  `allowed_parameters`, and `operation`.
- Operation contracts:
  - `search`: required `operation`, `query`; optional `search_media_types`,
    `artist`, `album`, `library_only`, `limit`.
  - `browse_library`: required `operation`, `media_type`; optional `query`,
    `favorite`, `limit`, `offset`, `album_type`.
  - `play_by_uri`: required `operation`, `player_entity_id`, `media_uris`;
    optional `enqueue`, `radio_mode`.
  - `play_by_name`: required `operation`, `player_entity_id`, `play_queries`,
    `media_type`; optional `enqueue`, `radio_mode`.
  - `get_queue`: required `operation`, `player_entity_id`; optional `limit`.
  - `transfer_queue`: required `operation`, `source_player_entity_id`,
    `target_player_entity_id`; optional `auto_play`.
  - `set_playback_mode`: required `operation`, `player_entity_id`, and at
    least one of `shuffle_mode`, `repeat`; optional `shuffle_mode`, `repeat`.
  - `group_join`: required `operation`, `leader_entity_id`,
    `member_entity_ids`; optional `ungroup_first`, `replace_existing`.
  - `group_unjoin`: required `operation`, `member_entity_ids`.
  - `group_clear_members`: required `operation`, `leader_entity_id`.
- Operation parameter allowlists:
  - `search`: `operation`, `query`, `search_media_types`, `artist`, `album`,
    `library_only`, `limit`
  - `browse_library`: `operation`, `query`, `media_type`, `favorite`, `limit`,
    `offset`, `album_type`
  - `play_by_uri`: `operation`, `player_entity_id`, `media_uris`, `enqueue`,
    `radio_mode`
  - `play_by_name`: `operation`, `player_entity_id`, `play_queries`,
    `media_type`, `enqueue`, `radio_mode`
  - `get_queue`: `operation`, `player_entity_id`, `limit`
  - `transfer_queue`: `operation`, `source_player_entity_id`,
    `target_player_entity_id`, `auto_play`
  - `set_playback_mode`: `operation`, `player_entity_id`, `shuffle_mode`,
    `repeat`
  - `group_join`: `operation`, `leader_entity_id`, `member_entity_ids`,
    `ungroup_first`, `replace_existing`
  - `group_unjoin`: `operation`, `member_entity_ids`
  - `group_clear_members`: `operation`, `leader_entity_id`
- No ADR for the replacement decision; this plan is enough.

## Tool description examples

- Provider search:

```yaml
operation: search
query: Bohemian Rhapsody
search_media_types: track
limit: 5
```

- Explicit library grouped search when the media type is uncertain:

```yaml
operation: search
query: Queen
search_media_types: artist,album,playlist,track
library_only: true
limit: 20
```

- Browse favorite playlists:

```yaml
operation: browse_library
media_type: playlist
favorite: true
limit: 20
offset: 0
```

- Play selected Music Assistant media URIs:

```yaml
operation: play_by_uri
player_entity_id: media_player.kitchen
media_uris: |-
  spotify://track/abc
  spotify://track/def
enqueue: replace
```

- Fast name-based playback:

```yaml
operation: play_by_name
player_entity_id: media_player.kitchen
play_queries: |-
  Lady Gaga - Aura
  Queen - Don't Stop Me Now
media_type: track
enqueue: replace
```

- Join media players before playback:

```yaml
operation: group_join
leader_entity_id: media_player.living_room
member_entity_ids: media_player.kitchen,media_player.bedroom
replace_existing: true
```

## Tool contract

Successful search:

```yaml
success: true
answer: "Found 3 media items."
data:
  results:
    - media_type: track
      count: 2
      total: 2
      items:
        - name: Bohemian Rhapsody
          uri: spotify://track/abc
          media_type: track
          artist_names:
            - Queen
          album_name: A Night at the Opera
        - name: Bohemian Rhapsody
          uri: tidal://track/def
          media_type: track
          version: Remastered 2011
          artist_names:
            - Queen
          album_name: A Night at the Opera
    - media_type: album
      count: 1
      total: 1
      items:
        - name: A Night at the Opera
          uri: spotify://album/ghi
          media_type: album
          artist_names:
            - Queen
meta:
  tool: llmtool_media_manager
  operation: search
  query: Bohemian Rhapsody
  search_media_types:
    - track
    - album
  library_only: false
  limit: 20
  count: 3
  total: 3
  count_by_media_type:
    track: 2
    album: 1
  total_by_media_type:
    track: 2
    album: 1
```

Truncated search:

```yaml
success: true
answer: "Found 20 of 36 returned media items. Attention: returned data is truncated because total matching media items (36) exceeded limit (20). Search a single media type, raise limit, or narrow with artist/album. If a media type has total > 0 but count_returned is 0, search that type separately."
data:
  results:
    - media_type: track
      count: 20
      total: 31
      items: []
    - media_type: album
      count: 0
      total: 5
      items: []
  truncation:
    truncated: true
    count_returned: 20
    count_total_before_truncation: 36
    limit: 20
    by_media_type:
      track:
        count_returned: 20
        count_total_before_truncation: 31
      album:
        count_returned: 0
        count_total_before_truncation: 5
        hidden_by_global_limit: true
    retry_hint: "Search a single media type, raise limit, or narrow with artist/album. If a media type has total > 0 but count_returned is 0, search that type separately."
meta:
  tool: llmtool_media_manager
  operation: search
  query: Queen
  search_media_types:
    - track
    - album
  library_only: false
  limit: 20
  count: 20
  total: 36
  count_by_media_type:
    track: 20
    album: 0
  total_by_media_type:
    track: 31
    album: 5
  truncated: true
```

The truncated example omits item details only to keep this plan short. Runtime
responses return the first 20 track items and the empty album group.

Successful library browse:

```yaml
success: true
answer: "Found 2 library items."
data:
  media_type: playlist
  items:
    - name: Dinner
      uri: spotify://playlist/abc
      media_type: playlist
    - name: Favorites
      uri: library://playlist/def
      media_type: playlist
meta:
  tool: llmtool_media_manager
  operation: browse_library
  media_type: playlist
  favorite: true
  limit: 20
  offset: 0
  count: 2
```

Successful URI playback:

```yaml
success: true
answer: "Sent 2 media URIs to media_player.kitchen."
data:
  player_entity_id: media_player.kitchen
  media_uris:
    - spotify://track/abc
    - spotify://track/def
  uri_count: 2
  enqueue: replace
  radio_mode: false
meta:
  tool: llmtool_media_manager
  operation: play_by_uri
  player_entity_id: media_player.kitchen
  uri_count: 2
  enqueue: replace
```

Successful name-based playback:

```yaml
success: true
answer: "Sent 2 play queries to media_player.kitchen."
data:
  player_entity_id: media_player.kitchen
  play_queries:
    - Lady Gaga - Aura
    - Queen - Don't Stop Me Now
  query_count: 2
  media_type: track
  enqueue: replace
  radio_mode: false
meta:
  tool: llmtool_media_manager
  operation: play_by_name
  player_entity_id: media_player.kitchen
  query_count: 2
  media_type: track
  enqueue: replace
  match_precision: name_based
```

Successful queue read:

```yaml
success: true
answer: "Queue has 12 media items."
data:
  player_entity_id: media_player.kitchen
  active: true
  current_index: 3
  item_count: 12
  current_item:
    name: Bohemian Rhapsody
    uri: spotify://track/abc
    media_type: track
    artist_names:
      - Queen
    album_name: A Night at the Opera
    duration_seconds: 355
    elapsed_seconds: 42
  next_item:
    name: Don't Stop Me Now
    uri: spotify://track/def
    media_type: track
    artist_names:
      - Queen
  items:
    - name: Bohemian Rhapsody
      uri: spotify://track/abc
      media_type: track
    - name: Don't Stop Me Now
      uri: spotify://track/def
      media_type: track
meta:
  tool: llmtool_media_manager
  operation: get_queue
  player_entity_id: media_player.kitchen
  limit: 20
  count: 2
  total: 12
```

Successful queue transfer:

```yaml
success: true
answer: "Transferred queue from media_player.kitchen to media_player.living_room."
data:
  source_player_entity_id: media_player.kitchen
  target_player_entity_id: media_player.living_room
  auto_play: true
meta:
  tool: llmtool_media_manager
  operation: transfer_queue
```

Successful group join:

```yaml
success: true
answer: "Joined 2 media player group members."
data:
  operation: group_join
  leader_entity_id: media_player.living_room
  joined_member_entity_ids:
    - media_player.kitchen
    - media_player.bedroom
  unjoined_entity_ids: []
  ignored_member_entity_ids: []
  duplicate_member_entity_ids: []
  ungroup_first: false
  replace_existing: true
meta:
  tool: llmtool_media_manager
  operation: group_join
  leader_entity_id: media_player.living_room
```

Validation failure:

```yaml
success: false
error: "Invalid parameters for operation."
data:
  operation: play_by_uri
  invalid_parameters:
    - query
  allowed_parameters:
    - operation
    - player_entity_id
    - media_uris
    - enqueue
    - radio_mode
meta:
  tool: llmtool_media_manager
  operation: play_by_uri
```

Music Assistant Instance setup failure:

```yaml
success: false
error: "Music Assistant instance is ambiguous. Ask the user to set input_text.llmtool_media_manager_music_assistant_config_entry_id."
data:
  helper_entity_id: input_text.llmtool_media_manager_music_assistant_config_entry_id
meta:
  tool: llmtool_media_manager
  operation: search
```

## Expected soft errors

- Invalid operation.
- Non-empty parameter outside the operation allowlist.
- Invalid boolean value.
- Invalid `limit`.
- Invalid `offset`.
- Missing Music Assistant Instance for `search` or `browse_library`.
- Multiple Music Assistant Instances for `search` or `browse_library`.
- Helper contains invalid, unloaded, or non-Music-Assistant config entry ID.
- Missing `query` for `search`.
- Invalid `search_media_types`.
- `artist` or `album` supplied when `search_media_types` does not include
  `track` or `album`.
- Missing `media_type` for `browse_library`.
- Invalid `media_type`.
- `album_type` supplied for non-`album` `browse_library`.
- Invalid `album_type`.
- Missing `player_entity_id` for playback or `get_queue`.
- Invalid `player_entity_id`.
- Non-Music-Assistant `player_entity_id` for Music Assistant playback or queue
  operations.
- Missing `media_uris` for `play_by_uri`.
- More than 100 `media_uris`.
- Missing `play_queries` for `play_by_name`.
- More than 100 `play_queries`.
- Missing `play_by_name.media_type`.
- Invalid `play_by_name.media_type`.
- Invalid `enqueue`.
- `radio_mode=true` with zero or multiple media URIs or play queries.
- Missing `source_player_entity_id` for `transfer_queue`.
- Missing `target_player_entity_id` for `transfer_queue`.
- Invalid source or target player for `transfer_queue`.
- Missing `player_entity_id` for `set_playback_mode`.
- Missing both `shuffle_mode` and `repeat` for `set_playback_mode`.
- Invalid `shuffle_mode`.
- Invalid `repeat`.
- Invalid media player entity ID for `set_playback_mode`.
- Missing `leader_entity_id` for `group_join` or `group_clear_members`.
- Missing `member_entity_ids` for `group_join` or `group_unjoin`.
- Invalid media player entity ID for grouping operations.
- `group_join` member list contains only the leader after cleanup.
- `ungroup_first` or `replace_existing` supplied outside `group_join`.

## Implementation notes

- Added `custom_llm_tools/llm_scripts/media_manager.yaml`.
- Added `python_scripts/llmtool_media_manager.py`.
- Added `llmtool_media_manager` to `python_scripts/services.yaml`.
- Added `tests/test_llmtool_media_manager.py`.
- Removed `custom_llm_tools/llm_scripts/media_player_group_manager.yaml`.
- Removed `python_scripts/llmtool_media_player_group_manager.py`.
- Removed `tests/test_llmtool_media_player_group_manager.py`.
- Removed `llmtool_media_player_group_manager` from `python_scripts/services.yaml`.
- Removed `docs/plans/implemented/media-player-group-manager.md`.
- Update README status, install/usage docs, Prompt overview, validation
  commands, and docs links.
- Keep the LLM Tool Script `mode: parallel`.
- Use `action:` syntax for all Home Assistant actions.
- Use YAML comments for non-obvious phases.
- Resolve Music Assistant Instance in YAML templates before calling the Python
  Helper for search/library action data.
- Build Music Assistant action payloads only after helper validation succeeds.
- Use Home Assistant action response variables for Music Assistant actions.
- Serialize complex action responses before Python Helper handoff.
- Keep config entry IDs out of success responses and Assistant-facing setup
  failure data.
- Keep implementation details out of Tool descriptions except where the
  Assistant must act on them.
- Do not use imports in the Python Helper.

## Test cases

- Resolves Music Assistant Instance from helper.
- Auto-resolves exactly one Music Assistant Instance from Music Assistant media
  player entities.
- Returns setup soft failure when no Music Assistant Instance is found.
- Returns setup soft failure when multiple Music Assistant Instances are found.
- Returns setup soft failure for invalid helper value without auto-fallback.
- Search validates required query.
- Search defaults `search_media_types`.
- Search validates media types.
- Search rejects `artist` or `album` when no `track` or `album` type is
  requested.
- Search applies global limit across requested media types in caller order.
- Search preserves empty result groups after truncation.
- Search returns `count`, `total`, `count_by_media_type`, and
  `total_by_media_type`.
- Browse library validates media type.
- Browse library validates limit and offset.
- Browse library validates album type only for albums.
- Browse library treats `favorite=false` as no favorite filter.
- Empty search and browse results return success with count 0.
- `play_by_uri` validates Music Assistant player entity ID.
- `play_by_uri` parses newline-separated media URIs and preserves order.
- `play_by_uri` rejects more than 100 media URIs.
- `play_by_uri` rejects `radio_mode=true` with multiple media URIs.
- `play_by_uri` returns sent-media summary without claiming playback state.
- `play_by_name` validates Music Assistant player entity ID.
- `play_by_name` parses newline-separated play queries and preserves order.
- `play_by_name` rejects more than 100 play queries.
- `play_by_name` rejects missing media type.
- `play_by_name` rejects invalid media type.
- `play_by_name` returns `match_precision: name_based` without claiming exact
  match.
- Get queue validates Music Assistant player entity ID.
- Get queue shapes current item, next item, and current-forward item list.
- Transfer queue requires source and target.
- Transfer queue rejects non-Music-Assistant source or target.
- Set playback mode accepts generic media player entity ID.
- Set playback mode supports `shuffle_mode=on|off`.
- Set playback mode supports `repeat=off|all|one`.
- Set playback mode may set shuffle and repeat in one operation.
- Set playback mode returns requested values without claiming final state.
- Strict allowlist treats `shuffle_mode=off` and `repeat=off` as explicit
  non-empty parameters.
- Group join keeps existing Media Player Group Manager duplicate, self-member,
  `ungroup_first`, and `replace_existing` behavior.
- Group unjoin keeps existing de-dupe and validation behavior.
- Group clear members keeps existing `group_members` snapshot behavior.
- Strict allowlist returns invalid-parameter soft failures for every operation.
- Unexpected Home Assistant action failures are not swallowed.

## Open questions

None.
