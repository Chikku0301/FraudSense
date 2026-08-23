import os
import json
import joblib
import pandas as pd
import numpy as np

# Dataset splitting and preprocessing
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# Evaluation metrics
from sklearn.metrics import (
    average_precision_score,
    precision_recall_fscore_support,
    confusion_matrix
)

# Handling class imbalance
from imblearn.over_sampling import SMOTE

# Supervised fraud classification model
from xgboost import XGBClassifier

# Unsupervised anomaly detection model
from sklearn.ensemble import IsolationForest

# Model explainability
import shap

# Import project-specific paths for storing models, scaler,
# metrics, SHAP explainer, and the unseen transaction pool
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
    """
    Complete ML training pipeline for credit card fraud detection.

    Pipeline steps:
    1. Load dataset
    2. Split data into Train, Validation, and Unseen Pool
    3. Scale numerical features
    4. Handle class imbalance using SMOTE
    5. Train XGBoost classifier
    6. Train Isolation Forest anomaly detector
    7. Create SHAP explainer for model interpretability
    8. Evaluate the combined model on validation data
    9. Save models, preprocessing objects, and metrics
    """

    print("[ML Pipeline] Starting data split and training pipeline...")

    # Create the directory for storing trained models and artifacts
    # if it does not already exist.
    os.makedirs(MODEL_STORE_DIR, exist_ok=True)

    # Path to the original credit card transaction dataset
    csv_path = "data/creditcard.csv"

    # Ensure that the dataset exists before starting training
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"Source credit card dataset not found at {csv_path}"
        )

    # ------------------------------------------------------------------
    # STEP 1: LOAD DATASET
    # ------------------------------------------------------------------

    # Load the anonymized credit card transaction dataset.
    #
    # Dataset columns:
    # - Time: Time elapsed since the first transaction
    # - V1 to V28: PCA-transformed anonymized features
    # - Amount: Transaction amount
    # - Class: Target variable
    #          0 -> Normal transaction
    #          1 -> Fraudulent transaction
    print(f"[ML Pipeline] Loading source data from {csv_path}...")
    df = pd.read_csv(csv_path)

    # ------------------------------------------------------------------
    # STEP 2: SPLIT DATASET
    # ------------------------------------------------------------------

    # Split the dataset into:
    # - 60% Training data
    # - 15% Validation data
    # - 25% Unseen Pool
    #
    # Stratification ensures that the fraud-to-normal ratio remains
    # approximately the same across all splits.
    print(
        "[ML Pipeline] Splitting dataset: "
        "60% Train, 15% Val, 25% Pool..."
    )

    # First split:
    # 60% -> Training
    # 40% -> Temporary dataset
    train_df, temp_df = train_test_split(
        df,
        test_size=0.40,
        stratify=df["Class"],
        random_state=42
    )

    # Split the remaining 40% into:
    # 15% Validation
    # 25% Unseen transaction pool
    #
    # 0.625 * 40% = 25%
    val_df, pool_df = train_test_split(
        temp_df,
        test_size=0.625,
        stratify=temp_df["Class"],
        random_state=42
    )

    # Save the unseen 25% transaction pool.
    #
    # This pool can later simulate incoming/live transactions and should
    # not be used during model training.
    print(f"[ML Pipeline] Saving incoming pool to {POOL_CSV_PATH}...")
    pool_df.to_csv(POOL_CSV_PATH, index=False)

    # ------------------------------------------------------------------
    # STEP 3: SEPARATE FEATURES AND TARGET
    # ------------------------------------------------------------------

    # Remove the target column from the input features
    X_train = train_df.drop(columns=["Class"])
    y_train = train_df["Class"]

    X_val = val_df.drop(columns=["Class"])
    y_val = val_df["Class"]

    # ------------------------------------------------------------------
    # STEP 4: FEATURE SCALING
    # ------------------------------------------------------------------

    # The V1-V28 features are already PCA-transformed.
    # Only Time and Amount require standardization.
    print(
        "[ML Pipeline] Fitting StandardScaler on "
        "'Time' and 'Amount' features..."
    )

    scaler = StandardScaler()

    # Create copies to preserve the original feature DataFrames
    X_train_scaled = X_train.copy()

    # Fit the scaler ONLY on training data to prevent data leakage,
    # then transform the training features.
    X_train_scaled[["Time", "Amount"]] = scaler.fit_transform(
        X_train[["Time", "Amount"]]
    )

    X_val_scaled = X_val.copy()

    # Transform validation data using the scaler fitted on training data.
    # We do not fit again on validation data.
    X_val_scaled[["Time", "Amount"]] = scaler.transform(
        X_val[["Time", "Amount"]]
    )

    # Save the fitted scaler for use during future inference.
    joblib.dump(scaler, SCALER_PATH)

    print(f"[ML Pipeline] Scaler saved to {SCALER_PATH}")

    # ------------------------------------------------------------------
    # STEP 5: HANDLE CLASS IMBALANCE USING SMOTE
    # ------------------------------------------------------------------

    # Fraud transactions are extremely rare in this dataset.
    #
    # SMOTE creates synthetic examples of the minority class
    # to help the supervised model learn fraud patterns better.
    #
    # Important:
    # SMOTE is applied ONLY to training data to avoid data leakage.
    print("[ML Pipeline] Applying SMOTE to balance training classes...")

    smote = SMOTE(random_state=42)

    X_train_res, y_train_res = smote.fit_resample(
        X_train_scaled,
        y_train
    )

    print(
        f"[ML Pipeline] Resampled training data shape: "
        f"{X_train_res.shape} "
        f"(Original: {X_train_scaled.shape})"
    )

    # ------------------------------------------------------------------
    # STEP 6: TRAIN SUPERVISED MODEL - XGBOOST
    # ------------------------------------------------------------------

    # XGBoost learns from labeled examples:
    #
    # Class 0 -> Normal
    # Class 1 -> Fraud
    #
    # The model is trained on the SMOTE-balanced training dataset.
    print("[ML Pipeline] Training XGBoost Classifier...")

    xgb_model = XGBClassifier(
        n_estimators=50,       # Number of boosting trees
        max_depth=5,           # Maximum depth of each tree
        learning_rate=0.1,     # Learning step size
        subsample=0.8,         # Fraction of samples used per tree
        colsample_bytree=0.8,  # Fraction of features used per tree
        random_state=42,       # Ensures reproducibility
        n_jobs=-1              # Use all available CPU cores
    )

    # Train the supervised fraud detection model
    xgb_model.fit(X_train_res, y_train_res)

    # Save the trained XGBoost model
    joblib.dump(xgb_model, XGB_MODEL_PATH)

    print(
        f"[ML Pipeline] XGBoost model saved to "
        f"{XGB_MODEL_PATH}"
    )

    # ------------------------------------------------------------------
    # STEP 7: TRAIN UNSUPERVISED MODEL - ISOLATION FOREST
    # ------------------------------------------------------------------

    # Isolation Forest detects unusual or anomalous transactions.
    #
    # Unlike XGBoost, it does not directly depend on fraud labels
    # during its anomaly detection process.
    print("[ML Pipeline] Training Isolation Forest...")

    iforest = IsolationForest(
        n_estimators=100,      # Number of isolation trees
        max_samples="auto",    # Automatically determine sample size
        contamination=0.01,    # Expected proportion of anomalies
        random_state=42,
        n_jobs=-1
    )

    # Train on the original scaled training data rather than
    # SMOTE-generated data so that the model learns the natural
    # distribution of transactions.
    iforest.fit(X_train_scaled)

    # Save the trained Isolation Forest model
    joblib.dump(iforest, IFOREST_MODEL_PATH)

    print(
        f"[ML Pipeline] Isolation Forest saved to "
        f"{IFOREST_MODEL_PATH}"
    )

    # ------------------------------------------------------------------
    # STEP 8: CREATE SHAP EXPLAINER
    # ------------------------------------------------------------------

    # SHAP TreeExplainer is used to explain which features
    # contributed to the XGBoost model's prediction.
    print("[ML Pipeline] Fitting SHAP TreeExplainer...")

    explainer = shap.TreeExplainer(xgb_model)

    # Save the SHAP explainer for later use in prediction explanations
    joblib.dump(explainer, SHAP_EXPLAINER_PATH)

    print(
        f"[ML Pipeline] SHAP Explainer saved to "
        f"{SHAP_EXPLAINER_PATH}"
    )

    # ------------------------------------------------------------------
    # STEP 9: EVALUATE MODELS ON VALIDATION DATA
    # ------------------------------------------------------------------

    print("[ML Pipeline] Evaluating models on validation split...")

    # ---------------- XGBOOST SCORE ----------------

    # Get the probability that each transaction belongs to Class 1 (fraud).
    y_prob_xgb = xgb_model.predict_proba(
        X_val_scaled
    )[:, 1]

    # ---------------- ISOLATION FOREST SCORE ----------------

    # Isolation Forest returns a decision score where lower values
    # generally indicate more anomalous transactions.
    if_decision = iforest.decision_function(X_val_scaled)

    # Convert anomaly scores into an approximate probability-like
    # range between 0 and 1 using a sigmoid transformation.
    #
    # More anomalous transactions should receive higher scores.
    y_prob_iforest = 1.0 / (
        1.0 + np.exp(if_decision * 10.0)
    )

    # ---------------- COMBINED SCORE ----------------

    # Combine predictions from both models:
    #
    # 80% weight -> Supervised XGBoost prediction
    # 20% weight -> Unsupervised Isolation Forest anomaly score
    #
    # This creates a hybrid fraud detection system.
    y_prob_combined = (
        0.8 * y_prob_xgb
        + 0.2 * y_prob_iforest
    )

    # ------------------------------------------------------------------
    # STEP 10: CONVERT SCORES TO FINAL PREDICTIONS
    # ------------------------------------------------------------------

    # Transactions with a combined fraud score >= 0.3
    # are classified as fraudulent.
    y_pred = (y_prob_combined >= 0.3).astype(int)

    # ------------------------------------------------------------------
    # STEP 11: CALCULATE VALIDATION METRICS
    # ------------------------------------------------------------------

    # AUC-PR is useful for highly imbalanced datasets because
    # it focuses on the performance of the minority/fraud class.
    auc_pr = average_precision_score(
        y_val,
        y_prob_combined
    )

    # Calculate precision, recall, and F1-score for the fraud class.
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_val,
        y_pred,
        average="binary"
    )

    # Calculate the confusion matrix:
    #
    # TN -> Correctly identified normal transactions
    # FP -> Normal transactions incorrectly flagged as fraud
    # FN -> Fraud transactions incorrectly classified as normal
    # TP -> Correctly identified fraud transactions
    tn, fp, fn, tp = confusion_matrix(
        y_val,
        y_pred
    ).ravel()

    # Store all important evaluation results in a dictionary.
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

        # Record the class imbalance of the original dataset.
        "minority_class_imbalance":
            "0.172% positive class in full dataset"
    }

    # ------------------------------------------------------------------
    # STEP 12: DISPLAY AND SAVE METRICS
    # ------------------------------------------------------------------

    print(
        "[ML Pipeline] Validation Metrics "
        "(Combined Score at threshold 0.3):"
    )

    print(
        f"  - AUC-PR (Average Precision): "
        f"{metrics['auc_pr']:.4f}"
    )

    print(
        f"  - Minority Class F1: "
        f"{metrics['f1']:.4f}"
    )

    print(
        f"  - Minority Class Recall: "
        f"{metrics['recall']:.4f}"
    )

    print(
        f"  - Minority Class Precision: "
        f"{metrics['precision']:.4f}"
    )

    print(
        f"  - Confusion Matrix: "
        f"TP={tp}, FP={fp}, FN={fn}, TN={tn}"
    )

    # Save the evaluation metrics as a JSON file.
    with open(METRICS_PATH, "w") as f:
        json.dump(
            metrics,
            f,
            indent=4
        )

    print(
        f"[ML Pipeline] Metrics report saved to "
        f"{METRICS_PATH}"
    )

    print("[ML Pipeline] Training pipeline complete!")


# Execute the training pipeline only when this file
# is run directly, not when it is imported as a module.
if __name__ == "__main__":
    run_training_pipeline()