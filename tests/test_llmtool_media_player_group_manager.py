from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "python_scripts" / "llmtool_media_player_group_manager.py"


def run_helper(overrides):
    data = {
        "mode": "prepare",
        "operation": "join",
        "leader_entity_id": "media_player.living_room",
        "member_entity_ids": "media_player.kitchen,media_player.bedroom",
        "ungroup_first": "",
        "replace_existing": "",
        "current_group_members": [],
    }
    data.update(overrides)

    output = {}
    exec(SCRIPT.read_text(), {"data": data, "output": output})
    return output


def shape_payload(overrides):
    data = {
        "mode": "shape",
        "operation": "join",
        "leader_entity_id": "media_player.living_room",
        "join_member_entity_ids": "media_player.kitchen,media_player.bedroom",
        "unjoin_entity_ids": "",
        "previous_member_entity_ids": "",
        "ignored_member_entity_ids": "",
        "duplicate_member_entity_ids": "",
        "ungroup_first": "false",
        "replace_existing": "false",
    }
    data.update(overrides)
    return run_helper(data)


class MediaPlayerGroupManagerHelperTest(unittest.TestCase):
    def test_join_builds_action_plan(self):
        result = run_helper({})

        self.assertTrue(result["success"])
        self.assertEqual("join", result["data"]["operation"])
        self.assertEqual("media_player.living_room", result["data"]["join_leader_entity_id"])
        self.assertEqual(
            ["media_player.kitchen", "media_player.bedroom"],
            result["data"]["join_member_entity_ids"],
        )
        self.assertEqual([], result["data"]["unjoin_entity_ids"])

    def test_join_removes_leader_and_dedupes_members(self):
        result = run_helper(
            {
                "member_entity_ids": (
                    "media_player.kitchen,media_player.living_room,"
                    "media_player.kitchen,media_player.bedroom"
                )
            }
        )

        self.assertTrue(result["success"])
        self.assertEqual(
            ["media_player.kitchen", "media_player.bedroom"],
            result["data"]["join_member_entity_ids"],
        )
        self.assertEqual(["media_player.living_room"], result["data"]["ignored_member_entity_ids"])
        self.assertEqual(["media_player.kitchen"], result["data"]["duplicate_member_entity_ids"])

    def test_join_self_only_returns_soft_failure(self):
        result = run_helper({"member_entity_ids": "media_player.living_room"})

        self.assertFalse(result["success"])
        self.assertIn("different from leader_entity_id", result["error"])
        self.assertEqual(["media_player.living_room"], result["data"]["ignored_member_entity_ids"])

    def test_join_ungroup_first_and_replace_existing_dedupe_unjoins(self):
        result = run_helper(
            {
                "member_entity_ids": "media_player.kitchen,media_player.bedroom",
                "ungroup_first": "true",
                "replace_existing": "true",
                "current_group_members": [
                    "media_player.living_room",
                    "media_player.kitchen",
                    "media_player.office",
                ],
            }
        )

        self.assertTrue(result["success"])
        self.assertEqual(
            [
                "media_player.living_room",
                "media_player.kitchen",
                "media_player.bedroom",
                "media_player.office",
            ],
            result["data"]["unjoin_entity_ids"],
        )
        self.assertEqual(["media_player.kitchen", "media_player.office"], result["data"]["previous_member_entity_ids"])

    def test_invalid_operation_and_entity_ids_return_soft_failures(self):
        invalid_operation = run_helper({"operation": "group"})
        invalid_leader = run_helper({"leader_entity_id": "light.living_room"})
        invalid_member = run_helper({"member_entity_ids": "media_player.kitchen,light.kitchen"})

        self.assertFalse(invalid_operation["success"])
        self.assertIn("join", invalid_operation["data"]["known_operations"])
        self.assertFalse(invalid_leader["success"])
        self.assertEqual(["light.living_room"], invalid_leader["data"]["invalid_entity_ids"])
        self.assertFalse(invalid_member["success"])
        self.assertEqual(["light.kitchen"], invalid_member["data"]["invalid_entity_ids"])

    def test_non_join_flags_return_soft_failure(self):
        unjoin = run_helper(
            {
                "operation": "unjoin",
                "leader_entity_id": "",
                "member_entity_ids": "media_player.kitchen",
                "ungroup_first": "true",
            }
        )
        clear = run_helper(
            {
                "operation": "clear_members",
                "member_entity_ids": "",
                "replace_existing": "true",
            }
        )

        self.assertFalse(unjoin["success"])
        self.assertEqual(["ungroup_first"], unjoin["data"]["invalid_flags"])
        self.assertFalse(clear["success"])
        self.assertEqual(["replace_existing"], clear["data"]["invalid_flags"])

    def test_unjoin_requires_members_and_rejects_leader(self):
        missing = run_helper({"operation": "unjoin", "leader_entity_id": "", "member_entity_ids": ""})
        leader = run_helper({"operation": "unjoin", "leader_entity_id": "media_player.living_room"})
        valid = run_helper(
            {
                "operation": "unjoin",
                "leader_entity_id": "",
                "member_entity_ids": "media_player.kitchen,media_player.kitchen,media_player.bedroom",
            }
        )

        self.assertFalse(missing["success"])
        self.assertEqual("member_entity_ids", missing["data"]["required"])
        self.assertFalse(leader["success"])
        self.assertEqual(["leader_entity_id"], leader["data"]["invalid_parameters"])
        self.assertTrue(valid["success"])
        self.assertEqual(["media_player.kitchen", "media_player.bedroom"], valid["data"]["unjoin_entity_ids"])
        self.assertEqual(["media_player.kitchen"], valid["data"]["duplicate_member_entity_ids"])

    def test_clear_members_uses_current_non_leader_members(self):
        result = run_helper(
            {
                "operation": "clear_members",
                "member_entity_ids": "",
                "current_group_members": [
                    "media_player.living_room",
                    "media_player.kitchen",
                    "media_player.bedroom",
                ],
            }
        )

        self.assertTrue(result["success"])
        self.assertEqual(["media_player.kitchen", "media_player.bedroom"], result["data"]["unjoin_entity_ids"])
        self.assertEqual(["media_player.kitchen", "media_player.bedroom"], result["data"]["previous_member_entity_ids"])

    def test_clear_members_rejects_explicit_members(self):
        result = run_helper(
            {
                "operation": "clear_members",
                "member_entity_ids": "media_player.kitchen",
            }
        )

        self.assertFalse(result["success"])
        self.assertEqual(["member_entity_ids"], result["data"]["invalid_parameters"])

    def test_string_current_group_members_is_empty(self):
        result = run_helper(
            {
                "operation": "clear_members",
                "member_entity_ids": "",
                "current_group_members": "media_player.kitchen",
            }
        )

        self.assertTrue(result["success"])
        self.assertEqual([], result["data"]["unjoin_entity_ids"])

    def test_shape_join_response(self):
        result = shape_payload(
            {
                "unjoin_entity_ids": "media_player.office",
                "previous_member_entity_ids": "media_player.office",
                "ignored_member_entity_ids": "media_player.living_room",
                "duplicate_member_entity_ids": "media_player.kitchen",
                "replace_existing": "true",
            }
        )

        self.assertTrue(result["success"])
        self.assertEqual("Joined 2 media player group members.", result["answer"])
        self.assertEqual(["media_player.office"], result["data"]["unjoined_entity_ids"])
        self.assertEqual(["media_player.office"], result["data"]["previous_member_entity_ids"])
        self.assertEqual(["media_player.living_room"], result["data"]["ignored_member_entity_ids"])
        self.assertTrue(result["data"]["replace_existing"])

    def test_shape_unjoin_and_clear_responses(self):
        unjoin = shape_payload(
            {
                "operation": "unjoin",
                "leader_entity_id": "",
                "join_member_entity_ids": "",
                "unjoin_entity_ids": "media_player.kitchen",
            }
        )
        clear = shape_payload(
            {
                "operation": "clear_members",
                "join_member_entity_ids": "",
                "unjoin_entity_ids": "media_player.kitchen,media_player.bedroom",
                "previous_member_entity_ids": "media_player.kitchen,media_player.bedroom",
            }
        )

        self.assertTrue(unjoin["success"])
        self.assertEqual("Unjoined 1 media player.", unjoin["answer"])
        self.assertTrue(clear["success"])
        self.assertEqual("Cleared 2 media player group members.", clear["answer"])
        self.assertEqual(["media_player.kitchen", "media_player.bedroom"], clear["data"]["cleared_member_entity_ids"])

    def test_invalid_helper_mode_returns_soft_failure(self):
        result = run_helper({"mode": "execute"})

        self.assertFalse(result["success"])
        self.assertIn("prepare", result["data"]["known_modes"])


if __name__ == "__main__":
    unittest.main()
