# Architecture and Decision Log

This document records key technical decisions, environment constraints, and fallbacks applied per SPEC.md Section 10.4.

## D-001: Preflight Environment Inspection (Phase 0)
- **Date**: 2026-11-09
- **Observation**:
  - Python: 3.14.3 with pip 26.2.1
  - Node.js: v24.13.0 with builtin `--test`
  - Core dependencies: `fastapi` 0.135.2, `pydantic` 2.12.5, `numpy` 2.4.3, `pandas` 3.0.5, `scikit-learn` 1.8.0, `joblib` 1.5.3, `Pillow` 12.3.0, `pytest` 9.2.0, `httpx` 0.28.1, `xgboost` 3.2.0 are pre-installed and functional.
  - Playwright: Not pre-installed in the global environment. In accordance with Section 10.4 ("Playwright missing -> browser-tool screenshots plus API tests, noted in the log"), we record this fallback for browser E2E tests if offline sandbox pip install cannot fetch browser binaries.
  - TTS: Windows native `System.Speech.Synthesis.SpeechSynthesizer` is available in PowerShell / SAPI5. We will utilize this to generate the required 10 digit wav clips without remote dependencies.

