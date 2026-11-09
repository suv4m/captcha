# 3-Minute Demonstration Walkthrough Script

This script provides an interactive step-by-step guide to demonstrate the key innovations of the Adaptive and Accessible CAPTCHA system in under 3 minutes.

---

### Step 1: Normal User Sign-in (Low-Risk Silent Pass) — 45 Seconds
1. Navigate to the demo portal at `http://127.0.0.1:8000/`.
2. Move your mouse smoothly across the screen into the sign-in form.
3. Click the checkbox labeled **"Verify you are human"**.
4. **Observe:**
   - The checkbox instantly transitions to a green checkmark (`✓`) with zero friction.
   - Look at the **Decision Trace** panel on the right:
     - Calculated Risk ($p$) is in the **LOW** band ($p < 0.15$).
     - Chosen challenge is `none`.
     - Data sent is only 68 bytes (8 features).
5. Click **"Sign In"** to complete authentication via the backend verification API (`/api/demo/login` -> `/api/siteverify`).

---

### Step 2: Simulated Bot Attack (Automated Scripted Detection) — 45 Seconds
1. Open a new terminal and run:
   ```bash
   python scripts/bot_demo.py
   ```
2. **Observe:**
   - Scripted `linear` and `noisy` bots exhibit unnaturally constant velocity and zero lateral noise.
   - The risk model immediately scores them in the **HIGH** band ($p \approx 0.992$).
   - The decision engine automatically routes them to the strongest challenges (`vis3` with $S_b = 0.15$) or locks the session.

---

### Step 3: Accessibility Constraint Enforcement — 45 Seconds
1. Return to the browser sign-in page and reload.
2. Click **"Accessibility options"** under the verification box.
3. Check the **"Vision"** checkbox (declaring severe visual impairment).
4. In the Decision Trace panel, select **Policy P3**.
5. Trigger the checkbox.
6. **Observe:**
   - Look at the **Allowed Set** chips in the decision trace:
     - `vis1`, `vis2`, `vis3`, `drg1`, `drg2`, `drg3` are **completely eliminated**.
   - Instead, the widget serves an accessible **Audio Challenge** (or PoW), ensuring the user is never locked out by an incompatible visual puzzle.
7. Click **"Try a different challenge"** to demonstrate user-initiated escape:
   - The engine instantly swaps to an alternate accessible challenge without penalty.

---

### Step 4: Strictness Slider & Research Lab — 45 Seconds
1. Drag the **"Strictness (Breach cost B)"** slider from `60` to `180`.
2. Notice how candidate costs re-evaluate dynamically.
3. Click **"Lab"** in the top navigation bar (`http://127.0.0.1:8000/lab`).
4. **Observe:**
   - **Four-Policy Benchmark Table:** Shows that while fixed CAPTCHAs (P0) cause a 6.07% accessibility violation rate, Adaptive Policies P2 and P3 achieve strictly **0.00% accessibility violations** while boosting security to 85.0%.
   - **Interactive Policy Simulation:** Move the live slider to re-simulate all 6,000 sessions live via vectorized NumPy in under 50 ms.
   - **Classifier & Bot Archetypes:** Review the ROC curve, feature pruning curve, and honest reporting of the unseen `humanized` bot detection rate.
