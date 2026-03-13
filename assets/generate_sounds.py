"""Generate crystal/glass sound effects — clear, warm, elegant."""
import struct
import wave
import math
import os


def save_wav(filename, samples, sample_rate=44100):
    peak = max(abs(s) for s in samples) or 1
    samples = [s / peak * 0.75 for s in samples]
    with wave.open(filename, 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        for s in samples:
            w.writeframes(struct.pack('<h', int(s * 32767)))


def _sine(freq, t):
    return math.sin(2 * math.pi * freq * t)


def generate_glass_click(filename, sr=44100):
    """Soft crystal tap — warm and brief."""
    dur = 0.35
    n = int(sr * dur)
    samples = [0.0] * n

    tones = [
        (1200, 0.30, 6.0),
        (1800, 0.18, 8.0),
        (2400, 0.10, 11.0),
        (3000, 0.05, 14.0),
    ]

    for freq, vol, decay in tones:
        for i in range(n):
            t = i / sr
            attack = min(t / 0.003, 1.0)
            env = attack * math.exp(-t * decay) * vol
            samples[i] += env * _sine(freq, t)
            samples[i] += env * 0.15 * _sine(freq * 2.0, t)

    save_wav(filename, samples, sr)


def generate_glass_chime(filename, sr=44100):
    """Ascending wind-chime — three clear notes."""
    dur = 1.0
    n = int(sr * dur)
    samples = [0.0] * n

    notes = [
        (880,  0.00, 0.28, 4.0),
        (1109, 0.10, 0.24, 3.5),
        (1319, 0.22, 0.22, 3.0),
    ]

    for freq, start, vol, decay in notes:
        si = int(sr * start)
        for i in range(si, n):
            t = (i - si) / sr
            attack = min(t / 0.005, 1.0)
            env = attack * math.exp(-t * decay) * vol
            samples[i] += env * _sine(freq, t)
            samples[i] += env * 0.2 * _sine(freq * 2.0, t)
            samples[i] += env * 0.08 * _sine(freq * 3.0, t)

    save_wav(filename, samples, sr)


def generate_capture_sound(filename, sr=44100):
    """Quick camera-like crystal ping."""
    dur = 0.2
    n = int(sr * dur)
    samples = [0.0] * n

    tones = [
        (1500, 0.30, 12.0),
        (2200, 0.18, 16.0),
        (3300, 0.08, 22.0),
    ]

    for freq, vol, decay in tones:
        for i in range(n):
            t = i / sr
            attack = min(t / 0.002, 1.0)
            env = attack * math.exp(-t * decay) * vol
            samples[i] += env * _sine(freq, t)

    save_wav(filename, samples, sr)


if __name__ == '__main__':
    sound_dir = os.path.dirname(os.path.abspath(__file__))
    sounds_dir = os.path.join(sound_dir, 'sounds')
    os.makedirs(sounds_dir, exist_ok=True)

    generate_glass_click(os.path.join(sounds_dir, 'click.wav'))
    generate_glass_chime(os.path.join(sounds_dir, 'chime.wav'))
    generate_capture_sound(os.path.join(sounds_dir, 'capture.wav'))
    print("Sound effects generated.")
