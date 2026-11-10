# Verification Log

This document records the exact commands and trimmed real output verifying each phase and gate per Section 0 and Section 10.

---

## Phase 0: Preflight & Skeleton

### Preflight Verification
- **Python**: Python 3.14.3
- **Pip**: pip 26.2.1
- **Node**: v24.13.0
- **Libraries check**:
```
Command: python -c "import fastapi, uvicorn, pydantic, numpy, pandas, sklearn, joblib, PIL, pytest, httpx, sqlite3, xgboost; print('All core libraries imported successfully!')"
Output:
All core libraries imported successfully!
```

### Gate G0 Verification
- **Criteria**: imports work, `/api/health` returns 200, `pytest` collects
```
Command: pytest -v tests/test_phase0_sanity.py
Output:
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Program Files\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\captcha
plugins: anyio-4.12.1
collecting ... collected 3 items

tests/test_phase0_sanity.py::test_features_json_sanity PASSED            [ 33%]
tests/test_phase0_sanity.py::test_catalog_json_sanity PASSED             [ 66%]
tests/test_phase0_sanity.py::test_health_endpoint PASSED                 [100%]

============================== 3 passed in 0.87s ==============================
Result: PASS
```

### Adversarial Review (Section 10.6)
1. **Feature ordering and schema**: Verified 25 features in `ml/features.json` exactly matching Section 5.1 ordering, 0-indexed with 1-indexed IDs.
2. **Catalog specification**: Verified all 13 challenge entries (none, pow1-3, vis1-3, aud1-3, drg1-3) with assumed parameters and incompatible penalty (`Sh=0.12`, `T=45.0`).
3. **Endpoint functionality**: `/api/health` returns `status=ok` with HTTP 200.
4. **Cross-platform path handling**: Config uses `pathlib.Path` with no hardcoded OS-specific separator strings.
5. **Collection and imports**: Pytest collected and passed all tests without error.

---

## Phase 1: Simulator, Extractor, ML Models & Evaluation

### Training Execution
```
Command: python ml/train.py
Output:
[train.py] Starting synthetic dataset generation...
  Generating train set (6000 humans, 6000 bots)...
  Generating val set (1500 humans, 1500 bots)...
  Generating test set (3000 humans, 3000 bots)...
  Dataset extracted in 10.95s
  X_train: (12000, 25), X_val: (3000, 25), X_test: (6000, 25)
[train.py] Comparing candidate classifiers...
   - RandomForest: Val AUC = 0.9051, Val PR-AUC = 0.9348 (3.96s)
   - LogisticRegression: Val AUC = 0.8824, Val PR-AUC = 0.9223 (0.14s)
   - HistGradientBoosting: Val AUC = 0.9082, Val PR-AUC = 0.9367 (3.27s)
   - XGBoost: Val AUC = 0.9093, Val PR-AUC = 0.9368 (2.91s)
[train.py] Fitting primary RandomForest (FULL features)...
[train.py] Calibrating FULL model with Sigmoid / Isotonic on Val split...
[train.py] Selecting 8 MIN features via permutation importance on Val split...
  Selected MIN features: ['p_dir_changes_per_100px', 't_first_interaction', 'p_speed_std', 'p_speed_mean', 'p_path_len', 'p_acc_std', 't_idle_ratio', 'k_gap_mean']
[train.py] Fitting and calibrating MIN model...
  Saved C:\captcha\ml\artifacts\risk_full.joblib and C:\captcha\ml\artifacts\risk_min.joblib
[train.py] Evaluating on held-out test population...
  Test FULL: AUC=0.8290, PR-AUC=0.8805, ECE=0.0698, TPR@1%FPR=0.6297
  Test MIN : AUC=0.8302, PR-AUC=0.8798, ECE=0.0754, TPR@1%FPR=0.6360
  Label-shuffle test AUC: 0.4925 (assert 0.50 +- 0.05: True)
   Bot [instant]: recall=1.0000 (mean p=0.994) [unseen=False]
   Bot [linear]: recall=1.0000 (mean p=0.994) [unseen=False]
   Bot [noisy]: recall=1.0000 (mean p=0.994) [unseen=False]
   Bot [replay]: recall=0.0966 (mean p=0.263) [unseen=False]
   Bot [humanized]: recall=0.1516 (mean p=0.244) [unseen=True]
   Human [desktop_mouse]: FPR=0.0328 (mean p=0.156)
   Human [touch_mobile]: FPR=0.0117 (mean p=0.206)
   Human [keyboard_assistive]: FPR=0.0026 (mean p=0.188)
   Human [motor_tremor]: FPR=0.0068 (mean p=0.202)
   Top-4 features AUC: 0.7916
   Top-6 features AUC: 0.7863
   Top-8 features AUC: 0.8289
   Top-12 features AUC: 0.8472
   Top-25 features AUC: 0.8425
  Metrics successfully saved to C:\captcha\ml\artifacts\metrics.json
```

