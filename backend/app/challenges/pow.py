import hashlib
import secrets
import random
from typing import Dict, Any, Tuple


def count_leading_zero_bits(hash_bytes: bytes) -> int:
    zeros = 0
    for b in hash_bytes:
        if b == 0:
            zeros += 8
        else:
            zeros += (8 - b.bit_length())
            break
    return zeros


def create(level: int = 1, rng: random.Random = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    # Difficulty bits scaled with level (calibrated: 12, 15, 17 bits)
    bits_map = {1: 12, 2: 15, 3: 17}
    bits = bits_map.get(level, 12)

    nonce = secrets.token_hex(16)
    public = {
        "type": "pow",
        "level": level,
        "nonce": nonce,
        "bits": bits
    }
    secret = {
        "nonce": nonce,
        "bits": bits
    }
    return public, secret


def verify(secret: Dict[str, Any], answer: Any, interaction: Dict[str, Any] = None) -> bool:
    if not isinstance(answer, (dict, str, int)):
        return False

    nonce = secret["nonce"]
    bits = secret["bits"]

    if isinstance(answer, dict):
        counter = str(answer.get("counter", ""))
    else:
        counter = str(answer)

    data = f"{nonce}:{counter}".encode("utf-8")
    h = hashlib.sha256(data).digest()
    zeros = count_leading_zero_bits(h)
    return zeros >= bits

