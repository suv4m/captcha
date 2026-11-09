import math
import random
import numpy as np
from typing import Dict, Any, List, Tuple, Optional

HUMAN_SUBGROUPS = ["desktop_mouse", "touch_mobile", "keyboard_assistive", "motor_tremor"]
TRAIN_BOT_TYPES = ["instant", "linear", "noisy", "replay"]
ALL_BOT_TYPES = ["instant", "linear", "noisy", "replay", "humanized"]


def _bezier_point(p0: Tuple[float, float], p1: Tuple[float, float],
                  p2: Tuple[float, float], p3: Tuple[float, float], t: float) -> Tuple[float, float]:
    u = 1.0 - t
    tt = t * t
    uu = u * u
    uuu = uu * u
    ttt = tt * t

    x = uuu * p0[0] + 3 * uu * t * p1[0] + 3 * u * tt * p2[0] + ttt * p3[0]
    y = uuu * p0[1] + 3 * uu * t * p1[1] + 3 * u * tt * p2[1] + ttt * p3[1]
    return x, y


def generate_human_trace(rng: random.Random, subgroup: str) -> Dict[str, Any]:
    events = []
    current_t = rng.uniform(250.0, 900.0)  # Initial thinking / mount delay

    if subgroup == "desktop_mouse":
        pointer_type = "mouse"
        # 1-3 mouse gestures
        num_gestures = rng.randint(1, 3)
        cx, cy = rng.uniform(100.0, 300.0), rng.uniform(100.0, 300.0)

        for _ in range(num_gestures):
            target_x = rng.uniform(150.0, 850.0)
            target_y = rng.uniform(150.0, 650.0)
            steps = rng.randint(25, 60)

            # Control points for curved movement
            ctrl_x = (cx + target_x) / 2.0 + rng.gauss(0.0, 50.0)
            ctrl_y = (cy + target_y) / 2.0 + rng.gauss(0.0, 50.0)

            for step in range(steps):
                t_ratio = (step + 1) / steps
                # Minimum-jerk bell-shaped profile: s(t) = 10 t^3 - 15 t^4 + 6 t^5
                s = 10.0 * (t_ratio ** 3) - 15.0 * (t_ratio ** 4) + 6.0 * (t_ratio ** 5)
                # Quadratic bezier interpolation with jitter
                curr_x = (1 - s)**2 * cx + 2 * (1 - s) * s * ctrl_x + s**2 * target_x + rng.gauss(0.0, 1.2)
                curr_y = (1 - s)**2 * cy + 2 * (1 - s) * s * ctrl_y + s**2 * target_y + rng.gauss(0.0, 1.2)

                dt = max(4.0, rng.gauss(14.0, 4.0))
                # Occasional human hesitation / micro-pause
                if rng.random() < 0.05:
                    dt += rng.uniform(155.0, 350.0)
                current_t += dt
                events.append([round(current_t, 1), 0, round(curr_x, 1), round(curr_y, 1)])

            cx, cy = target_x, target_y
            # Click at destination
            current_t += rng.uniform(30.0, 120.0)
            events.append([round(current_t, 1), 1, round(cx, 1), round(cy, 1)])

        # Some keyboard interaction (e.g. typing username/email)
        num_keys = rng.randint(5, 18)
        current_t += rng.uniform(200.0, 600.0)
        for _ in range(num_keys):
            dt = max(60.0, rng.lognormvariate(math.log(180.0), 0.35))
            current_t += dt
            if rng.random() < 0.08:
                events.append([round(current_t, 1), 3, 0.0, 0.0])  # Backspace
            else:
                events.append([round(current_t, 1), 2, 0.0, 0.0])  # Keydown

    elif subgroup == "touch_mobile":
        pointer_type = "touch"
        num_swipes = rng.randint(1, 3)
        for _ in range(num_swipes):
            # Swipe / scroll gesture
            sx = rng.uniform(100.0, 300.0)
            sy = rng.uniform(300.0, 600.0)
            steps = rng.randint(8, 20)
            dy_step = rng.uniform(-30.0, 30.0)

            for step in range(steps):
                current_t += rng.uniform(10.0, 22.0)
                curr_x = sx + rng.gauss(0.0, 2.0)
                curr_y = sy + step * dy_step + rng.gauss(0.0, 2.0)
                events.append([round(current_t, 1), 0, round(curr_x, 1), round(curr_y, 1)])

            # Scroll event
            current_t += rng.uniform(20.0, 60.0)
            events.append([round(current_t, 1), 4, 0.0, 0.0])

        # Taps
        for _ in range(rng.randint(1, 3)):
            current_t += rng.uniform(180.0, 500.0)
            events.append([round(current_t, 1), 1, round(rng.uniform(50.0, 350.0), 1), round(rng.uniform(200.0, 500.0), 1)])

        # Mobile typing
        num_keys = rng.randint(4, 14)
        for _ in range(num_keys):
            current_t += max(90.0, rng.lognormvariate(math.log(220.0), 0.38))
            events.append([round(current_t, 1), 2, 0.0, 0.0])

    elif subgroup == "keyboard_assistive":
        pointer_type = "none"
        # Pure tab and keyboard navigation
        num_tabs = rng.randint(3, 8)
        for _ in range(num_tabs):
            current_t += rng.uniform(250.0, 800.0)
            events.append([round(current_t, 1), 5, 0.0, 0.0])  # Focus change
            current_t += rng.uniform(50.0, 150.0)
            events.append([round(current_t, 1), 2, 0.0, 0.0])  # Tab key

        # Typing
        num_keys = rng.randint(8, 22)
        for _ in range(num_keys):
            current_t += max(100.0, rng.lognormvariate(math.log(260.0), 0.45))
            if rng.random() < 0.12:
                events.append([round(current_t, 1), 3, 0.0, 0.0])
            else:
                events.append([round(current_t, 1), 2, 0.0, 0.0])

    elif subgroup == "motor_tremor":
        pointer_type = "mouse"
        cx, cy = rng.uniform(100.0, 300.0), rng.uniform(100.0, 300.0)
        target_x, target_y = rng.uniform(300.0, 700.0), rng.uniform(200.0, 600.0)
        steps = rng.randint(45, 90)

        for step in range(steps):
            ratio = (step + 1) / steps
            # Oscillatory tremor noise (high direction changes)
            tremor_x = 7.0 * math.sin(step * 0.8) + rng.gauss(0.0, 3.5)
            tremor_y = 7.0 * math.cos(step * 0.8) + rng.gauss(0.0, 3.5)
            curr_x = cx + ratio * (target_x - cx) + tremor_x
            curr_y = cy + ratio * (target_y - cy) + tremor_y

            dt = max(8.0, rng.gauss(24.0, 8.0))
            if rng.random() < 0.08:
                dt += rng.uniform(160.0, 420.0)
            current_t += dt
            events.append([round(current_t, 1), 0, round(curr_x, 1), round(curr_y, 1)])

        # Clicks with possible hesitation
        current_t += rng.uniform(100.0, 300.0)
        events.append([round(current_t, 1), 1, round(target_x, 1), round(target_y, 1)])

        # Typing with extra backspaces
        num_keys = rng.randint(6, 16)
        for _ in range(num_keys):
            current_t += max(120.0, rng.lognormvariate(math.log(310.0), 0.5))
            if rng.random() < 0.22:
                events.append([round(current_t, 1), 3, 0.0, 0.0])
            else:
                events.append([round(current_t, 1), 2, 0.0, 0.0])

    else:
        raise ValueError(f"Unknown human subgroup: {subgroup}")

    verify_t = round(current_t + rng.uniform(80.0, 400.0), 1)

    return {
        "meta": {
            "verify_t": verify_t,
            "pointer_type": pointer_type,
            "subgroup": subgroup,
            "is_bot": 0
        },
        "events": events
    }


