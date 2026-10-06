import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import onnxruntime  # noqa: F401  # Preserve the application's DLL import order.
from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtWidgets import QApplication

from ui.screenshot import ScreenshotOverlay, _physical_capture_rect


def screen(geometry, ratio):
    return SimpleNamespace(geometry=lambda: geometry, devicePixelRatio=lambda: ratio,
                           virtualGeometry=lambda: geometry)


class ScreenshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.overlay = ScreenshotOverlay()

    def tearDown(self):
        self.overlay.close()
        self.overlay.deleteLater()

    def test_capture_uses_physical_pixels_at_windows_display_scales(self):
        for ratio in (1.0, 1.25, 1.5, 2.0):
            with self.subTest(ratio=ratio):
                monitor = screen(QRect(0, 0, 1920, 1080), ratio)
                width, height = round(400 * ratio), round(100 * ratio)
                screenshot = SimpleNamespace(size=(width, height), bgra=b"\0\0\0\xff" * width * height)
                capture = Mock()
                capture.grab.return_value = screenshot
                result, error = Mock(), Mock()
                self.overlay.region_captured.connect(result)
                self.overlay.capture_failed.connect(error)
                with (patch("ui.screenshot.QGuiApplication.screens", return_value=[monitor]),
                      patch("ui.screenshot.mss.mss") as create_capture):
                    create_capture.return_value.__enter__.return_value = capture
                    self.overlay._capture_region(QRect(800, 400, 400, 100))
                capture.grab.assert_called_once_with({
                    "left": round(800 * ratio), "top": round(400 * ratio),
                    "width": width, "height": height,
                })
                self.assertEqual(result.call_args.args[0].size, (width, height))
                error.assert_not_called()
                self.overlay.region_captured.disconnect(result)
                self.overlay.capture_failed.disconnect(error)

    def test_scaled_secondary_screen_keeps_its_native_origin(self):
        for origin in (QPoint(2880, 0), QPoint(-2560, -200)):
            with self.subTest(origin=origin):
                monitor = screen(QRect(origin.x(), origin.y(), 1707, 960), 1.5)
                selection = QRect(origin.x() + 200, origin.y() + 100, 400, 120)
                with patch("ui.screenshot.QGuiApplication.screens", return_value=[monitor]):
                    self.assertEqual(_physical_capture_rect(selection),
                                     QRect(origin.x() + 300, origin.y() + 150, 600, 180))

    def test_selection_spanning_screens_converts_each_screen_scale(self):
        monitors = [screen(QRect(0, 0, 1920, 1080), 1.5),
                    screen(QRect(2880, 0, 1920, 1080), 1.0)]
        with patch("ui.screenshot.QGuiApplication.screens", return_value=monitors):
            self.assertEqual(_physical_capture_rect(QRect(1800, 100, 1280, 100)),
                             QRect(2700, 100, 380, 200))

    def test_fractional_scale_rounds_edges_without_losing_a_pixel(self):
        monitor = screen(QRect(0, 0, 1920, 1080), 1.25)
        with patch("ui.screenshot.QGuiApplication.screens", return_value=[monitor]):
            self.assertEqual(_physical_capture_rect(QRect(1, 1, 2, 2)), QRect(1, 1, 3, 3))

    def test_selection_outside_screens_reports_capture_failure(self):
        result, error = Mock(), Mock()
        self.overlay.region_captured.connect(result)
        self.overlay.capture_failed.connect(error)
        with (patch("ui.screenshot.QGuiApplication.screens", return_value=[]),
              patch("ui.screenshot.mss.mss") as create_capture,
              self.assertLogs(level="ERROR") as logs):
            self.overlay._capture_region(QRect(0, 0, 100, 100))
        create_capture.assert_not_called()
        error.assert_called_once_with("截图选区不在可用屏幕内")
        result.assert_not_called()
        self.assertIn("Screenshot capture failed", logs.output[0])
        self.assertIn("Traceback", logs.output[0])

    def test_capture_exception_is_logged_and_reported(self):
        result, error = Mock(), Mock()
        self.overlay.region_captured.connect(result)
        self.overlay.capture_failed.connect(error)
        monitor = screen(QRect(0, 0, 1920, 1080), 1.0)
        with (patch("ui.screenshot.QGuiApplication.screens", return_value=[monitor]),
              patch("ui.screenshot.mss.mss", side_effect=RuntimeError("capture test failure")),
              self.assertLogs(level="ERROR") as logs):
            self.overlay._capture_region(QRect(0, 0, 100, 100))
        error.assert_called_once_with("capture test failure")
        result.assert_not_called()
        self.assertIn("capture test failure", logs.output[0])

    def _queue_selection(self):
        self.overlay._origin = QPoint(0, 0)
        self.overlay._current = QPoint(50, 30)
        self.overlay._selecting = True
        event = SimpleNamespace(button=lambda: Qt.MouseButton.LeftButton,
                                pos=lambda: QPoint(100, 50))
        self.overlay.mouseReleaseEvent(event)

    def test_delayed_capture_fixes_global_selection_before_overlay_moves(self):
        self.overlay.move(400, 200)
        expected = QRect(self.overlay.mapToGlobal(QPoint(0, 0)), QRect(0, 0, 101, 51).size())
        with patch.object(self.overlay, "_capture_region") as capture:
            self._queue_selection()
            capture.assert_not_called()
            self.assertFalse(self.overlay.isVisible())
            self.assertTrue(self.overlay._capture_timer.isActive())
            self.assertTrue(self.overlay._capture_timer.isSingleShot())
            self.assertEqual(self.overlay._capture_timer.interval(), 50)
            self.overlay.move(800, 600)
            self.overlay._capture_timer.timeout.emit()
            capture.assert_called_once_with(expected)
            self.assertIsNone(self.overlay._pending_region)
            self.assertFalse(self.overlay._capture_timer.isActive())

    def test_cancel_and_close_clear_delayed_capture(self):
        escape = SimpleNamespace(key=lambda: Qt.Key.Key_Escape)
        right_click = SimpleNamespace(button=lambda: Qt.MouseButton.RightButton)
        actions = (self.overlay.cancel_capture,
                   lambda: self.overlay.keyPressEvent(escape),
                   lambda: self.overlay.mousePressEvent(right_click),
                   self.overlay.close)
        for action in actions:
            with self.subTest(action=action), patch.object(self.overlay, "_capture_region") as capture:
                self._queue_selection()
                action()
                self.assertIsNone(self.overlay._pending_region)
                self.assertFalse(self.overlay._capture_timer.isActive())
                self.overlay._capture_timer.timeout.emit()
                capture.assert_not_called()

    def test_restarting_capture_cancels_pending_capture_and_keeps_virtual_geometry(self):
        monitor = screen(QRect(-1280, 0, 3200, 1080), 1.0)
        with (patch.object(self.overlay, "_capture_region") as capture,
              patch.object(self.overlay, "show") as show,
              patch.object(self.overlay, "showFullScreen") as full_screen,
              patch.object(self.overlay, "activateWindow"),
              patch("ui.screenshot.QGuiApplication.primaryScreen", return_value=monitor)):
            self._queue_selection()
            self.overlay.start_capture()
            self.assertEqual(self.overlay.geometry(), monitor.geometry())
            self.assertFalse(self.overlay._capture_timer.isActive())
            self.assertIsNone(self.overlay._pending_region)
            self.overlay._capture_timer.timeout.emit()
            capture.assert_not_called()
            show.assert_called_once_with()
            full_screen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