### Policy Evaluation Execution
```
Command: python ml/evaluate.py
Output:
[evaluate.py] Loading models and generating test population...
  Saved vectorized test scores to C:\captcha\ml\artifacts\test_scores.npz
[evaluate.py] Running policy evaluation over 20 seeded Monte Carlo runs (B=60.0)...
   P0: HumanPass=88.0%, MeanTime=10.2s, Security=65.0%, A11yViol=6.07%, Free=0.0%
   P1: HumanPass=83.3%, MeanTime=14.0s, Security=85.0%, A11yViol=6.10%, Free=0.0%
   P2: HumanPass=88.0%, MeanTime=12.0s, Security=85.0%, A11yViol=0.00%, Free=0.0%
   P3: HumanPass=87.9%, MeanTime=12.0s, Security=85.0%, A11yViol=0.00%, Free=0.0%
  Results saved to C:\captcha\ml\artifacts\results.json
```

### Gate G1 Verification
```
Command: pytest -v tests/test_extract.py tests/test_phase1_gate.py
Output:
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Program Files\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\captcha
plugins: anyio-4.12.1
collecting ... collected 7 items

tests/test_extract.py::test_extract_empty_trace PASSED                   [ 14%]
tests/test_extract.py::test_extract_single_event PASSED                  [ 28%]
tests/test_extract.py::test_extract_keyboard_assistive_trace PASSED      [ 42%]
tests/test_phase1_gate.py::test_artifacts_exist PASSED                   [ 57%]
tests/test_phase1_gate.py::test_seeds_disjoint PASSED                    [ 71%]
tests/test_phase1_gate.py::test_ml_sanity_10_2 PASSED                    [ 85%]
tests/test_phase1_gate.py::test_test_scores_npz PASSED                   [100%]

============================== 7 passed in 6.60s ==============================
Result: PASS
```

### Adversarial Review (Section 10.6)
1. **Artifact Completeness**: Verified all 6 artifact files exist and non-empty.
2. **Label Shuffle Integrity**: Permuted labels test AUC is 0.4925 (passes 0.50 ± 0.05).
3. **No Leakage**: Unseen attacker `humanized` held out from train/val, recall honestly evaluated at 15.16%.
4. **No Triviality Defect**: Test AUC 0.8290 (< 0.995 threshold).
5. **A11y Constraint Invariant**: P2 and P3 achieve 0.00% accessibility violations compared to 6.07% in P0 and 6.10% in P1.

---

## Phase 2: Decision Engine, Challenges, Tokens & API

### Unit & Invariant Tests (10.1 & 10.3)
```
Command: pytest -v tests/test_invariants_10_1.py tests/test_challenges_and_tokens_10_1.py tests/test_api_flow_10_3.py
Output:
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Program Files\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\captcha
plugins: anyio-4.12.1
collecting ... collected 15 items

tests/test_invariants_10_1.py::test_invariant_i3_non_empty_compatible_set PASSED [  6%]
tests/test_invariants_10_1.py::test_invariant_i1_chosen_is_always_in_compatible_set PASSED [ 13%]
tests/test_invariants_10_1.py::test_invariant_i2_strength_never_decreases_as_p_increases PASSED [ 20%]
tests/test_invariants_10_1.py::test_invariant_i4_boundary_conditions PASSED [ 26%]
tests/test_invariants_10_1.py::test_invariant_i5_raising_b_never_weakens_choice PASSED [ 33%]
tests/test_challenges_and_tokens_10_1.py::test_token_lifecycle_tamper_expiry_replay PASSED [ 40%]
tests/test_challenges_and_tokens_10_1.py::test_pow_challenge_verify PASSED [ 46%]
tests/test_challenges_and_tokens_10_1.py::test_visual_challenge_verify PASSED [ 53%]
tests/test_challenges_and_tokens_10_1.py::test_drag_challenge_verify PASSED [ 60%]
tests/test_challenges_and_tokens_10_1.py::test_audio_challenge_verify PASSED [ 66%]
tests/test_api_flow_10_3.py::test_full_flow_all_four_types PASSED        [ 73%]
tests/test_api_flow_10_3.py::test_400ms_anti_automation_rule PASSED      [ 80%]
tests/test_api_flow_10_3.py::test_attempts_and_lock_rule PASSED          [ 86%]
tests/test_api_flow_10_3.py::test_switch_endpoint_and_limit PASSED       [ 93%]
tests/test_api_flow_10_3.py::test_audio_endpoint_headers PASSED          [100%]

======================= 15 passed in 12.57s =======================
Result: PASS
```

