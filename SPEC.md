# Build Spec: Adaptive and Accessible CAPTCHA using AIML

Agent-facing spec for a 5 to 6 hour build. Read all of it before writing code. Priority: everything shipped works and is verified. Fewer features is acceptable. Unverified features are not.

## 0. Operating rules (non-negotiable)

1. **Evidence over claims.** A task is done only after you ran its verification command and saw it pass. Append the command and trimmed real output to `docs/VERIFICATION.md`. Never write "should work".
2. **Phases and gates.** Follow Section 9 in order. Do not start a phase until the previous gate passes.
3. **Fixed scope.** Build only what Section 8 lists. If behind schedule, cut in the stated order. Never cut: gates, accessibility constraints, honesty labels.
4. **Pinned stack.** Use only Section 3. Check installed versions first and adapt to API differences (especially scikit-learn).
5. **Offline at runtime.** No CDNs, remote fonts, or remote APIs. Everything runs offline after `pip install`.
6. **Honesty.** All security and ML numbers come from a simulated population with assumed parameters. Label them "simulation" in the UI, README and results. Never claim real-world bot resistance.
7. **Safety.** Do not build or run anything that solves CAPTCHAs or attacks real services. "Bots" are synthetic behaviour-trace generators plus a parametric success model. Playwright drives localhost only.
8. **When blocked:** find the root cause, try at most 2 fixes, then use the fallback in Section 10.4 and log it in `docs/DECISIONS.md`. Never silently weaken a requirement.
9. **Cross-platform** (Windows, macOS, Linux): use `pathlib`, no bash-only syntax, no `make`.
10. **Answers never reach the client.** No challenge solution may appear in any API response or DOM.

## 1. Product

A self-hosted CAPTCHA framework delivered as:

- **SDK:** an embeddable web component `<adaptive-captcha>` (framework-agnostic, Shadow DOM).
- **Service:** a FastAPI backend with a verification API (`/api/siteverify`, reCAPTCHA-style).
- **Demo site:** a sign-in form with a live decision-trace panel, plus a **Lab** page with experiment results.

Instead of giving everyone the same challenge, the system decides per session how much verification is needed and which challenge the person can actually use.

**Research question:** does ML-driven adaptive selection, with accessibility as a hard constraint and privacy-minimised features, improve the security vs usability trade-off compared with a fixed CAPTCHA?

## 2. Core idea and decision logic

Pipeline per session: **Accessibility filter → Risk model → Expected-cost selection.** Accessibility is a constraint, never traded for security.

1. `A` = needs declared by the user, subset of `{vision, hearing, motor, cognitive}`.
2. `C(A)` = catalog entries compatible with `A`. Proof-of-work is compatible with everyone, so `C(A)` is never empty. If `cognitive` is in `A`, drop all level-3 entries.
3. `p` = calibrated probability the session is automated, from the risk model.
4. Choose `c*` = argmin over `C(A) ∪ {none}` of `J(c) = (1-p) * [T(c)/10 + 3*(1-Sh(c))] + p * B * Sb(c)` where `T` is human seconds, `Sh` human success, `Sb` bot success, `B` the breach cost (default 60; UI "Strictness" maps 20 to 200). Break ties by lower `T`.
5. If `p > 0.5` and the chosen `Sb > 0.45` (accessible set is weak), set `step_up_suggested = true` and show a note that the site should add extra verification.

**Catalog** (assumed values, stored in `backend/app/catalog.json`, labelled as assumptions everywhere):

| id | type | level | T (s) | Sh | Sb | incompatible with |
| --- | --- | --- | --- | --- | --- | --- |
| none | none | - | 0 | 1.00 | 1.00 | - |
| pow1 / pow2 / pow3 | pow | 1 / 2 / 3 | 0.2 / 0.8 / 3 | .99 / .98 / .96 | .85 / .65 / .50 | - |
| vis1 / vis2 / vis3 | visual | 1 / 2 / 3 | 5 / 8 / 12 | .97 / .93 / .88 | .55 / .35 / .15 | vision |
| aud1 / aud2 / aud3 | audio | 1 / 2 / 3 | 12 / 16 / 22 | .93 / .87 / .78 | .55 / .35 / .20 | hearing |
| drg1 / drg2 / drg3 | drag | 1 / 2 / 3 | 5 / 8 / 12 | .97 / .93 / .85 | .50 / .30 / .18 | vision, motor |

