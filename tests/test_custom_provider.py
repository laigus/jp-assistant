import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

import core.translator as translator_module
import ui.ui_config as ui_config_module
from core.prompt_manager import PromptManager
from core.translator import GrammarAnalyzer, ModelsConfig, build_openai_endpoint
from ui.settings_dialog import SettingsDialog


class FakeStreamingResponse:
    status_code = 200

    def __init__(self):
        self.closed = False

    def raise_for_status(self):
        return None

    def iter_lines(self):
        yield b'data: {"choices":[{"delta":{"content":"ok"}}]}'
        yield b"data: [DONE]"

    def close(self):
        self.closed = True


class CustomProviderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        self.models_path = root / "models_config.json"
        self.ui_path = root / "ui_config.json"
        self.models_patch = patch.object(
            translator_module, "_MODELS_CONFIG", str(self.models_path)
        )
        self.ui_patch = patch.object(
            ui_config_module, "_CONFIG_FILE", str(self.ui_path)
        )
        self.models_patch.start()
        self.ui_patch.start()
        ui_config_module.UIConfig._instance = None
        self.models_cfg = ModelsConfig()
        self.prompt_manager = PromptManager(str(root))
        self.dialogs = []

    def tearDown(self):
        for dialog in self.dialogs:
            dialog.deleteLater()
        self.app.processEvents()
        ui_config_module.UIConfig._instance = None
        self.ui_patch.stop()
        self.models_patch.stop()
        self.tempdir.cleanup()

    def make_dialog(self, models_cfg=None):
        dialog = SettingsDialog(
            self.prompt_manager, models_cfg or self.models_cfg
        )
        self.dialogs.append(dialog)
        dialog._begin_provider_edit_session()
        dialog._refresh_providers()
        return dialog

    def test_openai_endpoint_accepts_base_versioned_and_full_chat_url(self):
        self.assertEqual(
            build_openai_endpoint("https://gateway.example", "chat/completions"),
            "https://gateway.example/v1/chat/completions",
        )
        self.assertEqual(
            build_openai_endpoint("https://gateway.example/v1", "chat/completions"),
            "https://gateway.example/v1/chat/completions",
        )
        self.assertEqual(
            build_openai_endpoint(
                "https://gateway.example/api/paas/v4", "chat/completions"
            ),
            "https://gateway.example/api/paas/v4/chat/completions",
        )
        self.assertEqual(
            build_openai_endpoint(
                "https://gateway.example/v1/chat/completions", "models"
            ),
            "https://gateway.example/v1/models",
        )

    def test_add_save_use_and_remove_custom_provider(self):
        dialog = self.make_dialog()
        dialog._on_add_provider()
        custom_key = dialog.current_provider_key
        self.assertTrue(self.models_cfg.is_custom_provider(custom_key))

        dialog.provider_name_edit.setText("Custom Gateway")
        dialog.apiurl_edit.setText("https://gateway.example/v1/")
        dialog.apikey_edit.setText("test-token")
        dialog.model_combo.setEditText("model-x")
        dialog._on_save()

        stored = json.loads(self.models_path.read_text(encoding="utf-8"))
        provider = stored["providers"][custom_key]
        self.assertEqual(stored["active_provider"], custom_key)
        self.assertEqual(provider["name"], "Custom Gateway")
        self.assertEqual(provider["base_url"], "https://gateway.example/v1")
        self.assertEqual(provider["models"], ["model-x"])
        self.assertEqual(provider["default_model"], "model-x")
        self.assertNotIn(
            "selected_model",
            json.loads(self.ui_path.read_text(encoding="utf-8")),
        )

        reloaded = ModelsConfig()
        analyzer = GrammarAnalyzer(models_cfg=reloaded)
        response = FakeStreamingResponse()
        analyzer._session.post = Mock(return_value=response)
        result = analyzer.analyze("prompt")

        self.assertEqual(result, "ok")
        self.assertTrue(response.closed)
        call = analyzer._session.post.call_args
        self.assertEqual(
            call.args[0], "https://gateway.example/v1/chat/completions"
        )
        self.assertEqual(call.kwargs["json"]["model"], "model-x")
        self.assertEqual(
            call.kwargs["headers"]["Authorization"], "Bearer test-token"
        )

        remove_dialog = self.make_dialog(reloaded)
        self.assertEqual(remove_dialog.current_provider_key, custom_key)
        remove_dialog._on_remove_provider(confirm=False)
        remove_dialog._on_save()
        removed = json.loads(self.models_path.read_text(encoding="utf-8"))
        self.assertNotIn(custom_key, removed["providers"])
        self.assertEqual(removed["active_provider"], "ollama")

    def test_cancel_restores_provider_snapshot(self):
        original = json.loads(json.dumps(self.models_cfg.providers))
        dialog = self.make_dialog()
        dialog._on_add_provider()
        self.assertNotEqual(self.models_cfg.providers, original)
        dialog._restore_provider_snapshot()
        self.assertEqual(self.models_cfg.providers, original)


if __name__ == "__main__":
    unittest.main()
