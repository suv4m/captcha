import math
import numpy as np
from typing import Dict, Any, List

FEATURE_NAMES = [
    "p_n_moves",
    "p_path_len",
    "p_straightness",
    "p_speed_mean",
    "p_speed_std",
    "p_speed_max",
    "p_acc_std",
    "p_dir_changes_per_100px",
    "p_pauses",
    "p_dt_std",
    "p_clicks",
    "p_click_gap_std",
    "k_n",
    "k_gap_mean",
    "k_gap_std",
    "k_backspaces",
    "t_since_mount",
    "t_first_interaction",
    "t_idle_ratio",
    "t_scrolls",
    "t_focus_changes",
    "t_events_total",
    "d_pointer_mouse",
    "d_pointer_touch",
    "d_pointer_none",
]

def extract_features(trace: Dict[str, Any]) -> List[float]:
    """
    Extract 25 features from raw trace according to SPEC.md Section 5.1.
    Trace format:
    {
      "meta": {"verify_t": ms, "pointer_type": "mouse"|"touch"|"none"},
      "events": [[t_ms, code, x, y], ...]
    }
    """
    meta = trace.get("meta", {})
    verify_t = float(meta.get("verify_t", 0.0))
    pointer_type = str(meta.get("pointer_type", "none")).lower()

    events = trace.get("events", [])
    t_events_total = float(len(events))

    pointer_moves = []
    pointer_clicks_t = []
    keys_t = []
    k_backspaces = 0.0
    t_scrolls = 0.0
    t_focus_changes = 0.0

    for ev in events:
        t = float(ev[0])
        code = int(ev[1])
        x = float(ev[2]) if len(ev) > 2 else 0.0
        y = float(ev[3]) if len(ev) > 3 else 0.0

        if code == 0:
            pointer_moves.append((t, x, y))
        elif code == 1:
            pointer_clicks_t.append(t)
        elif code == 2:
            keys_t.append(t)
        elif code == 3:
            keys_t.append(t)
            k_backspaces += 1.0
        elif code == 4:
            t_scrolls += 1.0
        elif code == 5:
            t_focus_changes += 1.0

    if len(pointer_moves) > 500:
        pointer_moves = pointer_moves[-500:]

    p_n_moves = float(len(pointer_moves))

    if p_n_moves < 2:
        p_path_len = 0.0
        p_straightness = 0.0
        p_speed_mean = 0.0
        p_speed_std = 0.0
        p_speed_max = 0.0
        p_acc_std = 0.0
        p_dir_changes_per_100px = 0.0
        p_pauses = 0.0
        p_dt_std = 0.0
    else:
        dists = []
        dts_ms = []
        speeds = []
        headings = []

        total_path = 0.0
        pauses = 0.0

        for i in range(1, len(pointer_moves)):
            t_prev, x_prev, y_prev = pointer_moves[i - 1]
            t_curr, x_curr, y_curr = pointer_moves[i]

            dx = x_curr - x_prev
            dy = y_curr - y_prev
            dist = math.hypot(dx, dy)
            dt_raw = t_curr - t_prev
            dt_eff = max(dt_raw, 1.0)

            dists.append(dist)
            dts_ms.append(dt_raw)
            total_path += dist

            speed = (dist / dt_eff) * 1000.0
            speeds.append(speed)

            if dt_raw > 150.0:
                pauses += 1.0

            if dist >= 4.0:
                headings.append(math.atan2(dy, dx))

        p_path_len = total_path
        net_disp = math.hypot(pointer_moves[-1][1] - pointer_moves[0][1],
                              pointer_moves[-1][2] - pointer_moves[0][2])
        p_straightness = (net_disp / p_path_len) if p_path_len > 0.0 else 0.0

        p_speed_mean = float(np.mean(speeds))
        p_speed_std = float(np.std(speeds, ddof=0))
        p_speed_max = float(np.max(speeds))

        if len(speeds) >= 2:
            accs = []
            for i in range(1, len(speeds)):
                dt_s = max(dts_ms[i], 1.0) / 1000.0
                accs.append((speeds[i] - speeds[i - 1]) / dt_s)
            p_acc_std = float(np.std(accs, ddof=0))
        else:
            p_acc_std = 0.0

        dir_changes = 0.0
        for i in range(1, len(headings)):
            diff = abs(headings[i] - headings[i - 1])

            while diff > math.pi:
                diff = abs(diff - 2.0 * math.pi)
            if diff > (30.0 * math.pi / 180.0):
                dir_changes += 1.0

        p_dir_changes_per_100px = ((dir_changes / p_path_len) * 100.0) if p_path_len > 0.0 else 0.0
        p_pauses = pauses
        p_dt_std = float(np.std(dts_ms, ddof=0))

    p_clicks = float(len(pointer_clicks_t))
    if p_clicks >= 3:
        click_gaps = [pointer_clicks_t[i] - pointer_clicks_t[i - 1] for i in range(1, len(pointer_clicks_t))]
        p_click_gap_std = float(np.std(click_gaps, ddof=0))
    else:
        p_click_gap_std = 0.0

    k_n = float(len(keys_t))
    if k_n >= 2:
        key_gaps = [keys_t[i] - keys_t[i - 1] for i in range(1, len(keys_t))]
        k_gap_mean = float(np.mean(key_gaps))
        k_gap_std = float(np.std(key_gaps, ddof=0)) if k_n >= 3 else 0.0
    else:
        k_gap_mean = 0.0
        k_gap_std = 0.0

    t_since_mount = verify_t
    if len(events) > 0:
        t_first_interaction = float(events[0][0])
    else:
        t_first_interaction = verify_t

    if len(events) >= 2:
        t_first = float(events[0][0])
        t_last = float(events[-1][0])
        duration = t_last - t_first
        if duration > 0.0:
            num_bins = math.ceil(duration / 100.0)
            occupied_bins = set()
            for ev in events:
                b = int((float(ev[0]) - t_first) / 100.0)
                if b >= num_bins:
                    b = num_bins - 1
                occupied_bins.add(b)
            empty_bins = num_bins - len(occupied_bins)
            t_idle_ratio = float(empty_bins) / float(num_bins)
        else:
            t_idle_ratio = 0.0
    else:
        t_idle_ratio = 0.0

    d_pointer_mouse = 1.0 if pointer_type == "mouse" else 0.0
    d_pointer_touch = 1.0 if pointer_type == "touch" else 0.0
    d_pointer_none = 1.0 if pointer_type == "none" else 0.0

    return [
        p_n_moves,
        p_path_len,
        p_straightness,
        p_speed_mean,
        p_speed_std,
        p_speed_max,
        p_acc_std,
        p_dir_changes_per_100px,
        p_pauses,
        p_dt_std,
        p_clicks,
        p_click_gap_std,
        k_n,
        k_gap_mean,
        k_gap_std,
        k_backspaces,
        t_since_mount,
        t_first_interaction,
        t_idle_ratio,
        t_scrolls,
        t_focus_changes,
        t_events_total,
        d_pointer_mouse,
        d_pointer_touch,
        d_pointer_none,
    ]

