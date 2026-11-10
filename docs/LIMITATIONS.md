# System Limitations and Honest Disclosures

This document details the architectural boundaries, threat model constraints, and real-world limitations of the Adaptive and Accessible CAPTCHA system. In adherence to honest scientific practice, these disclosures describe where the current design succeeds, where it degrades, and where empirical guarantees cannot be made.

---

## 1. Synthetic Data Only (No Real User Study)
All behavioral models, feature distributions, and human/bot benchmarks are developed exclusively on **synthetic population data**:
- Human behavioral traces are simulated using kinematic equations (cubic Bézier curves, minimum-jerk velocity profiles, log-normal hesitation pauses, and Gaussian jitter).
- While these distributions incorporate assistive variations (such as tremor and keyboard-assistive tab navigation), **no formal human-subject user study** has been conducted.
- Real human motor noise, fatigue, assistive software hooks, screen-reader interactions, and browser extension interference may diverge substantially from these synthetic distributions in the wild.

---

## 2. Replay Bots Defeat the Behavioral Classifier Alone
- A replay bot replays a recorded human trajectory with identical timing or minor linear perturbation. Because the underlying kinematic features mirror genuine human interaction, the machine learning classifier assigns these traces near-zero risk ($p \approx 0.00066$) when evaluated purely on single-session behavioral telemetry.
- Protection against replay relies entirely on the **`replay_guard`** in the session store, which hashes the feature vector and rejects exact duplicate vectors seen within the session time-to-live (`TTL = 300s`).
- If an adversary perturbs the vector beyond exact floating-point equality or replays after the TTL expires, the single-session classifier alone cannot distinguish the replay from a human. A production deployment requires persistent IP/subnet rate-limiting, TLS fingerprinting, and stateful multi-session risk scoring.

---

## 3. Vulnerability of Audio and Visual Puzzles to Multimodal Models
- Visual challenges (3x3 grid image classification) and audio challenges (digits spoken over synthetic background noise) are generated offline without proprietary adversarial perturbations.
- Modern off-the-shelf multimodal large language models and vision-language APIs (e.g., GPT-4o, Gemini 1.5 Pro) can solve these visual and audio challenges with high accuracy, often exceeding 90%.
- The catalog bot solve rates ($S_b$) used in the expected-cost decision engine represent nominal parametric estimates, not cryptographic barriers against advanced vision models.

---

## 4. Proof of Work Burns Client Battery and Does Not Stop Botnets
- Proof of Work (PoW) is executed in the browser using client-side SHA-256 hash collision search via Web Workers (`pow1`: 12 bits, `pow2`: 15 bits, `pow3`: 17 bits).
- Computing PoW consumes CPU cycles and drains battery on mobile and embedded devices, penalizing legitimate low-power users.
- Furthermore, PoW imposes negligible deterrence against distributed botnets with access to cheap ASIC mining hardware, GPU clusters, or cloud compute instances capable of computing billions of hashes per second.

---

## 5. Accessibility Switcher Relies on Honest Self-Declaration
- The zero-declaration alternative switcher and declared accessibility filters rely entirely on honest client declaration:
  - The modal switch endpoint (`/api/challenge/switch`) and declared access needs (`vision`, `hearing`, `motor`, `cognitive`) filter the challenge candidate set $C(A)$.
  - A malicious bot can trivially declare an accessibility need (or request an audio/drag challenge via the switcher) to avoid difficult visual challenges or force the server to issue alternative modalities.
- The system deliberately prioritizes **accessible inclusion over unforgeable proof of disability**, ensuring that no disabled human is ever trapped or forced into an inaccessible test.

---

## 6. Accessibility Compliance Status
- The user interface **targets WCAG 2.1 AA**; colour contrast is checked across all light and dark tokens (`tests/contrast_check.py`), and full keyboard end-to-end traversal is validated via automated Playwright tests.
- However, **no formal independent third-party accessibility audit** has been performed.