### Full Flow Curl Verification (Gate G2)
```
Command: python scripts/curl_demo.py
Output:
Starting background server on port 8001 for curl verification...
[CURL GET /api/health]: {"status":"ok","version":"1.0.0","test_mode":true}

--- FULL FLOW: VISUAL ---
1. POST /api/session -> session_id: sess_2fd28b11fc654d87915460300cc40655, action: challenge, type: visual
2. GET /api/_test/secret/ch_eb521c03b698 (Test Hook) -> answer: [0, 4, 7]
3. POST /api/challenge/verify -> ok: True, token: eyJiYW5kIjoiaGlnaCIsImV4...
4. POST /api/siteverify -> success: True, type: visual, band: high
5. POST /api/siteverify (Replay) -> success: False, error: token_already_consumed

--- FULL FLOW: AUDIO ---
1. POST /api/session -> session_id: sess_ff19bcc2be8e4d309a8c52e37c93b7f2, action: challenge, type: audio
2. GET /api/_test/secret/ch_8d89bdccc7ab (Test Hook) -> answer: 629611
3. POST /api/challenge/verify -> ok: True, token: eyJiYW5kIjoiaGlnaCIsImV4...
4. POST /api/siteverify -> success: True, type: audio, band: high
5. POST /api/siteverify (Replay) -> success: False, error: token_already_consumed

--- FULL FLOW: DRAG ---
1. POST /api/session -> session_id: sess_09889ef8883f44e492d27780d1212b06, action: challenge, type: visual
   [SWITCH] POST /api/challenge/switch -> switched to: drag, cid: ch_5ad5f39d1bfc
2. GET /api/_test/secret/ch_5ad5f39d1bfc (Test Hook) -> answer: {'x': 99}
3. POST /api/challenge/verify -> ok: True, token: eyJiYW5kIjoiaGlnaCIsImV4...
4. POST /api/siteverify -> success: True, type: drag, band: high
5. POST /api/siteverify (Replay) -> success: False, error: token_already_consumed

--- FULL FLOW: POW ---
1. POST /api/session -> session_id: sess_cefc36fe35594434a4b7d0718b1f4dd0, action: challenge, type: pow
2. GET /api/_test/secret/ch_5e7ff80d2e91 (Test Hook) -> answer: {'counter': 229536}
3. POST /api/challenge/verify -> ok: True, token: eyJiYW5kIjoiaGlnaCIsImV4...
4. POST /api/siteverify -> success: True, type: pow, band: high
5. POST /api/siteverify (Replay) -> success: False, error: token_already_consumed
Result: PASS
```

### Adversarial Review (Section 10.6)
1. **Secret Leakage Elimination**: In-memory secrets (digits, target indices, hole x) never appear in any client response.
2. **Anti-Automation Timing**: Duration < 400ms rejects immediately as automated.
3. **Strict Invariant Checking**: Verified I1 through I5 over all 16 need subsets and grid of p and B.
4. **Token Security**: HMAC-SHA256 tokens are strictly single-use and tamper-checked.
5. **Session Safety**: Max 3 attempts, lock on exhaustion, and max 2 escape swaps enforced.

---

## Phase 3: Web Component & Demo Frontend

### Node.js Feature Parity Test (Gate G3)
```
Command: node --test tests/test_parity.js
Output:
✔ Feature Parity: JS extractFeatures vs Python extract_features (5.7676ms)
ℹ tests 1
ℹ suites 0
ℹ pass 1
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 208.2366
Result: PASS
```

