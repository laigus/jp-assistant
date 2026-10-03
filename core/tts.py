"""Multilingual text-to-speech using the existing Edge online service."""
import edge_tts
import aiohttp
import asyncio
import threading
import tempfile
import os
from urllib.parse import urlsplit
from urllib.request import getproxies, proxy_bypass

from edge_tts.constants import VOICE_LIST, WSS_URL


def _resolve_proxy(url: str) -> str | None:
    """Use the configured HTTP proxy for both HTTPS and speech WebSocket traffic."""
    target = urlsplit(url)
    if target.hostname and proxy_bypass(target.hostname):
        return None
    proxies = getproxies()
    for scheme in (target.scheme, "https", "http", "all"):
        proxy = proxies.get(scheme)
        if proxy and urlsplit(proxy).scheme in {"http", "https"}:
            return proxy
    return None


def tts_error_message(error: Exception) -> str:
    """Give all speech workers the same actionable connection error messages."""
    if isinstance(error, aiohttp.ClientSSLError):
        return "语音服务证书或 TLS 连接失败，请检查系统时间、证书和代理设置。"
    if isinstance(error, TimeoutError):
        return "连接语音服务超时，请检查网络或系统代理后重试。"
    if isinstance(error, aiohttp.ClientHttpProxyError) and error.status == 407:
        return "代理认证失败，请检查系统代理的账号和密码。"
    if isinstance(error, aiohttp.ClientConnectionError):
        return "连接语音服务失败，请检查网络和代理设置，稍后重试。"
    return str(error)


async def _request_with_retry(operation):
    """Retry one transient connection failure, not TLS or request validation errors."""
    for attempt in range(2):
        try:
            return await operation()
        except aiohttp.ClientSSLError:
            raise
        except (aiohttp.ClientConnectionError, TimeoutError):
            if attempt:
                raise
            await asyncio.sleep(0.5)


class TextToSpeech:
    def __init__(self):
        self._temp_dir = tempfile.mkdtemp(prefix="jp_assistant_tts_")
        self._counter = 0
        self._lock = threading.Lock()

    def _next_path(self):
        with self._lock:
            self._counter += 1
            return os.path.join(self._temp_dir, f"tts_{self._counter}.mp3")

    async def _synthesize(self, text: str, output_path: str, voice: str, rate: int):
        proxy = _resolve_proxy(WSS_URL)

        async def synthesize():
            # Communicate is single-use; save opens the audio in write mode each time.
            communicate = edge_tts.Communicate(text, voice, rate=f"{rate:+d}%", proxy=proxy)
            await communicate.save(output_path)

        await _request_with_retry(synthesize)

    def speak(self, text: str, voice: str, rate: int = 0):
        output_path = self._next_path()

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._synthesize(text, output_path, voice, rate))
        except Exception:
            try:
                os.remove(output_path)
            except OSError:
                pass
            raise
        finally:
            loop.close()

        return output_path

    @staticmethod
    def list_voices() -> list[dict]:
        proxy = _resolve_proxy(VOICE_LIST)
        return asyncio.run(_request_with_retry(lambda: edge_tts.list_voices(proxy=proxy)))

    def cleanup(self):
        import shutil
        if os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir, ignore_errors=True)