When a policy ignores accessibility and shows an incompatible challenge to a human with that need, use `Sh = 0.12`, `T = 45` (assumed penalty).

**Invariants** (must be tested, see 10.1):

- I1: `c*` is always in `C(A)`.
- I2: for fixed `A` and `B`, challenge strength (lower `Sb`) never decreases as `p` increases.
- I3: `C(A)` is non-empty for all 16 need subsets.
- I4: at `p=0` the default `B` yields `none`; at `p=1` it yields the lowest-`Sb` allowed entry.
- I5: raising `B` never weakens the choice.

**Tuning step:** print a policy curve for `p` in `{0, .01, .02, .05, .1, .2, .4, .7, 1}` for `A={}`, `{vision}`, `{vision, hearing}`. It must progress from none to easy to medium to hard. If degenerate (for example it never picks easy), adjust catalog numbers, not the formula, and log it.

**User-initiated escape:** every challenge shows "Try a different challenge" (max 2 swaps per session). The engine re-runs with the current type excluded. Swaps are logged as a usability signal.

## 3. Form factor and stack

One repo, one process, one port (8000): FastAPI serves the API and the static frontend.

- **Backend:** Python 3.10+, FastAPI, uvicorn, pydantic v2, numpy, pandas, scikit-learn, joblib, Pillow, pytest, httpx, sqlite3 (stdlib). Optional: xgboost (skip if the install is not trivial).
- **Frontend:** vanilla ES2020 modules, Web Components, Shadow DOM, CSS variables. No framework, no bundler, no CDN.
- **Testing:** pytest, `node --test` (Node 18+) for the JS feature parity test, Playwright (Python, Chromium) for end-to-end tests.
- **Run:** `python run.py` trains the model if artifacts are missing (target under 90 s), then starts the server.

## 4. Architecture

```
captcha-aiml/
  run.py  requirements.txt  README.md  SPEC.md
  ml/
    features.json        # single source of truth: 25 features, order, definitions
    simulate.py          # synthetic humans and bots as raw event traces
    extract.py           # Python feature extractor
    train.py             # compare, select, calibrate, export, metrics
    evaluate.py          # policy simulation P0-P3 -> results.json, test_scores.npz
    artifacts/           # risk_full.joblib risk_min.joblib metrics.json results.json feature_sets.json
  backend/app/
    main.py config.py schemas.py store.py tokens.py risk.py decision.py catalog.json
    challenges/ visual.py audio.py drag.py pow.py
    assets/digits/0.wav ... 9.wav
  widget/ adaptive-captcha.js  features.js
  web/ index.html  lab.html  styles.css  chart.js
  scripts/ make_digit_clips.py  bot_demo.py
  tests/ unit, api, parity, e2e, fixtures
  docs/ VERIFICATION.md  DECISIONS.md  DEMO_SCRIPT.md  screens/
```

Data flow: widget collects interaction events in memory → computes only the features the server asks for (`required_features`) → `POST /api/session` with features and declared needs → server filters, scores, selects → returns pass or a challenge → user solves → `POST /api/challenge/verify` → single-use signed token → site backend calls `/api/siteverify`.

Privacy by construction: raw coordinates and key identities never leave the browser. Only the numeric feature vector is sent (about 8 numbers in default mode). Declared accessibility needs are held in memory for the session only and are never written to logs or the database.

## 5. Contracts

### 5.1 Features (`ml/features.json`, 25, fixed order)

Trace format: `{"meta": {"verify_t": ms, "pointer_type": "mouse"|"touch"|"none"}, "events": [[t_ms, code, x, y], ...]}` with codes 0 pointermove, 1 pointerdown, 2 keydown, 3 Backspace keydown, 4 scroll, 5 focusin. Keep the last 500 pointermoves. Key identity is never recorded, except code 3 for Backspace.

