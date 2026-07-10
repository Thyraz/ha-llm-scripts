import builtins
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "python_scripts" / "llmtool_media_manager.py"


class NativeMappingWithMissingGet:
    get = None

    def __init__(self, values):
        self.values = values

    def __getitem__(self, key):
        return self.values[key]

    def __contains__(self, key):
        return key in self.values


def base_data():
    return {
        "mode": "prepare",
        "operation": "search",
        "query": "Queen",
        "search_media_types": "",
        "media_type": "",
        "artist": "",
        "album": "",
        "library_only": "",
        "favorite": "",
        "limit": "",
        "offset": "",
        "album_type": "",
        "player_entity_id": "",
        "media_uris": "",
        "play_queries": "",
        "enqueue": "",
        "radio_mode": "",
        "source_player_entity_id": "",
        "target_player_entity_id": "",
        "auto_play": "",
        "leader_entity_id": "",
        "member_entity_ids": "",
        "ungroup_first": "",
        "replace_existing": "",
        "helper_config_entry_id": "",
        "helper_config_entry_id_is_music_assistant_loaded": "",
        "music_assistant_config_entry_ids": ["ma_entry"],
        "player_entity_id_is_music_assistant": "",
        "source_player_entity_id_is_music_assistant": "",
        "target_player_entity_id_is_music_assistant": "",
        "current_group_members": [],
    }


def run_helper(overrides, restricted_builtins=None):
    data = base_data()
    data.update(overrides)
    output = {}
    exec(
        SCRIPT.read_text(),
        {
            "data": data,
            "output": output,
            "__builtins__": restricted_builtins or builtins.__dict__,
        },
    )
    return output


def shape_payload(prepared, action_response=None, restricted_builtins=None):
    return run_helper(
        {
            "mode": "shape",
            "operation": "",
            "query": "",
            "prepared": prepared,
            "action_response": action_response or {},
        },
        restricted_builtins=restricted_builtins,
    )


