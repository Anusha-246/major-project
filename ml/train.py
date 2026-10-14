"""Train churn, value, segmentation, and persist scores into SQLite."""
from __future__ import annotations

import json
import os
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
    silhouette_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier, XGBRegressor

from config import Config
from database.db import db_session, get_connection
from ml.behaviour_shift import compute_behaviour_shifts
from ml.features import CHURN_FEATURES, build_feature_frame
from ml.retention import build_retention_and_alerts

try:
    import shap
except ImportError:  # pragma: no cover
    shap = None


def _classification_metrics(y_true, y_pred, y_prob) -> dict:
    tn, fp, fn, tp = confusion_matrix(
        y_true,
        y_pred,
        labels=[0, 1],
    ).ravel()

    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(
            float(precision_score(y_true, y_pred, zero_division=0)), 4
        ),
        "recall": round(
            float(recall_score(y_true, y_pred, zero_division=0)), 4
        ),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4),
        "pr_auc": round(float(average_precision_score(y_true, y_prob)), 4),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        },
    }


def _risk_level(p: float) -> str:
    if p >= 0.70:
        return "Critical"
    if p >= 0.45:
        return "High"
    if p >= 0.25:
        return "Medium"
    return "Low"


def _segment_name(centroid_row: pd.Series) -> str:
    value = centroid_row.get("predicted_future_value", centroid_row.get("predicted_future_value", 0))
    shift = centroid_row.get("shift_score", 0)
    digital = centroid_row.get("recent_digital_engagement", centroid_row.get("recent_digital_engagement", 0))
    if value >= centroid_row.get("_value_p75", value) and shift < 40:
        return "High-Value Loyal"
    if value >= centroid_row.get("_value_p60", value) and shift >= 45:
        return "High-Value At Risk"
    if digital >= 55 and shift < 35:
        return "Digitally Engaged"
    if shift >= 55:
        return "Behaviour Drift"
    if digital < 30:
        return "Low Engagement"
    return "Core Mass Market"


