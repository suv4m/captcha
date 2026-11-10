import re
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent


def test_limitations_md_exists_and_covers_five_topics():
    limitations_path = BASE_DIR / "docs" / "LIMITATIONS.md"
    assert limitations_path.exists(), "docs/LIMITATIONS.md must exist"

    text = limitations_path.read_text(encoding="utf-8").lower()
    
    # 1. Synthetic data only, no real user study
    assert "synthetic" in text and ("real user" in text or "no real" in text)

    # 2. Replay bots defeat behavioral classifier alone; replay guard relies on exact match within TTL
    assert "replay" in text and "ttl" in text

    # 3. Audio and visual solvers can be beaten by off-the-shelf multimodal models
    assert "multimodal" in text or ("vision" in text and "model" in text)

    # 4. Proof of work burns client battery / compute
    assert "battery" in text or "compute" in text or "proof of work" in text

    # 5. Accessibility switcher relies on honest self-declaration
    assert "self-declaration" in text or "honest" in text


def test_grep_disallowed_phrases_returns_zero_matches():
    disallowed = [
        "who estimates",
        "cognitive latency distributions",
        "wcag aa compliant"
    ]

    target_files = [BASE_DIR / "README.md"]
    target_files.extend((BASE_DIR / "docs").rglob("*.md"))

    matches = []
    for f in target_files:
        if not f.exists():
            continue
        content = f.read_text(encoding="utf-8").lower()
        for phrase in disallowed:
            if phrase in content:
                matches.append((str(f), phrase))

    assert len(matches) == 0, f"Found disallowed phrases in docs: {matches}"


def test_formula_explanation_in_readme():
    readme = (BASE_DIR / "README.md").read_text(encoding="utf-8")
    assert "missed-pass friction penalty in equivalent seconds of user frustration, chosen arbitrarily by the authors" in readme