| # | name | definition |
| --- | --- | --- |
| 1 | p\_n\_moves | count of pointermoves |
| 2 | p\_path\_len | sum of segment lengths (px) |
| 3 | p\_straightness | net displacement / path length, 0 if path is 0 |
| 4 | p\_speed\_mean | mean segment speed (px/s), speed = dist/max(dt,1ms)\*1000 |
| 5 | p\_speed\_std | population std (ddof=0) of speeds |
| 6 | p\_speed\_max | max speed |
| 7 | p\_acc\_std | std of (speed\_i - speed\_{i-1}) / dt\_i(s) |
| 8 | p\_dir\_changes\_per\_100px | count of heading changes over 30° between segments of length ≥ 4 px, per 100 px of path |
| 9 | p\_pauses | count of inter-move gaps over 150 ms |
| 10 | p\_dt\_std | std of inter-move intervals (ms) |
| 11 | p\_clicks | count of pointerdown |
| 12 | p\_click\_gap\_std | std of gaps between clicks (ms), 0 if under 3 clicks |
| 13 | k\_n | count of codes 2 and 3 |
| 14 | k\_gap\_mean | mean gap between key events (ms), 0 if under 2 keys |
| 15 | k\_gap\_std | std of gaps, 0 if under 3 keys |
| 16 | k\_backspaces | count of code 3 |
| 17 | t\_since\_mount | meta.verify\_t (ms) |
| 18 | t\_first\_interaction | time of first event, or verify\_t if none |
| 19 | t\_idle\_ratio | fraction of 100 ms bins with no event between first and last event, 0 if under 2 events |
| 20 | t\_scrolls | count of code 4 |
| 21 | t\_focus\_changes | count of code 5 |
| 22 | t\_events\_total | number of events |
| 23 | d\_pointer\_mouse | 1 if pointer\_type is mouse |
| 24 | d\_pointer\_touch | 1 if pointer\_type is touch |
| 25 | d\_pointer\_none | 1 if pointer\_type is none |

With fewer than 2 pointermoves, all pointer-motion features (2 to 10) are 0. `webdriver` flags and device fingerprints are **excluded** by design (spoofable, and they would inflate results).

### 5.2 API (Pydantic models, OpenAPI at `/docs`)

- `GET /api/config` returns `{required_features, version, mode}`.
- `POST /api/session` takes `{site_key, features, access_needs[], policy?}` and returns `{session_id, action: "pass"|"challenge", token?, challenge?, trace}`. `trace` holds `p`, band, allowed ids, top 3 candidate costs, chosen id, `B`, `step_up_suggested`, and `data_sent_bytes`.
- `POST /api/challenge/verify` takes `{session_id, challenge_id, answer, interaction:{duration_ms}}` and returns `{ok, token?, attempts_left, locked}`.
- `POST /api/challenge/switch` takes `{session_id}` and returns a new challenge.
- `GET /api/challenge/{id}/audio` returns `audio/wav` with `Cache-Control: no-store`.
- `POST /api/siteverify` takes `{token}` and returns `{success, challenge_type, band, ts}`. Tokens are HMAC-SHA256 signed, single-use, 120 s TTL.
- `POST /api/demo/login` is the demo site backend; it calls siteverify server-side.
- `GET /api/lab/results` and `GET /api/lab/simulate?policy=P3&breach_cost=60&runs=20`.
- `POST /api/collect` is opt-in research contribution (features plus a human label, no needs, no IDs) appended to `data/collected.jsonl`.
- `GET /api/health`.
- Test hook `GET /api/_test/secret/{challenge_id}` exists **only** when `CAPTCHA_TEST_MODE=1` and returns 404 otherwise.

Rules: sessions live in memory with a 5 min TTL; 3 attempts per session (a fresh challenge of the same type after 2 failures; lock after 3); solves faster than 400 ms fail as automation; the persistent log (SQLite) stores only time, band, type, level, outcome, duration, swap count.

## 6. Component specs

### 6.1 Simulator (`ml/simulate.py`)

Generates raw traces, never features, so the real extractor is exercised. Seeded; train, validation and test use disjoint seeds.

- **Human subgroups:** `desktop_mouse` (bell-shaped speed profile, lateral noise, log-normal pauses, log-normal key gaps around 180 ms); `touch_mobile` (short strokes, scrolls, touch type); `keyboard_assistive` (no pointer events, tab-driven focus changes, slower and more variable typing); `motor_tremor` (slow, jittery, many direction changes and pauses, extra backspaces).
- **Bot types:** `instant` (no pointer, near-zero time, instant or no key events); `linear` (straight constant-speed moves, fixed intervals); `noisy` (linear plus Gaussian jitter and uniform intervals); `humanized` (Bezier path, easing, log-normal timing, pauses: the hard case); `replay` (a recorded human trace with ±5% time and ±1 px noise).
- Parameter ranges of humans and bots **must overlap** so the task is not trivial.
- Sizes: train 6000 humans and 6000 bots, validation 1500 and 1500, test 3000 and 3000.
- Test humans carry assumed needs (configurable: vision 6%, hearing 4%, motor 6%, cognitive 4%, random combinations), documented as assumptions.

