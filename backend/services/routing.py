from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import joblib
import numpy as np

from backend.db import get_con, ROOT


ARTIFACT_DIR = ROOT / "ml" / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "routing_model.joblib"
ENCODER_PATH = ARTIFACT_DIR / "routing_encoder.joblib"


_model = None
_encoder = None


def _load_model():
    global _model, _encoder
    if _model is None and MODEL_PATH.exists():
        try:
            _model = joblib.load(MODEL_PATH)
        except Exception:
            _model = None
    if _encoder is None and ENCODER_PATH.exists():
        try:
            _encoder = joblib.load(ENCODER_PATH)
        except Exception:
            _encoder = None


def _onehot_from_fields(request_type: str, origin: str, district: str, create_month: int):
    if _encoder is None:
        return None
    X = [{
        "Request_Type": request_type or "",
        "Origin": origin or "",
        "District": district or "",
        "create_month": int(create_month) if create_month is not None else -1,
    }]
    try:
        return _encoder.transform(X)
    except Exception:
        return None


def _freq_baseline(request_type: Optional[str]) -> Tuple[Optional[str], float, List[Tuple[str, int]]]:
    """Return (dept, confidence, top_list) using historical distribution for the Request_Type.
    Confidence = top_count / total for that Request_Type. If no rows, return (None, 0, []).
    """
    if not request_type:
        return None, 0.0, []
    con = get_con()
    rows = con.execute(
        """
        select Department, count(*) as c
        from tickets
        where Request_Type = ? and Department is not null and Department <> ''
        group by 1 order by c desc
        """,
        [request_type],
    ).fetchall()
    if not rows:
        return None, 0.0, []
    total = sum(r[1] for r in rows)
    top = rows[0]
    conf = (top[1] / total) if total else 0.0
    return top[0], float(conf), [(r[0], int(r[1])) for r in rows[:3]]


def recommend_department(fields: Dict[str, Any]) -> Dict[str, Any]:
    """FR-ROUTE-01: Recommend department given features.

    fields expects: Request_Type, Origin, District, create_month. Optionally Department for misroute flag.
    """
    _load_model()
    req_type = (fields.get("Request_Type") or "").strip()
    origin = (fields.get("Origin") or "").strip()
    district = (fields.get("District") or "").strip()
    create_month = fields.get("create_month")

    explanation = {}
    top3_list: List[Dict[str, Any]] = []
    recommended: Optional[str] = None
    confidence: float = 0.0

    if _model is not None and _encoder is not None:
        X = _onehot_from_fields(req_type, origin, district, create_month if create_month is not None else -1)
        if X is not None:
            try:
                proba = _model.predict_proba(X)[0]
                classes = list(_model.classes_)
                order = np.argsort(proba)[::-1]
                for idx in order[:3]:
                    top3_list.append({"department": classes[idx], "prob": float(proba[idx])})
                recommended = classes[order[0]]
                confidence = float(proba[order[0]])
            except Exception:
                recommended = None

    # Fallback: frequency baseline
    if recommended is None:
        dept, conf, rows = _freq_baseline(req_type)
        recommended = dept
        confidence = conf
        top3_list = [{"department": r[0], "prob": float(r[1])} for r in rows]  # counts as proxy
        # Explanation: historical distribution for this Request_Type
        explanation = {"basis": "historical_distribution", "group": "Request_Type", "key": req_type}
    else:
        explanation = {"basis": "model_logreg", "features": ["Request_Type", "Origin", "District", "create_month"]}

    actual_dept = fields.get("Department")
    threshold = float(fields.get("threshold", 0.8))
    possible_misroute = bool(actual_dept and recommended and actual_dept != recommended and confidence >= threshold)

    return {
        "recommended_department": recommended,
        "confidence": confidence,
        "top3": top3_list,
        "explanation": explanation,
        "possible_misroute": possible_misroute,
    }
