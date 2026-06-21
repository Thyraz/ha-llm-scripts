# Raw Entity History Uses REST Command

Status: accepted

Raw Entity History will query Home Assistant's REST history API through a user-configured `rest_command` with the access token stored in `secrets.yaml`. Home Assistant exposes raw entity history through REST and websocket APIs, but not through a documented script action; using `rest_command` keeps this project a Home Assistant script collection while avoiding direct database access or a custom integration.
