from __future__ import annotations

import io
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from .config import MODEL_DIR
from .model_loader import (
    find_model_entry,
    get_artifacts,
    list_model_entries,
    load_model,
    predict_proba,
)
from .schemas import ModelInfo, PredictResponse, RowPrediction
from .ui import render_index


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
# `swagger_ui_parameters={"defaultModelsExpandDepth": -1}` hides the giant
# "Schemas" section at the bottom of /docs (per user's "remove schemas part
# from the web" request). `redoc_url=None` disables the redoc page entirely
# since redoc always lists schemas.
app = FastAPI(
    title="CSE499A IDS Model API",
    version="0.2.0",
    description="Web UI + JSON API for the trained IDS models in '../Saved models'.",
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
MAX_BATCH_ROWS = 200


def _scale(x: np.ndarray) -> np.ndarray:
    arts = get_artifacts()
    if arts.scaler is None:
        return x.astype(np.float32, copy=False)
    return arts.scaler.transform(x).astype(np.float32, copy=False)


def _build_row(probs_row: np.ndarray, top_k: int) -> RowPrediction:
    arts = get_artifacts()
    pred_idx = int(np.argmax(probs_row))
    k = max(1, min(int(top_k), probs_row.shape[0]))
    top_idx = list(np.argsort(-probs_row)[:k])
    top_data: List[Dict[str, Any]] = [
        {
            "index": int(i),
            "label": arts.class_names[int(i)] if 0 <= int(i) < len(arts.class_names) else None,
            "prob": float(probs_row[int(i)]),
        }
        for i in top_idx
    ]
    pred_label: Optional[str] = (
        arts.class_names[pred_idx] if 0 <= pred_idx < len(arts.class_names) else None
    )
    return RowPrediction(
        pred_class_id=pred_idx,
        pred_label=pred_label,
        proba=[float(v) for v in probs_row.tolist()],
        top_k=top_data,
    )


def _parse_features_string(s: str, expected: int) -> np.ndarray:
    parts = [p.strip() for p in s.replace("\n", ",").split(",") if p.strip()]
    if len(parts) != expected:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Feature count mismatch.",
                "expected": expected,
                "received": len(parts),
            },
        )
    try:
        values = [float(p) for p in parts]
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"message": f"Could not parse number: {e}"},
        )
    return np.asarray([values], dtype=np.float32)


def _parse_csv_bytes(raw: bytes, feature_columns: List[str]) -> np.ndarray:
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"message": f"Could not parse CSV: {e}"},
        )
    missing = [c for c in feature_columns if c not in df.columns]
    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "CSV is missing required feature columns.",
                "missing": missing[:20],
            },
        )
    arr = df[feature_columns].to_numpy(dtype=np.float32)
    if arr.shape[0] > MAX_BATCH_ROWS:
        arr = arr[:MAX_BATCH_ROWS]
    if arr.shape[0] == 0:
        raise HTTPException(
            status_code=400,
            detail={"message": "CSV contained zero data rows."},
        )
    return arr


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index() -> HTMLResponse:
    """Serve the HTML web UI."""
    arts = get_artifacts()
    model_options = [e.id for e in list_model_entries()]
    html = render_index(
        model_options=model_options,
        feature_count=arts.num_features,
        feature_preview=arts.feature_columns,
        class_names=arts.class_names,
    )
    return HTMLResponse(content=html)


@app.get("/health", include_in_schema=False)
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> JSONResponse:
    return JSONResponse(content={}, status_code=204)


@app.get("/models", response_model=List[ModelInfo])
def models() -> List[ModelInfo]:
    """List every loadable model under the Saved models folder."""
    arts = get_artifacts()
    out: List[ModelInfo] = []
    for e in list_model_entries():
        item = ModelInfo(
            id=e.id,
            family=e.family,
            framework=e.framework,
            path=str(e.path),
            num_classes=arts.num_classes,
            class_names=arts.class_names,
        )
        if e.framework == "keras":
            try:
                loaded = load_model(e)
                if loaded.input_shape is not None:
                    item.input_shape = [
                        (None if v is None else int(v)) for v in loaded.input_shape
                    ]
            except Exception:
                pass
        out.append(item)
    return out


@app.post("/predict", response_model=PredictResponse)
async def predict(
    model_id: str = Form(..., description="One of the IDs from GET /models."),
    file: Optional[UploadFile] = File(None, description="Optional CSV with the feature columns."),
    features: Optional[str] = Form(None, description="Optional comma-separated feature values for a single row."),
    top_k: int = Form(5, description="Number of top classes to return per row."),
) -> PredictResponse:
    """Run a prediction.

    Provide *either* a CSV file (batch) **or** a comma-separated string of
    feature values (single row). The CSV path supports up to 200 rows.
    """
    entry = find_model_entry(model_id)
    if entry is None:
        available = [e.id for e in list_model_entries()]
        raise HTTPException(
            status_code=404,
            detail={"message": f"Unknown model_id '{model_id}'.", "available": available},
        )

    arts = get_artifacts()

    if file is not None and file.filename:
        raw = await file.read()
        if not raw:
            raise HTTPException(status_code=400, detail={"message": "Empty CSV upload."})
        x_raw = _parse_csv_bytes(raw, arts.feature_columns)
    elif features and features.strip():
        x_raw = _parse_features_string(features, arts.num_features)
    else:
        raise HTTPException(
            status_code=400,
            detail={"message": "Provide either a CSV file or comma-separated feature values."},
        )

    x_scaled = _scale(x_raw)
    loaded = load_model(entry)
    probs = predict_proba(loaded, x_scaled)
    rows = [_build_row(probs[i], top_k) for i in range(probs.shape[0])]

    return PredictResponse(model_id=model_id, num_rows=int(probs.shape[0]), predictions=rows)
