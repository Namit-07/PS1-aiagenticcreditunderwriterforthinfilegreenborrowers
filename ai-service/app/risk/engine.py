"""Risk scoring engine (Team B).

XGBoost is used as a SECONDARY quantitative signal — it never makes the final
decision. If the ``xgboost`` package is unavailable we fall back to a deterministic,
calibrated scoring function that returns the SAME contract.

Everything here is fitted ONLY on synthetic data. This is NOT a production credit model.
"""

from __future__ import annotations

from typing import Any

FEATURE_NAMES = [
    "verified_monthly_income",
    "income_volatility",
    "income_stability",
    "foir",
    "ltv",
    "emi_to_income",
    "existing_monthly_obligations",
    "bank_balance_trend",
    "income_sources",
    "income_mismatch_percentage",
    "document_confidence",
    "identity_mismatch_flag",
    "repayment_history_score",
    "employment_stability",
    "loan_amount",
    "vehicle_price",
    "tenure_months",
]

MODEL_VERSION = "xgb-v1"
_FALLBACK = "fallback"
_FEATURES_ATTR = "features"


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _deterministic_risk(features: dict[str, float]) -> float:
    """Calibrated deterministic risk score.

    Mirrors the synthetic-label generator so the fallback is consistent with what an
    XGBoost model would learn from the same synthetic dataset.
    """
    foir = _clamp(features.get("foir", 0.0))
    ltv = _clamp(features.get("ltv", 0.0), 0.0, 1.2)
    emi_income = _clamp(features.get("emi_to_income", 0.0))
    volatility = _clamp(features.get("income_volatility", 0.0))
    mismatch = _clamp(features.get("income_mismatch_percentage", 0.0))
    obligations_ratio = _clamp(
        features.get("existing_monthly_obligations", 0.0)
        / max(1.0, features.get("verified_monthly_income", 1.0))
    )
    repayment = _clamp(features.get("repayment_history_score", 0.7))
    identity = 1.0 if features.get("identity_mismatch_flag", 0) else 0.0
    employment = _clamp(features.get("employment_stability", 0.7))

    raw = (
        0.30 * foir
        + 0.18 * ltv
        + 0.15 * emi_income
        + 0.10 * volatility
        + 0.10 * mismatch
        + 0.05 * obligations_ratio
        + 0.20 * (1.0 - repayment)
        + 0.15 * identity
        + 0.10 * (1.0 - employment)
    )
    return _clamp(raw)


class RiskScorer:
    """Wrapper over an optional fitted XGBoost model with a deterministic fallback."""

    def __init__(self) -> None:
        self._model: Any = None
        self._backend: str = _FALLBACK
        self._data_version = "synthetic-v1"
        self.training_meta: dict[str, Any] = {}

    @property
    def backend(self) -> str:
        return self._backend

    @property
    def model(self) -> Any:
        """The fitted XGBoost model, or ``None`` when the deterministic fallback is active."""
        return self._model

    def explain(self, features: dict[str, float]) -> dict[str, Any]:
        """SHAP contributions for one feature vector (see :mod:`app.risk.explain`)."""
        from app.risk.explain import explain_risk

        return explain_risk(features, self._model)

    def load_or_train(self, model_dir: str | None = None) -> None:
        """Load a saved XGBoost model if present, else fit one on synthetic data.

        Falls back to the deterministic scorer when ``xgboost`` is unavailable.
        """
        if self._backend != _FALLBACK:
            return
        model, meta = _try_load_saved(model_dir)
        if model is None:
            model, trained, meta = _try_train_xgboost(_synthetic_dataset())
            if not trained:
                model = None
        if model is not None:
            self._model = model
            self._backend = "xgboost"
            self._data_version = str(meta.get("data_version", self._data_version))
        self.training_meta = meta

    def score(self, features: dict[str, float]) -> dict[str, Any]:
        """Return the risk signal contract (score, band, model_version, backend)."""
        vector = [float(features.get(name, 0.0)) for name in FEATURE_NAMES]
        if self._model is not None:
            score = _predict_model(self._model, vector)
        else:
            score = _deterministic_risk(features)
        band = "LOW" if score < 0.33 else ("MEDIUM" if score < 0.66 else "HIGH")
        return {
            "risk_score": round(score, 4),
            "risk_band": band,
            "model_version": MODEL_VERSION,
            "model_backend": self._backend,
            "data_version": self._data_version,
        }

    def _raw_score(self, features: dict[str, float]) -> float:
        """Return the raw continuous score (0..1) without banding."""
        vector = [float(features.get(name, 0.0)) for name in FEATURE_NAMES]
        if self._model is not None:
            return _predict_model(self._model, vector)
        return _deterministic_risk(features)

    def metrics(
        self,
        threshold: float = 0.50,
        n: int = 800,
        seed: int = 7,
    ) -> dict[str, Any]:
        """Evaluate the risk signal as a binary classifier.

        The synthetic risk score is binarized at ``threshold`` (default 0.50 =
        ``elevated/high risk``). Metrics are computed in pure numpy so they work with
        or without scikit-learn. NOTE: on synthetic data the deterministic fallback
        mirrors the label generator, so these numbers are near-perfect by construction
        — treat them as a correctness check, not a production-grade credit signal.
        """
        rows = _synthetic_dataset(n=n, seed=seed)
        y_true = [1 if r["label"] >= threshold else 0 for r in rows]
        y_score = [self._raw_score(r["features"]) for r in rows]
        return _evaluate_binary(y_true, y_score, threshold=threshold, backend=self._backend,
                                model_version=MODEL_VERSION, data_version=self._data_version)


