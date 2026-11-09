/**
 * Client-side feature extractor.
 * Implements SPEC.md Section 5.1 with 100% parity with ml/extract.py.
 */

export const FEATURE_NAMES = [
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
];

function mean(arr) {
  if (arr.length === 0) return 0.0;
  let sum = 0.0;
  for (let i = 0; i < arr.length; i++) sum += arr[i];
  return sum / arr.length;
}

function std(arr) {
  if (arr.length === 0) return 0.0;
  const m = mean(arr);
  let sumSq = 0.0;
  for (let i = 0; i < arr.length; i++) {
    const diff = arr[i] - m;
    sumSq += diff * diff;
  }
  return Math.sqrt(sumSq / arr.length);
}

export function extractFeatures(trace) {
  const meta = trace.meta || {};
  const verifyT = Number(meta.verify_t || 0.0);
  const pointerType = String(meta.pointer_type || "none").toLowerCase();

  const events = trace.events || [];
  const tEventsTotal = events.length;

  let pointerMoves = [];
  let pointerClicksT = [];
  let keysT = [];
  let kBackspaces = 0.0;
  let tScrolls = 0.0;
  let tFocusChanges = 0.0;

  for (let i = 0; i < events.length; i++) {
    const ev = events[i];
    const t = Number(ev[0]);
    const code = Number(ev[1]);
    const x = ev.length > 2 ? Number(ev[2]) : 0.0;
    const y = ev.length > 3 ? Number(ev[3]) : 0.0;

    if (code === 0) {
      pointerMoves.push([t, x, y]);
    } else if (code === 1) {
      pointerClicksT.push(t);
    } else if (code === 2) {
      keysT.push(t);
    } else if (code === 3) {
      keysT.push(t);
      kBackspaces += 1.0;
    } else if (code === 4) {
      tScrolls += 1.0;
    } else if (code === 5) {
      tFocusChanges += 1.0;
    }
  }

  // Keep last 500 pointermoves per spec
  if (pointerMoves.length > 500) {
    pointerMoves = pointerMoves.slice(pointerMoves.length - 500);
  }

  const pNMoves = pointerMoves.length;

  let pPathLen = 0.0;
  let pStraightness = 0.0;
  let pSpeedMean = 0.0;
  let pSpeedStd = 0.0;
  let pSpeedMax = 0.0;
  let pAccStd = 0.0;
  let pDirChangesPer100px = 0.0;
  let pPauses = 0.0;
  let pDtStd = 0.0;

  if (pNMoves >= 2) {
    const dists = [];
    const dtsMs = [];
    const speeds = [];
    const headings = [];

    let totalPath = 0.0;
    let pauses = 0.0;

    for (let i = 1; i < pointerMoves.length; i++) {
      const prev = pointerMoves[i - 1];
      const curr = pointerMoves[i];
      const dx = curr[1] - prev[1];
      const dy = curr[2] - prev[2];
      const dist = Math.hypot(dx, dy);
      const dtRaw = curr[0] - prev[0];
      const dtEff = Math.max(dtRaw, 1.0);

      dists.push(dist);
      dtsMs.push(dtRaw);
      totalPath += dist;

      const speed = (dist / dtEff) * 1000.0;
      speeds.append ? speeds.push(speed) : speeds.push(speed);

      if (dtRaw > 150.0) {
        pauses += 1.0;
      }

      if (dist >= 4.0) {
        headings.push(Math.atan2(dy, dx));
      }
    }

    pPathLen = totalPath;
    const netDisp = Math.hypot(
      pointerMoves[pointerMoves.length - 1][1] - pointerMoves[0][1],
      pointerMoves[pointerMoves.length - 1][2] - pointerMoves[0][2]
    );
    pStraightness = pPathLen > 0.0 ? netDisp / pPathLen : 0.0;

    pSpeedMean = mean(speeds);
    pSpeedStd = std(speeds);
    pSpeedMax = speeds.length > 0 ? Math.max(...speeds) : 0.0;

    // Accelerations
    if (speeds.length >= 2) {
      const accs = [];
      for (let i = 1; i < speeds.length; i++) {
        const dtS = Math.max(dtsMs[i], 1.0) / 1000.0;
        accs.push((speeds[i] - speeds[i - 1]) / dtS);
      }
      pAccStd = std(accs);
    }

    // Direction changes > 30 deg between segments >= 4px per 100px path
    let dirChanges = 0.0;
    for (let i = 1; i < headings.length; i++) {
      let diff = Math.abs(headings[i] - headings[i - 1]);
      while (diff > Math.PI) {
        diff = Math.abs(diff - 2.0 * Math.PI);
      }
      if (diff > (30.0 * Math.PI) / 180.0) {
        dirChanges += 1.0;
      }
    }

    pDirChangesPer100px = pPathLen > 0.0 ? (dirChanges / pPathLen) * 100.0 : 0.0;
    pPauses = pauses;
    pDtStd = std(dtsMs);
  }

  // Clicks
  const pClicks = pointerClicksT.length;
  let pClickGapStd = 0.0;
  if (pClicks >= 3) {
    const gaps = [];
    for (let i = 1; i < pointerClicksT.length; i++) {
      gaps.push(pointerClicksT[i] - pointerClicksT[i - 1]);
    }
    pClickGapStd = std(gaps);
  }

  // Keys
  const kN = keysT.length;
  let kGapMean = 0.0;
  let kGapStd = 0.0;
  if (kN >= 2) {
    const gaps = [];
    for (let i = 1; i < keysT.length; i++) {
      gaps.push(keysT[i] - keysT[i - 1]);
    }
    kGapMean = mean(gaps);
    if (kN >= 3) {
      kGapStd = std(gaps);
    }
  }

  // Timing
  const tSinceMount = verifyT;
  const tFirstInteraction = events.length > 0 ? Number(events[0][0]) : verifyT;

  // Idle ratio
  let tIdleRatio = 0.0;
  if (events.length >= 2) {
    const tFirst = Number(events[0][0]);
    const tLast = Number(events[events.length - 1][0]);
    const duration = tLast - tFirst;
    if (duration > 0.0) {
      const numBins = Math.ceil(duration / 100.0);
      const occupied = new Set();
      for (let i = 0; i < events.length; i++) {
        let b = Math.floor((Number(events[i][0]) - tFirst) / 100.0);
        if (b >= numBins) b = numBins - 1;
        occupied.add(b);
      }
      tIdleRatio = (numBins - occupied.size) / numBins;
    }
  }

  const dPointerMouse = pointerType === "mouse" ? 1.0 : 0.0;
  const dPointerTouch = pointerType === "touch" ? 1.0 : 0.0;
  const dPointerNone = pointerType === "none" ? 1.0 : 0.0;

  return [
    pNMoves,
    pPathLen,
    pStraightness,
    pSpeedMean,
    pSpeedStd,
    pSpeedMax,
    pAccStd,
    pDirChangesPer100px,
    pPauses,
    pDtStd,
    pClicks,
    pClickGapStd,
    kN,
    kGapMean,
    kGapStd,
    kBackspaces,
    tSinceMount,
    tFirstInteraction,
    tIdleRatio,
    tScrolls,
    tFocusChanges,
    tEventsTotal,
    dPointerMouse,
    dPointerTouch,
    dPointerNone,
  ];
}

