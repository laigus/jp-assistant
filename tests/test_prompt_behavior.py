import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QLabel, QTextBrowser, QTextEdit

from core.prompt_manager import PromptManager
from ui.main_window import MainWindow


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
        self.prompt_manager.system_prompt = "SYSTEM::{text}"

        prompt = self.prompt_manager.build_prompt("本文")

        self.assertEqual(prompt, "SYSTEM::本文")

    def test_temp_instruction_replaces_system_prompt_with_complete_request(self):
        self.prompt_manager.system_prompt = "SYSTEM::{text}"

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


if __name__ == "__main__":
    unittest.main()
