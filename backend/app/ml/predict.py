import os
import joblib
import pandas as pd
import numpy as np

from backend.app.config import (
    SCALER_PATH,
    XGB_MODEL_PATH,
    IFOREST_MODEL_PATH,
    THRESHOLD_CLEAR,
    THRESHOLD_BLOCK
)

# Global variables for caching model artifacts in memory
_scaler = None
_xgb_model = None
_iforest_model = None

def load_ml_artifacts():
    global _scaler, _xgb_model, _iforest_model
    
    if _scaler is not None and _xgb_model is not None and _iforest_model is not None:
        return _scaler, _xgb_model, _iforest_model

    if not (os.path.exists(SCALER_PATH) and os.path.exists(XGB_MODEL_PATH) and os.path.exists(IFOREST_MODEL_PATH)):
        raise RuntimeError(
            "ML models are not trained yet. Please run backend/app/ml/train_fraud_model.py first."
        )

    _scaler = joblib.load(SCALER_PATH)
    _xgb_model = joblib.load(XGB_MODEL_PATH)
    _iforest_model = joblib.load(IFOREST_MODEL_PATH)
    return _scaler, _xgb_model, _iforest_model


def score_transaction(feature_vector: dict) -> dict:
    """
    Scores a single transaction feature vector.
    
    Parameters:
        feature_vector (dict): A dictionary containing 'Time', 'Amount', and 'V1' through 'V28' keys.
        
    Returns:
        dict: {
            'fraud_score': int (0-100),
            'fraud_probability': float (0.0-1.0),
            'model_decision': str ('clear' | 'flag_for_review' | 'block')
        }
    """
    scaler, xgb, iforest = load_ml_artifacts()

    # The order of features MUST match the training order:
    # Time, V1...V28, Amount
    feature_names = ["Time"] + [f"V{i}" for i in range(1, 29)] + ["Amount"]
    
    # Extract features in correct order
    features = []
    for name in feature_names:
        if name not in feature_vector:
            raise ValueError(f"Missing required feature: {name}")
        features.append(float(feature_vector[name]))

    # Create a DataFrame for model input
    df_in = pd.DataFrame([features], columns=feature_names)

    # Scale Time and Amount
    df_in_scaled = df_in.copy()
    df_in_scaled[['Time', 'Amount']] = scaler.transform(df_in[['Time', 'Amount']])

    # Predict using XGBoost
    # predict_proba returns [prob_class_0, prob_class_1]
    prob_xgb = float(xgb.predict_proba(df_in_scaled)[0, 1])

    # Predict using Isolation Forest
    if_decision = float(iforest.decision_function(df_in_scaled)[0])
    prob_iforest = 1.0 / (1.0 + np.exp(if_decision * 10.0))

    # Combine both scores: 80% Supervised (XGBoost) + 20% Unsupervised (Isolation Forest)
    prob_combined = 0.8 * prob_xgb + 0.2 * prob_iforest
    
    # Clip probability between 0.0 and 1.0
    prob_combined = float(np.clip(prob_combined, 0.0, 1.0))
    fraud_score = int(round(prob_combined * 100))

    # Map probability to model decision based on configurable thresholds
    if prob_combined < THRESHOLD_CLEAR:
        decision = "clear"
    elif prob_combined <= THRESHOLD_BLOCK:
        decision = "flag_for_review"
    else:
        decision = "block"

    return {
        "fraud_score": fraud_score,
        "fraud_probability": prob_combined,
        "model_decision": decision
    }
