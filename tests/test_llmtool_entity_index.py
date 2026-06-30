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
    unit_of_measurement="",
    device_class="",
    state_class="",
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
    if unit_of_measurement:
        result["unit_of_measurement"] = unit_of_measurement
    if device_class:
        result["device_class"] = device_class
    if state_class:
        result["state_class"] = state_class
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


if __name__ == "__main__":
    unittest.main()
