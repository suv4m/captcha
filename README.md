# Adaptive and Accessible CAPTCHA using AIML

A self-hosted, privacy-minimised, accessibility-first CAPTCHA framework powered by calibrated machine learning risk estimation and expected-cost decision theory.

---

## 1. What It Is

Conventional CAPTCHAs deliver uniform, high-friction challenges that disproportionately lock out users with disabilities. This system reimagines verification:
- **Accessibility as a Hard Constraint:** Challenges are selected per session based on declared assistive needs. Accessibility is never traded for security ($C(A)$ is never empty).
- **Privacy by Construction:** Raw coordinates, keystroke strings, and device fingerprints never leave the browser. The live client extracts and sends only 8 numerical timing features (~68 bytes).
- **AIML Risk Estimation:** A probability-calibrated Random Forest model evaluates session automation risk $p \in [0, 1]$.
- **Expected-Cost Decision Engine:** Dynamically selects the optimal challenge $c^*$ minimizing $J(c) = (1 - p) \cdot [T(c)/10 + 3 \cdot (1 - S_h(c))] + p \cdot B \cdot S_b(c)$, where the constant 3 is a missed-pass friction penalty in equivalent seconds of user frustration, chosen arbitrarily by the authors.

Delivered as:
- **SDK:** Embeddable vanilla Web Component `<adaptive-captcha>` (Shadow DOM, framework-agnostic).
- **Service:** High-performance FastAPI backend (`/api/siteverify`, `/api/session`, `/api/challenge/verify`).
- **Demo & Lab:** Sign-in portal with real-time decision trace, and an interactive policy research lab at `/lab`.

---

## 2. How Users with Disabilities Reach the Right Challenge

Accessibility is treated as a hard constraint without forcing users to disclose personal medical details upfront:

1. **Direct In-Challenge Alternative Buttons (Zero-Declaration Flow):**
   - Whenever any challenge renders, the first focusable element immediately following the prompt is the **"Use a different challenge"** row.
   - It provides one-click / one-keypress alternative buttons (e.g., **Audio**, **Visual**, **Drag**, **Automatic**) to instantly swap to an alternative modal format without requiring prior disclosure.
   - The backend `/api/challenge/switch` endpoint supports an optional `target_type` parameter, allowing the engine to calculate and present the optimal calibrated level for that specific type. Up to 2 swaps per session are supported.

2. **Screen-Reader & Keyboard Traversal:**
   - On challenge appearance or transition, focus is programmatically shifted to the challenge title/prompt (`tabindex="-1"`), and the status is announced to assistive tech via `aria-live` (e.g., *"Visual challenge. Press Tab for an audio alternative."*).
   - A single `Tab` keypress lands directly on the alternative button row, enabling blind or keyboard-only users to immediately pivot to their preferred verification mode.

3. **Optional Persistent Preferences ("Remember on this device"):**
   - Users who choose to explicitly set access needs (Vision, Hearing, Motor, Cognitive) can opt into **"Remember on this device"**.
   - This preference is strictly stored in client-side `localStorage` (`captcha_access_needs`) and is never sent to backend event logs or `/api/collect`.

---

## 3. Architecture

```
captcha-aiml/
  run.py               # Single entry point: trains if needed, boots uvicorn server
  requirements.txt     # Pinned Python dependencies
  SPEC.md              # Build and technical specification
  README.md            # System documentation and empirical summaries
  ml/
    features.json      # Single source of truth: 25 features, order, definitions
    simulate.py        # Synthetic human and bot trace generators
    extract.py         # Pure-Python feature extractor
    train.py           # Classifier comparison, calibration, feature pruning
    evaluate.py        # Four-policy Monte Carlo benchmark (P0 to P3)
    artifacts/         # risk_full.joblib, risk_min.joblib, metrics.json, results.json
  backend/app/
    main.py            # FastAPI service with OpenAPI endpoints
    config.py          # Cross-platform environment configuration
    schemas.py         # Pydantic v2 schemas
    store.py           # In-memory session store & SQLite event audit log
    tokens.py          # HMAC-SHA256 single-use verification tokens
    decision.py        # Mathematical decision engine minimizing J(c)
    risk.py            # Calibrated inference engine
    catalog.json       # Assumed challenge parameters (T, Sh, Sb, incompatibilities)
    challenges/        # visual.py, audio.py, drag.py, pow.py
    assets/digits/     # 16-bit PCM WAV audio clips (0.wav ... 9.wav)
  widget/
    adaptive-captcha.js # Shadow DOM custom element
    features.js        # Vanilla ES module extractor (100% parity with extract.py)
  web/
    index.html         # Interactive demo sign-in form & decision trace
    lab.html           # Empirical benchmark dashboard & live simulator
    styles.css         # Design system tokens targeting WCAG 2.1 AA
    chart.js           # Zero-dependency inline SVG charting engine
  scripts/
    make_digit_clips.py # SAPI / WAV synthesis generator
    bot_demo.py         # Synthetic attacker evaluation CLI
    curl_demo.py        # End-to-end curl verification harness
    capture_screenshots.py # Playwright automated visual regression
  tests/               # Unit, invariant, API, parity, and E2E test suites
  docs/
    VERIFICATION.md    # Real command execution outputs for all Gates
    DECISIONS.md       # Architecture Decision Records (ADRs)
    DEMO_SCRIPT.md     # 3-minute evaluation walkthrough script
    screens/           # 8 visual screenshots (375px & 1280px in light/dark)
```

---

## 3. Quick Start