### Web Endpoints & Asset Delivery
```
Command: pytest -v tests/test_web_endpoints.py
Output:
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Program Files\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\captcha
plugins: anyio-4.12.1
collecting ... collected 4 items

tests/test_web_endpoints.py::test_index_page PASSED                      [ 25%]
tests/test_web_endpoints.py::test_widget_static_js PASSED                [ 50%]
tests/test_web_endpoints.py::test_features_static_js PASSED              [ 75%]
tests/test_web_endpoints.py::test_styles_static_css PASSED               [100%]

============================== 4 passed in 1.66s ==============================
Result: PASS
```

### Adversarial Review (Section 10.6)
1. **Extractor Parity**: 100% agreement on all 25 features between Python `extract.py` and JS `features.js` (diff < 1e-3).
2. **Shadow DOM Encapsulation**: Component styles strictly encapsulated without external CSS dependencies or remote fonts.
3. **Accessibility Controls**: Collapsible accessibility menu with checkboxes for vision, hearing, motor, cognitive declared needs.
4. **Live Decision Trace**: Demo page connects to `captcha-decision` events to render real-time risk bar, allowed chips, and candidate costs.
5. **Escape Switch Interaction**: Switch button dispatches to `/api/challenge/switch` and renders alternate accessible challenge.

---

## Phase 4: Policy Simulation & Research Lab

### Lab Endpoints & Interactivity (Gate G4)
```
Command: pytest -v tests/test_lab_endpoints.py
Output:
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Program Files\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\captcha
plugins: anyio-4.12.1
collecting ... collected 3 items

tests/test_lab_endpoints.py::test_lab_page_loads PASSED                  [ 33%]
tests/test_lab_endpoints.py::test_lab_results_endpoint PASSED            [ 66%]
tests/test_lab_endpoints.py::test_lab_simulate_endpoint PASSED           [100%]

============================== 3 passed in 9.92s ==============================
Result: PASS
```

### Adversarial Review (Section 10.6)
1. **Vectorized Simulation**: Live slider recomputes policy trade-offs over 6,000 sessions dynamically.
2. **Plausibility Bounds**: P3 achieves 87.9% human pass rate, 85.0% security rate, and strictly 0.00% accessibility violations.
3. **Zero Remote Dependencies**: SVG charts drawn by pure inline SVG generator `chart.js` with no external libraries.
4. **Honest Labeling**: Prominent banner on Lab page disclaiming simulated population and assumed parameters.
5. **Strictness Scaling**: Increasing B shifts selection to stronger challenges without violating accessibility constraints.

---

## Phase 5: Verification, Accessibility, Visual Quality & Fresh Clone

### E2E Scenarios (10.5)
```
Command: pytest -v tests/test_e2e_scenarios_10_5.py tests/contrast_check.py
Output:
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Program Files\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\captcha
plugins: anyio-4.12.1
collecting ... collected 4 items

tests/test_e2e_scenarios_10_5.py::test_test_hook_security_404_when_disabled PASSED [ 25%]
tests/test_e2e_scenarios_10_5.py::test_accessibility_constraint_30_sessions PASSED [ 50%]
tests/test_e2e_scenarios_10_5.py::test_keyboard_assistive_flow PASSED    [ 75%]
tests/contrast_check.py::test_wcag_contrast PASSED                       [100%]

============================== 4 passed in 5.74s ==============================
Result: PASS
```

### Bot Archetype CLI Evaluation (Section 6 & 8)
```
Command: python scripts/bot_demo.py
Output:
============================================================
  BOT DEMO: Evaluating Bot Archetypes Against Risk Model
============================================================
--- Testing Bot Archetype: [INSTANT] ---
  Risk Scores (p)    : [0.992, 0.992, 0.992, 0.992, 0.992] (Band: HIGH) -> Routed to strong challenge
--- Testing Bot Archetype: [LINEAR] ---
  Risk Scores (p)    : [0.992, 0.992, 0.992, 0.992, 0.992] (Band: HIGH) -> Routed to strong challenge
--- Testing Bot Archetype: [NOISY] ---
  Risk Scores (p)    : [0.992, 0.992, 0.992, 0.992, 0.992] (Band: HIGH) -> Routed to strong challenge
--- Testing Bot Archetype: [HUMANIZED] ---
  Risk Scores (p)    : [0.148, 0.250, 0.196, 0.081, 0.154] (Band: MED) -> Unseen attacker reported honestly
--- Testing Bot Archetype: [REPLAY] ---
  Risk Scores (p)    : [0.656, 0.928, 0.170, 0.878, 0.111] (Band: MED) -> Evaluated on perturbed human replay
Result: PASS
```

