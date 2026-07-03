# Media Manager Plan

Status: planning.

## Purpose

Media Manager lets an Assistant search Music Assistant, browse the user's Music
Assistant library, play selected Music Assistant media URIs, inspect and
transfer Music Assistant queues, and change Home Assistant media player groups.

## Current decisions

- Tool name: Media Manager.
- Script ID: `llmtool_media_manager`.
- Entity after reload: `script.llmtool_media_manager`.
- Python action: `python_script.llmtool_media_manager`.
- Media Manager replaces Media Player Group Manager as a breaking change.
- Remove the old Media Player Group Manager script, Python Helper, services
  entry, tests, README section, plan doc, and Prompt overview text when Media
  Manager is implemented.
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
- `play`, `get_queue`, and `transfer_queue` use Music Assistant media player
  entities as targets and do not need a separate config entry ID.
- `play`, `get_queue`, and `transfer_queue` validate that supplied
  `media_player.*` entity IDs belong to Music Assistant when Home Assistant
  template config-entry functions can determine that.
- Grouping operations accept generic Home Assistant `media_player.*` entity IDs
  and are not limited to Music Assistant players.
- Supported operations:
  - `search`
  - `browse_library`
  - `play`
  - `get_queue`
  - `transfer_queue`
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
- Use `library_only=true` when the user asks for the user's Music Assistant
  library but the requested media type is uncertain.
- Empty or false `library_only` searches Music Assistant and connected
  providers; it does not exclude library items.
- `search` supports optional `artist` and `album` to make a query more precise.
  These are not strict filters.
- `search.artist` and `search.album` are valid only when `search_media_types`
  includes `track` or `album`.
- `browse_library` uses `music_assistant.get_library`.
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
- Browse-library response data uses:
  - `data.media_type`
  - `data.items`
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
- Do not add `truncation_possible`; existing tools use `meta.truncated`.
- For normal music playback, the Assistant should search or browse first, then
  pass selected Music Assistant media URIs to `play`.
- Do not document a direct plain-text playback path.
- `play` uses `music_assistant.play_media`.
- `play` requires `player_entity_id`.
- `play` requires newline-separated `media_ids` containing Music Assistant media
  URIs from prior search or library results.
- `play` supports multiple `media_ids` and preserves order.
- `play` accepts at most 100 media IDs.
- `play` uses selected Music Assistant media URIs and does not expose a
  separate `media_type` field for playback.
- `play` supports `enqueue`.
- `enqueue` values:
  - `play`
  - `replace`
  - `next`
  - `add`
- Empty `enqueue` means `play`.
- Do not expose `replace_next`.
- `play` supports `radio_mode`.
- Empty `radio_mode` means `false`.
- `radio_mode=true` requires exactly one media ID.
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
- `transfer_queue` uses `music_assistant.transfer_queue`.
- `transfer_queue` requires `source_player_entity_id`.
- `transfer_queue` requires `target_player_entity_id`.
- `auto_play` is optional for `transfer_queue`.
- Empty `auto_play` means `true`.
- Media Manager intentionally rejects Music Assistant's implicit first-playing
  player behavior when `source_player` is omitted.
- Grouping operations use Home Assistant native `media_player.join` and
  `media_player.unjoin` actions.
- Grouping operations keep the existing Media Player Group Manager semantics.
- Media Manager does not combine grouping and playback in one operation. The
  Assistant should call a grouping operation first, then search/play.
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
  - `media_ids`
  - `enqueue`
  - `radio_mode`
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
- Operation parameter allowlists:
  - `search`: `operation`, `query`, `search_media_types`, `artist`, `album`,
    `library_only`, `limit`
  - `browse_library`: `operation`, `query`, `media_type`, `favorite`, `limit`,
    `offset`, `album_type`
  - `play`: `operation`, `player_entity_id`, `media_ids`, `enqueue`,
    `radio_mode`
  - `get_queue`: `operation`, `player_entity_id`, `limit`
  - `transfer_queue`: `operation`, `source_player_entity_id`,
    `target_player_entity_id`, `auto_play`
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

- Library grouped search when the media type is uncertain:

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
operation: play
player_entity_id: media_player.kitchen
media_ids: |-
  spotify://track/abc
  spotify://track/def
enqueue: play
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
answer: "Found 20 of 36 returned media items."
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

Successful play:

```yaml
success: true
answer: "Sent 2 media items to media_player.kitchen."
data:
  player_entity_id: media_player.kitchen
  media_ids:
    - spotify://track/abc
    - spotify://track/def
  media_count: 2
  enqueue: play
  radio_mode: false
meta:
  tool: llmtool_media_manager
  operation: play
  player_entity_id: media_player.kitchen
  media_count: 2
  enqueue: play
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
  operation: play
  invalid_parameters:
    - query
  allowed_parameters:
    - operation
    - player_entity_id
    - media_ids
    - enqueue
    - radio_mode
meta:
  tool: llmtool_media_manager
  operation: play
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
- Missing `player_entity_id` for `play` or `get_queue`.
- Invalid `player_entity_id`.
- Non-Music-Assistant `player_entity_id` for Music Assistant playback or queue
  operations.
- Missing `media_ids` for `play`.
- More than 100 `media_ids`.
- Invalid `enqueue`.
- `radio_mode=true` with zero or multiple `media_ids`.
- Missing `source_player_entity_id` for `transfer_queue`.
- Missing `target_player_entity_id` for `transfer_queue`.
- Invalid source or target player for `transfer_queue`.
- Missing `leader_entity_id` for `group_join` or `group_clear_members`.
- Missing `member_entity_ids` for `group_join` or `group_unjoin`.
- Invalid media player entity ID for grouping operations.
- `group_join` member list contains only the leader after cleanup.
- `ungroup_first` or `replace_existing` supplied outside `group_join`.

## Implementation notes

- Add `custom_llm_tools/llm_scripts/media_manager.yaml`.
- Add `python_scripts/llmtool_media_manager.py`.
- Add `llmtool_media_manager` to `python_scripts/services.yaml`.
- Add `tests/test_llmtool_media_manager.py`.
- Remove `custom_llm_tools/llm_scripts/media_player_group_manager.yaml`.
- Remove `python_scripts/llmtool_media_player_group_manager.py`.
- Remove `tests/test_llmtool_media_player_group_manager.py`.
- Remove `llmtool_media_player_group_manager` from `python_scripts/services.yaml`.
- Remove `docs/plans/implemented/media-player-group-manager.md`.
- Update README status, install/usage docs, Prompt overview, validation
  commands, and docs links.
- Keep the LLM Tool Script `mode: queued` and `max: 2`.
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
- Play validates Music Assistant player entity ID.
- Play parses newline-separated media IDs and preserves order.
- Play rejects more than 100 media IDs.
- Play rejects `radio_mode=true` with multiple media IDs.
- Play returns sent-media summary without claiming playback state.
- Get queue validates Music Assistant player entity ID.
- Get queue shapes current item, next item, and current-forward item list.
- Transfer queue requires source and target.
- Transfer queue rejects non-Music-Assistant source or target.
- Group join keeps existing Media Player Group Manager duplicate, self-member,
  `ungroup_first`, and `replace_existing` behavior.
- Group unjoin keeps existing de-dupe and validation behavior.
- Group clear members keeps existing `group_members` snapshot behavior.
- Strict allowlist returns invalid-parameter soft failures for every operation.
- Unexpected Home Assistant action failures are not swallowed.

## Open questions

None.
