from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    id: str = Field(..., description="Model identifier (filename)")
    family: str = Field(..., description="'Deep_Learning' or 'Traditional_ML'")
    framework: str = Field(..., description="'keras' or 'sklearn'")
    path: str
    num_classes: Optional[int] = None
    class_names: Optional[List[str]] = None
    input_shape: Optional[List[Optional[int]]] = None


class RowPrediction(BaseModel):
    pred_class_id: int
    pred_label: Optional[str] = None
    proba: Optional[List[float]] = None
    top_k: Optional[List[Dict[str, Any]]] = None


class PredictResponse(BaseModel):
    model_id: str
    num_rows: int
    predictions: List[RowPrediction]