# --------------------------------------------------------------------------- #
# Synthetic training data + optional XGBoost fit
# --------------------------------------------------------------------------- #
def _synthetic_dataset(n: int = 1200, seed: int = 42) -> list[dict[str, Any]]:
    """Justine realistic synthetic borrowers spanning LOW/MEDIUM/HIGH risk.

    Features are drawn from risk-stratified ranges (low half vs high half) so the
    resulting deterministic score spreads from ~0.25 to ~0.9 instead of collapsing
    into a single narrow band. This gives the model — and its evaluation metrics —
    real ranking signal (meaningful AUC).
    """
    import random

    rng = random.Random(seed)

    def _range(lo: float, hi: float) -> float:
        return rng.uniform(lo, hi)

    rows: list[dict[str, Any]] = []
    for _ in range(n):
        income = _range(15000, 80000)
        # Latent risk propensity -> samples from either the benign or stressed ranges.
        if rng.random() < 0.25:          # HIGH profile (stressed)
            r_foir, r_ltv, r_emi = (0.42, 0.92), (0.55, 1.15), (0.30, 0.70)
            r_vol, r_mis = (0.22, 0.60), (0.10, 0.45)
            r_repay, r_emp = (0.30, 0.60), (0.30, 0.62)
            r_doc, r_oblig = (0.50, 0.85), (0.20, 0.50)
            identity = 1 if rng.random() < 0.30 else 0
            trend = _range(-0.30, 0.10)
        elif rng.random() < 0.4:         # MEDIUM profile
            r_foir, r_ltv, r_emi = (0.28, 0.62), (0.50, 0.98), (0.24, 0.52)
            r_vol, r_mis = (0.10, 0.38), (0.0, 0.25)
            r_repay, r_emp = (0.50, 0.85), (0.50, 0.85)
            r_doc, r_oblig = (0.70, 1.0), (0.10, 0.35)
            identity = 0
            trend = _range(-0.10, 0.25)
        else:                            # LOW profile (benign)
            r_foir, r_ltv, r_emi = (0.12, 0.38), (0.38, 0.72), (0.12, 0.34)
            r_vol, r_mis = (0.0, 0.22), (0.0, 0.10)
            r_repay, r_emp = (0.78, 1.0), (0.78, 1.0)
            r_doc, r_oblig = (0.85, 1.0), (0.0, 0.20)
            identity = 0
            trend = _range(0.0, 0.35)

        foir, ltv, emi_income = _range(*r_foir), _range(*r_ltv), _range(*r_emi)
        volatility, mismatch = _range(*r_vol), _range(*r_mis)
        repayment, employment = _range(*r_repay), _range(*r_emp)
        doc_conf, oblig_ratio = _range(*r_doc), _range(*r_oblig)

        features = {
            "verified_monthly_income": income,
            "income_volatility": volatility,
            "income_stability": 1.0 - volatility,
            "foir": foir,
            "ltv": ltv,
            "emi_to_income": emi_income,
            "existing_monthly_obligations": income * oblig_ratio,
            "bank_balance_trend": trend,
            "income_sources": _range(1, 3),
            "income_mismatch_percentage": mismatch,
            "document_confidence": doc_conf,
            "identity_mismatch_flag": identity,
            "repayment_history_score": repayment,
            "employment_stability": employment,
            "loan_amount": _range(60000, 400000),
            "vehicle_price": _range(80000, 500000),
            "tenure_months": rng.choice([24, 36, 48, 60]),
        }
        # The deterministic scorer already incorporates identity; keep the label a
        # slightly-noisy version of the scorer so the fallback and the fitted XGBoost
        # both learn a self-consistent target (honest for synthetic evaluation).
        label = _deterministic_risk(features) + rng.uniform(-0.04, 0.04)
        rows.append({"features": features, "label": _clamp(label)})
    return rows


