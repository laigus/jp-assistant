"""Text-to-speech using edge-tts (Microsoft free TTS with high-quality Japanese voice)."""
import edge_tts
import asyncio
import threading
import tempfile
import os
import time

VOICE_JA = "ja-JP-NanamiNeural"


class TextToSpeech:
    def __init__(self):
        self._temp_dir = tempfile.mkdtemp(prefix="jp_assistant_tts_")
        self._counter = 0

    def _next_path(self):
        self._counter += 1
        return os.path.join(self._temp_dir, f"tts_{self._counter}.mp3")

    async def _synthesize(self, text: str, output_path: str):
        communicate = edge_tts.Communicate(text, VOICE_JA)
        await communicate.save(output_path)

    def speak(self, text: str, play_callback=None):
        output_path = self._next_path()

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._synthesize(text, output_path))
        finally:
            loop.close()

        if play_callback and os.path.exists(output_path):
            play_callback(output_path)

        return output_path

    def cleanup(self):
        import shutil
        if os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir, ignore_errors=True)
