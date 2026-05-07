from __future__ import annotations

import os
from pathlib import Path


def _default_model_dir() -> Path:
    # Default points to the project's "Saved models" folder, which sits next to
    # the "Global API" folder. Override with the MODEL_DIR env var if needed.
    return (Path(__file__).resolve().parents[2] / "Saved models").resolve()


MODEL_DIR = Path(os.environ.get("MODEL_DIR", str(_default_model_dir()))).expanduser().resolve()
DL_DIR = MODEL_DIR / "Deep_Learning"
ML_DIR = MODEL_DIR / "Traditional_ML"

API_HOST = os.environ.get("API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("API_PORT", "8000"))
