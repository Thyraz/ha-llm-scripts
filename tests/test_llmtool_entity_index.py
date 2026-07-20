from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "python_scripts" / "llmtool_entity_index.py"


def run_helper(overrides):
    data = {
        "known_labels": ["Light", "Wohnzimmer", "TemperatureSensor"],
        "visibility_label": "Everywhere",
        "inside_label": "Inside",
        "outside_label": "Outside",
        "labels": "",
        "location": "everywhere",
        "entity_scope": "all",
        "label_operator": "",
        "verbosity": "compact",
        "state_filter": "",
        "limit": "50",
        "candidates": [],
    }
    data.update(overrides)

    output = {}
    exec(SCRIPT.read_text(), {"data": data, "output": output})
    return output


def candidate(
    entity_id,
    labels=None,
    visible=True,
    location=True,
    state="on",
    display_state=None,
    unit_of_measurement="",
    device_class="",
    state_class="",
    attributes=None,
):
    result = {
        "entity_id": entity_id,
        "friendly_name": entity_id,
        "state": state,
        "matched_labels": labels or [],
        "visibility_matched": visible,
        "location_matched": location,
        "domain": entity_id.split(".")[0],
    }
    if display_state is not None:
        result["display_state"] = display_state
    if unit_of_measurement:
        result["unit_of_measurement"] = unit_of_measurement
    if device_class:
        result["device_class"] = device_class
    if state_class:
        result["state_class"] = state_class
    if attributes:
        result.update(attributes)
    return result