### 6.2 ML (`ml/train.py`, `ml/evaluate.py`)

- Train on bots `instant, linear, noisy, replay`. **`humanized` is held out of training** and appears only in test to measure generalisation to an unseen attacker.
- Compare RandomForest (300 trees, `min_samples_leaf=3`, balanced), LogisticRegression (scaled), SVM-RBF (probability on), HistGradientBoosting (and xgboost if available) on the same split.
- Final model: RandomForest, probability-calibrated on validation (isotonic or sigmoid; in recent scikit-learn use the frozen-estimator pattern, check the installed version).
- Two feature sets: **FULL** (25) and **MIN** (8, chosen by permutation importance on validation, then retrained). Save `risk_full.joblib`, `risk_min.joblib`, `feature_sets.json`. The live service defaults to MIN.
- `metrics.json` must contain: ROC-AUC, PR-AUC, TPR at 1% FPR, Brier score and ECE; model comparison table; recall per bot type (including unseen `humanized`); false-positive rate per human subgroup for FULL and MIN; AUC vs number of features for k in `{4, 6, 8, 12, 25}`; ROC curve points.
- `evaluate.py` simulates four policies on the held-out test population, 20 seeded runs, mean and std:
  - **P0 Fixed:** everyone gets `vis2`, no model, 0 bytes.
  - **P1 Adaptive:** FULL model, selection ignores `A`.
  - **P2 Adaptive + Accessible:** FULL model, filter by `A`.
  - **P3 Adaptive + Accessible + Private:** MIN model, filter by `A`.
  - Metrics: human pass rate, mean human time, bot pass rate (security is `1 - this`), challenge-free rate, accessibility-violation rate, human block rate by subgroup, bytes collected per session.
- Save per-session scores to `test_scores.npz` so `/api/lab/simulate` can recompute any `B` in under 100 ms (vectorised numpy).

### 6.3 Challenges (each module: `create(level, rng) -> (public, secret)`, `verify(secret, answer, interaction) -> bool`)

- **Visual:** Pillow renders a 3×3 grid of 120 px tiles as data URIs. Each tile has a shape (circle, triangle, square, star, hexagon, cross), random fill, rotation, and noise or distractors scaling with level. Prompt: "Select every tile containing a \[shape\]". Differentiate by shape, never by colour alone. 2 to 4 targets. Secret: target indices.
- **Audio:** concatenate pre-rendered digit clips with random gaps (0.25 to 0.6 s), ±8% resampling, and background noise at SNR 20 / 12 / 6 dB for levels 1 to 3. Lengths 4 / 5 / 6 digits. Max 3 replays. Secret: the digits.
- **Drag (slider puzzle):** Pillow renders a procedural textured scene with a puzzle-shaped hole and a separate piece image. The user drags the piece horizontally; the client sends the final x. Level 3 adds decoy holes and a tighter tolerance. Must also work by keyboard (`role="slider"`, arrow keys, Enter). Secret: hole x.
- **PoW:** server sends `nonce` and `bits` (levels 1 to 3 start at 12 / 15 / 17; measure on this machine and adjust so the times in the catalog are roughly true). The client finds `counter` with `SHA-256(nonce + ":" + counter)` having at least `bits` leading zero bits, in a Web Worker. Server verification is O(1).
- `scripts/make_digit_clips.py` renders the 10 clips with the first available TTS engine: `espeak-ng`, then `pyttsx3`, then macOS `say`. The clips must end as 16-bit PCM mono WAV (verify with the `wave` module, non-silent by RMS, 0.3 to 1.2 s each). If no engine works, tell the user exactly what to install. Only if that fails use the contingency: audio level encodes a count of beeps, flagged `audio_mode: beeps` in the README limitations.

### 6.4 Widget (`widget/adaptive-captcha.js`)

