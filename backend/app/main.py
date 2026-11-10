import os
import time
import json
import uuid
import hashlib
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
import numpy as np

from fastapi import FastAPI, HTTPException, Depends, Query, Response
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app import config
from backend.app.config import (
    DEFAULT_BREACH_COST, MIN_INTERACTION_MS,
    DATA_DIR, ARTIFACTS_DIR, WEB_DIR, WIDGET_DIR
)
from backend.app.schemas import (
    ConfigResponse, SessionRequest, SessionResponse,
    VerifyRequest, VerifyResponse, SwitchRequest,
    SiteVerifyRequest, SiteVerifyResponse,
    DemoLoginRequest, DemoLoginResponse
)
from backend.app.store import store
from backend.app.tokens import generate_token, parse_and_verify_token
from backend.app.risk import score_session_risk, get_required_features
from backend.app.decision import select_best_challenge
from backend.app.challenges import visual, audio, drag, pow as pow_mod

app = FastAPI(
    title="Adaptive and Accessible CAPTCHA",
    version="1.0.0",
    description="ML-driven adaptive CAPTCHA with accessibility as a hard constraint."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _instantiate_challenge(ctype: str, level: int) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    cid = f"ch_{uuid.uuid4().hex[:12]}"
    if ctype == "visual":
        pub, sec = visual.create(level=level)
    elif ctype == "audio":
        pub, sec = audio.create(level=level)
        pub["audio_url"] = f"/api/challenge/{cid}/audio"
    elif ctype == "drag":
        pub, sec = drag.create(level=level)
    elif ctype == "pow":
        pub, sec = pow_mod.create(level=level)
    else:
        raise ValueError(f"Unknown challenge type: {ctype}")

    pub["challenge_id"] = cid
    pub["id"] = cid
    return pub, sec


@app.get("/")
def serve_index():
    index_file = WEB_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Index page not found")
    return FileResponse(index_file)


@app.get("/lab")
def serve_lab():
    lab_file = WEB_DIR / "lab.html"
    if not lab_file.exists():
        raise HTTPException(status_code=404, detail="Lab page not found")
    return FileResponse(lab_file)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "test_mode": config.CAPTCHA_TEST_MODE
    }


@app.get("/api/config", response_model=ConfigResponse)
def get_config(mode: str = "min"):
    req_feats = get_required_features(mode=mode)
    return ConfigResponse(
        required_features=req_feats,
        version="1.0.0",
        mode=mode
    )


@app.post("/api/session", response_model=SessionResponse)
def create_session(req: SessionRequest):
    session_id = f"sess_{uuid.uuid4().hex}"
    mode = "full" if req.policy in ["P1", "P2"] else "min"

    # 1. Score risk
    p = score_session_risk(req.features, mode=mode)
    B = float(req.breach_cost if req.breach_cost is not None else DEFAULT_BREACH_COST)

    # 2. Decision selection
    filter_accessible = req.policy != "P1"
    decision = select_best_challenge(
        p, req.access_needs, B=B, filter_accessible=filter_accessible
    )

    chosen_c = decision["chosen_challenge"]
    cid = chosen_c["id"]
    band = decision["band"]

    # Calculate data sent bytes for transparency
    payload_str = json.dumps(req.features)
    data_sent_bytes = len(payload_str.encode("utf-8"))

    trace = {
        "p": round(p, 4),
        "band": band,
        "allowed_ids": decision["allowed_ids"],
        "top_3_candidates": decision["top_3_candidates"],
        "chosen_id": cid,
        "chosen_type": chosen_c["type"],
        "B": B,
        "step_up_suggested": decision["step_up_suggested"],
        "data_sent_bytes": data_sent_bytes,
        "policy": req.policy or "P3"
    }

    if cid == "none":
        # Friction-free silent pass
        token = generate_token(session_id, challenge_type="none", band=band)
        store.create_session(session_id, {
            "p": p,
            "band": band,
            "challenge_type": "none",
            "level": 0,
            "access_needs": req.access_needs,
            "B": B,
            "policy": req.policy
        })
        store.log_event(band=band, challenge_type="none", level=0, outcome="pass_silent",
                        duration_ms=0, swap_count=0)
        return SessionResponse(
            session_id=session_id,
            action="pass",
            token=token,
            challenge=None,
            trace=trace
        )

    # Create challenge
    pub, sec = _instantiate_challenge(chosen_c["type"], chosen_c["level"])
    challenge_id = pub["challenge_id"]

    # Store challenge securely in-memory
    store.save_challenge(challenge_id, {
        "type": chosen_c["type"],
        "level": chosen_c["level"],
        "secret": sec,
        "session_id": session_id
    })

    # Store session
    store.create_session(session_id, {
        "p": p,
        "band": band,
        "challenge_type": chosen_c["type"],
        "level": chosen_c["level"],
        "current_challenge_id": challenge_id,
        "access_needs": req.access_needs,
        "B": B,
        "policy": req.policy,
        "start_t": time.time()
    })

    return SessionResponse(
        session_id=session_id,
        action="challenge",
        token=None,
        challenge=pub,
        trace=trace
    )


