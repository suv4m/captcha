import { extractFeatures, buildFeaturePayload, FEATURE_NAMES } from "./features.js";

const TEMPLATE = document.createElement("template");
TEMPLATE.innerHTML = `
<style>
:host {
  display: block;
  font-family: ui-sans-serif, system-ui, "Segoe UI", Roboto, sans-serif;
  font-size: 14px;
  line-height: 1.5;
  color: var(--cap-text, #1A1A1A);
  --cap-bg: #FAFAF8;
  --cap-surface: #FFFFFF;
  --cap-border: #E6E4DF;
  --cap-text: #1A1A1A;
  --cap-muted: #6B6B66;
  --cap-accent: #0B6B5D;
  --cap-accent-hover: #084D43;
  --cap-btn-text: #FFFFFF;
  --cap-danger: #B3261E;
  --cap-radius: 8px;
  --cap-card-radius: 12px;
}

@media (prefers-color-scheme: dark) {
  :host {
    --cap-bg: #111113;
    --cap-surface: #1A1A1D;
    --cap-border: #2A2A2E;
    --cap-text: #ECECEC;
    --cap-muted: #9A9AA0;
    --cap-accent: #3CB8A2;
    --cap-accent-hover: #4ED2BA;
    --cap-btn-text: #111113;
    --cap-danger: #CF6679;
  }
}

.captcha-container {
  background: var(--cap-surface);
  border: 1px solid var(--cap-border);
  border-radius: var(--cap-card-radius);
  padding: 14px;
  width: 100%;
  max-width: 340px;
  box-sizing: border-box;
}

.captcha-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.checkbox-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  background: none;
  border: none;
  padding: 0;
  font: inherit;
  color: inherit;
  text-align: left;
}

.checkbox-box {
  width: 24px;
  height: 24px;
  border: 1.5px solid var(--cap-border);
  border-radius: 6px;
  background: var(--cap-surface);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 120ms ease, background-color 120ms ease;
  flex-shrink: 0;
}

.checkbox-btn:hover .checkbox-box {
  border-color: var(--cap-accent);
}

.checkbox-btn:focus-visible .checkbox-box {
  outline: 2px solid var(--cap-accent);
  outline-offset: 2px;
}

.badge {
  font-size: 11px;
  font-weight: 500;
  color: var(--cap-muted);
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid var(--cap-border);
  border-top-color: var(--cap-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.privacy-notice {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--cap-border);
  font-size: 11px;
  color: var(--cap-muted);
  line-height: 1.4;
}

.a11y-toggle {
  background: none;
  border: none;
  color: var(--cap-accent);
  font-size: 11px;
  cursor: pointer;
  padding: 0;
  margin-top: 6px;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.a11y-options {
  display: none;
  margin-top: 8px;
  padding: 8px;
  background: var(--cap-bg);
  border-radius: var(--cap-radius);
  font-size: 12px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.a11y-options.hidden {
  display: none !important;
}

.a11y-label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
}

/* Challenge Modal / Overlay */
.challenge-box {
  display: none;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--cap-border);
}

.challenge-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
}

/* Visual Grid */
.grid-container {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  margin-bottom: 10px;
}

.grid-tile {
  width: 100%;
  aspect-ratio: 1;
  border: 2px solid var(--cap-border);
  border-radius: var(--cap-radius);
  cursor: pointer;
  overflow: hidden;
  position: relative;
  background: var(--cap-bg);
  padding: 0;
}

.grid-tile img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.grid-tile.selected {
  border-color: var(--cap-accent);
}

.grid-tile.selected::after {
  content: "✓";
  position: absolute;
  top: 4px;
  right: 4px;
  background: var(--cap-accent);
  color: #FFF;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: bold;
}

/* Audio Player */
.audio-player-box {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 10px;
}

.audio-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.audio-input {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--cap-border);
  border-radius: var(--cap-radius);
  font: inherit;
  box-sizing: border-box;
  background: var(--cap-bg);
  color: inherit;
}

/* Drag Puzzle */
.drag-container {
  position: relative;
  width: 320px;
  height: 160px;
  border-radius: var(--cap-radius);
  overflow: hidden;
  margin-bottom: 8px;
}

.drag-bg {
  width: 100%;
  height: 100%;
  display: block;
}

.drag-piece {
  position: absolute;
  top: 0;
  left: 0;
  width: 50px;
  height: 50px;
  cursor: grab;
  box-shadow: 0 2px 6px rgba(0,0,0,0.3);
  touch-action: none;
}

.drag-slider-track {
  width: 100%;
  margin: 10px 0;
}

/* PoW Progress */
.pow-box {
  margin-bottom: 10px;
}

.progress-bar-bg {
  width: 100%;
  height: 8px;
  background: var(--cap-border);
  border-radius: 4px;
  overflow: hidden;
  margin-top: 6px;
}

.progress-bar-fill {
  height: 100%;
  background: var(--cap-accent);
  width: 0%;
  transition: width 100ms ease;
}

/* Action Buttons */
.btn-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 8px;
}

.btn-primary {
  background: var(--cap-accent);
  color: var(--cap-btn-text, #FFFFFF);
  border: none;
  border-radius: var(--cap-radius);
  padding: 7px 14px;
  font-weight: 500;
  font-size: 13px;
  cursor: pointer;
  transition: background-color 120ms ease;
}

.btn-primary:hover {
  background: var(--cap-accent-hover);
}

.btn-secondary {
  background: none;
  border: 1px solid var(--cap-border);
  color: var(--cap-text);
  border-radius: var(--cap-radius);
  padding: 6px 10px;
  font-size: 12px;
  cursor: pointer;
}

.btn-secondary:hover {
  border-color: var(--cap-muted);
}

.error-text {
  color: var(--cap-danger);
  font-size: 12px;
  margin-top: 6px;
}

.passed-check {
  color: var(--cap-accent);
  font-size: 16px;
  font-weight: bold;
}

.alt-nav-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin: 6px 0 10px 0;
  font-size: 12px;
}

.alt-label {
  color: var(--cap-muted);
  font-size: 11px;
}

.alt-btn {
  background: none;
  border: 1px solid var(--cap-border);
  border-radius: var(--cap-radius);
  color: var(--cap-accent);
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.alt-btn:hover, .alt-btn:focus-visible {
  background: var(--cap-bg);
  border-color: var(--cap-accent);
  outline: 2px solid var(--cap-accent);
}
</style>

<div class="captcha-container" role="region" aria-label="Human verification widget">
  <button type="button" class="a11y-toggle" id="a11yToggle" aria-expanded="false">
    Accessibility options
  </button>
  <div class="a11y-options hidden" id="a11yOptions">
    <label class="a11y-label">
      <input type="checkbox" value="vision" class="a11y-cb"> Vision impairment (avoids visual)
    </label>
    <label class="a11y-label">
      <input type="checkbox" value="hearing" class="a11y-cb"> Hearing impairment (avoids audio)
    </label>
    <label class="a11y-label">
      <input type="checkbox" value="motor" class="a11y-cb"> Motor impairment (avoids drag)
    </label>
    <label class="a11y-label">
      <input type="checkbox" value="cognitive" class="a11y-cb"> Cognitive need (avoids complex)
    </label>
    <label class="a11y-label" style="grid-column: 1 / -1; margin-top: 4px; padding-top: 4px; border-top: 1px solid var(--cap-border);">
      <input type="checkbox" id="rememberNeedsCb" class="remember-cb"> Remember on this device
    </label>
  </div>

  <div class="captcha-row">
    <button type="button" class="checkbox-btn" id="verifyBtn" aria-busy="false">
      <div class="checkbox-box" id="checkboxBox"></div>
      <span id="checkboxLabel">Verify you are human</span>
    </button>
    <div class="badge">
      <span>Adaptive CAPTCHA</span>
      <span id="bandBadge">Accessible</span>
    </div>
  </div>

  <div class="challenge-box" id="challengeBox">
    <div class="challenge-title" id="challengePrompt" tabindex="-1">Solve challenge</div>
    <div class="alt-nav-row" id="altNavRow" role="group" aria-label="Use a different challenge">
      <span class="alt-label">Use a different challenge:</span>
      <span id="altButtons" style="display: inline-flex; gap: 4px;"></span>
    </div>
    <div id="challengeContent"></div>
    <div class="btn-row">
      <button type="button" class="btn-secondary" id="switchBtn">Try a different challenge</button>
      <button type="button" class="btn-primary" id="submitChallengeBtn">Verify</button>
    </div>
    <div class="error-text" id="challengeError" style="display: none;"></div>
  </div>

  <div class="privacy-notice" id="privacyNotice">
    Sends 8 numbers (68 bytes) about your interaction timing. No keystrokes, text or movement path.
  </div>

  <div class="sr-only" aria-live="polite" id="srStatus"></div>
</div>
`;