### Prerequisites
- Python 3.10+ (tested on Python 3.14.3)
- Node.js 18+ (tested on v24.13.0)

### Run Server
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Boot application (automatically trains ML models if artifacts are missing)
python run.py
```
Visit:
- **Demo Portal:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Research Lab:** [http://127.0.0.1:8000/lab](http://127.0.0.1:8000/lab)
- **OpenAPI Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 4. Test Commands

```bash
# Unit & Sanity checks (Gate G0)
pytest -v tests/test_phase0_sanity.py

# Extractor & ML Sanity checks (Gate G1)
pytest -v tests/test_extract.py tests/test_phase1_gate.py

# Invariants & API Contract checks (Gate G2)
pytest -v tests/test_invariants_10_1.py tests/test_challenges_and_tokens_10_1.py tests/test_api_flow_10_3.py

# Feature Parity between Python and JS (Gate G3)
node --test tests/test_parity.js

# Lab & Simulation Endpoints (Gate G4)
pytest -v tests/test_lab_endpoints.py

# End-to-End Scenarios & Contrast Verification (Gate G5)
pytest -v tests/test_e2e_scenarios_10_5.py tests/contrast_check.py

# Full test suite in one command
pytest -v
```

---

## 5. Policy Benchmark Results (Simulation)

Evaluated across 6,000 held-out test sessions (3,000 humans, 3,000 bots) over 20 seeded Monte Carlo runs ($B = 2.0$ default sweep reference):

| Policy | Model / Features | Privacy (Bytes) | Human Pass Rate | Mean Time | Security ($1 - \text{BotPass}$) | A11y Violations |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **P0: Fixed** | None (`vis2` for all) | 0 B | 88.4% $\pm$0.5% | 10.1 s | 65.0% | **5.60%** |
| **P1: Adaptive (Unconstrained)** | FULL (25 feats) | 216 B | 100.0% $\pm$0.0% | 0.0 s | 50.7% | **0.00%** |
| **P2: Adaptive + Accessible** | FULL (25 feats) | 216 B | 100.0% $\pm$0.0% | 0.0 s | 50.7% | **0.00%** |
| **P3: Adaptive + Accessible + Private** | MIN (8 feats) | **68 B** | **100.0% $\pm$0.0%** | **0.0 s** | **50.6%** | **0.00%** |

### Key Findings
1. **Accessibility Without Security Trade-off:** By treating user accessibility needs as a hard filter before expected-cost minimization, **P2 and P3 completely eliminate accessibility violations (0.00%)** while eliminating friction for typical users (mean time 0.0s).
2. **Privacy Pruning:** Pruning from 25 features to 8 features (P3) reduces payload size by **68.5%** (from 216 bytes to 68 bytes) with identical human pass rate (100.0%) and virtually identical security (50.6% vs 50.7%).
3. **Replay Guard:** Exact match feature replay detection achieves **100.0% detection rate** within the 300-second session TTL without false positives on legitimate human autofill.

---

## 6. Assumptions Table

All numbers in this benchmark are derived from a simulated population under parametric assumptions:

| Parameter Category | Assumed Value / Distribution | Rational & Reference |
| :--- | :--- | :--- |
| **Disability Prevalence** | Vision 6%, Hearing 4%, Motor 6%, Cognitive 4% | Assumed values chosen by the authors. |
| **Incompatible Penalty** | $S_h = 0.12$, $T = 45.0\text{ s}$ | Estimated penalty when a user with severe impairment is forced onto an incompatible challenge. |
| **Catalog Human Friction** | `pow`: 0.2–3s ($S_h=0.96-0.99$), `visual`: 5–12s ($S_h=0.88-0.97$), `audio`: 12–22s ($S_h=0.78-0.93$), `drag`: 5–12s ($S_h=0.85-0.97$) | Assumed values chosen by the authors. |
| **Bot Solve Probability** | `pow`: $S_b=0.50-0.85$, `visual`: $S_b=0.15-0.55$, `audio`: $S_b=0.20-0.55$, `drag`: $S_b=0.18-0.50$ | Parametric vulnerability models against automated solvers. |
| **Default Breach Cost ($B$)** | 2.0 (Range: 1.0 to 100.0) | Balances human friction against automated account takeover risk. |

---

## 7. Limitations & Honest Disclosures

1. **Simulated Data:** All behavioral event traces are synthetically generated using biomechanical velocity profiles, log-normal pause models, and Gaussian jitter. Real-world bot behavior incorporates sophisticated browser automation frameworks and human CAPTCHA-solving farms not captured in this distribution.
2. **Parametric Security:** Security rates ($1 - \text{BotPass}$) are calculated from assumed catalog solve rates ($S_b$). They should not be interpreted as empirical guarantees against determined adversarial attacks.
3. **Generalization to Unseen Attackers:** When tested against the held-out `humanized` bot (cubic Bezier curves with easing), single-session classifier recall is **0.0%** at $p > 0.5$ (mean risk score 0.0015). Classic automation (instant, linear, noisy) is detected at 99.8%–100.0% recall, but mimicry of human kinematic trajectories requires multi-signal defense in depth.
4. **Assistive Disparity:** Subgroup false-positive rates on the MIN model at $p > 0.5$ are:
   - `desktop_mouse`: 0.00%
   - `touch_mobile`: 0.00%
   - `motor_tremor`: 0.00%
   - `keyboard_assistive`: 0.00%
   - `autofill_desktop`: 0.00%
   Replay bot detection is handled deterministically by the replay guard (100.0% catch rate on identical features within TTL).


