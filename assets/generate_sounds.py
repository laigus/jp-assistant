"""Generate crystal/glass sound effects programmatically."""
import struct
import wave
import math
import os

def generate_tone(freq, duration, volume=0.3, sample_rate=44100):
    samples = []
    n_samples = int(sample_rate * duration)
    for i in range(n_samples):
        t = i / sample_rate
        envelope = math.exp(-t * 8) * volume
        sample = envelope * math.sin(2 * math.pi * freq * t)
        samples.append(sample)
    return samples

def generate_glass_click(filename, sample_rate=44100):
    """Crystal glass click - short, bright, elegant."""
    duration = 0.4
    samples = [0.0] * int(sample_rate * duration)
    
    for freq, vol, decay in [(2800, 0.25, 12), (4200, 0.18, 15), (5600, 0.12, 18), (7000, 0.08, 22)]:
        n = int(sample_rate * duration)
        for i in range(n):
            t = i / sample_rate
            env = math.exp(-t * decay) * vol
            samples[i] += env * math.sin(2 * math.pi * freq * t)
    
    for freq, vol in [(1400, 0.15), (2100, 0.10)]:
        n = int(sample_rate * 0.05)
        for i in range(min(n, len(samples))):
            t = i / sample_rate
            env = math.exp(-t * 40) * vol
            samples[i] += env * math.sin(2 * math.pi * freq * t)
    
    save_wav(filename, samples, sample_rate)

def generate_glass_chime(filename, sample_rate=44100):
    """Longer glass chime for completion/success."""
    duration = 0.8
    samples = [0.0] * int(sample_rate * duration)
    
    notes = [
        (2093, 0.0, 0.20, 10),
        (2637, 0.08, 0.18, 9),
        (3136, 0.16, 0.15, 8),
    ]
    
    for freq, start, vol, decay in notes:
        start_idx = int(sample_rate * start)
        for i in range(start_idx, len(samples)):
            t = (i - start_idx) / sample_rate
            env = math.exp(-t * decay) * vol
            samples[i] += env * math.sin(2 * math.pi * freq * t)
            samples[i] += env * 0.3 * math.sin(2 * math.pi * freq * 2 * t)
    
    save_wav(filename, samples, sample_rate)

def generate_capture_sound(filename, sample_rate=44100):
    """Quick shutter-like crystal sound for screenshot capture."""
    duration = 0.25
    samples = [0.0] * int(sample_rate * duration)
    
    for freq, vol, decay in [(3500, 0.3, 20), (5000, 0.2, 25), (7000, 0.1, 30)]:
        for i in range(len(samples)):
            t = i / sample_rate
            env = math.exp(-t * decay) * vol
            samples[i] += env * math.sin(2 * math.pi * freq * t)
    
    n_noise = int(sample_rate * 0.02)
    import random
    random.seed(42)
    for i in range(min(n_noise, len(samples))):
        t = i / sample_rate
        env = math.exp(-t * 60) * 0.08
        samples[i] += env * (random.random() * 2 - 1)
    
    save_wav(filename, samples, sample_rate)

def save_wav(filename, samples, sample_rate):
    max_val = max(abs(s) for s in samples) or 1
    samples = [s / max_val * 0.8 for s in samples]
    
    with wave.open(filename, 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        for s in samples:
            w.writeframes(struct.pack('<h', int(s * 32767)))

if __name__ == '__main__':
    sound_dir = os.path.dirname(os.path.abspath(__file__))
    sounds_dir = os.path.join(sound_dir, 'sounds')
    
    generate_glass_click(os.path.join(sounds_dir, 'click.wav'))
    generate_glass_chime(os.path.join(sounds_dir, 'chime.wav'))
    generate_capture_sound(os.path.join(sounds_dir, 'capture.wav'))
    print("Sound effects generated successfully!")
