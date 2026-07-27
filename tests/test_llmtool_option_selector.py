import builtins
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "python_scripts" / "llmtool_option_selector.py"
SCRIPT_YAML = Path(__file__).resolve().parents[1] / "custom_llm_tools" / "llm_scripts" / "option_selector.yaml"


class FakeState:
    def __init__(self, state="Home", attributes=None):
        self.state = state
        self.attributes = attributes or {}


class FakeStates:
    def __init__(self, states):
        self.states = states

    def get(self, entity_id):
        return self.states.get(entity_id)


class FakeHass:
    def __init__(self, states):
        self.states = FakeStates(states)


def default_states():
    return {
        "input_select.house_mode": FakeState(
            "Home",
            {
                "friendly_name": "House mode",
                "options": ["Home", "Away", "Sleep", "Guest"],
            },
        ),
        "select.program": FakeState(
            "Eco",
            {
                "friendly_name": "Washer program",
                "options": ["Eco", "Quick", "Cotton"],
            },
        ),
    }


def run_helper(overrides, states=None, restricted_builtins=None):
    data = {
        "operation": "get_options",
        "entity_id": "input_select.house_mode",
        "desired_option": "",
    }
    data.update(overrides)

    output = {}
    exec(
        SCRIPT.read_text(),
        {
            "data": data,
            "output": output,
            "hass": FakeHass(states or default_states()),
            "__builtins__": restricted_builtins or builtins.__dict__,
        },
    )
    return output


class OptionSelectorHelperTest(unittest.TestCase):
    def test_get_options_returns_current_and_all_options(self):
        result = run_helper({})

        self.assertTrue(result["success"])
        self.assertEqual("Found 4 options.", result["answer"])
        self.assertEqual("input_select.house_mode", result["data"]["entity_id"])
        self.assertEqual("input_select", result["data"]["domain"])
        self.assertEqual("House mode", result["data"]["friendly_name"])
        self.assertEqual("Home", result["data"]["current"])
        self.assertEqual(["Home", "Away", "Sleep", "Guest"], result["data"]["options"])
        self.assertEqual(4, result["meta"]["count"])

    def test_select_option_resolves_exact_option(self):
        result = run_helper({"operation": "select_option", "desired_option": "Away"})

        self.assertTrue(result["success"])
        self.assertEqual("select_option", result["meta"]["operation"])
        self.assertEqual("Home", result["data"]["previous"])
        self.assertEqual("Away", result["data"]["selected"])

    def test_select_option_resolves_case_insensitive_unique_option(self):
        result = run_helper({"operation": "select_option", "desired_option": "away"})

        self.assertTrue(result["success"])
        self.assertEqual("Away", result["data"]["selected"])

    def test_select_option_exact_match_wins_over_case_ambiguity(self):
        states = {
            "input_select.case_mode": FakeState(
                "Auto",
                {"friendly_name": "Case mode", "options": ["Auto", "auto"]},
            )
        }

        result = run_helper(
            {
                "operation": "select_option",
                "entity_id": "input_select.case_mode",
                "desired_option": "auto",
            },
            states=states,
        )

        self.assertTrue(result["success"])
        self.assertEqual("auto", result["data"]["selected"])

    def test_select_option_ambiguous_case_match_returns_allowed_options(self):
        states = {
            "input_select.case_mode": FakeState(
                "Auto",
                {"friendly_name": "Case mode", "options": ["Auto", "AUTO"]},
            )
        }

        result = run_helper(
            {
                "operation": "select_option",
                "entity_id": "input_select.case_mode",
                "desired_option": "auto",
            },
            states=states,
        )

        self.assertFalse(result["success"])
        self.assertEqual("Ambiguous option. Use exact option.", result["error"])
        self.assertEqual(["Auto", "AUTO"], result["data"]["matching_options"])
        self.assertEqual(["Auto", "AUTO"], result["data"]["allowed_options"])

    def test_select_option_unknown_option_returns_allowed_options(self):
        result = run_helper({"operation": "select_option", "desired_option": "Vacation"})

        self.assertFalse(result["success"])
        self.assertEqual("Unknown option. Use data.allowed_options and retry.", result["error"])
        self.assertEqual("Vacation", result["data"]["desired_option"])
        self.assertEqual(["Home", "Away", "Sleep", "Guest"], result["data"]["allowed_options"])

    def test_operation_contract_rejects_extra_desired_option_for_get_options(self):
        result = run_helper({"desired_option": "Away"})

        self.assertFalse(result["success"])
        self.assertEqual("Invalid parameters for operation.", result["error"])
        self.assertEqual(["desired_option"], result["data"]["invalid_parameters"])
        self.assertEqual(["operation", "entity_id"], result["data"]["allowed_parameters"])

    def test_validation_errors(self):
        invalid_operation = run_helper({"operation": "set"})
        self.assertFalse(invalid_operation["success"])
        self.assertEqual(["get_options", "select_option"], invalid_operation["data"]["known_operations"])

        missing_desired = run_helper({"operation": "select_option"})
        self.assertFalse(missing_desired["success"])
        self.assertEqual("Missing desired_option. Provide one available option.", missing_desired["error"])

        bad_domain = run_helper({"entity_id": "input_boolean.house_mode"})
        self.assertFalse(bad_domain["success"])
        self.assertEqual(["input_select", "select"], bad_domain["data"]["expected_domains"])

        unknown_entity = run_helper({"entity_id": "select.missing"})
        self.assertFalse(unknown_entity["success"])
        self.assertEqual("Unknown entity_id. Provide an existing input_select.* or select.* entity ID.", unknown_entity["error"])

    def test_existing_unknown_state_is_not_missing_entity(self):
        states = {
            "input_select.house_mode": FakeState(
                "unknown",
                {"friendly_name": "House mode", "options": ["Home", "Away"]},
            )
        }

        result = run_helper({}, states=states)

        self.assertTrue(result["success"])
        self.assertEqual("unknown", result["data"]["current"])

    def test_empty_options_returns_soft_failure(self):
        states = {
            "select.empty": FakeState(
                "unknown",
                {"friendly_name": "Empty select", "options": []},
            )
        }

        result = run_helper({"entity_id": "select.empty"}, states=states)

        self.assertFalse(result["success"])
        self.assertEqual("Entity has no selectable options.", result["error"])
        self.assertEqual([], result["data"]["options"])
        self.assertEqual("unknown", result["data"]["current"])

    def test_restricted_runtime_without_isinstance_builtin(self):
        restricted_builtins = builtins.__dict__.copy()
        restricted_builtins["isinstance"] = None

        result = run_helper({}, restricted_builtins=restricted_builtins)

        self.assertTrue(result["success"])

    def test_yaml_uses_domain_specific_select_action(self):
        script_yaml = SCRIPT_YAML.read_text()

        self.assertIn('action: "{{ option_selector_helper.data.domain }}.select_option"', script_yaml)
        self.assertIn('option: "{{ option_selector_helper.data.selected }}"', script_yaml)
