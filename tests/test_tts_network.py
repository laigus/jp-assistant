"""Focused speech-network tests without requests or generated audio files."""
import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch

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
            bypass.assert_called_once_with("speech.platform.bing.com")
            proxies.assert_not_called()

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

    def test_connection_errors_are_actionable_and_unknown_errors_are_preserved(self):
        cases = (
            (aiohttp.ClientConnectionError("raw host error"), "连接语音服务失败"),
            (TimeoutError(), "连接语音服务超时"),
            (aiohttp.ClientSSLError(None, OSError()), "证书或 TLS"),
            (aiohttp.ClientHttpProxyError(Mock(), (), status=407), "代理认证失败"),
            (ValueError("invalid voice"), "invalid voice"),
        )
        for error, expected in cases:
            with self.subTest(error=type(error).__name__):
                self.assertIn(expected, tts_error_message(error))


if __name__ == "__main__":
    unittest.main()
