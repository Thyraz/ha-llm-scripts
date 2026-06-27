# Optional Memory Manager Uses Variables+History

Status: accepted

Memory Manager will be optional and will store its data in a user-created `sensor.llm_memory` entity from the third-party Variables+History integration. This keeps the base project a Home Assistant script collection, gives memory users a Home Assistant UI editor for the store entity, and avoids adding an add-on, custom integration, shell command, or external service for v1. The trade-off is that Memory Manager is capped and local lexical search only; large or semantic memory can be revisited later without changing the core LLM Tool concept.
