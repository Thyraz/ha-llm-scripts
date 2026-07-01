import builtins
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "python_scripts" / "llmtool_memory_manager.py"
LOCAL_TZ = timezone(timedelta(hours=2))


class FakeDtUtil:
    def __init__(self, now=None):
        self.now_value = now or datetime(2026, 6, 26, 10, 15, 0, tzinfo=LOCAL_TZ)

    def now(self):
        return self.now_value

    def as_local(self, value):
        return value.astimezone(LOCAL_TZ)


class FakeState:
    def __init__(self, attributes=None):
        self.attributes = attributes or {}


class FakeStates:
    def __init__(self, states=None):
        self.states = states or {}

    def get(self, entity_id):
        return self.states.get(entity_id)


class FakeHass:
    def __init__(self, states=None):
        self.states = FakeStates(states=states)


def entry(topic="school", tags=None, text="School starts at 08:10.", created=None, updated=None):
    return {
        "topic": topic,
        "tags": tags or ["schedule", "kid_one"],
        "text": text,
        "created_at": created or "2026-06-20 08:00:00",
        "updated_at": updated or "2026-06-20 08:00:00",
    }


def store(entries=None, next_id=None):
    entries = entries or {}
    if next_id is None:
        next_id = len(entries) + 1
    return {
        "schema_version": 2,
        "next_id": next_id,
        "entries": entries,
    }


def run_helper(overrides, memory=store(), states=None, now=None, restricted_builtins=None):
    data = {
        "operation": "status",
        "memory_id": "",
        "topic": "",
        "tags": "",
        "tag_match_mode": "",
        "query": "",
        "text": "",
        "limit": "",
    }
    data.update(overrides)

    if states is None:
        states = {"sensor.llm_memory": FakeState({"memory": memory})}

    output = {}
    exec(
        SCRIPT.read_text(),
        {
            "data": data,
            "output": output,
            "hass": FakeHass(states=states),
            "dt_util": FakeDtUtil(now=now),
            "__builtins__": restricted_builtins or builtins.__dict__,
        },
    )
    return output