class EntityIndexHelperTest(unittest.TestCase):
    def test_all_scope_inside_returns_visible_inside_entity_without_query_label(self):
        result = run_helper(
            {
                "location": "inside",
                "verbosity": "id_only",
                "candidates": [
                    candidate("light.inside_visible", [], visible=True, location=True),
                    candidate("light.outside_visible", ["Light"], visible=True, location=False),
                    candidate("light.inside_hidden", ["Light"], visible=False, location=True),
                ],
            }
        )

        self.assertTrue(result["success"])
        self.assertEqual(["light.inside_visible"], result["data"]["entities"])
        self.assertNotIn("effective_labels", result["meta"])

    def test_state_filter_uses_raw_state_but_response_returns_display_state(self):
        result = run_helper(
            {
                "labels": "TemperatureSensor",
                "location": "inside",
                "entity_scope": "filtered_by_labels",
                "label_operator": "AND",
                "state_filter": "23.39",
                "candidates": [
                    candidate(
                        "sensor.room_temperature",
                        ["TemperatureSensor"],
                        visible=True,
                        location=True,
                        state="23.39",
                        display_state="23.4",
                    ),
                    candidate(
                        "sensor.other_temperature",
                        ["TemperatureSensor"],
                        visible=True,
                        location=True,
                        state="23.4",
                        display_state="23.4",
                    ),
                ],
            }
        )

        self.assertTrue(result["success"])
        self.assertEqual(1, result["meta"]["count"])
        entity = result["data"]["entities"][0]
        self.assertEqual("sensor.room_temperature", entity["entity_id"])
        self.assertEqual("23.4", entity["state"])
        self.assertEqual("23.39", result["meta"]["state_filter"])

    def test_all_scope_everywhere_only_requires_visibility(self):
        result = run_helper(
            {
                "location": "everywhere",
                "candidates": [
                    candidate("light.visible", [], visible=True, location=False),
                    candidate("light.hidden", ["Light"], visible=False, location=True),
                ],
                "verbosity": "id_only",
            }
        )

        self.assertTrue(result["success"])
        self.assertEqual(["light.visible"], result["data"]["entities"])
        self.assertNotIn("effective_labels", result["meta"])

    def test_truncated_response_includes_retry_payload(self):
        result = run_helper(
            {
                "location": "everywhere",
                "limit": "1",
                "verbosity": "id_only",
                "candidates": [
                    candidate("light.one", [], visible=True),
                    candidate("light.two", [], visible=True),
                ],
            }
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["meta"]["truncated"])
        self.assertIn("Attention: returned data is truncated", result["answer"])
        self.assertEqual(1, result["data"]["truncation"]["count_returned"])
        self.assertEqual(2, result["data"]["truncation"]["count_total_before_truncation"])
        self.assertEqual(1, result["data"]["truncation"]["limit"])

    def test_filtered_by_labels_requires_visibility_location_and_query_label(self):
        result = run_helper(
            {
                "labels": "Light",
                "location": "inside",
                "entity_scope": "filtered_by_labels",
                "label_operator": "AND",
                "verbosity": "id_only",
                "candidates": [
                    candidate("light.good", ["Light"], visible=True, location=True),
                    candidate("light.hidden", ["Light"], visible=False, location=True),
                    candidate("light.wrong_location", ["Light"], visible=True, location=False),
                    candidate("sensor.no_query_label", [], visible=True, location=True),
                ],
            }
        )

        self.assertTrue(result["success"])
        self.assertEqual(["light.good"], result["data"]["entities"])
        self.assertEqual(["Light"], result["meta"]["label_names"])
        self.assertNotIn("labels", result["meta"])
        self.assertNotIn("effective_labels", result["meta"])

    def test_filtered_by_labels_or_matches_any_requested_query_label(self):
        result = run_helper(
            {
                "labels": "Light,Wohnzimmer",
                "location": "inside",
                "entity_scope": "filtered_by_labels",
                "label_operator": "OR",
                "verbosity": "id_only",
                "candidates": [
                    candidate("light.living_room", ["Light", "Wohnzimmer"], visible=True, location=True),
                    candidate("light.other_room", ["Light"], visible=True, location=True),
                    candidate("sensor.living_room", ["Wohnzimmer"], visible=True, location=True),
                    candidate("sensor.unmatched", ["TemperatureSensor"], visible=True, location=True),
                ],
            }
        )

        self.assertTrue(result["success"])
        self.assertEqual(
            ["light.living_room", "light.other_room", "sensor.living_room"],
            result["data"]["entities"],
        )

    def test_filtered_by_labels_defaults_to_and(self):
        result = run_helper(
            {
                "labels": "Light,Wohnzimmer",
                "location": "inside",
                "entity_scope": "filtered_by_labels",
                "verbosity": "id_only",
                "candidates": [
                    candidate("light.living_room", ["Light", "Wohnzimmer"], visible=True, location=True),
                    candidate("light.other_room", ["Light"], visible=True, location=True),
                    candidate("sensor.living_room", ["Wohnzimmer"], visible=True, location=True),
                ],
            }
        )

        self.assertTrue(result["success"])
        self.assertEqual(["light.living_room"], result["data"]["entities"])
        self.assertEqual("AND", result["meta"]["label_operator"])

    def test_label_operator_is_case_insensitive(self):
        result = run_helper(
            {
                "labels": "Light,Wohnzimmer",
                "location": "inside",
                "entity_scope": "filtered_by_labels",
                "label_operator": "or",
                "verbosity": "id_only",
                "candidates": [
                    candidate("light.living_room", ["Light", "Wohnzimmer"], visible=True, location=True),
                    candidate("light.other_room", ["Light"], visible=True, location=True),
                    candidate("sensor.living_room", ["Wohnzimmer"], visible=True, location=True),
                ],
            }
        )

        self.assertTrue(result["success"])
        self.assertEqual(
            ["light.living_room", "light.other_room", "sensor.living_room"],
            result["data"]["entities"],
        )
        self.assertEqual("OR", result["meta"]["label_operator"])

    def test_internal_labels_are_rejected_as_public_query_labels(self):
        result = run_helper(
            {
                "labels": "Everywhere,Inside,Outside,Light",
                "entity_scope": "filtered_by_labels",
            }
        )

        self.assertFalse(result["success"])
        self.assertEqual(["Everywhere", "Inside", "Outside"], result["data"]["unknown_labels"])

    def test_string_candidates_return_actionable_error(self):
        result = run_helper(
            {
                "location": "inside",
                "candidates": "[{'entity_id': 'light.good'}]",
            }
        )

        self.assertFalse(result["success"])
        self.assertEqual("list", result["data"]["expected"])
        self.assertEqual("string", result["data"]["received"])
        self.assertEqual([], result["meta"]["label_names"])
        self.assertIn("Candidate records arrived as a string", result["error"])

    def test_label_names_array_shape_returns_actionable_error(self):
        result = run_helper(
            {
                "entity_scope": "filtered_by_labels",
                "label_names_invalid_shape": "true",
                "label_names_received_type": "array",
            }
        )

        self.assertFalse(result["success"])
        self.assertIn("comma-separated text", result["error"])
        self.assertEqual("label_names", result["data"]["parameter"])
        self.assertEqual("comma-separated text", result["data"]["expected"])
        self.assertEqual("array", result["data"]["received"])
        self.assertEqual("LivingRoom,Light", result["data"]["example"])

    def test_all_scope_rejects_labels_and_label_operator(self):
        labels = run_helper(
            {
                "entity_scope": "all",
                "labels": "Light",
            }
        )
        operator = run_helper(
            {
                "entity_scope": "all",
                "label_operator": "AND",
            }
        )

        self.assertFalse(labels["success"])
        self.assertIn("does not accept label_names", labels["error"])
        self.assertFalse(operator["success"])
        self.assertIn("does not accept label_operator", operator["error"])

    def test_compact_result_hints_for_cumulative_usage_sensors(self):
        result = run_helper(
            {
                "location": "inside",
                "entity_scope": "filtered_by_labels",
                "labels": "Energy",
                "known_labels": ["Energy"],
                "verbosity": "compact",
                "candidates": [
                    candidate(
                        "sensor.dishwasher_energy",
                        ["Energy"],
                        state="123.4",
                        unit_of_measurement="kWh",
                        device_class="energy",
                        state_class="total_increasing",
                    ),
                    candidate(
                        "sensor.dishwasher_power",
                        ["Energy"],
                        state="120",
                        unit_of_measurement="W",
                        device_class="power",
                        state_class="measurement",
                    ),
                ],
            }
        )

        self.assertTrue(result["success"])
        energy = result["data"]["entities"][0]
        power = result["data"]["entities"][1]

        self.assertEqual("sensor.dishwasher_energy", energy["entity_id"])
        self.assertIn("aggregation_type=change", energy["value_hint"])
        self.assertNotIn("value_hint", power)

    def test_detailed_result_adds_domain_limited_climate_fields(self):
        result = run_helper(
            {
                "location": "inside",
                "entity_scope": "filtered_by_labels",
                "labels": "TemperatureSensor",
                "verbosity": "detailed",
                "candidates": [
                    candidate(
                        "climate.thermostat",
                        ["TemperatureSensor"],
                        attributes={
                            "current_temperature": 22.4,
                            "temperature": 10,
                            "hvac_modes": ["off", "heat"],
                        },
                    ),
                    candidate(
                        "sensor.temperature",
                        ["TemperatureSensor"],
                        attributes={
                            "current_temperature": 99,
                            "temperature": 1,
                        },
                    ),
                ],
            }
        )

        self.assertTrue(result["success"])
        climate = result["data"]["entities"][0]
        sensor = result["data"]["entities"][1]

        self.assertEqual("climate.thermostat", climate["entity_id"])
        self.assertEqual(22.4, climate["current_temperature"])
        self.assertEqual(10, climate["temperature"])
        self.assertNotIn("hvac_modes", climate)
        self.assertNotIn("current_temperature", sensor)
        self.assertNotIn("temperature", sensor)

    def test_detailed_result_adds_media_player_fields_and_preserves_falsey_values(self):
        result = run_helper(
            {
                "location": "inside",
                "entity_scope": "filtered_by_labels",
                "labels": "Light",
                "verbosity": "detailed",
                "candidates": [
                    candidate(
                        "media_player.kitchen",
                        ["Light"],
                        attributes={
                            "volume_level": 0,
                            "is_volume_muted": False,
                            "media_title": "From disco to disco",
                            "media_album_name": "SWR3",
                            "shuffle": False,
                            "repeat": "off",
                            "group_members": [],
                        },
                    )
                ],
            }
        )

        self.assertTrue(result["success"])
        player = result["data"]["entities"][0]

        self.assertEqual(0, player["volume_level"])
        self.assertFalse(player["is_volume_muted"])
        self.assertEqual("From disco to disco", player["media_title"])
        self.assertEqual("SWR3", player["media_album_name"])
        self.assertFalse(player["shuffle"])
        self.assertEqual("off", player["repeat"])
        self.assertEqual([], player["group_members"])

    def test_detailed_result_omits_string_group_members(self):
        result = run_helper(
            {
                "location": "inside",
                "entity_scope": "filtered_by_labels",
                "labels": "Light",
                "verbosity": "detailed",
                "candidates": [
                    candidate(
                        "media_player.kitchen",
                        ["Light"],
                        attributes={
                            "group_members": "media_player.kitchen,media_player.office",
                        },
                    )
                ],
            }
        )

        self.assertTrue(result["success"])
        self.assertNotIn("group_members", result["data"]["entities"][0])

    def test_compact_result_omits_detailed_climate_and_media_fields(self):
        result = run_helper(
            {
                "location": "inside",
                "entity_scope": "filtered_by_labels",
                "labels": "TemperatureSensor",
                "verbosity": "compact",
                "candidates": [
                    candidate(
                        "climate.thermostat",
                        ["TemperatureSensor"],
                        attributes={
                            "current_temperature": 22.4,
                            "temperature": 10,
                            "volume_level": 0,
                        },
                    )
                ],
            }
        )

        self.assertTrue(result["success"])
        entity = result["data"]["entities"][0]
        self.assertNotIn("current_temperature", entity)
        self.assertNotIn("temperature", entity)
        self.assertNotIn("volume_level", entity)


if __name__ == "__main__":
    unittest.main()