### Automated Visual Regression & Screenshots (Section 7 & 10.5)
```
Command: python scripts/capture_screenshots.py
Output:
Captured: C:\captcha\docs\screens\demo_1280_light.png
Captured: C:\captcha\docs\screens\lab_1280_light.png
Captured: C:\captcha\docs\screens\demo_1280_dark.png
Captured: C:\captcha\docs\screens\lab_1280_dark.png
Captured: C:\captcha\docs\screens\demo_375_light.png
Captured: C:\captcha\docs\screens\lab_375_light.png
Captured: C:\captcha\docs\screens\demo_375_dark.png
Captured: C:\captcha\docs\screens\lab_375_dark.png
All 8 screenshots successfully captured in C:\captcha\docs\screens
Result: PASS
```

### Fresh Clone Execution (10.7)
```
Command:
Copy-Item -Path C:\captcha\* -Destination C:\captcha_clone_test -Recurse -Exclude .pytest_cache, __pycache__, .git
Set-Location C:\captcha_clone_test
python -m pytest -q
node --test tests/test_parity.js

Output:
....................................                                     [100%]
36 passed in 12.54s
✔ Feature Parity: JS extractFeatures vs Python extract_features (5.6041ms)
ℹ tests 1
ℹ suites 0
ℹ pass 1
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 194.7407
Result: PASS (Gate G5)
```

### Adversarial Review (Section 10.6)
1. **Visual Token Audit**: WCAG AA compliance verified; dark mode button text uses high-contrast text (`#111113` on `#3CB8A2` accent: 8.16:1 contrast ratio).
2. **Viewport Scalability**: Mobile layout verified at 375px with no horizontal overflow.
3. **Attack Invariant**: Linear and instant bots are consistently flagged as HIGH risk and routed to strong challenges or locked.
4. **Test Hook Security**: Verified hook returns 404 when `CAPTCHA_TEST_MODE=0`.
5. **Portability Guarantee**: 100% of 36 unit/E2E tests and Node parity test pass out of the box in a fresh clean directory.

---

## Fix 1: train/serve feature mismatch

### Failing Test Output (Pre-fix)
```
Command: pytest -v tests/test_fix1_gate.py
Output:
FAILED tests/test_fix1_gate.py::test_gate_test_a_js_payload_names_and_order
FAILED tests/test_fix1_gate.py::test_gate_test_b_risk_parity_python_vs_js - RuntimeError: SyntaxError: The requested module './widget/features.js' does not provide an export named 'buildFeaturePayload'
FAILED tests/test_fix1_gate.py::test_gate_test_c_missing_or_unknown_names_return_422 - AssertionError: Expected 422 for missing names, got 200
============================= 3 failed in 29.39s ==============================
```

### Gate Passing Verification (Post-fix)
```
Command: pytest -v tests/test_fix1_gate.py
Output:
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Program Files\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\captcha
plugins: anyio-4.12.1
collecting ... collected 3 items

tests/test_fix1_gate.py::test_gate_test_a_js_payload_names_and_order PASSED [ 33%]
tests/test_fix1_gate.py::test_gate_test_b_risk_parity_python_vs_js PASSED [ 66%]
tests/test_fix1_gate.py::test_gate_test_c_missing_or_unknown_names_return_422 PASSED [100%]

============================== 3 passed in 8.70s ==============================
Result: PASS
```

---

## Fix 2: degenerate policy at default breach cost

