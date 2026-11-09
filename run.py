import sys
from pathlib import Path
import uvicorn

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

def main():
    artifacts_dir = BASE_DIR / "ml" / "artifacts"
    risk_min = artifacts_dir / "risk_min.joblib"
    
    if not risk_min.exists():
        print("[run.py] Artifacts missing. Training models...")
        try:
            from ml.train import train_all
            train_all()
        except ImportError:
            print("[run.py] Training module not yet present (Phase 0). Skipping training.")
    
    print("[run.py] Starting server on http://127.0.0.1:8000 ...")
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=False)

if __name__ == "__main__":
    main()

