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
        "query_mode": "all_labeled",
        "match_mode": "all",
        "verbosity": "compact",
        "state_filter": "",
        "limit": "50",
        "candidates": [],
    }
    data.update(overrides)

    output = {}
    exec(SCRIPT.read_text(), {"data": data, "output": output})
    return output


def candidate(entity_id, labels=None, visible=True, location=True):
    return {
        "entity_id": entity_id,
        "friendly_name": entity_id,
        "state": "on",
        "matched_labels": labels or [],
        "visibility_matched": visible,
        "location_matched": location,
        "domain": entity_id.split(".")[0],
    }


class EntityIndexHelperTest(unittest.TestCase):
    def test_all_labeled_inside_returns_visible_inside_entity_without_query_label(self):
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

    def test_all_labeled_everywhere_only_requires_visibility(self):
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

    def test_by_labels_requires_visibility_location_and_query_label(self):
        result = run_helper(
            {
                "labels": "Light",
                "location": "inside",
                "query_mode": "by_labels",
                "match_mode": "all",
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
        self.assertNotIn("effective_labels", result["meta"])

    def test_by_labels_any_matches_any_requested_query_label(self):
        result = run_helper(
            {
                "labels": "Light,Wohnzimmer",
                "location": "inside",
                "query_mode": "by_labels",
                "match_mode": "any",
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

    def test_internal_labels_are_rejected_as_public_query_labels(self):
        result = run_helper(
            {
                "labels": "Everywhere,Inside,Outside,Light",
                "query_mode": "by_labels",
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
        self.assertIn("Candidate records arrived as a string", result["error"])


if __name__ == "__main__":
    unittest.main()
