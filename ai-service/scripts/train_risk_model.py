"""Train the (secondary) XGBoost risk signal on SYNTHETIC data and persist it.

    python ai-service/scripts/train_risk_model.py [--rows 1200] [--seed 42]

Outputs
  sample-data/synthetic_risk_training.csv   the generated training set (17 features + label)
  ai-service/models/risk_model.json         XGBoost booster (only when xgboost is installed)
  ai-service/models/risk_model.meta.json    model_version, data_version, feature list, metrics

Without ``xgboost`` the script still writes the CSV + a meta file describing the
deterministic fallback, so the service behaves identically (``model_backend=fallback``).
The model NEVER makes the final decision — policy rules do.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVICE = HERE.parent
ROOT = SERVICE.parent
sys.path.insert(0, str(SERVICE))

from app.risk.engine import (  # noqa: E402
    FEATURE_NAMES,
    MODEL_VERSION,
    _deterministic_risk,
    _synthetic_dataset,
)


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(FEATURE_NAMES + ["risk_label"])
        for r in rows:
            w.writerow([round(float(r["features"][f]), 6) for f in FEATURE_NAMES] + [round(float(r["label"]), 6)])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=1200)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(SERVICE / "models"))
    args = ap.parse_args()

    rows = _synthetic_dataset(n=args.rows, seed=args.seed)
    csv_path = ROOT / "sample-data" / "synthetic_risk_training.csv"
    write_csv(rows, csv_path)
    print(f"wrote {len(rows)} synthetic rows -> {csv_path}")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    data_version = f"synthetic-v1-n{args.rows}-s{args.seed}"
    meta = {
        "model_version": MODEL_VERSION,
        "data_version": data_version,
        "features": FEATURE_NAMES,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_rows": len(rows),
        "label": "deterministic risk function + noise (see app/risk/engine._synthetic_dataset)",
        "note": "SYNTHETIC ONLY - not a production credit model; secondary signal, never decides.",
    }
    try:
        import numpy as np
        import xgboost as xgb
    except Exception as exc:
        meta["backend"] = "fallback"
        meta["error"] = f"xgboost unavailable ({exc}); deterministic fallback scorer in use"
        (out / "risk_model.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print("xgboost not installed -> wrote meta only (fallback backend)")
        return 0

    X = np.array([[r["features"][f] for f in FEATURE_NAMES] for r in rows], dtype="float64")
    y = np.array([r["label"] for r in rows], dtype="float64")
    split = int(len(rows) * 0.8)
    model = xgb.XGBRegressor(n_estimators=200, max_depth=4, learning_rate=0.05,
                             objective="reg:squarederror", random_state=args.seed, verbosity=0)
    model.fit(X[:split], y[:split])
    pred = model.predict(X[split:])
    mae = float(np.mean(np.abs(pred - y[split:])))
    baseline = float(np.mean(np.abs(np.array([_deterministic_risk(r["features"]) for r in rows[split:]]) - y[split:])))
    model.fit(X, y)  # refit on everything for the shipped artefact
    model.save_model(str(out / "risk_model.json"))
    meta.update({"backend": "xgboost", "holdout_mae": round(mae, 5), "deterministic_mae": round(baseline, 5),
                 "xgboost_version": xgb.__version__})
    (out / "risk_model.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"saved model -> {out / 'risk_model.json'} (holdout MAE {mae:.4f}, deterministic {baseline:.4f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
