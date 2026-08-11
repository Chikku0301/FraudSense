import os
import json
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import average_precision_score, precision_recall_fscore_support, confusion_matrix
from imblearn.over_sampling import SMOTE
from xgboost import XGBClassifier
from sklearn.ensemble import IsolationForest
import shap

from backend.app.config import (
    MODEL_STORE_DIR,
    SCALER_PATH,
    XGB_MODEL_PATH,
    IFOREST_MODEL_PATH,
    SHAP_EXPLAINER_PATH,
    METRICS_PATH,
    POOL_CSV_PATH
)

def run_training_pipeline():
    print("[ML Pipeline] Starting data split and training pipeline...")
    os.makedirs(MODEL_STORE_DIR, exist_ok=True)

    csv_path = "data/creditcard.csv"
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Source credit card dataset not found at {csv_path}")

    # Load creditcard.csv (anonymized real card transactions)
    # Col schema: Time, V1...V28, Amount, Class
    print(f"[ML Pipeline] Loading source data from {csv_path}...")
    df = pd.read_csv(csv_path)

    # 1. Split creditcard.csv deterministically (stratified on Class)
    # 60% Train, 15% Validation, 25% Pool
    print("[ML Pipeline] Splitting dataset: 60% Train, 15% Val, 25% Pool...")
    train_df, temp_df = train_test_split(df, test_size=0.40, stratify=df['Class'], random_state=42)
    val_df, pool_df = train_test_split(temp_df, test_size=0.625, stratify=temp_df['Class'], random_state=42)

    # Save the incoming pool (25%) representing unseen live transactions
    print(f"[ML Pipeline] Saving incoming pool to {POOL_CSV_PATH}...")
    pool_df.to_csv(POOL_CSV_PATH, index=False)

    # Extract target and features
    X_train = train_df.drop(columns=['Class'])
    y_train = train_df['Class']
    X_val = val_df.drop(columns=['Class'])
    y_val = val_df['Class']

    # 2. Scale Time and Amount features with StandardScaler
    print("[ML Pipeline] Fitting StandardScaler on Train 'Time' and 'Amount' features...")
    scaler = StandardScaler()
    
    # We must fit only on training and transform train and validation
    X_train_scaled = X_train.copy()
    X_train_scaled[['Time', 'Amount']] = scaler.fit_transform(X_train[['Time', 'Amount']])
    
    X_val_scaled = X_val.copy()
    X_val_scaled[['Time', 'Amount']] = scaler.transform(X_val[['Time', 'Amount']])

    # Persist the fitted scaler
    joblib.dump(scaler, SCALER_PATH)
    print(f"[ML Pipeline] Scaler saved to {SCALER_PATH}")

    # 3. Apply SMOTE to training data only to balance the 0.172% class imbalance
    print("[ML Pipeline] Applying SMOTE to balance training classes...")
    smote = SMOTE(random_state=42)
    X_train_res, y_train_res = smote.fit_resample(X_train_scaled, y_train)
    print(f"[ML Pipeline] Resampled training data shape: {X_train_res.shape} (Original: {X_train_scaled.shape})")

    # 4. Train Supervised model (XGBoost Classifier)
    print("[ML Pipeline] Training XGBoost Classifier...")
    # Use optimized settings for training speed and accuracy
    xgb_model = XGBClassifier(
        n_estimators=50,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1
    )
    xgb_model.fit(X_train_res, y_train_res)
    joblib.dump(xgb_model, XGB_MODEL_PATH)
    print(f"[ML Pipeline] XGBoost model saved to {XGB_MODEL_PATH}")

    # 5. Train Unsupervised model (Isolation Forest anomaly detector)
    print("[ML Pipeline] Training Isolation Forest...")
    # Train on training set to find anomalies
    iforest = IsolationForest(
        n_estimators=100,
        max_samples='auto',
        contamination=0.01,
        random_state=42,
        n_jobs=-1
    )
    iforest.fit(X_train_scaled)  # fit on scaled features (non-SMOTE represents typical normal flow)
    joblib.dump(iforest, IFOREST_MODEL_PATH)
    print(f"[ML Pipeline] Isolation Forest saved to {IFOREST_MODEL_PATH}")

    # 6. Fit SHAP TreeExplainer on XGBoost
    print("[ML Pipeline] Fitting SHAP TreeExplainer...")
    explainer = shap.TreeExplainer(xgb_model)
    joblib.dump(explainer, SHAP_EXPLAINER_PATH)
    print(f"[ML Pipeline] SHAP Explainer saved to {SHAP_EXPLAINER_PATH}")

    # 7. Evaluate on Validation split
    print("[ML Pipeline] Evaluating models on validation split...")
    # XGBoost probability
    y_prob_xgb = xgb_model.predict_proba(X_val_scaled)[:, 1]

    # Isolation Forest anomaly score mapped to [0, 1] probability range
    # decision_function yields values where smaller is anomalous.
    # A standard Sigmoid maps -decision * 10 to [0,1]
    if_decision = iforest.decision_function(X_val_scaled)
    y_prob_iforest = 1.0 / (1.0 + np.exp(if_decision * 10.0))

    # Combine both scores: 80% Supervised (XGB) + 20% Unsupervised (Isolation Forest)
    y_prob_combined = 0.8 * y_prob_xgb + 0.2 * y_prob_iforest

    # Determine validation metrics (threshold 0.3 matches config THRESHOLD_CLEAR boundary)
    y_pred = (y_prob_combined >= 0.3).astype(int)

    auc_pr = average_precision_score(y_val, y_prob_combined)
    precision, recall, f1, _ = precision_recall_fscore_support(y_val, y_pred, average='binary')
    tn, fp, fn, tp = confusion_matrix(y_val, y_pred).ravel()

    metrics = {
        "auc_pr": float(auc_pr),
        "f1": float(f1),
        "recall": float(recall),
        "precision": float(precision),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp)
        },
        "minority_class_imbalance": "0.172% positive class in full dataset"
    }

    print(f"[ML Pipeline] Validation Metrics (Combined Score at threshold 0.3):")
    print(f"  - AUC-PR (Average Precision): {metrics['auc_pr']:.4f}")
    print(f"  - Minority Class F1: {metrics['f1']:.4f}")
    print(f"  - Minority Class Recall: {metrics['recall']:.4f}")
    print(f"  - Minority Class Precision: {metrics['precision']:.4f}")
    print(f"  - Confusion Matrix: TP={tp}, FP={fp}, FN={fn}, TN={tn}")

    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=4)
    print(f"[ML Pipeline] Metrics report saved to {METRICS_PATH}")
    print("[ML Pipeline] Training pipeline complete!")

if __name__ == "__main__":
    run_training_pipeline()
