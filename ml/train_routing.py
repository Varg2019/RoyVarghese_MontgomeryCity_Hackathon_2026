from __future__ import annotations

import os
from pathlib import Path

import duckdb
import joblib

try:
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.linear_model import LogisticRegression
    _SKLEARN_OK = True
except Exception:
    # Allow running without scikit-learn (e.g., Python 3.14) — runtime will use frequency fallback.
    _SKLEARN_OK = False

from backend.db import get_con, ROOT


ART_DIR = ROOT / "ml" / "artifacts"
ART_DIR.mkdir(parents=True, exist_ok=True)


def main(min_samples: int = 50):
    if not _SKLEARN_OK:
        print("scikit-learn not available; skipping training. Runtime will use frequency baseline.")
        return 0
    con = get_con()
    # Pull training data: only rows with Department present
    rows = con.execute(
        """
        select Request_Type, Origin, District, create_month, Department
        from tickets
        where Department is not null and Department <> ''
        """
    ).fetchall()
    if not rows or len(rows) < min_samples:
        print(f"Not enough rows to train (got {len(rows)}; need >= {min_samples}). Using frequency baseline at runtime.")
        return 0

    X = []
    y = []
    for r in rows:
        X.append({
            "Request_Type": r[0] or "",
            "Origin": r[1] or "",
            "District": r[2] or "",
            "create_month": int(r[3]) if r[3] is not None else -1,
        })
        y.append(r[4])

    dv = DictVectorizer(sparse=True)
    Xv = dv.fit_transform(X)
    clf = LogisticRegression(max_iter=500, multi_class="auto")
    clf.fit(Xv, y)

    joblib.dump(clf, ART_DIR / "routing_model.joblib")
    joblib.dump(dv, ART_DIR / "routing_encoder.joblib")
    con.execute("insert into model_metadata(name, version, trained_at) values('routing_logreg', '0.1', now())")
    print("Saved model to ml/artifacts/routing_model.joblib and encoder to routing_encoder.joblib")
    return 1


if __name__ == "__main__":
    main()
