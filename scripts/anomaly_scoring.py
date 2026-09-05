"""Unsupervised anomaly scoring and SHAP attribution over the reconciliation feature mart.

This is an architectural proof of concept, not a detection claim.  The snapshot
is wholly synthetic and its incidents are authored, so a high score here means a
payment looks unusual against the rest of the snapshot.  It says nothing about
fraud, and nothing about how this would behave on real payment traffic.

A model fitted on rule-flagged data can simply re-learn the rules it was handed.
The features below describe how far a payment sits from its own merchant's
rolling normal rather than from the fixed thresholds the SQL rules already test,
which blunts that circularity without pretending to remove it.
"""

from __future__ import annotations

import datetime as dt
import json

import duckdb
import pandas as pd
import shap
from sklearn.ensemble import IsolationForest

FEATURE_COLUMNS: tuple[str, ...] = (
    "settlement_delay_days",
    "fee_delta_minor_units",
    "amount_delta_minor_units",
    "delay_vs_merchant_avg",
    "amount_delta_vs_merchant_avg",
)
RANDOM_STATE = 42


def score_exceptions(
    connection: duckdb.DuckDBPyConnection, *, as_of: dt.date
) -> pd.DataFrame:
    """Fit an isolation forest over ``int_anomaly_features`` and attribute each score with SHAP."""

    frame = connection.execute(
        "SELECT * FROM int_anomaly_features WHERE analysis_as_of_date <= ? "
        "ORDER BY payment_id",
        [as_of],
    ).df()
    if frame.empty:
        raise ValueError(f"No eligible payments to score as of {as_of}")

    features = frame[list(FEATURE_COLUMNS)].astype(float)
    features = features.fillna(features.median()).fillna(0.0)

    model = IsolationForest(random_state=RANDOM_STATE).fit(features)
    outlier = -model.decision_function(features)
    floor = outlier.min()
    span = outlier.max() - floor or 1.0

    attribution = pd.DataFrame(
        shap.TreeExplainer(model).shap_values(features),
        columns=list(FEATURE_COLUMNS),
    )
    top_feature = attribution.abs().idxmax(axis=1)

    return pd.DataFrame(
        {
            "payment_id": frame["payment_id"],
            "merchant_id": frame["merchant_id"],
            "merchant_category": frame["merchant_category"],
            "transaction_date": frame["transaction_date"],
            "anomaly_score": (outlier - floor) / span,
            "top_feature": top_feature,
            "top_feature_contribution": [
                attribution.at[row, column] for row, column in top_feature.items()
            ],
            "shap_values_json": [
                json.dumps({name: float(value) for name, value in record.items()})
                for record in attribution.round(4).to_dict("records")
            ],
            "primary_reason": frame["primary_reason"],
            "is_match": frame["is_match"],
        }
    )
