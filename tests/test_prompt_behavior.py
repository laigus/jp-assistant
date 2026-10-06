import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import onnxruntime  # noqa: F401  # Preserve the application's DLL import order.
from PyQt6.QtWidgets import QApplication, QLabel, QTextBrowser, QTextEdit

from core.prompt_manager import PromptManager
from ui.main_window import MainWindow, OcrWorker


class PromptBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.prompt_manager = PromptManager(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_system_prompt_is_used_without_temp_instruction(self):
        self.prompt_manager.prompts["ja"] = "SYSTEM::{text}"

        prompt = self.prompt_manager.build_prompt("本文")

        self.assertEqual(prompt, "SYSTEM::本文")

    def test_temp_instruction_replaces_system_prompt_with_complete_request(self):
        self.prompt_manager.prompts["ja"] = "SYSTEM::{text}"

        prompt = self.prompt_manager.build_prompt("本文", "  敬语的作用是什么？  ")

        self.assertNotIn("SYSTEM::", prompt)
        self.assertIn("请针对以下日语文本", prompt)
        self.assertIn("待解释文本：\n本文", prompt)
        self.assertIn("临时指令：\n敬语的作用是什么？", prompt)

    def test_successful_nonempty_ocr_clears_temp_instruction(self):
        target = self._make_ocr_target("保留到新文本")

        MainWindow._on_ocr_done(target, "新しい本文")

        self.assertEqual(target.ocr_text.toPlainText(), "新しい本文")
        self.assertEqual(target.temp_prompt_edit.toPlainText(), "")
        self.assertEqual(target.status_label.text(), "识别完成")
        target._play_sound.assert_called_once_with("chime")

    def test_analyze_keeps_temp_instruction_for_current_text(self):
        target = self._make_analyze_target("只解释敬语")

        with patch("ui.main_window.AnalyzeWorker") as worker_class:
            worker = worker_class.return_value
            worker.progress = Mock()
            worker.result_ready = Mock()

            MainWindow._on_analyze_click(target)

        expected_prompt = self.prompt_manager.build_prompt("現在の本文", "只解释敬语")
        worker_class.assert_called_once_with(target.analyzer, expected_prompt)
        self.assertEqual(target.temp_prompt_edit.toPlainText(), "只解释敬语")
        target._start_worker.assert_called_once_with(worker)

    def test_empty_ocr_result_keeps_temp_instruction(self):
        target = self._make_ocr_target("继续保留")

        MainWindow._on_ocr_done(target, "   ")

        self.assertEqual(target.temp_prompt_edit.toPlainText(), "继续保留")
        self.assertIn("未识别到文字", target.status_label.text())
        target._play_sound.assert_not_called()

    def test_ocr_exception_is_logged_and_reported(self):
        engine = Mock()
        engine.recognize.side_effect = RuntimeError("recognition test failure")
        worker = OcrWorker(engine, object(), {})
        error, result = Mock(), Mock()
        worker.error.connect(error)
        worker.result_ready.connect(result)

        with self.assertLogs(level="ERROR") as logs:
            worker.run()

        self.assertIn("OCR recognition failed", logs.output[0])
        self.assertIn("Traceback", logs.output[0])
        error.assert_called_once_with("recognition test failure")
        result.assert_not_called()

    def test_capture_failure_is_distinguished_from_ocr_failure(self):
        target = self._make_ocr_target("继续保留")

        MainWindow._on_capture_error(target, "capture test failure")

        self.assertEqual(target.status_label.text(), "截图失败: capture test failure")
        self.assertEqual(target.temp_prompt_edit.toPlainText(), "继续保留")
        target._play_sound.assert_not_called()

    @staticmethod
    def _make_ocr_target(temp_instruction: str):
        target = SimpleNamespace(
            ocr_text=QTextEdit(),
            temp_prompt_edit=QTextEdit(),
            status_label=QLabel(),
            _play_sound=Mock(),
        )
        target.temp_prompt_edit.setPlainText(temp_instruction)
        return target

    def _make_analyze_target(self, temp_instruction: str):
        target = SimpleNamespace(
            _analyze_worker=None,
            _last_md="旧结果",
            _analysis_text="",
            _context_id=0,
            language="ja",
            _deliver=Mock(),
            ocr_text=QTextEdit(),
            temp_prompt_edit=QTextEdit(),
            status_label=QLabel(),
            analysis_browser=QTextBrowser(),
            prompt_mgr=self.prompt_manager,
            analyzer=Mock(),
            _play_sound=Mock(),
            _set_analyze_running=Mock(),
            _on_analysis_progress=Mock(),
            _on_analysis_done=Mock(),
            _start_worker=Mock(),
        )
        target.ocr_text.setPlainText("現在の本文")
        target.temp_prompt_edit.setPlainText(temp_instruction)
        return target

    def test_english_prompt_and_temp_instruction_use_english_context(self):
        self.prompt_manager.prompts["en"] = "EN::{text}"
        self.assertEqual(self.prompt_manager.build_prompt("Hello", language="en"), "EN::Hello")
        prompt = self.prompt_manager.build_prompt("Hello", "解释时态", "en")
        self.assertIn("英语文本", prompt)
        self.assertNotIn("EN::", prompt)
        self.assertNotIn("日语", prompt)


if __name__ == "__main__":
    unittest.main()