- Attributes `endpoint`, `site-key`, `policy` (demo only). Method `verify()` returns a Promise of a token. Events `captcha-verified`, `captcha-failed`, `captcha-error`.
- Collector: passive listeners on `document` from `connectedCallback`, ring buffer in memory, nothing persisted. Stops at verify and is cleared afterwards. Accepts untrusted events (for demos and tests).
- `features.js` is an ES module usable in browser and Node, implementing Section 5.1 exactly.
- States: idle, checking, passed (silent pass allowed), challenge, error, locked. Collapsible "Accessibility options" with four checkboxes and clear wording. A visible privacy line: "Sends N numbers (X bytes) about your interaction timing. No keystrokes, text or movement path." computed from the real payload.
- Keyboard and screen reader support for every challenge, `aria-live` status, focus management when the challenge changes.

### 6.5 Pages

- **Demo (`/`)**: left, a realistic sign-in form with the widget; right, a "Decision trace" panel (monospace): risk bar and value, allowed set as chips, top 3 candidate costs, chosen challenge, bytes sent, step-up note; controls for policy P0 to P3 and the Strictness slider; a toggle to hide the panel.
- **Lab (`/lab`)**: banner "Simulated population, assumed parameters". Sections: (1) four-policy table; (2) live Strictness slider re-running the simulation, with a security vs human-effort chart; (3) model comparison table and ROC; (4) false-positive rate by human subgroup, FULL vs MIN; (5) AUC vs feature count; (6) recall per bot type with the unseen attacker highlighted. At most 4 charts, drawn as inline SVG by one helper (`chart.js`: bars and lines).

## 7. UI design spec (minimal, modern, not AI-slop)

- **Tokens:** light bg `#FAFAF8`, surface `#FFFFFF`, border `#E6E4DF`, text `#1A1A1A`, muted `#6B6B66`, accent `#0B6B5D` (single accent), danger `#B3261E`. Dark (via `prefers-color-scheme`): bg `#111113`, surface `#1A1A1D`, border `#2A2A2E`, text `#ECECEC`, muted `#9A9AA0`, accent `#3CB8A2`. All text meets WCAG AA (4.5:1), checked by `tests/contrast_check.py` over the token pairs.
- **Type:** system stack (`ui-sans-serif, system-ui, "Segoe UI", Roboto, sans-serif`), mono `ui-monospace, "SF Mono", Consolas, monospace`. Scale 13 / 15 / 17 / 22 / 30 px; weights 400, 500, 600. Sentence case everywhere.
- **Space and shape:** 4 px grid; 8 px radius controls, 12 px cards; 1 px borders; no shadows except a 2 px focus ring with offset; max content width 1080 px; left-aligned layouts.
- **Motion:** 120 ms ease for state changes only; honour `prefers-reduced-motion`.
- **Forbidden:** gradients, glassmorphism, blur, glow, emoji as icons, stock illustrations, hero banners, purple or blue-violet palettes, pill-shaped everything, centred-everything layouts, "AI-powered ✨" copy, decorative animation. Icons: inline SVG, 1.5 px stroke, only where they carry meaning.
- **Copy:** plain and specific ("Verify", "Try a different challenge"). Error messages say what happened and what to do.
- Responsive from 360 px. The widget is 300 to 360 px wide, 1 px border, 10 px radius. Design every state (loading, error, locked, passed).

## 8. Scope

**Must:** `features.json`, simulator, Python and JS extractors with parity; training with calibration, FULL and MIN, `metrics.json`; decision engine with invariants; API with all four challenge types and tokens; widget with collector and all renderers; demo page with decision trace; `evaluate.py` with P0 to P3 and a Lab page showing results; README, VERIFICATION.md, DECISIONS.md, DEMO\_SCRIPT.md.

**Should:** live Strictness slider on Lab; per-subgroup and unseen-attacker panels; Playwright e2e suite; `scripts/bot_demo.py` (linear, bezier, replay; headed option); collect mode; contrast check; screenshots.

**Could:** dark mode; xgboost; merging real collected samples into evaluation as a clearly labelled "real sanity set".

**Cut order if behind:** dark mode → bot\_demo → collect mode → xgboost and SVM (keep RF and LR) → interactive slider (keep static table) → drag level 3 → AUC-vs-features curve. Do not add anything not listed.

## 9. Phases and gates (total about 6 h)

