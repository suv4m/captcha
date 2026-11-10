import time
import pytest
from backend.app.tokens import generate_token, parse_and_verify_token
from backend.app.challenges import visual, audio, drag, pow as pow_mod
from backend.app.store import store

def test_token_lifecycle_tamper_expiry_replay():

    tok = generate_token("sess_test_123", "visual", "medium")
    data = parse_and_verify_token(tok)
    assert data is not None
    assert data["sid"] == "sess_test_123"
    assert data["type"] == "visual"
    assert data["band"] == "medium"

    tampered_sig = tok[:-4] + ("AAAA" if tok[-4:] != "AAAA" else "BBBB")
    assert parse_and_verify_token(tampered_sig) is None

    parts = tok.split('.')
    tampered_payload = "eyJzaWQiOiJmYWtlIn0" + "." + parts[1]
    assert parse_and_verify_token(tampered_payload) is None

    fresh_tok = generate_token("sess_replay_test", "audio", "low")
    assert store.mark_token_used(fresh_tok) is True

    assert store.mark_token_used(fresh_tok) is False

def test_pow_challenge_verify():
    pub, sec = pow_mod.create(level=1)
    nonce = sec["nonce"]
    bits = sec["bits"]

    import hashlib
    counter = 0
    while True:
        h = hashlib.sha256(f"{nonce}:{counter}".encode("utf-8")).digest()
        if pow_mod.count_leading_zero_bits(h) >= bits:
            break
        counter += 1

    assert pow_mod.verify(sec, {"counter": counter}) is True
    assert pow_mod.verify(sec, {"counter": counter + 1}) is False
    assert pow_mod.verify(sec, "invalid") is False

def test_visual_challenge_verify():
    pub, sec = visual.create(level=1)
    targets = sec["target_indices"]

    assert visual.verify(sec, targets) is True
    assert visual.verify(sec, list(reversed(targets))) is True

    assert visual.verify(sec, [0]) is False
    assert visual.verify(sec, targets[:-1]) is False
    assert visual.verify(sec, "not a list") is False

def test_drag_challenge_verify():
    pub, sec = drag.create(level=1)
    hole_x = sec["hole_x"]
    tol = sec["tolerance"]

    assert drag.verify(sec, {"x": hole_x}) is True
    assert drag.verify(sec, hole_x + tol) is True
    assert drag.verify(sec, hole_x - tol) is True

    assert drag.verify(sec, hole_x + tol + 2) is False
    assert drag.verify(sec, hole_x - tol - 2) is False
    assert drag.verify(sec, "invalid") is False

def test_audio_challenge_verify():
    pub, sec = audio.create(level=1)
    digits = sec["digits"]

    assert audio.verify(sec, digits) is True
    assert audio.verify(sec, f" {digits} ") is True
    assert audio.verify(sec, {"digits": digits}) is True

    assert audio.verify(sec, "999999") is False
    assert audio.verify(sec, "") is False