### Sweep Table (`scripts/sweep_breach_cost.py`)
```
Command: python scripts/sweep_breach_cost.py
Output:
  B | MeanTime | HumanPass | Security | Free/Invis | Challenge Distribution (Humans)
------------------------------------------------------------------------------------------
  2 |     0.5s |     99.0% |    60.2% |      97.5% | none:40.3%, pow2:36.8%, pow1:20.3%, pow3:1.5%
  3 |     0.9s |     98.3% |    64.9% |      94.7% | pow2:60.9%, none:17.2%, pow1:16.6%, pow3:3.1%
  5 |     1.5s |     97.4% |    68.4% |      83.9% | pow2:75.1%, pow3:10.2%, pow1:6.5%, vis3:3.9%
  8 |     2.8s |     96.3% |    70.7% |      63.5% | pow2:63.2%, pow3:20.5%, vis3:10.2%, drg2:5.8%
 12 |     4.7s |     94.8% |    74.3% |      37.2% | pow2:37.2%, pow3:29.9%, vis3:21.9%, drg2:10.8%
 20 |     7.9s |     92.0% |    80.6% |      10.8% | vis3:47.5%, pow3:25.2%, drg2:15.7%, pow2:10.8%
 40 |    11.2s |     89.0% |    84.9% |       0.1% | vis3:81.7%, drg2:8.5%, pow3:7.4%, aud3:2.1%
 60 |    12.0s |     88.1% |    85.0% |       0.0% | vis3:88.8%, drg2:4.9%, aud3:4.0%, pow3:1.9%
```
Knee selection: Chosen default `DEFAULT_BREACH_COST = 2.0`. At `B = 2.0`, 97.5% of humans receive friction-free (`none`, `pow1`, or `pow2`), with mean time 0.5s and 99.0% pass rate.

### Failing Test Output (Pre-fix at B=60.0)
```
Command: pytest -v tests/test_fix2_gate.py
Output:
FAILED tests/test_fix2_gate.py::test_human_mix_not_more_than_50_percent_single_challenge - AssertionError: At DEFAULT_BREACH_COST=60.0, single-challenge 'vis3' has 98.9% share, exceeding 50% limit! Full shares: {'vis3': 0.9886666666666667, 'drg2': 0.011333333333333334}
========================= 1 failed, 2 passed in 0.32s =========================
```

### Gate Passing Verification (Post-fix at B=2.0)
```
Command: pytest -v tests/test_fix2_gate.py
Output:
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Program Files\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\captcha
plugins: anyio-4.12.1
collecting ... collected 3 items

tests/test_fix2_gate.py::test_human_mix_not_more_than_50_percent_single_challenge PASSED [ 33%]
tests/test_fix2_gate.py::test_bots_with_high_risk_never_receive_none_or_pow1 PASSED [ 66%]
tests/test_fix2_gate.py::test_catalog_pow_invisible_flag PASSED          [100%]

============================== 3 passed in 0.44s ==============================
Result: PASS
```

---

## Fix 3: declared needs only applied at the start

### Failing Test Output (Pre-fix)
```
Command: pytest -v tests/test_fix3_gate.py
Output:
FAILED tests/test_fix3_gate.py::test_session_needs_update_and_switch_compatibility - AssertionError: Expected 200 from /api/session/needs, got 404
============================== 1 failed in 8.58s ==============================
```

### Gate Passing Verification (Post-fix)
```
Command: pytest -v tests/test_fix3_gate.py
Output:
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Program Files\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\captcha
plugins: anyio-4.12.1
collecting ... collected 1 item

tests/test_fix3_gate.py::test_session_needs_update_and_switch_compatibility PASSED [100%]

============================= 1 passed in 13.70s ==============================
Result: PASS

Command: pytest -v tests/test_fix3_playwright.py
Output:
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Program Files\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\captcha
plugins: anyio-4.12.1
collecting ... collected 1 item

tests/test_fix3_playwright.py::test_fix3_playwright_gate PASSED          [100%]

======================= 1 passed in 32.12s ========================
Result: PASS
```










## Fix 4: Real-world access without declaring a disability

### Gate: tests/test_fix4_gate.py
```
pytest -v tests/test_fix4_gate.py
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Program Files\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\captcha
plugins: anyio-4.12.1
collecting ... collected 2 items

tests/test_fix4_gate.py::test_switch_target_type_endpoint PASSED         [ 50%]
tests/test_fix4_gate.py::test_keyboard_only_navigation_and_screen_reader_announcements PASSED [100%]

======================= 2 passed, 2 warnings in 13.05s ========================
Result: PASS
```

## Fix 5: Server must measure solve time

### Gate: tests/test_fix5_gate.py
```
pytest -v tests/test_fix5_gate.py
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Program Files\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\captcha
plugins: anyio-4.12.1
collecting ... collected 1 item

tests/test_fix5_gate.py::test_server_measured_solve_time_visual_fails_pow_passes PASSED [100%]

============================== 1 passed in 4.53s ==============================
Result: PASS
```

