import time
import sqlite3
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Set

from backend.app.config import (
    DATA_DIR, SESSION_TTL_SECONDS, MAX_ATTEMPTS, MIN_INTERACTION_MS
)

DB_PATH = DATA_DIR / "captcha.db"

class Storage:
    def __init__(self):
        self._lock = threading.Lock()
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._challenges: Dict[str, Dict[str, Any]] = {}
        self._used_tokens: Set[str] = set()
        self._seen_features: Dict[str, float] = {}
        self._init_sqlite()

    def check_replay(self, features: Dict[str, Any]) -> bool:
        """
        Replay guard per Fix 9:
        Returns True if feature vector is a duplicate seen within session TTL (replay attack).
        Returns False if fresh.
        """
        if not features:
            return False
        import hashlib
        import json
        items = sorted([(k, round(float(v), 5)) for k, v in features.items()])
        h = hashlib.sha256(json.dumps(items).encode("utf-8")).hexdigest()

        now = time.time()
        with self._lock:
            expired = [k for k, ts in self._seen_features.items() if now - ts > SESSION_TTL_SECONDS]
            for k in expired:
                del self._seen_features[k]

            if h in self._seen_features:
                return True

            self._seen_features[h] = now
            return False

    def _init_sqlite(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS event_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at INTEGER NOT NULL,
                    band TEXT NOT NULL,
                    challenge_type TEXT NOT NULL,
                    level INTEGER NOT NULL,
                    outcome TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    swap_count INTEGER NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def log_event(self, band: str, challenge_type: str, level: int,
                  outcome: str, duration_ms: int, swap_count: int):
        with self._lock:
            conn = sqlite3.connect(DB_PATH)
            try:
                conn.execute("""
                    INSERT INTO event_logs (created_at, band, challenge_type, level, outcome, duration_ms, swap_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (int(time.time()), band, challenge_type, level, outcome, duration_ms, swap_count))
                conn.commit()
            finally:
                conn.close()

    def create_session(self, session_id: str, data: Dict[str, Any]):
        with self._lock:
            now = time.time()
            self._cleanup_expired(now)
            data["created_at"] = now
            data["attempts_left"] = MAX_ATTEMPTS
            data["locked"] = False
            data["swap_count"] = 0
            self._sessions[session_id] = data

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            now = time.time()
            s = self._sessions.get(session_id)
            if not s:
                return None
            if now - s["created_at"] > SESSION_TTL_SECONDS:
                del self._sessions[session_id]
                return None
            return s

    def update_session(self, session_id: str, updates: Dict[str, Any]):
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].update(updates)

    def save_challenge(self, challenge_id: str, data: Dict[str, Any]):
        with self._lock:
            now = time.time()
            data["created_at"] = now
            data.setdefault("issued_at", now)
            self._challenges[challenge_id] = data

    def get_challenge(self, challenge_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._challenges.get(challenge_id)

    def delete_challenge(self, challenge_id: str):
        with self._lock:
            self._challenges.pop(challenge_id, None)

    def mark_token_used(self, token: str) -> bool:
        """Returns True if token was unused and is now marked used. False if replayed."""
        with self._lock:
            if token in self._used_tokens:
                return False
            self._used_tokens.add(token)
            return True

    def _cleanup_expired(self, now: float):
        expired_sessions = [
            sid for sid, s in self._sessions.items()
            if now - s["created_at"] > SESSION_TTL_SECONDS
        ]
        for sid in expired_sessions:
            del self._sessions[sid]

        expired_challenges = [
            cid for cid, c in self._challenges.items()
            if now - c.get("created_at", 0) > SESSION_TTL_SECONDS
        ]
        for cid in expired_challenges:
            del self._challenges[cid]

store = Storage()
