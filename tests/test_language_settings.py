import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Preserve the application's ONNX-before-Qt import order on Windows.
import onnxruntime  # noqa: F401
from PyQt6.QtWidgets import QApplication, QLabel

import core.translator as translator_module
import core.vocab as vocab_module
import ui.ui_config as ui_config_module
from core.languages import LANGUAGES, LanguageConfig
from core.prompt_manager import DEFAULT_PROMPTS, PromptManager
from core.translator import ModelsConfig
from core.tts import TextToSpeech
from core.vocab import VocabManager, VocabEntry
from ui.main_window import MainWindow, OcrWorker
from ui.icons import language_icon
from ui.settings_dialog import SettingsDialog
from ui.vocab_window import VocabWindow
from ui.widgets import ArrowComboBox
from app_info import APP_NAME, APP_ID, ICON_PATH
from assets.create_icon import ICON_SIZES


class LanguageSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.patches = [
            patch.object(translator_module, "_MODELS_CONFIG", str(self.root / "models_config.json")),
            patch.object(ui_config_module, "_CONFIG_FILE", str(self.root / "ui_config.json")),
            patch.object(vocab_module, "_VOCAB_FILE", str(self.root / "vocabulary.json")),
        ]
        for item in self.patches:
            item.start()
        ui_config_module.UIConfig._instance = None
        self.config = LanguageConfig(str(self.root))
        self.prompts = PromptManager(str(self.root))
        self.dialog = SettingsDialog(self.prompts, ModelsConfig(), self.config)
        self.dialog._begin_provider_edit_session()
        self.dialog._refresh_providers()
        self.page = self.dialog.language_page

    def tearDown(self):
        self.dialog.close()
        self.dialog.deleteLater()
        self.app.processEvents()
        ui_config_module.UIConfig._instance = None
        for item in reversed(self.patches):
            item.stop()
        self.tempdir.cleanup()

    def test_navigation_and_language_drafts_save_independently(self):
        for combo in (self.page.language_combo, self.page.ocr_combo, self.page.voice_combo):
            self.assertIsInstance(combo, ArrowComboBox)
        self.assertEqual(self.dialog.pages.count(), 2)
        self.dialog.navigation.setCurrentRow(1)
        self.assertEqual(self.dialog.pages.currentIndex(), 1)
        self.page.prompt_edit.setPlainText("JA::{text}")
        self.page.language_combo.setCurrentIndex(self.page.language_combo.findData("en"))
        self.page.prompt_edit.setPlainText("EN::{text}")
        self.page.voice_combo.setCurrentText("en-GB-SoniaNeural")
        self.page.rate_spin.setValue(-20)
        self.dialog.navigation.setCurrentRow(0)
        self.dialog.navigation.setCurrentRow(1)
        self.assertEqual(self.page.prompt_edit.toPlainText(), "EN::{text}")
        self.page.language_combo.setCurrentIndex(0)
        self.assertEqual(self.page.prompt_edit.toPlainText(), "JA::{text}")
        self.assertEqual(self.config.active_language, "ja")
        self.dialog._on_save()
        reloaded = LanguageConfig(str(self.root))
        self.assertEqual(reloaded.active_language, "ja")
        self.assertEqual(reloaded.profile("en")["voice"], "en-GB-SoniaNeural")
        self.assertEqual(reloaded.profile("en")["rate"], -20)
        self.assertEqual(PromptManager(str(self.root)).prompts, {"ja": "JA::{text}", "en": "EN::{text}"})

    def test_cancel_and_reset_do_not_change_other_language(self):
        self.page.prompt_edit.setPlainText("Draft::{text}")
        self.page.language_combo.setCurrentIndex(1)
        self.page.prompt_edit.setPlainText("English draft::{text}")
        self.page._reset_prompt()
        self.assertEqual(self.page.prompt_edit.toPlainText(), DEFAULT_PROMPTS["en"])
        self.page.language_combo.setCurrentIndex(0)
        self.assertEqual(self.page.prompt_edit.toPlainText(), "Draft::{text}")
        self.dialog.close()
        self.page.load()
        self.assertEqual(self.page.prompt_edit.toPlainText(), DEFAULT_PROMPTS["ja"])
        self.assertEqual(self.prompts.prompts, DEFAULT_PROMPTS)
        self.assertFalse((self.root / "languages.json").exists())

    def test_voice_refresh_keeps_selection_and_filters_by_language(self):
        self.page.language_combo.setCurrentIndex(1)
        self.page.voice_combo.setCurrentText("en-GB-SoniaNeural")
        self.page._on_voices([{"ShortName": "en-AU-TestNeural", "Locale": "en-AU"},
                              {"ShortName": "ja-JP-TestNeural", "Locale": "ja-JP"}])
        self.assertEqual(self.page.voice_combo.currentText(), "en-GB-SoniaNeural")
        self.assertGreaterEqual(self.page.voice_combo.findText("en-AU-TestNeural"), 0)
        self.assertEqual(self.page.voice_combo.findText("ja-JP-TestNeural"), -1)

    def test_existing_user_prompt_is_preserved_in_new_schema(self):
        path = self.root / "prompts.json"
        path.write_text(json.dumps({"system_prompt": "USER::{text}"}), encoding="utf-8")
        prompts = PromptManager(str(self.root))
        self.assertEqual(prompts.prompts["ja"], "USER::{text}")
        prompts.save()
        self.assertEqual(set(json.loads(path.read_text(encoding="utf-8"))), {"prompts"})

    def test_language_and_voice_cache_isolation(self):
        target = SimpleNamespace(language_config=self.config, language="ja")
        ja_key = MainWindow._tts_key(target, "same")
        target.language = "en"
        en_key = MainWindow._tts_key(target, "same")
        self.assertNotEqual(ja_key, en_key)
        changed = self.config.profile("en")
        changed["rate"] = -10
        self.config.set_profile("en", changed)
        self.assertNotEqual(en_key, MainWindow._tts_key(target, "same"))
        target._context_id = 2
        callback = Mock()
        MainWindow._deliver(target, 1, callback, "stale")
        callback.assert_not_called()
        MainWindow._deliver(target, 2, callback, "current")
        callback.assert_called_once_with("current")

    def test_ocr_worker_snapshots_profile(self):
        engine = Mock()
        engine.recognize.return_value = "Hello"
        profile = self.config.profile("en")
        worker = OcrWorker(engine, "image", profile)
        profile["ocr_locale"] = "ja-JP"
        worker.run()
        self.assertEqual(engine.recognize.call_args.args[1]["ocr_locale"], "en-US")

    def test_main_window_switches_language_and_drops_previous_results(self):
        with (patch("ui.main_window.DATA_DIR", str(self.root)),
              patch.object(MainWindow, "_load_models_async")):
            window = MainWindow(ocr_engine=Mock())
        try:
            self.assertFalse(hasattr(window, "language_combo"))
            self.assertNotIn("学习语言", [label.text() for label in window.findChildren(QLabel)])
            self.assertEqual(list(window.language_buttons), list(LANGUAGES))
            self.assertTrue(window.language_group.exclusive())
            self.assertTrue(window.language_buttons["ja"].isChecked())
            self.assertFalse(window.language_buttons["en"].isChecked())
            row = window.layout().itemAt(1).layout()
            for index, (key, button) in enumerate(window.language_buttons.items()):
                self.assertIs(row.itemAt(index).widget(), button)
                self.assertEqual(button.text(), "")
                self.assertFalse(button.icon().isNull())
                self.assertEqual((button.width(), button.height()), (36, 32))
                self.assertEqual(button.toolTip(), LANGUAGES[key].name)
                self.assertEqual(button.accessibleName(), f"学习{LANGUAGES[key].name}")
            window.ocr_text.setPlainText("previous text")
            window.temp_prompt_edit.setPlainText("previous instruction")
            window._last_md = "previous analysis"
            token = window._context_id
            window.language_buttons["en"].click()
            self.assertEqual(window.language, "en")
            self.assertTrue(window.language_buttons["en"].isChecked())
            self.assertFalse(window.language_buttons["ja"].isChecked())
            self.assertEqual(window.ocr_text.toPlainText(), "")
            self.assertEqual(window.temp_prompt_edit.toPlainText(), "")
            self.assertEqual(window._last_md, "")
            callback = Mock()
            window._deliver(token, callback, "late Japanese result")
            callback.assert_not_called()
            self.assertEqual(LanguageConfig(str(self.root)).active_language, "en")
            window.ocr_engine.preload.assert_called_with(window.language_config.profile("en"))
            window.ocr_text.setPlainText("keep current text")
            window.temp_prompt_edit.setPlainText("keep current instruction")
            current_token = window._context_id
            window.language_buttons["en"].click()
            self.assertTrue(window.language_buttons["en"].isChecked())
            self.assertEqual(window._context_id, current_token)
            self.assertEqual(window.ocr_text.toPlainText(), "keep current text")
            self.assertEqual(window.temp_prompt_edit.toPlainText(), "keep current instruction")
            window.language_buttons["ja"].click()
            self.assertEqual(window.language, "ja")
            self.assertTrue(window.language_buttons["ja"].isChecked())
            self.assertFalse(window.language_buttons["en"].isChecked())
            self.assertEqual(window.ocr_text.toPlainText(), "")
        finally:
            window.close()
            window.deleteLater()

    def test_main_window_uses_shared_branding_and_hamster_icon(self):
        from PIL import Image
        self.assertEqual(APP_NAME, "耗耗语言助手")
        with Image.open(ICON_PATH) as artwork:
            self.assertEqual(artwork.format, "ICO")
            self.assertEqual(artwork.ico.sizes(), {(size, size) for size in ICON_SIZES})
            for size in ICON_SIZES:
                frame = artwork.ico.getimage((size, size)).convert("RGBA")
                for point in ((0, 0), (size - 1, 0), (0, size - 1), (size - 1, size - 1)):
                    self.assertEqual(frame.getpixel(point)[3], 0)
                self.assertGreaterEqual(frame.getpixel((size // 2, size // 2))[3], 250)
        with (patch("ui.main_window.DATA_DIR", str(self.root)),
              patch.object(MainWindow, "_load_models_async")):
            window = MainWindow(ocr_engine=Mock())
        try:
            self.assertEqual(window.windowTitle(), APP_NAME)
            self.assertEqual(window.findChild(QLabel, "titleLabel").text(), APP_NAME)
            self.assertFalse(window.windowIcon().isNull())
            badge = window.layout().itemAt(0).layout().itemAt(0).widget()
            self.assertFalse(badge.pixmap().isNull())
            self.assertEqual((badge.width(), badge.height()), (24, 24))
        finally:
            window.close()
            window.deleteLater()

    def test_startup_registers_application_name_icon_and_windows_identity(self):
        import main as entry
        app = Mock()
        app.exec.return_value = 0
        with (patch.object(entry, "_setup_logging"),
              patch.object(entry.sys, "excepthook"),
              patch.object(entry, "QApplication", return_value=app),
              patch.object(entry, "OCRService"),
              patch.object(entry, "MainWindow"),
              patch.object(entry, "HotkeyBridge"),
              patch.object(entry.keyboard, "add_hotkey"),
              patch.object(entry.keyboard, "remove_hotkey"),
              patch.object(entry.ctypes.windll.shell32,
                           "SetCurrentProcessExplicitAppUserModelID") as identify):
            with self.assertRaises(SystemExit) as stopped:
                entry.main()
        self.assertEqual(stopped.exception.code, 0)
        identify.assert_called_once_with(APP_ID)
        app.setApplicationName.assert_called_once_with(APP_NAME)
        app.setApplicationDisplayName.assert_called_once_with(APP_NAME)
        self.assertFalse(app.setWindowIcon.call_args.args[0].isNull())

    def test_main_window_language_icons_restore_selection_and_refresh_theme(self):
        self.config.active_language = "en"
        self.config.save()
        with (patch("ui.main_window.DATA_DIR", str(self.root)),
              patch.object(MainWindow, "_load_models_async"),
              patch("ui.main_window.enable_acrylic"),
              patch("ui.main_window.disable_acrylic")):
            window = MainWindow(ocr_engine=Mock())
            try:
                self.assertEqual(window.language, "en")
                selected = window.language_buttons["en"]
                self.assertTrue(selected.isChecked())
                self.assertFalse(window.language_buttons["ja"].isChecked())
                cfg = ui_config_module.UIConfig()
                cfg.acrylic_enabled = False
                keys = []
                for theme in ("dark", "light"):
                    cfg.theme = theme
                    window._reapply_appearance()
                    keys.append(selected.icon().cacheKey())
                    self.assertTrue(selected.isChecked())
                    self.assertIn("QPushButton#languageBtn:checked", window.styleSheet())
                self.assertNotEqual(*keys)
                self.assertEqual(window._context_id, 0)
                self.assertEqual(LanguageConfig(str(self.root)).active_language, "en")
            finally:
                window.close()
                window.deleteLater()

    def test_language_icons_render_badges_and_unknown_language_fallback(self):
        for key in (*LANGUAGES, "future-language"):
            with self.subTest(language=key):
                image = language_icon(key).pixmap(20, 20).toImage()
                self.assertTrue(any(image.pixelColor(x, y).alpha() > 0
                                    for x in range(20) for y in range(20)))

    def test_validation_prevents_partial_language_save(self):
        self.page.language_combo.setCurrentIndex(1)
        self.page.prompt_edit.setPlainText("missing input placeholder")
        with patch("ui.settings_dialog.QMessageBox.warning") as warning:
            self.dialog._on_save()
        warning.assert_called_once()
        self.assertEqual(self.dialog.pages.currentIndex(), 1)
        self.assertEqual(self.prompts.prompts, DEFAULT_PROMPTS)
        self.assertFalse((self.root / "languages.json").exists())

    def test_edge_tts_keeps_engine_and_passes_voice_and_rate(self):
        # No audio file or network request is needed to verify the Edge contract.
        from unittest.mock import AsyncMock
        target = TextToSpeech.__new__(TextToSpeech)
        import asyncio
        communicate = Mock()
        communicate.save = AsyncMock()
        with (patch("core.tts.edge_tts.Communicate", return_value=communicate) as create,
              patch("core.tts._resolve_proxy", return_value=None)):
            asyncio.run(target._synthesize("Hello", "output.mp3", "en-US-JennyNeural", -20))
        create.assert_called_once_with("Hello", "en-US-JennyNeural", rate="-20%", proxy=None)
        communicate.save.assert_awaited_once_with("output.mp3")

    def test_vocabulary_dedup_and_historical_language(self):
        vocab = VocabManager()
        vocab.add("same", "Japanese", language="ja")
        vocab.add("same", "English", language="en")
        self.assertEqual(vocab.count(), 2)
        vocab.add("same", "Updated", language="en")
        self.assertEqual(vocab.count(), 2)
        self.assertEqual(vocab.entries("en")[0].analysis, "Updated")
        self.assertEqual(len(VocabManager().entries("ja")), 1)
        self.assertEqual(VocabEntry.from_dict({"sentence": "old"}).language, "ja")
        entry = vocab.entries("en")[0]
        target = SimpleNamespace(_play_id=0, _language_config=self.config, _tts=Mock(),
                                 _workers=[], _cleanup_worker=Mock(), _on_tts_done=Mock(),
                                 _on_tts_error=Mock())
        with patch("ui.vocab_window.TtsWorker") as worker:
            VocabWindow._on_play(target, entry)
        worker.assert_called_once_with(target._tts, "same", LANGUAGES["en"].voice, 0)


if __name__ == "__main__":
    unittest.main()