def _try_train_xgboost(rows: list[dict[str, Any]]) -> tuple[Any | None, bool, dict[str, Any]]:
    """Fit a small XGBoost regressor on synthetic rows when the package is available."""
    try:
        import numpy as np
        import xgboost as xgb
    except Exception:  # pragma: no cover
        return None, False, {"error": "xgboost unavailable", "backend": _FALLBACK}

    try:
        X = np.array([[r["features"][f] for f in FEATURE_NAMES] for r in rows], dtype="float64")
        y = np.array([r["label"] for r in rows], dtype="float64")
        model = xgb.XGBRegressor(
            n_estimators=120,
            max_depth=4,
            learning_rate=0.05,
            objective="reg:squarederror",
            random_state=42,
            verbosity=0,
        )
        model.fit(X, y)
        return model, True, {"trained_on": f"xgb-{len(rows)}-rows", "backend": "xgboost"}
    except Exception as exc:  # pragma: no cover
        return None, False, {"error": str(exc), "backend": _FALLBACK}


def default_model_dir() -> str:
    from pathlib import Path

    return str(Path(__file__).resolve().parent.parent.parent / "models")


def _try_load_saved(model_dir: str | None) -> tuple[Any | None, dict[str, Any]]:
    """Load ``risk_model.json`` + ``risk_model.meta.json`` written by scripts/train_risk_model.py."""
    import json
    from pathlib import Path

    d = Path(model_dir or default_model_dir())
    model_path, meta_path = d / "risk_model.json", d / "risk_model.meta.json"
    if not model_path.exists():
        return None, {}
    try:
        import xgboost as xgb

        model = xgb.XGBRegressor()
        model.load_model(str(model_path))
        meta: dict[str, Any] = {}
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta.setdefault("backend", "xgboost")
        meta.setdefault("loaded_from", str(model_path))
        return model, meta
    except Exception as exc:  # pragma: no cover
        return None, {"error": str(exc), "backend": _FALLBACK}


def _predict_model(model: Any, vector: list[float]) -> float:
    try:
        import numpy as np

        pred = float(model.predict(np.array([vector], dtype="float64"))[0])
    except Exception:  # pragma: no cover
        pred = 0.5
    return _clamp(pred)


