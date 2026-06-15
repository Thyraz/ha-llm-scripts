# HA-native LLM Tool Scripts

Status: accepted

This project will remain a Home Assistant script collection, not a custom integration. LLM Tool Scripts should use HA-native operations first, because Home Assistant already exposes scripts, templates, actions, labels, and response variables to Assist; LLM Tool Python Helpers are reserved for data shaping or handoff cases where YAML/Jinja would become hard to read. This trades some framework power for simpler installation, better user inspection, and fewer hidden moving parts.
