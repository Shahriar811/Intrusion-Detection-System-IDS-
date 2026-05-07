from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, List, Optional, Tuple

import joblib
import numpy as np

from .config import DL_DIR, ML_DIR, MODEL_DIR


# ---------------------------------------------------------------------------
# Shared artifacts (scaler, label encoder, feature columns, model_info.json)
# ---------------------------------------------------------------------------
@dataclass
class Artifacts:
    feature_columns: List[str]
    class_names: List[str]
    num_features: int
    num_classes: int
    scaler: Any
    label_encoder: Any
    info: dict = field(default_factory=dict)


@lru_cache(maxsize=1)
def get_artifacts() -> Artifacts:
    info_path = MODEL_DIR / "model_info.json"
    feat_path = MODEL_DIR / "feature_cols.joblib"
    le_path = MODEL_DIR / "label_encoder.joblib"
    sc_path = MODEL_DIR / "scaler.joblib"

    if not info_path.exists():
        raise FileNotFoundError(f"model_info.json not found in {MODEL_DIR}")

    with info_path.open("r", encoding="utf-8") as f:
        info = json.load(f)

    feature_columns = (
        list(joblib.load(feat_path)) if feat_path.exists() else list(info.get("feature_columns", []))
    )
    class_names = list(info.get("class_names", []))

    scaler = joblib.load(sc_path) if sc_path.exists() else None
    label_encoder = joblib.load(le_path) if le_path.exists() else None

    if label_encoder is not None and not class_names:
        class_names = list(getattr(label_encoder, "classes_", []))

    return Artifacts(
        feature_columns=feature_columns,
        class_names=class_names,
        num_features=int(info.get("num_features", len(feature_columns))),
        num_classes=int(info.get("num_classes", len(class_names))),
        scaler=scaler,
        label_encoder=label_encoder,
        info=info,
    )


# ---------------------------------------------------------------------------
# Model discovery
# ---------------------------------------------------------------------------
@dataclass
class ModelEntry:
    id: str
    family: str
    framework: str
    path: Path


def list_model_entries() -> List[ModelEntry]:
    entries: List[ModelEntry] = []
    if DL_DIR.exists():
        for p in sorted(DL_DIR.glob("*.keras")):
            entries.append(ModelEntry(id=p.name, family="Deep_Learning", framework="keras", path=p))
    if ML_DIR.exists():
        for p in sorted(ML_DIR.glob("*.joblib")):
            entries.append(ModelEntry(id=p.name, family="Traditional_ML", framework="sklearn", path=p))
    return entries


def find_model_entry(model_id: str) -> Optional[ModelEntry]:
    for e in list_model_entries():
        if e.id == model_id:
            return e
    return None


# ---------------------------------------------------------------------------
# Loaded model wrapper
# ---------------------------------------------------------------------------
@dataclass
class LoadedModel:
    entry: ModelEntry
    obj: Any
    input_shape: Optional[Tuple[Optional[int], ...]] = None


@lru_cache(maxsize=32)
def _get_loaded(model_path_str: str, framework: str) -> Any:
    p = Path(model_path_str)
    if not p.exists():
        raise FileNotFoundError(model_path_str)
    if framework == "sklearn":
        return joblib.load(p)
    if framework == "keras":
        # Lazy import so the API can still serve traditional ML models
        # even on machines where TensorFlow installs flaky.
        from tensorflow import keras  # type: ignore

        return keras.models.load_model(p, compile=False)
    raise ValueError(f"Unsupported framework: {framework}")


def load_model(entry: ModelEntry) -> LoadedModel:
    obj = _get_loaded(str(entry.path), entry.framework)
    input_shape = None
    if entry.framework == "keras":
        try:
            input_shape = tuple(obj.input_shape)  # type: ignore[attr-defined]
        except Exception:
            input_shape = None
    return LoadedModel(entry=entry, obj=obj, input_shape=input_shape)


# ---------------------------------------------------------------------------
# Inference helpers
# ---------------------------------------------------------------------------
def _reshape_for_keras(x_2d: np.ndarray, input_shape: Optional[Tuple[Optional[int], ...]]) -> np.ndarray:
    """Reshape a (batch, num_features) float array to whatever the keras model expects.

    Handles the common cases used in this project:
      - Dense:        (None, F)
      - 1D conv/RNN:  (None, F, 1)  or  (None, 1, F)
      - 2D conv:      (None, H, W, 1) where H*W == F
    """
    n, f = x_2d.shape
    if input_shape is None:
        return x_2d
    shape = tuple(s for s in input_shape if s is not None)

    if len(shape) == 1:
        return x_2d.astype(np.float32, copy=False)

    if len(shape) == 2:
        a, b = shape
        if a == f and b == 1:
            return x_2d.reshape(n, f, 1).astype(np.float32, copy=False)
        if a == 1 and b == f:
            return x_2d.reshape(n, 1, f).astype(np.float32, copy=False)
        return x_2d.reshape((n,) + shape).astype(np.float32, copy=False)

    if len(shape) == 3:
        a, b, c = shape
        if a * b == f and c == 1:
            return x_2d.reshape(n, a, b, 1).astype(np.float32, copy=False)
        if a == f and b == 1 and c == 1:
            return x_2d.reshape(n, f, 1, 1).astype(np.float32, copy=False)

    return x_2d.reshape((n,) + shape).astype(np.float32, copy=False)


def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def predict_proba(loaded: LoadedModel, x_scaled_2d: np.ndarray) -> np.ndarray:
    """Return a (batch, num_classes) probability array for any supported model."""
    if loaded.entry.framework == "sklearn":
        m = loaded.obj
        if hasattr(m, "predict_proba"):
            return np.asarray(m.predict_proba(x_scaled_2d), dtype=np.float32)
        if hasattr(m, "decision_function"):
            scores = np.asarray(m.decision_function(x_scaled_2d), dtype=np.float32)
            if scores.ndim == 1:
                scores = np.stack([-scores, scores], axis=1)
            return _softmax(scores)
        preds = np.asarray(m.predict(x_scaled_2d)).astype(int)
        n_classes = int(preds.max()) + 1
        out = np.zeros((preds.shape[0], n_classes), dtype=np.float32)
        out[np.arange(preds.shape[0]), preds] = 1.0
        return out

    # Keras
    x = _reshape_for_keras(x_scaled_2d, loaded.input_shape)
    out = np.asarray(loaded.obj.predict(x, verbose=0))
    if out.ndim != 2:
        out = out.reshape(out.shape[0], -1)
    # DQN-style models output raw Q-values; everything else outputs softmax-ish probs.
    row_sums = out.sum(axis=1)
    looks_like_probs = (
        np.all(out >= -1e-4)
        and np.all(out <= 1.0 + 1e-4)
        and np.all(np.abs(row_sums - 1.0) < 1e-2)
    )
    if not looks_like_probs:
        out = _softmax(out)
    return out.astype(np.float32, copy=False)