@app.post("/api/challenge/verify", response_model=VerifyResponse)
def verify_challenge(req: VerifyRequest):
    sess = store.get_session(req.session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    if sess.get("locked", False):
        return VerifyResponse(ok=False, attempts_left=0, locked=True, error="Session locked")

    ch_data = store.get_challenge(req.challenge_id)
    if not ch_data or ch_data.get("session_id") != req.session_id:
        raise HTTPException(status_code=400, detail="Invalid challenge for session")

    # Minimum interaction duration check (anti-instant-bot)
    duration_ms = int(req.interaction.get("duration_ms", 0))
    if duration_ms < MIN_INTERACTION_MS:
        # Solve faster than 400 ms fails as automation per Section 5.2
        attempts_left = sess["attempts_left"] - 1
        locked = (attempts_left <= 0)
        store.update_session(req.session_id, {"attempts_left": attempts_left, "locked": locked})
        store.log_event(band=sess["band"], challenge_type=sess["challenge_type"],
                        level=sess["level"], outcome="fail_too_fast",
                        duration_ms=duration_ms, swap_count=sess.get("swap_count", 0))
        return VerifyResponse(
            ok=False,
            attempts_left=max(0, attempts_left),
            locked=locked,
            error=f"Verification too fast ({duration_ms}ms < {MIN_INTERACTION_MS}ms threshold)"
        )

    # Verify answer against challenge secret
    ctype = ch_data["type"]
    secret = ch_data["secret"]
    is_correct = False

    if ctype == "visual":
        is_correct = visual.verify(secret, req.answer, req.interaction)
    elif ctype == "audio":
        is_correct = audio.verify(secret, req.answer, req.interaction)
    elif ctype == "drag":
        is_correct = drag.verify(secret, req.answer, req.interaction)
    elif ctype == "pow":
        is_correct = pow_mod.verify(secret, req.answer, req.interaction)

    if is_correct:
        token = generate_token(req.session_id, challenge_type=ctype, band=sess["band"])
        store.log_event(band=sess["band"], challenge_type=ctype, level=sess["level"],
                        outcome="pass_solved", duration_ms=duration_ms,
                        swap_count=sess.get("swap_count", 0))
        return VerifyResponse(
            ok=True,
            token=token,
            attempts_left=sess["attempts_left"],
            locked=False
        )

    # Failed attempt
    attempts_left = sess["attempts_left"] - 1
    locked = (attempts_left <= 0)
    store.update_session(req.session_id, {"attempts_left": attempts_left, "locked": locked})
    store.log_event(band=sess["band"], challenge_type=ctype, level=sess["level"],
                    outcome="fail_incorrect", duration_ms=duration_ms,
                    swap_count=sess.get("swap_count", 0))

    new_challenge = None
    if attempts_left > 0:
        # Fresh challenge of same type per Section 5.2
        pub, sec = _instantiate_challenge(ctype, sess["level"])
        new_cid = pub["challenge_id"]
        store.save_challenge(new_cid, {
            "type": ctype,
            "level": sess["level"],
            "secret": sec,
            "session_id": req.session_id
        })
        store.update_session(req.session_id, {"current_challenge_id": new_cid})
        new_challenge = pub

    return VerifyResponse(
        ok=False,
        token=None,
        attempts_left=max(0, attempts_left),
        locked=locked,
        error="Incorrect challenge solution",
        new_challenge=new_challenge
    )


@app.post("/api/challenge/switch")
def switch_challenge(req: SwitchRequest):
    sess = store.get_session(req.session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    if sess.get("locked", False):
        raise HTTPException(status_code=400, detail="Session is locked")

    swap_count = sess.get("swap_count", 0)
    if swap_count >= 2:
        raise HTTPException(status_code=400, detail="Maximum 2 challenge swaps allowed per session")

    current_type = sess.get("challenge_type")
    filter_accessible = sess.get("policy") != "P1"

    # Re-run selection excluding current type
    decision = select_best_challenge(
        sess["p"], sess.get("access_needs", []), B=sess.get("B", 60.0),
        exclude_type=current_type, filter_accessible=filter_accessible
    )

    chosen_c = decision["chosen_challenge"]
    new_type = chosen_c["type"]
    new_level = chosen_c["level"]

    pub, sec = _instantiate_challenge(new_type, new_level)
    new_cid = pub["challenge_id"]

    store.save_challenge(new_cid, {
        "type": new_type,
        "level": new_level,
        "secret": sec,
        "session_id": req.session_id
    })

    store.update_session(req.session_id, {
        "challenge_type": new_type,
        "level": new_level,
        "current_challenge_id": new_cid,
        "swap_count": swap_count + 1
    })

    return {
        "ok": True,
        "challenge": pub,
        "swap_count": swap_count + 1
    }


@app.get("/api/challenge/{cid}/audio")
def get_challenge_audio(cid: str):
    ch_data = store.get_challenge(cid)
    if not ch_data or ch_data.get("type") != "audio":
        raise HTTPException(status_code=404, detail="Audio challenge not found")

    audio_bytes = ch_data["secret"].get("audio_bytes")
    if not audio_bytes:
        raise HTTPException(status_code=404, detail="Audio track not ready")

    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={"Cache-Control": "no-store"}
    )


@app.post("/api/siteverify", response_model=SiteVerifyResponse)
def siteverify(req: SiteVerifyRequest):
    data = parse_and_verify_token(req.token)
    if not data:
        return SiteVerifyResponse(success=False, error="invalid_or_expired_token")

    # Single-use guarantee
    if not store.mark_token_used(req.token):
        return SiteVerifyResponse(success=False, error="token_already_consumed")

    return SiteVerifyResponse(
        success=True,
        challenge_type=data.get("type"),
        band=data.get("band"),
        ts=data.get("ts")
    )


@app.post("/api/demo/login", response_model=DemoLoginResponse)
def demo_login(req: DemoLoginRequest):
    # Server-side verification of captcha token
    res = siteverify(SiteVerifyRequest(token=req.captcha_token))
    if not res.success:
        raise HTTPException(status_code=400, detail=f"CAPTCHA verification failed: {res.error}")

    return DemoLoginResponse(
        success=True,
        message=f"Welcome {req.username}! Verified via {res.challenge_type} ({res.band} risk)."
    )


@app.get("/api/lab/results")
def get_lab_results():
    results_path = ARTIFACTS_DIR / "results.json"
    metrics_path = ARTIFACTS_DIR / "metrics.json"
    sweep_path = ARTIFACTS_DIR / "b_sweep.json"

    if not results_path.exists() or not metrics_path.exists():
        raise HTTPException(status_code=404, detail="Lab artifacts not found. Run training/eval first.")

    with open(results_path, "r", encoding="utf-8") as f:
        results = json.load(f)
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    b_sweep = None
    if sweep_path.exists():
        with open(sweep_path, "r", encoding="utf-8") as f:
            b_sweep = json.load(f)

    return {
        "results": results,
        "metrics": metrics,
        "b_sweep": b_sweep
    }


@app.get("/api/lab/simulate")
def lab_simulate(
    policy: str = Query("P3", pattern="^(P0|P1|P2|P3)$"),
    breach_cost: float = Query(2.0, ge=1.0, le=200.0),
    runs: int = Query(20, ge=1, le=50)
):
    from ml.evaluate import CHALLENGES, INCOMPAT_PENALTY, select_challenge, simulate_session
    scores_path = ARTIFACTS_DIR / "test_scores.npz"
    if not scores_path.exists():
        raise HTTPException(status_code=404, detail="Test scores artifact missing")

    data = np.load(scores_path)
    y_test = data["y_test"]
    p_full = data["p_full"]
    p_min = data["p_min"]
    subgroups = data["subgroups"]
    needs_mat = data["needs_mat"]
    needs_keys = ["vision", "hearing", "motor", "cognitive"]

    n_sessions = len(y_test)
    human_passes = []
    bot_passes = []
    human_times = []
    violations = []
    free_sessions = []

    p_vec = p_min if policy == "P3" else p_full
    filter_accessible = policy not in ["P0", "P1"]

    for r in range(runs):
        rng = np.random.RandomState(r + 100)
        h_pass = 0
        b_pass = 0
        h_time = 0.0
        n_h = 0
        n_b = 0
        v_count = 0
        f_count = 0

        for i in range(n_sessions):
            is_bot = int(y_test[i])
            sg = str(subgroups[i])
            needs = [needs_keys[j] for j in range(4) if needs_mat[i, j] == 1]

            if policy == "P0":
                cid = "vis2"
            else:
                p = float(p_vec[i])
                cid = select_challenge(p, needs, B=breach_cost, filter_accessible=filter_accessible)

            sim = simulate_session(is_bot, sg, needs, cid, rng)
            if is_bot:
                n_b += 1
                if sim["passed"]:
                    b_pass += 1
            else:
                n_h += 1
                h_time += sim["time_spent"]
                if sim["passed"]:
                    h_pass += 1
                if sim["is_violation"]:
                    v_count += 1
                if sim["is_free"]:
                    f_count += 1

        human_passes.append(h_pass / max(1, n_h))
        bot_passes.append(b_pass / max(1, n_b))
        human_times.append(h_time / max(1, n_h))
        violations.append(v_count / max(1, n_h))
        free_sessions.append(f_count / max(1, n_h))

    return {
        "policy": policy,
        "breach_cost": breach_cost,
        "human_pass_rate": round(float(np.mean(human_passes)), 4),
        "mean_human_time_s": round(float(np.mean(human_times)), 2),
        "security_rate": round(1.0 - float(np.mean(bot_passes)), 4),
        "a11y_violation_rate": round(float(np.mean(violations)), 4),
        "challenge_free_rate": round(float(np.mean(free_sessions)), 4)
    }


@app.post("/api/collect")
def collect_sample(payload: Dict[str, Any]):
    """Opt-in research data collection: features + human label only."""
    features = payload.get("features")
    is_human = payload.get("is_human", True)
    if not features:
        raise HTTPException(status_code=400, detail="Missing features")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": int(time.time()),
        "is_human": bool(is_human),
        "features": features
    }
    with open(DATA_DIR / "collected.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    return {"status": "collected"}


@app.get("/api/_test/secret/{cid}")
def get_test_secret(cid: str):
    """
    Test hook per Section 5.2: Exists ONLY when CAPTCHA_TEST_MODE=1.
    Returns 404 otherwise!
    """
    if not config.CAPTCHA_TEST_MODE:
        raise HTTPException(status_code=404, detail="Not found")

    ch = store.get_challenge(cid)
    if not ch:
        raise HTTPException(status_code=404, detail="Challenge not found")

    sec = ch.get("secret", {})
    # Return answer format suitable for test solver
    ctype = ch.get("type")
    if ctype == "visual":
        return {"answer": sec.get("target_indices")}
    elif ctype == "audio":
        return {"answer": sec.get("digits")}
    elif ctype == "drag":
        return {"answer": {"x": sec.get("hole_x")}}
    elif ctype == "pow":
        # Solve pow for test
        nonce = sec.get("nonce")
        bits = sec.get("bits")
        counter = 0
        while True:
            h = hashlib.sha256(f"{nonce}:{counter}".encode("utf-8")).digest()
            if pow_mod.count_leading_zero_bits(h) >= bits:
                return {"answer": {"counter": counter}}
            counter += 1

    return {"secret": sec}


# Mount static web assets if directory exists
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
if WIDGET_DIR.exists():
    app.mount("/widget", StaticFiles(directory=str(WIDGET_DIR)), name="widget")