class MediaManagerHelperTest(unittest.TestCase):
    def test_search_defaults_types_and_builds_action(self):
        result = run_helper({})

        self.assertTrue(result["success"])
        self.assertEqual("music_assistant.search", result["data"]["action"])
        self.assertEqual("ma_entry", result["data"]["action_data"]["config_entry_id"])
        self.assertEqual(["track", "album", "artist", "playlist", "radio"], result["data"]["search_media_types"])
        self.assertEqual(20, result["data"]["limit"])
        self.assertEqual(100, result["data"]["action_data"]["limit"])

    def test_search_does_not_require_iter_builtin(self):
        restricted_builtins = builtins.__dict__.copy()
        restricted_builtins.pop("iter")

        result = run_helper(
            {
                "query": "Aura",
                "search_media_types": "track,artist",
                "limit": "10",
            },
            restricted_builtins=restricted_builtins,
        )

        self.assertTrue(result["success"])

    def test_search_shape_does_not_require_isinstance_builtin(self):
        restricted_builtins = builtins.__dict__.copy()
        restricted_builtins["isinstance"] = None
        prepared = run_helper({"query": "swr3", "search_media_types": "radio"})["data"]

        result = shape_payload(
            prepared,
            {
                "radio": [
                    {
                        "name": "SWR3",
                        "uri": "library://radio/1",
                        "media_type": "radio",
                        "favorite": True,
                    },
                    {
                        "name": "SWR3 Rock",
                        "uri": "tunein://radio/s97033",
                        "media_type": "radio",
                    },
                ],
            },
            restricted_builtins=restricted_builtins,
        )

        self.assertTrue(result["success"])
        self.assertEqual(2, result["meta"]["count"])
        self.assertEqual("library://radio/1", result["data"]["results"][0]["items"][0]["uri"])

    def test_search_shape_does_not_call_missing_get_on_native_mappings(self):
        prepared = run_helper({"query": "swr3", "search_media_types": "radio"})["data"]

        result = shape_payload(
            NativeMappingWithMissingGet(prepared),
            NativeMappingWithMissingGet(
                {
                    "radio": [
                        NativeMappingWithMissingGet(
                            {
                                "name": "SWR3",
                                "uri": "library://radio/1",
                                "media_type": "radio",
                            }
                        )
                    ]
                }
            ),
        )

        self.assertTrue(result["success"])
        self.assertEqual(1, result["meta"]["count"])
        self.assertEqual("SWR3", result["data"]["results"][0]["items"][0]["name"])

    def test_group_prepare_does_not_require_isinstance_builtin(self):
        restricted_builtins = builtins.__dict__.copy()
        restricted_builtins["isinstance"] = None

        result = run_helper(
            {
                "operation": "group_clear_members",
                "query": "",
                "leader_entity_id": "media_player.living_room",
                "current_group_members": ["media_player.living_room", "media_player.kitchen"],
            },
            restricted_builtins=restricted_builtins,
        )

        self.assertTrue(result["success"])
        self.assertEqual(["media_player.kitchen"], result["data"]["unjoin_entity_ids"])

    def test_search_resolves_helper_and_multiple_instance_soft_failures(self):
        helper = run_helper(
            {
                "helper_config_entry_id": "ma_entry",
                "helper_config_entry_id_is_music_assistant_loaded": "true",
            }
        )
        helper_without_player = run_helper(
            {
                "helper_config_entry_id": "ma_entry",
                "helper_config_entry_id_is_music_assistant_loaded": "true",
                "music_assistant_config_entry_ids": [],
            }
        )
        invalid_helper = run_helper({"helper_config_entry_id": "missing"})
        ambiguous = run_helper({"music_assistant_config_entry_ids": ["ma_one", "ma_two"]})
        missing = run_helper({"music_assistant_config_entry_ids": []})

        self.assertTrue(helper["success"])
        self.assertTrue(helper_without_player["success"])
        self.assertFalse(invalid_helper["success"])
        self.assertIn("helper", invalid_helper["error"])
        self.assertFalse(ambiguous["success"])
        self.assertIn("ambiguous", ambiguous["error"])
        self.assertFalse(missing["success"])
        self.assertIn("not seem to be installed", missing["error"])

    def test_search_validates_required_query_types_and_artist_album(self):
        missing_query = run_helper({"query": ""})
        invalid_type = run_helper({"search_media_types": "track,folder"})
        artist_for_radio = run_helper({"search_media_types": "radio", "artist": "Queen"})

        self.assertFalse(missing_query["success"])
        self.assertEqual("query", missing_query["data"]["required"])
        self.assertFalse(invalid_type["success"])
        self.assertEqual(["folder"], invalid_type["data"]["invalid_media_types"])
        self.assertFalse(artist_for_radio["success"])
        self.assertEqual(["artist", "album"], artist_for_radio["data"]["invalid_parameters"])

    def test_search_strict_parameter_allowlist(self):
        result = run_helper({"player_entity_id": "media_player.kitchen"})

        self.assertFalse(result["success"])
        self.assertEqual(["player_entity_id"], result["data"]["invalid_parameters"])
        self.assertIn("query", result["data"]["allowed_parameters"])

    def test_shape_search_global_limit_and_empty_groups(self):
        prepared = run_helper({"search_media_types": "track,album", "limit": "2"})["data"]
        response = {
            "tracks": [
                {
                    "name": "Song A",
                    "uri": "spotify://track/a",
                    "artists": [{"name": "Queen"}],
                    "album": {"name": "Album A"},
                },
                {"name": "Song B", "uri": "spotify://track/b", "version": "Live"},
                {"name": "Song C", "uri": "spotify://track/c"},
            ],
            "albums": [{"name": "Album A", "uri": "spotify://album/a"}],
        }

        result = shape_payload(prepared, response)

        self.assertTrue(result["success"])
        self.assertEqual(2, result["meta"]["count"])
        self.assertEqual(4, result["meta"]["total"])
        self.assertTrue(result["meta"]["truncated"])
        self.assertEqual(2, result["data"]["results"][0]["count"])
        self.assertEqual(0, result["data"]["results"][1]["count"])
        self.assertEqual("Queen", result["data"]["results"][0]["items"][0]["artist_names"][0])
        self.assertEqual("Album A", result["data"]["results"][0]["items"][0]["album_name"])

    def test_browse_library_validates_album_type_and_shapes_items(self):
        invalid_album_type = run_helper(
            {
                "operation": "browse_library",
                "query": "",
                "media_type": "playlist",
                "album_type": "ep",
            }
        )
        prepared = run_helper(
            {
                "operation": "browse_library",
                "query": "Dinner",
                "media_type": "playlist",
                "favorite": "true",
                "limit": "1",
            }
        )
        shaped = shape_payload(
            prepared["data"],
            {"items": [{"name": "Dinner", "uri": "spotify://playlist/dinner"}]},
        )

        self.assertFalse(invalid_album_type["success"])
        self.assertEqual(["album_type"], invalid_album_type["data"]["invalid_parameters"])
        self.assertTrue(prepared["success"])
        self.assertEqual("music_assistant.get_library", prepared["data"]["action"])
        self.assertEqual("Dinner", prepared["data"]["action_data"]["search"])
        self.assertTrue(prepared["data"]["action_data"]["favorite"])
        self.assertTrue(shaped["success"])
        self.assertEqual(1, shaped["meta"]["count"])
        self.assertTrue(shaped["meta"]["truncated"])
        self.assertEqual(1, shaped["meta"]["next_offset"])

    def test_browse_library_sends_album_type_as_list(self):
        prepared = run_helper(
            {
                "operation": "browse_library",
                "query": "",
                "media_type": "album",
                "album_type": "ep",
            }
        )

        self.assertTrue(prepared["success"])
        self.assertEqual(["ep"], prepared["data"]["action_data"]["album_type"])

    def test_play_by_uri_validates_player_media_uris_and_radio_mode(self):
        old_operation = run_helper(
            {
                "operation": "play",
                "query": "",
                "player_entity_id": "media_player.kitchen",
                "player_entity_id_is_music_assistant": "true",
                "media_uris": "spotify://track/a",
            }
        )
        invalid_player = run_helper(
            {
                "operation": "play_by_uri",
                "query": "",
                "player_entity_id": "media_player.kitchen",
                "player_entity_id_is_music_assistant": "false",
                "media_uris": "spotify://track/a",
            }
        )
        radio_many = run_helper(
            {
                "operation": "play_by_uri",
                "query": "",
                "player_entity_id": "media_player.kitchen",
                "player_entity_id_is_music_assistant": "true",
                "media_uris": "spotify://track/a\nspotify://track/b",
                "radio_mode": "true",
            }
        )
        valid = run_helper(
            {
                "operation": "play_by_uri",
                "query": "",
                "player_entity_id": "media_player.kitchen",
                "player_entity_id_is_music_assistant": "true",
                "media_uris": "spotify://track/a\nspotify://track/b",
                "enqueue": "add",
            }
        )
        shaped = shape_payload(valid["data"])

        self.assertFalse(old_operation["success"])
        self.assertIn("play_by_uri", old_operation["data"]["known_operations"])
        self.assertFalse(invalid_player["success"])
        self.assertEqual(["media_player.kitchen"], invalid_player["data"]["invalid_entity_ids"])
        self.assertFalse(radio_many["success"])
        self.assertEqual(2, radio_many["data"]["uri_count"])
        self.assertTrue(valid["success"])
        self.assertEqual(["spotify://track/a", "spotify://track/b"], valid["data"]["media_uris"])
        self.assertEqual("add", valid["data"]["action_data"]["enqueue"])
        self.assertTrue(shaped["success"])
        self.assertEqual("Sent 2 media URIs to media_player.kitchen.", shaped["answer"])

    def test_play_by_name_sends_queries_with_media_type(self):
        valid = run_helper(
            {
                "operation": "play_by_name",
                "query": "",
                "player_entity_id": "media_player.kitchen",
                "player_entity_id_is_music_assistant": "true",
                "play_queries": "Lady Gaga - Aura\nQueen - Don't Stop Me Now",
            }
        )
        shaped = shape_payload(valid["data"])

        self.assertTrue(valid["success"])
        self.assertEqual(["Lady Gaga - Aura", "Queen - Don't Stop Me Now"], valid["data"]["play_queries"])
        self.assertEqual("track", valid["data"]["media_type"])
        self.assertEqual("track", valid["data"]["action_data"]["media_type"])
        self.assertEqual(["Lady Gaga - Aura", "Queen - Don't Stop Me Now"], valid["data"]["action_data"]["media_id"])
        self.assertTrue(shaped["success"])
        self.assertEqual("Sent 2 play queries to media_player.kitchen.", shaped["answer"])
        self.assertEqual("name_based", shaped["meta"]["match_precision"])

    def test_play_by_name_validates_media_type_and_radio_mode(self):
        invalid_type = run_helper(
            {
                "operation": "play_by_name",
                "query": "",
                "player_entity_id": "media_player.kitchen",
                "player_entity_id_is_music_assistant": "true",
                "play_queries": "Lady Gaga - Aura",
                "media_type": "podcast",
            }
        )
        radio_many = run_helper(
            {
                "operation": "play_by_name",
                "query": "",
                "player_entity_id": "media_player.kitchen",
                "player_entity_id_is_music_assistant": "true",
                "play_queries": "Lady Gaga - Aura\nQueen - Don't Stop Me Now",
                "radio_mode": "true",
            }
        )

        self.assertFalse(invalid_type["success"])
        self.assertEqual(["podcast"], invalid_type["data"]["invalid_media_types"])
        self.assertFalse(radio_many["success"])
        self.assertEqual(2, radio_many["data"]["query_count"])

    def test_get_queue_and_transfer_queue(self):
        queue_prepare = run_helper(
            {
                "operation": "get_queue",
                "query": "",
                "player_entity_id": "media_player.kitchen",
                "player_entity_id_is_music_assistant": "true",
                "limit": "2",
            }
        )
        queue = shape_payload(
            queue_prepare["data"],
            {
                "media_player.kitchen": {
                    "active": True,
                    "current_index": 1,
                    "item_count": 3,
                    "items": [
                        {"name": "Before", "uri": "spotify://track/before"},
                        {"name": "Current", "uri": "spotify://track/current"},
                        {"name": "Next", "uri": "spotify://track/next"},
                    ],
                }
            },
        )
        transfer = run_helper(
            {
                "operation": "transfer_queue",
                "query": "",
                "source_player_entity_id": "media_player.kitchen",
                "source_player_entity_id_is_music_assistant": "true",
                "target_player_entity_id": "media_player.living_room",
                "target_player_entity_id_is_music_assistant": "true",
            }
        )
        transfer_no_autoplay = run_helper(
            {
                "operation": "transfer_queue",
                "query": "",
                "source_player_entity_id": "media_player.kitchen",
                "source_player_entity_id_is_music_assistant": "true",
                "target_player_entity_id": "media_player.living_room",
                "target_player_entity_id_is_music_assistant": "true",
                "auto_play": "false",
            }
        )

        self.assertTrue(queue_prepare["success"])
        self.assertTrue(queue["success"])
        self.assertEqual("Current", queue["data"]["current_item"]["name"])
        self.assertEqual("Next", queue["data"]["next_item"]["name"])
        self.assertEqual(["Current", "Next"], [item["name"] for item in queue["data"]["items"]])
        self.assertNotIn("truncated", queue["meta"])
        self.assertTrue(transfer["success"])
        self.assertTrue(transfer["data"]["auto_play"])
        self.assertFalse(transfer_no_autoplay["data"]["auto_play"])
        self.assertEqual("media_player.living_room", transfer["data"]["target_entity_id"])

    def test_group_join_removes_leader_and_dedupes_members(self):
        result = run_helper(
            {
                "operation": "group_join",
                "query": "",
                "leader_entity_id": "media_player.living_room",
                "member_entity_ids": (
                    "media_player.kitchen,media_player.living_room,"
                    "media_player.kitchen,media_player.bedroom"
                ),
            }
        )

        self.assertTrue(result["success"])
        self.assertEqual(["media_player.kitchen", "media_player.bedroom"], result["data"]["join_member_entity_ids"])
        self.assertEqual(["media_player.living_room"], result["data"]["ignored_member_entity_ids"])
        self.assertEqual(["media_player.kitchen"], result["data"]["duplicate_member_entity_ids"])

    def test_group_join_ungroup_first_and_replace_existing_dedupe_unjoins(self):
        result = run_helper(
            {
                "operation": "group_join",
                "query": "",
                "leader_entity_id": "media_player.living_room",
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

    def test_group_unjoin_and_clear_members(self):
        unjoin = run_helper(
            {
                "operation": "group_unjoin",
                "query": "",
                "member_entity_ids": "media_player.kitchen,media_player.kitchen,media_player.bedroom",
            }
        )
        clear = run_helper(
            {
                "operation": "group_clear_members",
                "query": "",
                "leader_entity_id": "media_player.living_room",
                "current_group_members": [
                    "media_player.living_room",
                    "media_player.kitchen",
                    "media_player.bedroom",
                ],
            }
        )
        shaped_clear = shape_payload(clear["data"])

        self.assertTrue(unjoin["success"])
        self.assertEqual(["media_player.kitchen", "media_player.bedroom"], unjoin["data"]["unjoin_entity_ids"])
        self.assertEqual(["media_player.kitchen"], unjoin["data"]["duplicate_member_entity_ids"])
        self.assertTrue(clear["success"])
        self.assertEqual(["media_player.kitchen", "media_player.bedroom"], clear["data"]["unjoin_entity_ids"])
        self.assertEqual("Cleared 2 media player group members.", shaped_clear["answer"])

    def test_invalid_helper_mode_returns_soft_failure(self):
        result = run_helper({"mode": "execute"})

        self.assertFalse(result["success"])
        self.assertIn("prepare", result["data"]["known_modes"])


if __name__ == "__main__":
    unittest.main()
