# Notification Manager Plan

Status: implemented

Notification Manager sends a Notification message to exact Notification target
entities. v1 supports `media_player.*` targets and delivers through Home
Assistant `tts.speak`.

## Decisions

- Tool name: Notification Manager.
- Public script ID: `script.llmtool_notification_manager`.
- Public fields: `target_entity_ids`, `message`.
- `target_entity_ids` is comma-separated text and currently accepts only
  existing `media_player.*` entities.
- Room or floor targeting stays in Entity Index via `label_names`; Notification
  Manager receives exact entity IDs only.
- TTS entity selection is admin configuration. Use
  `input_text.llmtool_notification_manager_tts_entity_id` when set, otherwise
  use `tts.home_assistant_cloud` if it exists.
- If no TTS entity is configured, return a soft failure with setup details.
- No Python Helper for v1; YAML/Jinja is readable enough.
- No pause/restore logic; TTS/media integrations own queue, ducking, and jingle
  behavior.
- No ADR; this follows ADR-0001 and is easy to reverse.

## Response

Success:

```yaml
success: true
answer: Sent notification to 1 media player.
data:
  target_entity_ids:
    - media_player.kitchen
  duplicate_target_entity_ids: []
  message: Dinner is ready.
meta:
  tool: llmtool_notification_manager
  target_count: 1
  delivery: tts
```

Soft setup failure:

```yaml
success: false
error: No TTS entity configured. Ask the user to create input_text.llmtool_notification_manager_tts_entity_id with a valid tts.* entity ID, or enable tts.home_assistant_cloud.
data:
  helper_entity_id: input_text.llmtool_notification_manager_tts_entity_id
  default_tts_entity_id: tts.home_assistant_cloud
meta:
  tool: llmtool_notification_manager
```

## Validation

- Confirm `script.llmtool_notification_manager` exists after script reload.
- Configure or verify a `tts.*` entity.
- Use Entity Index to find a room media player when exact ID is unknown.
- Call Notification Manager with one exact `media_player.*` entity and a short
  message.
- Confirm the spoken result and structured response.

## Unresolved Questions

None.
