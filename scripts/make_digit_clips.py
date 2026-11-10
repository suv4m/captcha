import os
import sys
import wave
import struct
import math
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.config import DIGITS_DIR

def generate_synthesized_digit(digit: int, out_path: Path):
    """
    Fallback synthesis: Generate distinct audible tones/chimes encoding the digit.
    16-bit mono PCM WAV at 16000 Hz, length 0.5s.
    """
    sample_rate = 16000
    duration = 0.55
    n_samples = int(sample_rate * duration)

    f1 = 300.0 + digit * 85.0
    f2 = f1 * 1.5

    data = bytearray()
    for i in range(n_samples):
        t = float(i) / sample_rate

        env = math.sin(math.pi * t / duration)
        val = 0.6 * math.sin(2.0 * math.pi * f1 * t) + 0.4 * math.sin(2.0 * math.pi * f2 * t)
        sample = int(32767.0 * env * val * 0.7)
        data.extend(struct.pack("<h", sample))

    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(data)

def render_with_powershell_tts(digit: int, out_path: Path) -> bool:
    """
    Use Windows System.Speech.Synthesis to speak digit to WAV file.
    """
    words = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
    word = words[digit]
    ps_script = f"""
    Add-Type -AssemblyName System.Speech
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $synth.SetOutputToWaveFile('{str(out_path)}')
    $synth.Speak('{word}')
    $synth.Dispose()
    """
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            timeout=10
        )
        return proc.returncode == 0 and out_path.exists() and out_path.stat().st_size > 500
    except Exception as e:
        return False

def verify_wav_clip(p: Path) -> bool:
    try:
        with wave.open(str(p), "rb") as wf:
            channels = wf.getnchannels()
            width = wf.getsampwidth()
            rate = wf.getframerate()
            frames = wf.getnframes()
            duration = frames / float(rate)
            if width != 2:
                return False
            if duration < 0.25 or duration > 1.8:
                return False

            raw = wf.readframes(frames)
            count = len(raw) // 2
            samples = struct.unpack(f"<{count}h", raw)
            rms = math.sqrt(sum(s * s for s in samples) / max(1, count))
            return rms > 100.0
    except Exception:
        return False

def make_all_clips():
    DIGITS_DIR.mkdir(parents=True, exist_ok=True)
    tts_used = False

    for digit in range(10):
        out_path = DIGITS_DIR / f"{digit}.wav"

        success = render_with_powershell_tts(digit, out_path)
        if success and verify_wav_clip(out_path):
            tts_used = True
        else:

            generate_synthesized_digit(digit, out_path)
            assert verify_wav_clip(out_path), f"Verification failed for digit {digit}"

        print(f"Generated {out_path} (TTS: {tts_used}, verified: {verify_wav_clip(out_path)})")

    print(f"All 10 digit clips successfully generated in {DIGITS_DIR}")

if __name__ == "__main__":
    make_all_clips()

