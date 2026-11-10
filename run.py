import sys
import os
from pathlib import Path
import uvicorn

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

def main_train_step(force: bool = False):
    artifacts_dir = BASE_DIR / "ml" / "artifacts"
    risk_min = artifacts_dir / "risk_min.joblib"

    if force or not risk_min.exists():
        print("[run.py] Artifacts missing. Training models...")
        try:
            from ml.train import train_all
        except ModuleNotFoundError as e:
            if "ml.train" in str(e) or getattr(e, "name", "") == "ml.train":
                print("[run.py] Training module ml.train not found.")
                sys.exit(1)
            raise

        train_all()

        assert (artifacts_dir / "risk_min.joblib").exists(), "Missing risk_min.joblib artifact after training!"
        assert (artifacts_dir / "risk_full.joblib").exists(), "Missing risk_full.joblib artifact after training!"
        assert (artifacts_dir / "metrics.json").exists(), "Missing metrics.json artifact after training!"

def main():
    main_train_step()
    print("[run.py] Starting server on http://127.0.0.1:8000 ...")
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=False)

if __name__ == "__main__":
    main()