def train_and_score(customers, behaviour, engagement, branches) -> dict:
    os.makedirs(Config.MODEL_DIR, exist_ok=True)
    shifts, iso_model, _ = compute_behaviour_shifts(behaviour, Config.RANDOM_STATE)
    feat = build_feature_frame(customers, behaviour, engagement, shifts)

    X = feat[CHURN_FEATURES]
    y = feat["churn_label"].astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=Config.RANDOM_STATE, stratify=y
    )

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    models = {
        "Logistic Regression": LogisticRegression(max_iter=400, class_weight="balanced"),
        "Random Forest": RandomForestClassifier(
            n_estimators=180, max_depth=12, class_weight="balanced", random_state=Config.RANDOM_STATE
        ),
        "XGBoost": XGBClassifier(
            n_estimators=220,
            max_depth=5,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="logloss",
            random_state=Config.RANDOM_STATE,
        ),
    }
    metrics = {}
    fitted = {}
    for name, model in models.items():
        if name == "Logistic Regression":
            model.fit(X_train_s, y_train)
            prob = model.predict_proba(X_test_s)[:, 1]
        else:
            model.fit(X_train, y_train)
            prob = model.predict_proba(X_test)[:, 1]
        pred = (prob >= 0.5).astype(int)
        metrics[name] = _classification_metrics(y_test, pred, prob)
        fitted[name] = model

    best_name = max(metrics, key=lambda n: metrics[n]["roc_auc"])
    best_model = fitted[best_name]
    if best_name == "Logistic Regression":
        full_prob = best_model.predict_proba(scaler.transform(X))[:, 1]
    else:
        full_prob = best_model.predict_proba(X)[:, 1]

    # Prefer XGBoost for SHAP explanations even if another model wins slightly
    xgb_model = fitted["XGBoost"]
    xgb_prob = xgb_model.predict_proba(X)[:, 1]
    use_prob = xgb_prob if best_name != "XGBoost" else full_prob
    primary_name = "XGBoost" if abs(metrics["XGBoost"]["roc_auc"] - metrics[best_name]["roc_auc"]) < 0.02 else best_name
    if primary_name == "XGBoost":
        use_prob = xgb_prob
        primary_model = xgb_model
    else:
        primary_model = best_model

    shap_rows = ["[]"] * len(feat)
    global_importance = {}
    if shap is not None:
        explainer = shap.TreeExplainer(xgb_model)
        sample = X.sample(min(400, len(X)), random_state=Config.RANDOM_STATE)
        sv = explainer.shap_values(sample)
        mean_abs = np.abs(sv).mean(axis=0)
        global_importance = {
            CHURN_FEATURES[i]: round(float(mean_abs[i]), 6) for i in range(len(CHURN_FEATURES))
        }
        # Per-customer top factors on a batched transform
        all_sv = explainer.shap_values(X)
        for i in range(len(feat)):
            pairs = sorted(
                [
                    {"feature": CHURN_FEATURES[j], "impact": round(float(all_sv[i, j]), 4)}
                    for j in range(len(CHURN_FEATURES))
                ],
                key=lambda z: abs(z["impact"]),
                reverse=True,
            )[:6]
            shap_rows[i] = json.dumps(pairs)

    y_value = feat["future_value_target"]
    Xv_train, Xv_test, yv_train, yv_test = train_test_split(
        X, y_value, test_size=0.25, random_state=Config.RANDOM_STATE
    )
    value_model = XGBRegressor(
        n_estimators=220,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=Config.RANDOM_STATE,
    )
    value_model.fit(Xv_train, yv_train)
    yv_pred_test = value_model.predict(Xv_test)
    value_metrics = {
        "mae": round(float(mean_absolute_error(yv_test, yv_pred_test)), 2),
        "rmse": round(float(np.sqrt(mean_squared_error(yv_test, yv_pred_test))), 2),
        "r2": round(float(r2_score(yv_test, yv_pred_test)), 4),
    }
    future_value = value_model.predict(X)
    feat["predicted_future_value"] = future_value
    feat["churn_probability"] = use_prob
    feat["value_at_risk"] = feat["predicted_future_value"] * feat["churn_probability"]
    high_value_cut = feat["current_value"].quantile(0.80)
    feat["is_high_value"] = (feat["current_value"] >= high_value_cut).astype(int)

    cluster_cols = [
        "recent_txn_frequency",
        "recent_avg_balance",
        "recent_digital_engagement",
        "product_usage_score",
        "shift_score",
        "predicted_future_value",
        "nps_score",
    ]
    cluster_scaler = StandardScaler()
    Z = cluster_scaler.fit_transform(feat[cluster_cols])
    kmeans = KMeans(n_clusters=5, random_state=Config.RANDOM_STATE, n_init=10)
    feat["segment_id"] = kmeans.fit_predict(Z)
    sil = float(silhouette_score(Z, feat["segment_id"]))
    centroids = pd.DataFrame(cluster_scaler.inverse_transform(kmeans.cluster_centers_), columns=cluster_cols)
    centroids["_value_p75"] = feat["predicted_future_value"].quantile(0.75)
    centroids["_value_p60"] = feat["predicted_future_value"].quantile(0.60)
    names = {}
    used = set()
    for sid, row in centroids.iterrows():
        name = _segment_name(row)
        if name in used:
            name = f"{name} {sid + 1}"
        used.add(name)
        names[sid] = name
    feat["segment_name"] = feat["segment_id"].map(names)

    joblib.dump(fitted["Logistic Regression"], os.path.join(Config.MODEL_DIR, "lr_churn.joblib"))
    joblib.dump(fitted["Random Forest"], os.path.join(Config.MODEL_DIR, "rf_churn.joblib"))
    joblib.dump(xgb_model, os.path.join(Config.MODEL_DIR, "xgb_churn.joblib"))
    joblib.dump(value_model, os.path.join(Config.MODEL_DIR, "xgb_value.joblib"))
    joblib.dump(iso_model, os.path.join(Config.MODEL_DIR, "isolation_forest.joblib"))
    joblib.dump(kmeans, os.path.join(Config.MODEL_DIR, "kmeans.joblib"))
    joblib.dump(scaler, os.path.join(Config.MODEL_DIR, "churn_scaler.joblib"))
    joblib.dump(cluster_scaler, os.path.join(Config.MODEL_DIR, "cluster_scaler.joblib"))
    joblib.dump(CHURN_FEATURES, os.path.join(Config.MODEL_DIR, "feature_names.joblib"))
    joblib.dump(global_importance, os.path.join(Config.MODEL_DIR, "shap_global.joblib"))
    joblib.dump(names, os.path.join(Config.MODEL_DIR, "segment_names.joblib"))

    summary = {
        "churn_models": metrics,
        "best_churn_model": best_name,
        "primary_serving_model": primary_name,
        "value_model": value_metrics,
        "kmeans": {"k": 5, "silhouette": round(sil, 4), "segments": names},
        "shap_global": global_importance,
        "trained_at": datetime.utcnow().isoformat() + "Z",
    }
    with open(os.path.join(Config.MODEL_DIR, "metrics.json"), "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    retention_df, alerts_df = build_retention_and_alerts(feat, branches)

    persist_scores(feat, shifts, shap_rows, primary_name, retention_df, alerts_df, summary)
    return summary


train_and_score = train_and_score


def persist_scores(feat, shifts, shap_rows, model_name, retention_df, alerts_df, summary):
    with db_session() as conn:
        conn.execute("DELETE FROM behaviour_deviations")
        conn.execute("DELETE FROM churn_predictions")
        conn.execute("DELETE FROM customer_value")
        conn.execute("DELETE FROM customer_segments")
        conn.execute("DELETE FROM retention_strategies")
        conn.execute("DELETE FROM alerts")
        conn.execute("DELETE FROM model_metrics")

        conn.executemany(
            """INSERT INTO behaviour_deviations
               (customer_id, shift_score, anomaly_score, classification, deviating_attributes, attribute_details)
               VALUES (?, ?, ?, ?, ?, ?)""",
            shifts[
                ["customer_id", "shift_score", "anomaly_score", "classification", "deviating_attributes", "attribute_details"]
            ].itertuples(index=False, name=None),
        )
        shap_map = dict(zip(feat["customer_id"], shap_rows))
        pred_rows = [
            (
                r.customer_id,
                float(r.churn_probability),
                int(r.churn_probability >= 0.5),
                _risk_level(float(r.churn_probability)),
                model_name,
                shap_map[r.customer_id],
            )
            for r in feat.itertuples()
        ]
        conn.executemany(
            """INSERT INTO churn_predictions
               (customer_id, probability, prediction, risk_level, model_name, shap_top)
               VALUES (?, ?, ?, ?, ?, ?)""",
            pred_rows,
        )
        conn.executemany(
            """INSERT INTO customer_value
               (customer_id, current_value, predicted_future_value, value_at_risk, is_high_value)
               VALUES (?, ?, ?, ?, ?)""",
            feat[
                ["customer_id", "current_value", "predicted_future_value", "value_at_risk", "is_high_value"]
            ].itertuples(index=False, name=None),
        )
        conn.executemany(
            """INSERT INTO customer_segments (customer_id, segment_id, segment_name) VALUES (?, ?, ?)""",
            feat[["customer_id", "segment_id", "segment_name"]].itertuples(index=False, name=None),
        )
        conn.executemany(
            """INSERT INTO retention_strategies
               (customer_id, priority, strategy_title, actions, rationale)
               VALUES (?, ?, ?, ?, ?)""",
            retention_df.itertuples(index=False, name=None),
        )
        conn.executemany(
            """INSERT INTO alerts
               (alert_type, severity, customer_id, branch_id, message, created_at, is_read)
               VALUES (?, ?, ?, ?, ?, ?, 0)""",
            alerts_df.itertuples(index=False, name=None),
        )
        now = datetime.utcnow().isoformat() + "Z"
        for name, mets in summary["churn_models"].items():
            conn.execute(
                """INSERT INTO model_metrics (model_type, model_name, metrics_json, is_best, created_at)
                   VALUES ('churn', ?, ?, ?, ?)""",
                (name, json.dumps(mets), int(name == summary["best_churn_model"]), now),
            )
        conn.execute(
            """INSERT INTO model_metrics (model_type, model_name, metrics_json, is_best, created_at)
               VALUES ('value', 'XGBoost Regressor', ?, 1, ?)""",
            (json.dumps(summary["value_model"]), now),
        )
        conn.execute(
            """INSERT INTO model_metrics (model_type, model_name, metrics_json, is_best, created_at)
               VALUES ('segmentation', 'K-Means', ?, 1, ?)""",
            (json.dumps(summary["kmeans"]), now),
        )


def load_core_frames():
    conn = get_connection()
    customers = pd.read_sql_query("SELECT * FROM customers", conn)
    behaviour = pd.read_sql_query("SELECT * FROM customer_behaviour", conn)
    engagement = pd.read_sql_query("SELECT * FROM customer_engagement", conn)
    branches = pd.read_sql_query("SELECT * FROM branches", conn)
    conn.close()
    return customers, behaviour, engagement, branches