| Phase | Time | Work | Gate |
| --- | --- | --- | --- |
| P0 | 0:00 to 0:25 | Preflight (Python, Node, pip, Playwright availability), venv, requirements, tree, `features.json`, `catalog.json`, health endpoint | G0: imports work, `/api/health` returns 200, `pytest` collects |
| P1 | 0:25 to 1:35 | Simulator, extractor, training, metrics, parity fixtures | G1: artifacts exist; all 10.2 checks pass |
| P2 | 1:35 to 2:35 | Decision engine, four challenges, tokens, API | G2: 10.1 and 10.3 green; full flow shown with curl for each type |
| P3 | 2:35 to 4:00 | `features.js`, widget, demo page | G3: parity test green; manual walk-through of each type via browser tool |
| P4 | 4:00 to 4:50 | `evaluate.py`, lab endpoints, Lab page | G4: policy table plausible; slider updates live |
| P5 | 4:50 to 5:40 | E2E, a11y, screenshots reviewed against Section 7, README, fresh-clone test | G5: 10.5 and 10.7 pass |
| P6 | 5:40 to 6:00 | Buffer, final report, freeze | all gates re-run once |

If a phase ends more than 20 minutes late, apply the cut order immediately.

## 10. Verification protocol (decoupled: checks must not reuse the code they test)

**10.1 Unit (pytest):** all five invariants as property tests over all 16 need subsets × a `p` grid × several `B`; extractor edge cases (empty trace, one event, no keys, no pointer); token tamper, expiry, replay; each challenge accepts the correct answer and rejects wrong ones; attempts, lock and the 400 ms rule; **no response body contains any secret** (search every API response for the secret values).

**10.2 ML sanity:**

- Train, validation and test seeds are disjoint (assert).
- Label-shuffle test: AUC within 0.5 ± 0.05.
- If any test AUC is at or above 0.995, treat it as a defect (leakage or trivial simulator) and increase overlap before continuing.
- ECE reported; target at most 0.06.
- `humanized` recall is reported honestly even if low.
- Same seed gives identical `metrics.json`.
- Subgroup false-positive table printed. If `keyboard_assistive` or `motor_tremor` is much worse than `desktop_mouse`, say so in the README rather than hiding it.

**10.3 API contract:** FastAPI TestClient runs the full flow for each type, using in-process access to the store for secrets in tests only.

**10.4 Fallbacks:** xgboost missing → skip; TTS missing → Section 6.3 contingency; node missing → run the parity check via Playwright `page.evaluate`; Playwright missing → browser-tool screenshots plus API tests, noted in the log; training slow → reduce sizes proportionally; scikit-learn API change → adapt and log.

**10.5 End-to-end (Playwright, `CAPTCHA_TEST_MODE=1`, server as a subprocess):**

- Each challenge type solved through the real UI (the solver fetches the answer via the test hook; also assert the hook returns 404 without the env var).
- A linear scripted bot is routed to a strong challenge or locked; a bezier bot is reported honestly.
- A keyboard-only run completes a challenge using only the keyboard.
- With `vision` declared, 30 sessions never produce visual or drag challenges; with `vision` and `hearing` declared, only PoW is produced and the step-up note appears at high risk.
- Screenshots at 375 px and 1280 px in light and dark are saved to `docs/screens/`. **Open the images and critique them against Section 7**, then fix defects.

**10.6 Adversarial review:** at the end of each phase, switch to reviewer mode: re-read the relevant spec section, list at least 5 ways the work could be wrong or incomplete, test each, and record results in VERIFICATION.md.

**10.7 Fresh clone:** copy the repo to a new folder, create a new venv, `pip install -r requirements.txt`, `python run.py`, `pytest -q`, node parity test, and open the demo end to end. Paste the outputs.

## 11. Deliverables and definition of done

- Running system: `python run.py` serves the demo at `/` and Lab at `/lab`.
- `README.md`: what it is, quick start, architecture, test commands, results summary, an assumptions table (catalog values, needs prevalence, simulator parameters), and a limitations section (simulated data, parametric security, small real sample if any).
- `docs/VERIFICATION.md` with real command output for every gate; `docs/DECISIONS.md`; `docs/DEMO_SCRIPT.md` (a 3-minute walkthrough: low-risk silent pass, bot routed to a strong challenge, `vision` declared gives audio, strictness slider, Lab table).
- `ml/artifacts/metrics.json` and `results.json`.
- All tests green on a fresh clone.

## 12. Report format after every phase (15 lines max)

Built, gate commands with pass or fail, deviations and why, risks found by the review pass, next step. Do not continue past a failed gate.
