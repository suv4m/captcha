import sys
import json
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.simulate import (
    generate_human_trace, generate_bot_trace,
    HUMAN_SUBGROUPS, ALL_BOT_TYPES
)
from ml.extract import extract_features

def create_fixtures():
    rng = random.Random(42)
    fixtures = []

    human_corpus = []
    for sg in HUMAN_SUBGROUPS:
        tr = generate_human_trace(rng, sg)
        human_corpus.append(tr)
        feats = extract_features(tr)
        fixtures.append({
            "name": f"human_{sg}",
            "trace": tr,
            "features": feats
        })

    for btype in ALL_BOT_TYPES:
        tr = generate_bot_trace(rng, btype, human_corpus=human_corpus)
        feats = extract_features(tr)
        fixtures.append({
            "name": f"bot_{btype}",
            "trace": tr,
            "features": feats
        })

    out_path = Path(__file__).resolve().parent / "traces.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(fixtures, f, indent=2)
    print(f"Generated {len(fixtures)} fixture traces in {out_path}")

if __name__ == "__main__":
    create_fixtures()