def generate_bot_trace(rng: random.Random, bot_type: str, human_corpus: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    events = []

    if bot_type == "instant":
        pointer_type = rng.choice(["none", "mouse"])
        current_t = rng.uniform(10.0, 60.0)
        # Instant or zero events
        if rng.random() < 0.5:
            events.append([round(current_t, 1), 1, 200.0, 200.0])
            current_t += rng.uniform(2.0, 15.0)
            events.append([round(current_t, 1), 2, 0.0, 0.0])
        verify_t = round(current_t + rng.uniform(5.0, 30.0), 1)

    elif bot_type == "linear":
        pointer_type = "mouse"
        current_t = rng.uniform(40.0, 120.0)
        x0, y0 = rng.uniform(50.0, 200.0), rng.uniform(50.0, 200.0)
        x1, y1 = rng.uniform(400.0, 800.0), rng.uniform(300.0, 600.0)
        steps = rng.randint(15, 35)
        dt = rng.choice([16.0, 20.0, 25.0])  # strictly constant dt

        for step in range(steps):
            ratio = (step + 1) / steps
            curr_x = x0 + ratio * (x1 - x0)
            curr_y = y0 + ratio * (y1 - y0)
            current_t += dt
            events.append([round(current_t, 1), 0, round(curr_x, 1), round(curr_y, 1)])

        current_t += dt
        events.append([round(current_t, 1), 1, round(x1, 1), round(y1, 1)])
        # Fixed typing speed
        num_keys = rng.randint(3, 8)
        for _ in range(num_keys):
            current_t += 50.0
            events.append([round(current_t, 1), 2, 0.0, 0.0])
        verify_t = round(current_t + 20.0, 1)

    elif bot_type == "noisy":
        pointer_type = "mouse"
        current_t = rng.uniform(50.0, 150.0)
        x0, y0 = rng.uniform(50.0, 200.0), rng.uniform(50.0, 200.0)
        x1, y1 = rng.uniform(400.0, 800.0), rng.uniform(300.0, 600.0)
        steps = rng.randint(20, 45)

        for step in range(steps):
            ratio = (step + 1) / steps
            # Linear plus small i.i.d. Gaussian jitter
            curr_x = x0 + ratio * (x1 - x0) + rng.gauss(0.0, 1.5)
            curr_y = y0 + ratio * (y1 - y0) + rng.gauss(0.0, 1.5)
            # Uniform interval
            current_t += rng.uniform(14.0, 18.0)
            events.append([round(current_t, 1), 0, round(curr_x, 1), round(curr_y, 1)])

        current_t += rng.uniform(20.0, 50.0)
        events.append([round(current_t, 1), 1, round(x1, 1), round(y1, 1)])
        num_keys = rng.randint(4, 10)
        for _ in range(num_keys):
            current_t += rng.uniform(40.0, 80.0)
            events.append([round(current_t, 1), 2, 0.0, 0.0])
        verify_t = round(current_t + rng.uniform(30.0, 70.0), 1)

    elif bot_type == "humanized":
        # Unseen sophisticated bot: Bezier curve with easing and log-normal noise
        pointer_type = "mouse"
        current_t = rng.uniform(200.0, 500.0)
        p0 = (rng.uniform(100.0, 200.0), rng.uniform(100.0, 200.0))
        p3 = (rng.uniform(500.0, 800.0), rng.uniform(400.0, 600.0))
        p1 = (p0[0] + rng.uniform(50.0, 200.0), p0[1] + rng.uniform(-100.0, 100.0))
        p2 = (p3[0] - rng.uniform(50.0, 200.0), p3[1] + rng.uniform(-100.0, 100.0))

        steps = rng.randint(30, 55)
        for step in range(steps):
            t = (step + 1) / steps
            # Smooth cubic ease
            s = t * t * (3.0 - 2.0 * t)
            bx, by = _bezier_point(p0, p1, p2, p3, s)
            curr_x = bx + rng.gauss(0.0, 0.8)
            curr_y = by + rng.gauss(0.0, 0.8)

            dt = max(6.0, rng.gauss(15.0, 3.0))
            if rng.random() < 0.03:
                dt += rng.uniform(150.0, 250.0)
            current_t += dt
            events.append([round(current_t, 1), 0, round(curr_x, 1), round(curr_y, 1)])

        current_t += rng.uniform(40.0, 100.0)
        events.append([round(current_t, 1), 1, round(p3[0], 1), round(p3[1], 1)])
        num_keys = rng.randint(4, 12)
        for _ in range(num_keys):
            current_t += max(80.0, rng.gauss(140.0, 30.0))
            events.append([round(current_t, 1), 2, 0.0, 0.0])
        verify_t = round(current_t + rng.uniform(80.0, 200.0), 1)

    elif bot_type == "replay":
        # Perturbs a recorded human trace with +/-5% time and +/-1 px noise
        if human_corpus and len(human_corpus) > 0:
            donor = rng.choice(human_corpus)
            pointer_type = donor["meta"]["pointer_type"]
            time_scale = rng.uniform(0.95, 1.05)
            for ev in donor["events"]:
                t = ev[0] * time_scale
                code = ev[1]
                x = ev[2] + rng.gauss(0.0, 1.0) if len(ev) > 2 else 0.0
                y = ev[3] + rng.gauss(0.0, 1.0) if len(ev) > 3 else 0.0
                events.append([round(t, 1), code, round(x, 1), round(y, 1)])
            verify_t = round(donor["meta"]["verify_t"] * time_scale, 1)
        else:
            # Fallback if no corpus
            return generate_bot_trace(rng, "linear")

    else:
        raise ValueError(f"Unknown bot type: {bot_type}")

    return {
        "meta": {
            "verify_t": verify_t,
            "pointer_type": pointer_type,
            "subgroup": bot_type,
            "is_bot": 1
        },
        "events": events
    }


def assign_assumed_needs(rng: random.Random) -> List[str]:
    """
    Assumed prevalence for simulated population (SPEC.md Section 6.1):
    vision 6%, hearing 4%, motor 6%, cognitive 4%, random combinations.
    """
    needs = []
    if rng.random() < 0.06:
        needs.append("vision")
    if rng.random() < 0.04:
        needs.append("hearing")
    if rng.random() < 0.06:
        needs.append("motor")
    if rng.random() < 0.04:
        needs.append("cognitive")
    return needs


def generate_population(seed: int, n_humans: int, n_bots: int,
                        is_test: bool = False) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    traces = []

    # 1. Generate humans across subgroups
    humans = []
    for _ in range(n_humans):
        sg = rng.choice(HUMAN_SUBGROUPS)
        tr = generate_human_trace(rng, sg)
        if is_test:
            tr["meta"]["access_needs"] = assign_assumed_needs(rng)
        else:
            tr["meta"]["access_needs"] = []
        humans.append(tr)

    traces.extend(humans)

    # 2. Generate bots
    bot_types = ALL_BOT_TYPES if is_test else TRAIN_BOT_TYPES
    for _ in range(n_bots):
        btype = rng.choice(bot_types)
        tr = generate_bot_trace(rng, btype, human_corpus=humans)
        tr["meta"]["access_needs"] = []
        traces.append(tr)

    rng.shuffle(traces)
    return traces
