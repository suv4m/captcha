import time
import hmac
import hashlib
import base64
import json
from typing import Optional, Dict, Any

from backend.app.config import HMAC_SECRET, TOKEN_TTL_SECONDS

def generate_token(session_id: str, challenge_type: str, band: str) -> str:
    now = int(time.time())
    payload = {
        "sid": session_id,
        "type": challenge_type,
        "band": band,
        "exp": now + TOKEN_TTL_SECONDS,
        "ts": now
    }
    payload_json = json.dumps(payload, separators=(',', ':'), sort_keys=True)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode('utf-8')).decode('utf-8').rstrip('=')

    sig = hmac.new(
        HMAC_SECRET.encode('utf-8'),
        payload_b64.encode('utf-8'),
        hashlib.sha256
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode('utf-8').rstrip('=')

    return f"{payload_b64}.{sig_b64}"

def parse_and_verify_token(token: str) -> Optional[Dict[str, Any]]:
    parts = token.split('.')
    if len(parts) != 2:
        return None

    payload_b64, sig_b64 = parts

    expected_sig = hmac.new(
        HMAC_SECRET.encode('utf-8'),
        payload_b64.encode('utf-8'),
        hashlib.sha256
    ).digest()
    expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode('utf-8').rstrip('=')

    if not hmac.compare_digest(sig_b64, expected_sig_b64):
        return None

    try:

        pad = len(payload_b64) % 4
        if pad != 0:
            payload_b64 += '=' * (4 - pad)
        payload_json = base64.urlsafe_b64decode(payload_b64.encode('utf-8')).decode('utf-8')
        data = json.loads(payload_json)
    except Exception:
        return None

    now = int(time.time())
    if data.get("exp", 0) < now:
        return None

    return data

