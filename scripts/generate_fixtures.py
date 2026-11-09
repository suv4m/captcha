import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.simulate import generate_human_trace, generate_bot_trace
from ml.extract import extract_features
import random
import numpy as np

def make_fixtures():
    rng = random.Random(12345)
    np_rng = np.random.default_rng(12345)
    
    fixtures = []
    # 1. Empty trace
    t_empty = {"meta": {"verify_t": 500, "pointer_type": "none"}, "events": []}
    fixtures.append({"name": "empty", "trace": t_empty, "features": extract_features(t_empty)})
    
    # 2. Single event
    t_single = {"meta": {"verify_t": 800, "pointer_type": "mouse"}, "events": [[100, 0, 50, 60]]}
    fixtures.append({"name": "single_event", "trace": t_single, "features": extract_features(t_single)})
    
    # 3. Desktop mouse
    t_mouse = generate_human_trace("desktop_mouse", rng, np_rng)
    fixtures.append({"name": "desktop_mouse", "trace": t_mouse, "features": extract_features(t_mouse)})
    
    # 4. Touch mobile
    t_touch = generate_human_trace("touch_mobile", rng, np_rng)
    fixtures.append({"name": "touch_mobile", "trace": t_touch, "features": extract_features(t_touch)})
    
    # 5. Keyboard assistive
    t_kb = generate_human_trace("keyboard_assistive", rng, np_rng)
    fixtures.append({"name": "keyboard_assistive", "trace": t_kb, "features": extract_features(t_kb)})
    
    # 6. Motor tremor
    t_tremor = generate_human_trace("motor_tremor", rng, np_rng)
    fixtures.append({"name": "motor_tremor", "trace": t_tremor, "features": extract_features(t_tremor)})
    
    # 7. Linear bot
    t_linear = generate_bot_trace("linear", rng, np_rng)
    fixtures.append({"name": "linear_bot", "trace": t_linear, "features": extract_features(t_linear)})
    
    # 8. Humanized bot
    t_bezier = generate_bot_trace("humanized", rng, np_rng)
    fixtures.append({"name": "humanized_bot", "trace": t_bezier, "features": extract_features(t_bezier)})
    
    fixtures_path = Path("tests/fixtures/traces.json")
    fixtures_path.parent.mkdir(parents=True, exist_ok=True)
    with open(fixtures_path, "w", encoding="utf-8") as f:
        json.dump(fixtures, f, indent=2)
    print(f"Generated {len(fixtures)} fixtures in {fixtures_path}")

if __name__ == "__main__":
    make_fixtures()