# --------------------------------------------------------------------------- #
# Binary classification metrics (confusion matrix + scores + AUC + ROC)
# Pure numpy implementation so it works without scikit-learn.
# --------------------------------------------------------------------------- #
def _auc_roc(y_true: list[int], y_scores: list[float]) -> float | None:
    """Area under the ROC curve via the Mann-Whitney U (rank) method."""
    if not y_true or len(y_true) != len(y_scores):
        return None
    import numpy as np

    t = np.asarray(y_true, dtype=float)
    s = np.asarray(y_scores, dtype=float)
    n_pos = int(t.sum())
    n_neg = len(t) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    order = np.argsort(s, kind="mergesort")
    sorted_s = s[order]
    ranks = np.empty(len(s), dtype=float)
    i = 0
    k = len(s)
    while i < k:
        j = i
        while j + 1 < k and sorted_s[j + 1] == sorted_s[i]:
            j += 1
        ranks[order[i : j + 1]] = (i + j) / 2.0 + 1.0  # average 1-based rank
        i = j + 1
    sum_pos_ranks = float(np.sum(ranks[t == 1]))  # ranks match ORIGINAL positions
    return float((sum_pos_ranks - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def _roc_points(y_true: list[int], y_scores: list[float], steps: int = 11) -> list[dict[str, float]]:
    """Downsampled ROC curve (fpr, tpr) across thresholds 1.0..0.0."""
    total_pos = sum(1 for v in y_true if v == 1) or 1
    total_neg = sum(1 for v in y_true if v == 0) or 1
    pts: list[dict[str, float]] = []
    for th in [1.0 - i * (1.0 / max(1, steps - 1)) for i in range(steps)]:
        tp = sum(1 for y, s in zip(y_true, y_scores) if y == 1 and s >= th)
        fp = sum(1 for y, s in zip(y_true, y_scores) if y == 0 and s >= th)
        pts.append({"threshold": round(th, 4), "tpr": round(tp / total_pos, 4),
                    "fpr": round(fp / total_neg, 4)})
    return pts


def _evaluate_binary(
    y_true: list[int],
    y_scores: list[float],
    threshold: float = 0.66,
    backend: str = _FALLBACK,
    model_version: str = MODEL_VERSION,
    data_version: str = "synthetic-v1",
) -> dict[str, Any]:
    """Confusion matrix + all standard classification scores for a score threshold."""
    n = len(y_true)
    y_pred = [1 if s >= threshold else 0 for s in y_scores]

    tp = sum(1 for y, p in zip(y_true, y_pred) if y == 1 and p == 1)
    tn = sum(1 for y, p in zip(y_true, y_pred) if y == 0 and p == 0)
    fp = sum(1 for y, p in zip(y_true, y_pred) if y == 0 and p == 1)
    fn = sum(1 for y, p in zip(y_true, y_pred) if y == 1 and p == 0)

    def _safe(num: float, den: float) -> float:
        return round(num / den, 4) if den else 0.0

    accuracy = _safe(tp + tn, n)
    sensitivity = _safe(tp, tp + fn)          # recall
    specificity = _safe(tn, tn + fp)
    precision = _safe(tp, tp + fp)
    npv = _safe(tn, tn + fn)
    fpr = round(1.0 - specificity, 4)
    f1 = _safe(2 * precision * sensitivity, precision + sensitivity) if (precision + sensitivity) else 0.0
    youden = round(sensitivity + specificity - 1.0, 4)
    mcc_den = ((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)) ** 0.5
    mcc = _safe((tp * tn - fp * fn), mcc_den)
    auc = _auc_roc(y_true, y_scores)
    auc = round(auc, 4) if auc is not None else None

    positive_class = "HIGH_RISK" if threshold > 0.6 else ("ELEVATED_RISK" if threshold >= 0.5 else "POSITIVE")
    return {
        "metric": "binary classification of risky vs clean (score >= threshold)",
        "positive_class": positive_class,
        "threshold": threshold,
        "n_samples": n,
        "prevalence": _safe(tp + fn, n),
        "backend": backend,
        "model_version": model_version,
        "data_version": data_version,
        "confusion_matrix": {
            "tn": tn, "fp": fp, "fn": fn, "tp": tp,
            "matrix": [[tn, fp], [fn, tp]],  # rows=actual(0,1), cols=pred(0,1)
        },
        "accuracy": accuracy,
        "precision": precision,
        "recall_sensitivity": sensitivity,
        "specificity": specificity,
        "npv": npv,
        "fpr": fpr,
        "f1_score": f1,
        "youden_index": youden,
        "matthews_cc": mcc,
        "roc_auc": auc,
        "roc_points": _roc_points(y_true, y_scores),
        "note": "Trained/evaluated ONLY on synthetic data; not a production credit model.",
    }


_DEFAULT_SCORER: RiskScorer | None = None
_DEFAULT_READY = False


def get_risk_metrics(
    threshold: float = 0.50,
    n: int = 800,
    seed: int = 7,
) -> dict[str, Any]:
    """Module-level convenience: ensure the scorer is loaded, then compute metrics."""
    global _DEFAULT_SCORER, _DEFAULT_READY
    if not _DEFAULT_READY:
        _DEFAULT_SCORER = RiskScorer()
        _DEFAULT_SCORER.load_or_train()
        _DEFAULT_READY = True
    return _DEFAULT_SCORER.metrics(threshold=threshold, n=n, seed=seed)