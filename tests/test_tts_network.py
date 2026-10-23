"""Focused speech-network tests without requests or generated audio files."""
import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import urlsplit

import aiohttp
from edge_tts.constants import VOICE_LIST, WSS_URL

from core.tts import TextToSpeech, _request_with_retry, _resolve_proxy, tts_error_message


class TtsNetworkTests(unittest.TestCase):
    def test_proxy_selection_for_speech_and_voice_list(self):
        cases = (
            ({"wss": "http://wss-proxy:1", "https": "http://https-proxy:2"},
             "http://wss-proxy:1", "http://https-proxy:2"),
            ({"https": "http://https-proxy:2", "http": "http://http-proxy:3"},
             "http://https-proxy:2", "http://https-proxy:2"),
            ({"http": "http://http-proxy:3"}, "http://http-proxy:3", "http://http-proxy:3"),
            ({"all": "http://all-proxy:4"}, "http://all-proxy:4", "http://all-proxy:4"),
            ({"all": "socks5://socks-proxy:5"}, None, None),
            ({}, None, None),
        )
        for proxies, speech_proxy, voices_proxy in cases:
            with self.subTest(proxies=proxies), \
                    patch("core.tts.getproxies", return_value=proxies), \
                    patch("core.tts.proxy_bypass", return_value=False):
                self.assertEqual(_resolve_proxy(WSS_URL), speech_proxy)
                self.assertEqual(_resolve_proxy(VOICE_LIST), voices_proxy)

    def test_proxy_bypass_preserves_direct_connection(self):
        with (patch("core.tts.proxy_bypass", return_value=True) as bypass,
              patch("core.tts.getproxies") as proxies):
            self.assertIsNone(_resolve_proxy(WSS_URL))
            bypass.assert_called_once_with(urlsplit(WSS_URL).hostname)
            proxies.assert_not_called()

    def test_proxy_bypass_uses_the_requested_host_after_endpoint_changes(self):
        for host in ("speech.platform.bing.com", "api.msedgeservices.com"):
            with self.subTest(host=host), \
                    patch("core.tts.proxy_bypass", return_value=True) as bypass:
                self.assertIsNone(_resolve_proxy(f"wss://{host}/test"))
                bypass.assert_called_once_with(host)

    def test_synthesis_explicitly_passes_proxy_and_keeps_voice_and_rate(self):
        communicate = Mock(save=AsyncMock())
        target = TextToSpeech.__new__(TextToSpeech)
        with (patch("core.tts._resolve_proxy", return_value="http://proxy:8") as resolve,
              patch("core.tts.edge_tts.Communicate", return_value=communicate) as create):
            asyncio.run(target._synthesize("Hello", "output.mp3", "en-US-JennyNeural", -20))
        resolve.assert_called_once_with(WSS_URL)
        create.assert_called_once_with("Hello", "en-US-JennyNeural", rate="-20%",
                                       proxy="http://proxy:8")
        communicate.save.assert_awaited_once_with("output.mp3")

    def test_voice_list_uses_same_proxy_resolver(self):
        voices = [{"ShortName": "en-US-JennyNeural"}]
        with (patch("core.tts._resolve_proxy", return_value="http://proxy:8") as resolve,
              patch("core.tts.edge_tts.list_voices", new_callable=AsyncMock,
                    return_value=voices) as fetch):
            self.assertEqual(TextToSpeech.list_voices(), voices)
        resolve.assert_called_once_with(VOICE_LIST)
        fetch.assert_awaited_once_with(proxy="http://proxy:8")

    def test_failed_synthesis_removes_partial_audio_and_preserves_error(self):
        target = TextToSpeech.__new__(TextToSpeech)
        target._next_path = Mock(return_value="partial.mp3")
        failure = aiohttp.ClientConnectionError("connection failed")
        with (patch.object(target, "_synthesize", new_callable=AsyncMock,
                           side_effect=failure),
              patch("core.tts.os.remove") as remove):
            with self.assertRaises(aiohttp.ClientConnectionError) as caught:
                target.speak("Hello", "en-US-JennyNeural")
        self.assertIs(caught.exception, failure)
        remove.assert_called_once_with("partial.mp3")

    def test_connection_retry_creates_fresh_communication(self):
        first = Mock(save=AsyncMock(side_effect=aiohttp.ClientConnectionError("reset")))
        second = Mock(save=AsyncMock())
        target = TextToSpeech.__new__(TextToSpeech)
        with (patch("core.tts._resolve_proxy", return_value=None),
              patch("core.tts.edge_tts.Communicate", side_effect=[first, second]) as create,
              patch("core.tts.asyncio.sleep", new_callable=AsyncMock) as sleep):
            asyncio.run(target._synthesize("Hello", "output.mp3", "en-US-JennyNeural", 0))
        self.assertEqual(create.call_count, 2)
        first.save.assert_awaited_once_with("output.mp3")
        second.save.assert_awaited_once_with("output.mp3")
        sleep.assert_awaited_once_with(0.5)

    def test_retry_is_bounded_and_preserves_last_connection_error(self):
        failure = aiohttp.ClientConnectionError("still offline")
        operation = AsyncMock(side_effect=failure)
        with patch("core.tts.asyncio.sleep", new_callable=AsyncMock) as sleep:
            with self.assertRaises(aiohttp.ClientConnectionError) as caught:
                asyncio.run(_request_with_retry(operation))
        self.assertIs(caught.exception, failure)
        self.assertEqual(operation.await_count, 2)
        sleep.assert_awaited_once_with(0.5)

    def test_tls_and_invalid_voice_errors_are_not_retried(self):
        for error in (aiohttp.ClientSSLError(None, OSError()), ValueError("invalid voice")):
            with self.subTest(error=type(error).__name__):
                operation = AsyncMock(side_effect=error)
                with patch("core.tts.asyncio.sleep", new_callable=AsyncMock) as sleep:
                    with self.assertRaises(type(error)):
                        asyncio.run(_request_with_retry(operation))
                operation.assert_awaited_once()
                sleep.assert_not_awaited()

    def test_http_rejection_and_handshake_failures_are_not_retried(self):
        errors = (aiohttp.WSServerHandshakeError(Mock(), (), status=403),
                  aiohttp.WSServerHandshakeError(Mock(), (), status=502),
                  aiohttp.ClientResponseError(Mock(), (), status=403))
        for error in errors:
            with self.subTest(error=type(error).__name__, status=error.status):
                operation = AsyncMock(side_effect=error)
                with patch("core.tts.asyncio.sleep", new_callable=AsyncMock) as sleep:
                    with self.assertRaises(type(error)) as caught:
                        asyncio.run(_request_with_retry(operation))
                self.assertIs(caught.exception, error)
                operation.assert_awaited_once()
                sleep.assert_not_awaited()

    def test_connection_errors_are_actionable_and_unknown_errors_are_preserved(self):
        cases = (
            (aiohttp.ClientConnectionError("raw host error"), "连接语音服务失败"),
            (TimeoutError(), "连接语音服务超时"),
            (aiohttp.ClientSSLError(None, OSError()), "证书或 TLS"),
            (aiohttp.ClientHttpProxyError(Mock(), (), status=407), "代理认证失败"),
            (aiohttp.WSServerHandshakeError(Mock(), (), status=403), "HTTP 403"),
            (aiohttp.ClientResponseError(Mock(), (), status=403), "更新程序"),
            (aiohttp.WSServerHandshakeError(Mock(), (), status=502), "握手失败（HTTP 502）"),
            (ValueError("invalid voice"), "invalid voice"),
        )
        for error, expected in cases:
            with self.subTest(error=type(error).__name__):
                self.assertIn(expected, tts_error_message(error))


class TtsFeedbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        import onnxruntime  # noqa: F401  # Preserve the application's DLL import order.
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_main_window_preserves_complete_speech_error(self):
        from PyQt6.QtWidgets import QLabel, QPushButton
        from ui.main_window import MainWindow
        target = SimpleNamespace(speak_btn=QPushButton(), status_label=QLabel(),
                                 _set_speaking=Mock())
        target.speak_btn.setEnabled(False)
        message = "语音服务拒绝请求（HTTP 403），请更新程序，并检查系统时间和网络策略。更多错误信息。"
        self.assertGreater(len(message), 40)

        MainWindow._on_tts_error(target, message)

        self.assertEqual(target.status_label.text(), f"语音合成失败: {message}")
        self.assertTrue(target.speak_btn.isEnabled())
        target._set_speaking.assert_called_once_with(False)

    def test_workers_log_original_failure_and_emit_shared_message(self):
        from ui.tts_worker import TtsWorker, VoiceListWorker
        failure = aiohttp.WSServerHandshakeError(Mock(), (), status=403)
        tts = Mock()
        tts.speak.side_effect = failure
        cases = ((TtsWorker(tts, "Hello", "en-US-JennyNeural"), "Speech synthesis failed"),
                 (VoiceListWorker(), "Voice list request failed"))
        for worker, log_message in cases:
            with self.subTest(worker=type(worker).__name__):
                error, result = Mock(), Mock()
                worker.error.connect(error)
                worker.result_ready.connect(result)
                with (patch("ui.tts_worker.TextToSpeech.list_voices", side_effect=failure),
                      self.assertLogs(level="ERROR") as logs):
                    worker.run()
                self.assertIn(log_message, logs.output[0])
                self.assertIn("Traceback", logs.output[0])
                error.assert_called_once_with(tts_error_message(failure))
                result.assert_not_called()


if __name__ == "__main__":
    unittest.main()
