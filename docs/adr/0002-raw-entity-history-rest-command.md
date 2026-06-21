# LLM Tools Use a Shared Home Assistant API GET Command

Status: accepted

LLM Tools that need Home Assistant REST API reads will use the shared GET-only `rest_command.llmtool_home_assistant_api_get`, with the bearer token stored in `secrets.yaml`. Raw Entity History needs this because Home Assistant exposes raw entity history through REST and websocket APIs, but not through a documented script action; a shared GET command keeps this project a Home Assistant script collection while avoiding direct database access, a custom integration, or a growing set of one-off REST commands.
