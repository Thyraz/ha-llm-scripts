from pathlib import Path
import unittest


SCRIPT_YAML = (
    Path(__file__).resolve().parents[1]
    / "custom_llm_tools"
    / "llm_scripts"
    / "notification_manager.yaml"
)


class NotificationManagerScriptTest(unittest.TestCase):
    def test_yaml_uses_ha_native_tts_without_python_helper(self):
        script_yaml = SCRIPT_YAML.read_text()

        self.assertIn("llmtool_notification_manager:", script_yaml)
        self.assertIn("action: tts.speak", script_yaml)
        self.assertIn("media_player_entity_id: \"{{ repeat.item }}\"", script_yaml)
        self.assertNotIn("python_script.llmtool_notification_manager", script_yaml)
        self.assertNotIn("logbook.log", script_yaml)

    def test_yaml_documents_entity_index_and_tts_setup(self):
        script_yaml = SCRIPT_YAML.read_text()

        self.assertIn("Use Entity Index first", script_yaml)
        self.assertIn("target_entity_ids", script_yaml)
        self.assertIn("input_text.llmtool_notification_manager_tts_entity_id", script_yaml)
        self.assertIn("tts.home_assistant_cloud", script_yaml)
        self.assertIn("No TTS entity configured", script_yaml)

    def test_yaml_returns_structured_response(self):
        script_yaml = SCRIPT_YAML.read_text()

        self.assertIn("success: true", script_yaml)
        self.assertIn("success: false", script_yaml)
        self.assertIn("response_variable: notification_manager_response", script_yaml)
        self.assertIn("tool: llmtool_notification_manager", script_yaml)
        self.assertIn("duplicate_target_entity_ids", script_yaml)


if __name__ == "__main__":
    unittest.main()
