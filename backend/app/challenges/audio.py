import io
import wave
import struct
import math
import random
from pathlib import Path
from typing import Dict, Any, Tuple

from backend.app.config import DIGITS_DIR

def _read_wav(path: Path) -> Tuple[int, bytes]:
    with wave.open(str(path), "rb") as wf:
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
        return rate, frames

def _add_noise(samples: list, snr_db: float, rng: random.Random) -> list:

    p_signal = sum(s * s for s in samples) / max(1, len(samples))
    if p_signal <= 0:
        return samples
    p_noise = p_signal / (10.0 ** (snr_db / 10.0))
    noise_amp = math.sqrt(p_noise)

    noisy = []
    for s in samples:
        n = rng.gauss(0.0, noise_amp)
        val = int(s + n)
        val = max(-32767, min(32767, val))
        noisy.append(val)
    return noisy

def create(level: int = 1, rng: random.Random = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if rng is None:
        rng = random.Random()

    lengths = {1: 4, 2: 5, 3: 6}
    seq_len = lengths.get(level, 4)
    snr_map = {1: 20.0, 2: 12.0, 3: 6.0}
    snr_db = snr_map.get(level, 15.0)

    digits = [rng.randint(0, 9) for _ in range(seq_len)]
    digits_str = "".join(str(d) for d in digits)

    all_samples = []
    sample_rate = 16000

    for idx, d in enumerate(digits):
        wav_path = DIGITS_DIR / f"{d}.wav"
        if wav_path.exists():
            rate, raw_frames = _read_wav(wav_path)
            sample_rate = rate
            n = len(raw_frames) // 2
            samples = list(struct.unpack(f"<{n}h", raw_frames))
        else:

            samples = [int(15000.0 * math.sin(2.0 * math.pi * (300.0 + d * 100.0) * (i / 16000.0))) for i in range(8000)]

        resample_factor = rng.uniform(0.92, 1.08)
        new_len = int(len(samples) / resample_factor)
        resampled = []
        for i in range(new_len):
            orig_idx = int(i * resample_factor)
            if orig_idx < len(samples):
                resampled.append(samples[orig_idx])
            else:
                break

        all_samples.extend(resampled)

        if idx < len(digits) - 1:
            gap_duration = rng.uniform(0.25, 0.60)
            gap_samples = [0] * int(sample_rate * gap_duration)
            all_samples.extend(gap_samples)

    noisy_samples = _add_noise(all_samples, snr_db, rng)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        raw_out = struct.pack(f"<{len(noisy_samples)}h", *noisy_samples)
        wf.writeframes(raw_out)

    audio_bytes = buf.getvalue()

    public = {
        "type": "audio",
        "level": level,
        "prompt": f"Listen to the audio and enter the {seq_len} digits you hear.",
        "length": seq_len
    }
    secret = {
        "digits": digits_str,
        "audio_bytes": audio_bytes
    }
    return public, secret

def verify(secret: Dict[str, Any], answer: Any, interaction: Dict[str, Any] = None) -> bool:
    if not isinstance(answer, (str, int)):
        if isinstance(answer, dict):
            answer = answer.get("digits", answer.get("answer", ""))
        else:
            return False

    user_digits = "".join(c for c in str(answer).strip() if c.isdigit())
    expected_digits = str(secret["digits"]).strip()
    return user_digits == expected_digits