class MemoryManagerHelperTest(unittest.TestCase):
    def test_missing_store_entity_returns_setup_soft_failure(self):
        result = run_helper({"operation": "status"}, states={})

        self.assertFalse(result["response"]["success"])
        self.assertIn("sensor.llm_memory", result["response"]["error"])
        self.assertFalse(result["write_required"])

    def test_missing_memory_attribute_initializes_empty_store(self):
        result = run_helper({"operation": "status"}, states={"sensor.llm_memory": FakeState({})})

        self.assertTrue(result["response"]["success"])
        self.assertTrue(result["write_required"])
        self.assertEqual(2, result["write_memory"]["schema_version"])
        self.assertEqual({}, result["write_memory"]["entries"])

    def test_malformed_memory_attribute_returns_soft_failure(self):
        result = run_helper({"operation": "status"}, memory="not a mapping")

        self.assertFalse(result["response"]["success"])
        self.assertIn("Malformed memory store", result["response"]["error"])
        self.assertFalse(result["write_required"])

    def test_invalid_operation_returns_known_operations(self):
        result = run_helper({"operation": "merge"})

        self.assertFalse(result["response"]["success"])
        self.assertIn("remember", result["response"]["data"]["known_operations"])

    def test_remember_creates_stable_id_and_normalizes_topic_tags(self):
        result = run_helper(
            {
                "operation": "remember",
                "topic": "Kid School",
                "tags": "Schedule, Kid One, schedule",
                "text": "School starts at 08:10 on regular weekdays.",
            },
            memory=store(),
        )

        response = result["response"]

        self.assertTrue(response["success"])
        self.assertTrue(result["write_required"])
        self.assertEqual("m000001", response["data"]["memory_id"])
        self.assertEqual("kid_school", response["data"]["topic"])
        self.assertEqual(["schedule", "kid_one"], response["data"]["tags"])
        self.assertEqual(2, result["write_memory"]["next_id"])
        self.assertEqual("2026-06-26 10:15:00", result["write_memory"]["entries"]["m000001"]["created_at"])

    def test_remember_validation_and_limits(self):
        missing = run_helper({"operation": "remember", "topic": "", "tags": "", "text": ""})
        large_text = run_helper(
            {
                "operation": "remember",
                "topic": "school",
                "tags": "schedule",
                "text": "x" * 4097,
            }
        )

        self.assertFalse(missing["response"]["success"])
        self.assertEqual("topic", missing["response"]["data"]["required"])
        self.assertFalse(large_text["response"]["success"])
        self.assertEqual(4096, large_text["response"]["data"]["text_limit_bytes"])

    def test_remember_rejects_hard_store_limit_and_warns_at_soft_limit(self):
        near_soft_entries = {}
        for index in range(1, 26):
            near_soft_entries["m{}".format(str(index).rjust(6, "0"))] = entry(text="x" * 3900)
        near_soft = run_helper(
            {
                "operation": "remember",
                "topic": "school",
                "tags": "schedule",
                "text": "near soft limit",
            },
            memory=store(near_soft_entries, next_id=26),
        )

        too_large_entries = {}
        for index in range(1, 32):
            too_large_entries["m{}".format(str(index).rjust(6, "0"))] = entry(text="x" * 4000)
        too_large = run_helper(
            {
                "operation": "remember",
                "topic": "school",
                "tags": "schedule",
                "text": "too large",
            },
            memory=store(too_large_entries, next_id=32),
        )

        self.assertTrue(near_soft["response"]["success"])
        self.assertIn("warning", near_soft["response"]["meta"])
        self.assertFalse(too_large["response"]["success"])
        self.assertIn("attempted_size_bytes", too_large["response"]["data"])
        self.assertFalse(too_large["write_required"])

    def test_inspect_inventory_returns_counts_and_tags(self):
        memory = store(
            {
                "m000001": entry(topic="school", tags=["schedule", "kid_one"]),
                "m000002": entry(topic="school", tags=["teacher"]),
                "m000003": entry(topic="heating", tags=["bedroom", "preference"]),
            },
            next_id=4,
        )

        result = run_helper({"operation": "inspect_inventory"}, memory=memory)

        self.assertTrue(result["response"]["success"])
        self.assertEqual("inspect_inventory", result["response"]["meta"]["operation"])
        self.assertEqual("heating", result["response"]["data"]["topics"][0]["topic"])
        self.assertEqual(2, result["response"]["meta"]["topic_count"])
        self.assertEqual(["kid_one", "schedule", "teacher"], result["response"]["data"]["topics"][1]["tags"])

    def test_search_matches_query_topic_tags_and_limit(self):
        memory = store(
            {
                "m000001": entry(topic="school", tags=["schedule", "kid_one"], text="School starts at 08:10."),
                "m000002": entry(
                    topic="school",
                    tags=["teacher", "kid_two"],
                    text="Teacher conference is next week.",
                    updated="2026-06-24 08:00:00",
                ),
                "m000003": entry(topic="heating", tags=["bedroom"], text="Bedroom prefers 19 degrees."),
            },
            next_id=4,
        )

        topic_search = run_helper({"operation": "search", "topic": "School", "limit": "1"}, memory=memory)
        tag_any = run_helper(
            {"operation": "search", "tags": "kid_one,kid_two", "tag_match_mode": "any"},
            memory=memory,
        )
        query_search = run_helper({"operation": "search", "query": "school 08:10"}, memory=memory)

        self.assertTrue(topic_search["response"]["success"])
        self.assertEqual(1, topic_search["response"]["meta"]["count"])
        self.assertEqual(2, topic_search["response"]["meta"]["total"])
        self.assertTrue(topic_search["response"]["meta"]["truncated"])
        self.assertEqual(2, tag_any["response"]["meta"]["count"])
        self.assertEqual(["m000001"], [item["memory_id"] for item in query_search["response"]["data"]["entries"]])

    def test_empty_search_returns_inventory_retry_hint(self):
        memory = store({"m000001": entry(topic="car", tags=["model"], text="The car is a Volvo XC60.")}, next_id=2)

        result = run_helper({"operation": "search", "query": "auto"}, memory=memory)

        self.assertTrue(result["response"]["success"])
        self.assertEqual([], result["response"]["data"]["entries"])
        self.assertIn("inspect_inventory", result["response"]["answer"])
        self.assertIn("hint", result["response"]["data"])
        self.assertIn("hint", result["response"]["meta"])

    def test_search_requires_scope_and_valid_tag_match_mode(self):
        broad = run_helper({"operation": "search"})
        invalid_mode = run_helper({"operation": "search", "query": "school", "tag_match_mode": "some"})

        self.assertFalse(broad["response"]["success"])
        self.assertFalse(invalid_mode["response"]["success"])
        self.assertIn("all", invalid_mode["response"]["data"]["known_tag_match_modes"])

    def test_read_returns_full_text_and_unknown_id_fails(self):
        memory = store({"m000001": entry(text="Full memory text.")}, next_id=2)

        read = run_helper({"operation": "read", "memory_id": "m000001"}, memory=memory)
        unknown = run_helper({"operation": "read", "memory_id": "m000009"}, memory=memory)

        self.assertTrue(read["response"]["success"])
        self.assertEqual("Full memory text.", read["response"]["data"]["text"])
        self.assertFalse(unknown["response"]["success"])

    def test_update_replaces_text_and_preserves_or_replaces_metadata(self):
        memory = store({"m000001": entry()}, next_id=2)

        preserved = run_helper(
            {
                "operation": "update",
                "memory_id": "m000001",
                "text": "School starts at 08:20 now.",
            },
            memory=memory,
        )
        replaced = run_helper(
            {
                "operation": "update",
                "memory_id": "m000001",
                "topic": "After School",
                "tags": "Schedule, Pickup",
                "text": "Pickup is at 16:00.",
            },
            memory=memory,
        )

        self.assertTrue(preserved["response"]["success"])
        self.assertEqual("school", preserved["write_memory"]["entries"]["m000001"]["topic"])
        self.assertEqual(["schedule", "kid_one"], preserved["write_memory"]["entries"]["m000001"]["tags"])
        self.assertEqual("after_school", replaced["write_memory"]["entries"]["m000001"]["topic"])
        self.assertEqual(["schedule", "pickup"], replaced["write_memory"]["entries"]["m000001"]["tags"])

    def test_forget_removes_entry(self):
        memory = store({"m000001": entry(), "m000002": entry(topic="heating", tags=["bedroom"])}, next_id=3)

        result = run_helper({"operation": "forget", "memory_id": "m000001"}, memory=memory)

        self.assertTrue(result["response"]["success"])
        self.assertNotIn("m000001", result["write_memory"]["entries"])
        self.assertIn("m000002", result["write_memory"]["entries"])

    def test_list_recent_returns_snippets_only(self):
        memory = store(
            {
                "m000001": entry(text="Old text " + "x" * 300, updated="2026-06-20 08:00:00"),
                "m000002": entry(text="New text", updated="2026-06-25 08:00:00"),
            },
            next_id=3,
        )

        result = run_helper({"operation": "list_recent", "limit": "1"}, memory=memory)
        first = result["response"]["data"]["entries"][0]

        self.assertTrue(result["response"]["success"])
        self.assertEqual("m000002", first["memory_id"])
        self.assertIn("snippet", first)
        self.assertNotIn("text", first)
        self.assertTrue(result["response"]["meta"]["truncated"])

    def test_status_reports_counts_and_warning_state(self):
        memory = store({"m000001": entry(), "m000002": entry(topic="heating", tags=["bedroom"])}, next_id=3)

        result = run_helper({"operation": "status"}, memory=memory)

        self.assertTrue(result["response"]["success"])
        self.assertEqual(2, result["response"]["data"]["entry_count"])
        self.assertEqual(2, result["response"]["data"]["topic_count"])
        self.assertEqual("ok", result["response"]["data"]["warning_state"])

    def test_restricted_builtins_without_dict_or_list(self):
        restricted = builtins.__dict__.copy()
        restricted.pop("dict")
        restricted.pop("list")

        result = run_helper(
            {
                "operation": "remember",
                "topic": "school",
                "tags": "schedule",
                "text": "School starts at 08:10.",
            },
            memory=store(),
            restricted_builtins=restricted,
        )

        self.assertTrue(result["response"]["success"])


if __name__ == "__main__":
    unittest.main()