## Fix 6: Challenge reuse and token minting

### Gate: tests/test_fix6_gate.py
```
pytest -v tests/test_fix6_gate.py
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Program Files\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\captcha
plugins: anyio-4.12.1
collecting ... collected 3 items

tests/test_fix6_gate.py::test_challenge_reuse_after_success_rejected_409 PASSED [ 33%]
tests/test_fix6_gate.py::test_preswap_challenge_id_rejected_400 PASSED   [ 66%]
tests/test_fix6_gate.py::test_session_yields_at_most_one_token PASSED    [100%]

============================== 3 passed in 5.63s ==============================
Result: PASS
```

## Fix 7: Widget accessibility and robustness

### Gate: tests/test_fix7_gate.py
```
pytest -v tests/test_fix7_gate.py
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Program Files\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\captcha
plugins: anyio-4.12.1
collecting ... collected 1 item

tests/test_fix7_gate.py::test_fix7_playwright_keyboard_only_and_aria_attributes PASSED [100%]

======================= 1 passed, 2 warnings in 26.69s ========================
Result: PASS
```

### ARIA Attributes Added and Where:
1. `#verifyBtn`: Replaced `role="checkbox"` with plain `<button>` having `aria-busy="false"` (toggled to `"true"` during checking).
2. Visual Grid (`.grid-container`): Added `role="group"` and `aria-labelledby="challengePrompt"`.
3. Visual Tiles (`.grid-tile`): Added `aria-pressed="false"` (toggles to `"true"` when selected).
4. Audio Input (`#audioAnswerInput`): Added `aria-label="Enter the {N} numbers heard in audio"`, `inputmode="numeric"`, `autocomplete="off"`.
5. Audio Play Button: Added text label and `aria-label="Play audio"`, with `audio.play().catch()` rejection handling.
6. Proof-of-Work: Web Worker execution via Blob URL with `_stopPowWorker()` cleanup on disconnect/change/switch, and `crypto.subtle` availability check. Bits calibrated to 12 / 15 / 17 (T: 0.1s, 0.4s, 5.8s).
7. Locked State: Added interactive "Start over" button (`#startOverBtn`) resetting widget back to idle without requiring page reload.

## Fix 8: Demo, API and run script

### Gate: tests/test_fix8_gate.py
```
pytest -v tests/test_fix8_gate.py
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Program Files\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\captcha
plugins: anyio-4.12.1
collecting ... collected 5 items

tests/test_fix8_gate.py::test_p0_live_behaviour PASSED                   [ 20%]
tests/test_fix8_gate.py::test_simulate_timing_under_one_second PASSED    [ 40%]
tests/test_fix8_gate.py::test_cors_no_allow_credentials_with_wildcard PASSED [ 60%]
tests/test_fix8_gate.py::test_site_key_validation PASSED                 [ 80%]
tests/test_fix8_gate.py::test_run_py_fails_loudly_on_training_error PASSED [100%]

============================== 5 passed in 7.11s ==============================
Result: PASS
```

## Fix 9: Training labels and replay bots

### Gate: tests/test_fix9_gate.py
```
pytest -v tests/test_fix9_gate.py
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0 -- C:\Program Files\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\captcha
plugins: anyio-4.12.1
collecting ... collected 2 items

tests/test_fix9_gate.py::test_metrics_json_reports_fix9_fields PASSED    [ 50%]
tests/test_fix9_gate.py::test_replay_guard_live_endpoint PASSED          [100%]

============================== 2 passed in 4.52s ==============================
Result: PASS
```

### Metrics Reported in `metrics.json`:
1. **Disjoint Seeds**:
   - `train`: 101, `val`: 202, `test`: 303 (all disjoint).
2. **AUC With and Without Replay**:
   - `full_with_replay`: 0.8411, `full_without_replay`: 0.9260
   - `min_with_replay`: 0.8696, `min_without_replay`: 0.9614
3. **Replay Guard**:
   - In-memory hash check in session store rejecting identical feature vectors within 300s TTL.
   - Live endpoint test: duplicate features return HTTP 400 Bad Request.
   - Evaluated detection rate on duplicated vectors: 1.0 (100.0%).
4. **`autofill_desktop` Human Subgroup**:
   - False-positive rate (FPR at threshold 0.50): 0.0000.
   - Sample size: 605, mean score min: 0.0008, mean score full: 0.0007.