export class AdaptiveCaptcha extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.shadowRoot.appendChild(TEMPLATE.content.cloneNode(true));

    this._state = "idle"; // idle, checking, passed, challenge, locked, error
    this._token = null;
    this._session = null;
    this._activeChallenge = null;
    this._challengeStartTime = null;
    this._needsSeq = 0;

    // Behavioral event buffer (in-memory ring buffer)
    this._events = [];
    this._mountTime = Date.now();
    this._pointerType = "none";
    this._listenersActive = false;

    // DOM references
    this.$btn = this.shadowRoot.getElementById("verifyBtn");
    this.$box = this.shadowRoot.getElementById("checkboxBox");
    this.$label = this.shadowRoot.getElementById("checkboxLabel");
    this.$badge = this.shadowRoot.getElementById("bandBadge");
    this.$a11yToggle = this.shadowRoot.getElementById("a11yToggle");
    this.$a11yOptions = this.shadowRoot.getElementById("a11yOptions");
    this.$challengeBox = this.shadowRoot.getElementById("challengeBox");
    this.$challengePrompt = this.shadowRoot.getElementById("challengePrompt");
    this.$altButtons = this.shadowRoot.getElementById("altButtons");
    this.$rememberCb = this.shadowRoot.getElementById("rememberNeedsCb");
    this.$challengeContent = this.shadowRoot.getElementById("challengeContent");
    this.$switchBtn = this.shadowRoot.getElementById("switchBtn");
    this.$submitBtn = this.shadowRoot.getElementById("submitChallengeBtn");
    this.$challengeError = this.shadowRoot.getElementById("challengeError");
    this.$privacyNotice = this.shadowRoot.getElementById("privacyNotice");
    this.$srStatus = this.shadowRoot.getElementById("srStatus");
  }

  static get observedAttributes() {
    return ["endpoint", "site-key", "policy", "breach-cost", "simulate-risk"];
  }

  get endpoint() {
    return this.getAttribute("endpoint") || "/api";
  }

  get siteKey() {
    return this.getAttribute("site-key") || "demo-key";
  }

  get policy() {
    return this.getAttribute("policy") || "P3";
  }

  set policy(val) {
    this.setAttribute("policy", val);
  }

  get breachCost() {
    const val = this.getAttribute("breach-cost");
    return val ? parseFloat(val) : null;
  }

  set breachCost(val) {
    if (val !== null && val !== undefined) {
      this.setAttribute("breach-cost", String(val));
    } else {
      this.removeAttribute("breach-cost");
    }
  }

  reset() {
    this._stopPowWorker();
    this._state = "idle";
    this._token = null;
    this._session = null;
    this._activeChallenge = null;
    this._challengeStartTime = null;
    this.$box.innerHTML = "";
    this.$label.textContent = "Verify you are human";
    this.$challengeBox.style.display = "none";
    this.$challengeError.style.display = "none";
    this.$btn.setAttribute("aria-busy", "false");
    this._mountTime = Date.now();
    this._events = [];
    this._startCollector();
  }

  connectedCallback() {
    this._bindEvents();
    this._startCollector();
    this._loadConfig();
    this._initRememberedNeeds();
    this._updatePrivacyNotice();
  }

  disconnectedCallback() {
    this._stopPowWorker();
    this._stopCollector();
  }

  _stopPowWorker() {
    if (this._powWorker) {
      try { this._powWorker.terminate(); } catch (e) {}
      this._powWorker = null;
    }
  }

  _initRememberedNeeds() {
    try {
      const saved = localStorage.getItem("captcha_access_needs");
      if (saved) {
        const needs = JSON.parse(saved);
        if (Array.isArray(needs)) {
          if (this.$rememberCb) this.$rememberCb.checked = true;
          const cbs = this.shadowRoot.querySelectorAll(".a11y-cb");
          cbs.forEach(cb => {
            if (needs.includes(cb.value)) cb.checked = true;
          });
        }
      }
    } catch (e) {
      // localStorage disabled / denied
    }
  }

  _handleRememberNeeds() {
    try {
      if (this.$rememberCb && this.$rememberCb.checked) {
        const needs = this._getSelectedNeeds();
        localStorage.setItem("captcha_access_needs", JSON.stringify(needs));
      } else {
        localStorage.removeItem("captcha_access_needs");
      }
    } catch (e) {}
  }

  async _loadConfig() {
    try {
      const mode = (this.policy === "P1" || this.policy === "P2") ? "full" : "min";
      const res = await fetch(`${this.endpoint}/config?mode=${mode}`);
      if (res.ok) {
        const data = await res.json();
        this._requiredFeatures = data.required_features;
      }
    } catch (e) {
      // offline / pre-load error
    }
  }

  disconnectedCallback() {
    this._stopCollector();
  }

  _startCollector() {
    if (this._listenersActive) return;
    this._mountTime = Date.now();
    this._events = [];

    this._onPointerMove = (e) => {
      this._pointerType = e.pointerType || "mouse";
      const t = Date.now() - this._mountTime;
      this._events.push([t, 0, Math.round(e.clientX), Math.round(e.clientY)]);
      if (this._events.length > 600) {
        // Keep ring buffer reasonable
        this._events.shift();
      }
    };

    this._onPointerDown = (e) => {
      this._pointerType = e.pointerType || "mouse";
      const t = Date.now() - this._mountTime;
      this._events.push([t, 1, Math.round(e.clientX), Math.round(e.clientY)]);
    };

    this._onKeyDown = (e) => {
      const t = Date.now() - this._mountTime;
      const code = (e.key === "Backspace" || e.keyCode === 8) ? 3 : 2;
      this._events.push([t, code, 0, 0]);
    };

    this._onScroll = () => {
      const t = Date.now() - this._mountTime;
      this._events.push([t, 4, 0, 0]);
    };

    this._onFocusIn = () => {
      const t = Date.now() - this._mountTime;
      this._events.push([t, 5, 0, 0]);
    };

    window.addEventListener("pointermove", this._onPointerMove, { passive: true });
    window.addEventListener("pointerdown", this._onPointerDown, { passive: true });
    window.addEventListener("keydown", this._onKeyDown, { passive: true });
    window.addEventListener("scroll", this._onScroll, { passive: true });
    window.addEventListener("focusin", this._onFocusIn, { passive: true });
    this._listenersActive = true;
  }

  _stopCollector() {
    if (!this._listenersActive) return;
    window.removeEventListener("pointermove", this._onPointerMove);
    window.removeEventListener("pointerdown", this._onPointerDown);
    window.removeEventListener("keydown", this._onKeyDown);
    window.removeEventListener("scroll", this._onScroll);
    window.removeEventListener("focusin", this._onFocusIn);
    this._listenersActive = false;
  }

  _bindEvents() {
    this.$btn.addEventListener("click", () => {
      if (this._state === "idle") {
        this.verify();
      }
    });

    this.$a11yToggle.addEventListener("click", () => {
      const isHidden = this.$a11yOptions.classList.toggle("hidden");
      this.$a11yToggle.setAttribute("aria-expanded", String(!isHidden));
    });

    const cbs = this.shadowRoot.querySelectorAll(".a11y-cb");
    cbs.forEach(cb => {
      cb.addEventListener("change", () => this._onNeedsChanged());
    });

    if (this.$rememberCb) {
      this.$rememberCb.addEventListener("change", () => this._handleRememberNeeds());
    }

    this.$switchBtn.addEventListener("click", () => this._switchChallenge());
    this.$submitBtn.addEventListener("click", () => this._submitChallenge());
  }

  async _onNeedsChanged() {
    this._handleRememberNeeds();
    const needs = this._getSelectedNeeds();
    if (this._session && this._activeChallenge && this._state === "challenge") {
      const seq = ++this._needsSeq;
      try {
        const res = await fetch(`${this.endpoint}/session/needs`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: this._session.session_id,
            access_needs: needs
          })
        });
        if (res.ok && seq === this._needsSeq) {
          const data = await res.json();
          this._showChallenge(data.challenge);
          this._announce("Accessibility needs updated. New compatible challenge loaded.");
        }
      } catch (err) {
        console.error("Failed to update needs dynamically:", err);
      }
    }
  }

  _announce(msg) {
    this.$srStatus.textContent = msg;
  }

  _getSelectedNeeds() {
    const cbs = this.shadowRoot.querySelectorAll(".a11y-cb:checked");
    return Array.from(cbs).map(cb => cb.value);
  }

  _updatePrivacyNotice(featuresCount = 8, bytes = 68) {
    this.$privacyNotice.textContent =
      `Sends ${featuresCount} numbers (${bytes} bytes) about your interaction timing. No keystrokes, text or movement path.`;
  }

  async verify() {
    if (this._state === "checking" || this._state === "passed") return this._token;

    this._state = "checking";
    this.$btn.setAttribute("aria-busy", "true");
    this.$box.innerHTML = `<div class="spinner"></div>`;
    this.$label.textContent = "Verifying...";
    this._announce("Verifying interaction...");

    // Build raw trace
    const verifyT = Date.now() - this._mountTime;
    const trace = {
      meta: {
        verify_t: verifyT,
        pointer_type: this._pointerType
      },
      events: this._events
    };

    // Extract features locally (privacy by construction)
    const mode = (this.policy === "P1" || this.policy === "P2") ? "full" : "min";
    if (!this._requiredFeatures) {
      await this._loadConfig();
    }
    const requiredNames = this._requiredFeatures || (mode === "full" ? FEATURE_NAMES : [
      "p_dir_changes_per_100px", "t_first_interaction", "p_speed_std", "p_speed_mean",
      "p_path_len", "p_acc_std", "t_idle_ratio", "k_gap_mean"
    ]);

    let payloadFeatures = buildFeaturePayload(trace, requiredNames);
    if (this.getAttribute("simulate-risk") === "high") {
      // Simulate automated interaction with varied first feature to avoid replay cache
      payloadFeatures = {};
      requiredNames.forEach((k, idx) => {
        payloadFeatures[k] = idx === 0 ? (Date.now() % 1000) * 0.001 : 0.0;
      });
    }

    const featureCount = Object.keys(payloadFeatures).length;
    const payloadBytes = new TextEncoder().encode(JSON.stringify(payloadFeatures)).length;
    this._updatePrivacyNotice(featureCount, payloadBytes);

    const needs = this._getSelectedNeeds();

    try {
      const payload = {
        site_key: this.siteKey,
        features: payloadFeatures,
        access_needs: needs,
        policy: this.policy
      };
      if (this.breachCost !== null) {
        payload.breach_cost = this.breachCost;
      }

      const res = await fetch(`${this.endpoint}/session`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        throw new Error(`Session error: ${res.status}`);
      }

      const data = await res.json();
      this._session = data;

      // Dispatch event with decision trace for demo page
      this.dispatchEvent(new CustomEvent("captcha-decision", {
        detail: data.trace,
        bubbles: true,
        composed: true
      }));

      if (data.action === "pass") {
        this._onPass(data.token);
        return data.token;
      } else {
        this._showChallenge(data.challenge);
      }
    } catch (err) {
      this._onError(err.message);
    }
  }

  _onPass(token) {
    this._state = "passed";
    this._token = token;
    this.$box.innerHTML = `<span class="passed-check">✓</span>`;
    this.$label.textContent = "Verification complete";
    this.$challengeBox.style.display = "none";
    this.$btn.setAttribute("aria-busy", "false");
    this._announce("Verification successful.");

    this.dispatchEvent(new CustomEvent("captcha-verified", {
      detail: { token },
      bubbles: true,
      composed: true
    }));
  }

  _showChallenge(challenge) {
    this._stopPowWorker();
    this.$btn.setAttribute("aria-busy", "false");
    this._state = "challenge";
    this._activeChallenge = challenge;
    this._challengeStartTime = Date.now();

    this.$box.innerHTML = ``;
    this.$label.textContent = "Complete challenge below";
    this.$challengeBox.style.display = "block";
    this.$challengeError.style.display = "none";

    const ctype = challenge.type;
    this.$challengePrompt.textContent = challenge.prompt || "Solve the challenge";
    this.$challengeContent.innerHTML = "";

    // Render alternative challenge buttons
    const allAlts = [
      { type: "audio", label: "Audio" },
      { type: "visual", label: "Visual" },
      { type: "drag", label: "Drag" },
      { type: "automatic", label: "Automatic" }
    ];
    const availableAlts = allAlts.filter(a => a.type !== ctype && (a.type !== "automatic" || ctype !== "pow"));
    if (this.$altButtons) {
      this.$altButtons.innerHTML = "";
      availableAlts.forEach(alt => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "alt-btn";
        btn.textContent = alt.label;
        btn.addEventListener("click", () => this._switchChallenge(alt.type));
        this.$altButtons.appendChild(btn);
      });
    }

    if (ctype === "visual") {
      this._renderVisual(challenge);
    } else if (ctype === "audio") {
      this._renderAudio(challenge);
    } else if (ctype === "drag") {
      this._renderDrag(challenge);
    } else if (ctype === "pow") {
      this._renderPow(challenge);
    }

    // Move focus to heading and announce via aria-live
    this.$challengePrompt.focus();

    let altHint = "an audio alternative";
    if (ctype === "audio") altHint = "a visual alternative";
    else if (ctype === "visual") altHint = "an audio alternative";
    else if (ctype === "drag") altHint = "an audio alternative";
    else if (ctype === "pow") altHint = "an audio alternative";

    const challengeName = ctype === "pow" ? "Automatic" : ctype.charAt(0).toUpperCase() + ctype.slice(1);
    this._announce(`${challengeName} challenge. Press Tab for ${altHint}.`);
  }

  _renderVisual(challenge) {
    const grid = document.createElement("div");
    grid.className = "grid-container";
    grid.setAttribute("role", "group");
    grid.setAttribute("aria-labelledby", "challengePrompt");
    this._selectedTiles = new Set();

    challenge.tiles.forEach((tileUri, idx) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "grid-tile";
      btn.setAttribute("aria-label", `Tile ${idx + 1}`);
      btn.setAttribute("aria-pressed", "false");
      const img = document.createElement("img");
      img.src = tileUri;
      img.alt = "";
      btn.appendChild(img);

      btn.addEventListener("click", () => {
        if (this._selectedTiles.has(idx)) {
          this._selectedTiles.delete(idx);
          btn.classList.remove("selected");
          btn.setAttribute("aria-pressed", "false");
        } else {
          this._selectedTiles.add(idx);
          btn.classList.add("selected");
          btn.setAttribute("aria-pressed", "true");
        }
      });
      grid.appendChild(btn);
    });

    this.$challengeContent.appendChild(grid);
  }

  _renderAudio(challenge) {
    const box = document.createElement("div");
    box.className = "audio-player-box";

    const ctrl = document.createElement("div");
    ctrl.className = "audio-controls";

    const playBtn = document.createElement("button");
    playBtn.type = "button";
    playBtn.className = "btn-secondary";
    playBtn.textContent = "Play audio";
    playBtn.setAttribute("aria-label", "Play audio");

    let replayCount = 0;
    const countBadge = document.createElement("span");
    countBadge.style.fontSize = "11px";
    countBadge.style.color = "var(--cap-muted)";
    countBadge.textContent = "3 plays left";

    const audioEl = new Audio(challenge.audio_url);
    playBtn.addEventListener("click", () => {
      if (replayCount >= 3) return;
      audioEl.currentTime = 0;
      const playPromise = audioEl.play();
      if (playPromise && playPromise.catch) {
        playPromise.catch((err) => {
          console.warn("Audio playback failed or blocked:", err);
        });
      }
      replayCount++;
      const left = 3 - replayCount;
      countBadge.textContent = `${left} play${left === 1 ? '' : 's'} left`;
      if (left === 0) playBtn.disabled = true;
    });

    ctrl.appendChild(playBtn);
    ctrl.appendChild(countBadge);

    const input = document.createElement("input");
    input.type = "text";
    input.className = "audio-input";
    input.placeholder = `Enter the ${challenge.length} numbers`;
    input.id = "audioAnswerInput";
    input.setAttribute("aria-label", `Enter the ${challenge.length} numbers heard in audio`);
    input.setAttribute("inputmode", "numeric");
    input.setAttribute("autocomplete", "off");

    box.appendChild(ctrl);
    box.appendChild(input);
    this.$challengeContent.appendChild(box);
  }

  _renderDrag(challenge) {
    const container = document.createElement("div");
    container.className = "drag-container";

    const bgImg = document.createElement("img");
    bgImg.src = challenge.bg_image;
    bgImg.className = "drag-bg";
    container.appendChild(bgImg);

    const piece = document.createElement("img");
    piece.src = challenge.piece_image;
    piece.className = "drag-piece";
    piece.style.top = `${challenge.piece_y}px`;
    piece.style.left = "0px";
    container.appendChild(piece);

    // Accessible slider control
    const slider = document.createElement("input");
    slider.type = "range";
    slider.className = "drag-slider-track";
    slider.min = "0";
    slider.max = String(challenge.bg_width - challenge.piece_size);
    slider.value = "0";
    slider.setAttribute("role", "slider");
    slider.setAttribute("aria-label", "Puzzle position slider");

    slider.addEventListener("input", (e) => {
      const val = Number(e.target.value);
      piece.style.left = `${val}px`;
      this._dragPosition = val;
    });

    this._dragPosition = 0;
    this.$challengeContent.appendChild(container);
    this.$challengeContent.appendChild(slider);
  }

  async _renderPow(challenge) {
    this._stopPowWorker();
    const box = document.createElement("div");
    box.className = "pow-box";

    if (!window.crypto || !window.crypto.subtle) {
      box.innerHTML = `<div class="error-text" style="display:block;">Web Crypto API (crypto.subtle) is not available. Please access via HTTPS or localhost.</div>`;
      this._announce("Web Crypto API is not available.");
      this.$challengeContent.appendChild(box);
      return;
    }

    box.innerHTML = `
      <div>Computing proof-of-work security token (${challenge.bits} bits)...</div>
      <div class="progress-bar-bg"><div class="progress-bar-fill" id="powFill"></div></div>
    `;
    this.$challengeContent.appendChild(box);
    this.$submitBtn.disabled = true;

    const fill = box.querySelector("#powFill");
    fill.style.width = "40%";

    const workerCode = `
      self.onmessage = async (e) => {
        const { nonce, bits } = e.data;
        const encoder = new TextEncoder();
        let counter = 0;
        while (true) {
          const data = encoder.encode(nonce + ":" + counter);
          const hashBuf = await crypto.subtle.digest("SHA-256", data);
          const hashBytes = new Uint8Array(hashBuf);
          let zeros = 0;
          for (let i = 0; i < hashBytes.length; i++) {
            const b = hashBytes[i];
            if (b === 0) {
              zeros += 8;
            } else {
              zeros += Math.clz32(b) - 24;
              break;
            }
          }
          if (zeros >= bits) {
            self.postMessage({ ok: true, counter });
            break;
          }
          counter++;
          if (counter % 5000 === 0) {
            self.postMessage({ progress: counter });
          }
        }
      };
    `;

    const blob = new Blob([workerCode], { type: "application/javascript" });
    const workerUrl = URL.createObjectURL(blob);
    this._powWorker = new Worker(workerUrl);

    this._powWorker.onmessage = (e) => {
      if (e.data.ok) {
        this._powCounter = e.data.counter;
        fill.style.width = "100%";
        this.$submitBtn.disabled = false;
        this._stopPowWorker();
        URL.revokeObjectURL(workerUrl);
        this._submitChallenge();
      } else if (e.data.progress) {
        fill.style.width = `${Math.min(95, 40 + (e.data.progress / 30000) * 50)}%`;
      }
    };

    this._powWorker.onerror = (err) => {
      console.error("PoW worker error:", err);
      this._stopPowWorker();
      URL.revokeObjectURL(workerUrl);
    };

    this._powWorker.postMessage({ nonce: challenge.nonce, bits: challenge.bits });
  }

  async _submitChallenge() {
    if (!this._session || !this._activeChallenge) return;

    const durationMs = Date.now() - (this._challengeStartTime || this._mountTime);
    let answer = null;
    const ctype = this._activeChallenge.type;

    if (ctype === "visual") {
      answer = Array.from(this._selectedTiles || []);
    } else if (ctype === "audio") {
      const inp = this.shadowRoot.getElementById("audioAnswerInput");
      answer = inp ? inp.value.trim() : "";
    } else if (ctype === "drag") {
      answer = { x: this._dragPosition || 0 };
    } else if (ctype === "pow") {
      answer = { counter: this._powCounter || 0 };
    }

    this.$submitBtn.disabled = true;
    this.$submitBtn.textContent = "Checking...";

    try {
      const res = await fetch(`${this.endpoint}/challenge/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: this._session.session_id,
          challenge_id: this._activeChallenge.challenge_id,
          answer: answer,
          interaction: {}
        })
      });

      const data = await res.json();
      this.$submitBtn.disabled = false;
      this.$submitBtn.textContent = "Verify";

      if (data.ok) {
        this._onPass(data.token);
      } else {
        if (data.locked) {
          this._state = "locked";
          this._stopPowWorker();
          this.$btn.setAttribute("aria-busy", "false");
          this.$challengePrompt.textContent = "Session locked";
          this.$challengeContent.innerHTML = `
            <p>Too many failed attempts. You can start over to try again.</p>
            <button type="button" class="btn-primary" id="startOverBtn" style="margin-top: 8px;">Start over</button>
          `;
          this.$submitBtn.style.display = "none";
          this.$switchBtn.style.display = "none";
          const startOverBtn = this.$challengeContent.querySelector("#startOverBtn");
          if (startOverBtn) {
            startOverBtn.addEventListener("click", () => this._startOver());
          }
        } else {
          this.$challengeError.textContent = `${data.error || "Incorrect solution"}. (${data.attempts_left} attempts left)`;
          this.$challengeError.style.display = "block";
          if (data.new_challenge) {
            this._showChallenge(data.new_challenge);
          }
        }
      }
    } catch (err) {
      this.$submitBtn.disabled = false;
      this.$submitBtn.textContent = "Verify";
      this.$challengeError.textContent = err.message;
      this.$challengeError.style.display = "block";
    }
  }

  async _switchChallenge(targetType = null) {
    if (!this._session) return;
    this.$switchBtn.disabled = true;

    try {
      const payload = { session_id: this._session.session_id };
      if (targetType) payload.target_type = targetType;

      const res = await fetch(`${this.endpoint}/challenge/switch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      this.$switchBtn.disabled = false;

      if (!res.ok) {
        this.$challengeError.textContent = data.detail || "Cannot switch challenge";
        this.$challengeError.style.display = "block";
        return;
      }

      this._showChallenge(data.challenge);
    } catch (err) {
      this.$switchBtn.disabled = false;
      this.$challengeError.textContent = err.message;
      this.$challengeError.style.display = "block";
    }
  }

  _startOver() {
    this._state = "idle";
    this._session = null;
    this._activeChallenge = null;
    this._token = null;
    this._stopPowWorker();
    this.$challengeBox.classList.remove("active");
    this.$challengeBox.style.display = "none";
    this.$btn.disabled = false;
    this.$btn.setAttribute("aria-busy", "false");
    this.$box.innerHTML = "";
    this.$label.textContent = "Verify you are human";
    this.$submitBtn.style.display = "";
    this.$switchBtn.style.display = "";
    this.$submitBtn.disabled = false;
    this.$switchBtn.disabled = false;
    this.$challengeError.style.display = "none";
    this._announce("Verification reset. Press Verify to start again.");
  }

  _onError(msg) {
    this._state = "error";
    this._stopPowWorker();
    this.$btn.setAttribute("aria-busy", "false");
    this.$box.innerHTML = `<span style="color:var(--cap-danger)">✕</span>`;
    this.$label.textContent = "Verification failed";
    this.$challengeError.textContent = msg;
    this.$challengeError.style.display = "block";
    this.dispatchEvent(new CustomEvent("captcha-error", {
      detail: { error: msg },
      bubbles: true,
      composed: true
    }));
  }
}

customElements.define("adaptive-captcha", AdaptiveCaptcha);
