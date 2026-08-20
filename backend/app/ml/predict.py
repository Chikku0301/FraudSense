import os
import joblib
import pandas as pd
import numpy as np


# Import configuration values:
#
# SCALER_PATH        -> Path to the saved feature scaler
# XGB_MODEL_PATH     -> Path to the trained XGBoost fraud detection model
# IFOREST_MODEL_PATH -> Path to the trained Isolation Forest model
# THRESHOLD_CLEAR    -> Probability below which a transaction is considered safe
# THRESHOLD_BLOCK    -> Probability above which a transaction is blocked
from backend.app.config import (
    SCALER_PATH,
    XGB_MODEL_PATH,
    IFOREST_MODEL_PATH,
    THRESHOLD_CLEAR,
    THRESHOLD_BLOCK
)


# -------------------------------------------------------------
# GLOBAL MODEL CACHE
# -------------------------------------------------------------

# These variables store the loaded ML artifacts in memory.
#
# Initially, they are None.
# When load_ml_artifacts() is called for the first time,
# the models are loaded from disk and stored here.
#
# Future calls reuse these objects instead of loading the
# model files repeatedly from disk.
_scaler = None
_xgb_model = None
_iforest_model = None


def load_ml_artifacts():
    """
    Load the trained ML artifacts required for fraud prediction.

    The following artifacts are loaded:

    1. Scaler
       Used to scale the Time and Amount features.

    2. XGBoost model
       A supervised model trained using labeled
       legitimate and fraudulent transactions.

    3. Isolation Forest model
       An unsupervised anomaly detection model used
       to identify unusual transaction patterns.

    The loaded artifacts are cached in memory so they
    only need to be loaded from disk once.

    Returns:
        tuple:
            scaler       -> Loaded feature scaler
            xgb_model    -> Loaded XGBoost model
            iforest_model -> Loaded Isolation Forest model
    """

    # Tell Python that we want to modify the global variables
    # instead of creating new local variables.
    global _scaler, _xgb_model, _iforest_model


    # ---------------------------------------------------------
    # CHECK WHETHER MODELS ARE ALREADY LOADED
    # ---------------------------------------------------------

    # If all ML artifacts already exist in memory,
    # immediately return them.
    #
    # This avoids unnecessary disk reads for every
    # transaction prediction.
    if (
        _scaler is not None
        and _xgb_model is not None
        and _iforest_model is not None
    ):
        return _scaler, _xgb_model, _iforest_model


    # ---------------------------------------------------------
    # CHECK WHETHER MODEL FILES EXIST
    # ---------------------------------------------------------

    # Before attempting to load the models, verify that
    # all required files exist on disk.
    #
    # If any file is missing, the prediction system
    # cannot operate correctly.
    if not (
        os.path.exists(SCALER_PATH)
        and os.path.exists(XGB_MODEL_PATH)
        and os.path.exists(IFOREST_MODEL_PATH)
    ):
        raise RuntimeError(
            "ML models are not trained yet. "
            "Please run backend/app/ml/train_fraud_model.py first."
        )


    # ---------------------------------------------------------
    # LOAD ML ARTIFACTS FROM DISK
    # ---------------------------------------------------------

    # Load the scaler used during model training.
    _scaler = joblib.load(SCALER_PATH)

    # Load the trained XGBoost fraud classification model.
    _xgb_model = joblib.load(XGB_MODEL_PATH)

    # Load the trained Isolation Forest anomaly detection model.
    _iforest_model = joblib.load(IFOREST_MODEL_PATH)


    # Return all loaded artifacts.
    #
    # They will now remain cached in memory for future requests.
    return _scaler, _xgb_model, _iforest_model


def score_transaction(feature_vector: dict) -> dict:
    """
    Score a single transaction using both fraud detection models.

    The function performs the following steps:

    1. Load the trained ML artifacts.
    2. Validate the input transaction features.
    3. Arrange features in the same order used during training.
    4. Scale Time and Amount.
    5. Get fraud probability from XGBoost.
    6. Get anomaly score from Isolation Forest.
    7. Convert the Isolation Forest score into a probability-like value.
    8. Combine both model outputs.
    9. Convert the final probability into a fraud score from 0 to 100.
    10. Assign a final decision:
        - clear
        - flag_for_review
        - block

    Parameters:
        feature_vector (dict):
            Dictionary containing:

            Time
            Amount
            V1 through V28

    Returns:
        dict: {
            "fraud_score": int,
            "fraud_probability": float,
            "model_decision": str
        }
    """


    # ---------------------------------------------------------
    # LOAD TRAINED MODELS
    # ---------------------------------------------------------

    # Get the cached models if they are already loaded.
    # Otherwise, load them from disk.
    scaler, xgb, iforest = load_ml_artifacts()


    # ---------------------------------------------------------
    # DEFINE THE REQUIRED FEATURE ORDER
    # ---------------------------------------------------------

    # IMPORTANT:
    #
    # The feature order must exactly match the order used
    # when the models were trained.
    #
    # Expected order:
    #
    # Time, V1, V2, ..., V28, Amount
    feature_names = (
        ["Time"]
        + [f"V{i}" for i in range(1, 29)]
        + ["Amount"]
    )


    # ---------------------------------------------------------
    # VALIDATE AND EXTRACT INPUT FEATURES
    # ---------------------------------------------------------

    # Create a list to store feature values
    # in the correct order.
    features = []

    # Go through each required feature.
    for name in feature_names:

        # Check whether the feature exists in the input.
        #
        # This prevents incomplete transactions from
        # being sent to the ML models.
        if name not in feature_vector:
            raise ValueError(
                f"Missing required feature: {name}"
            )

        # Convert the feature value to float and add it
        # to the ordered feature list.
        features.append(
            float(feature_vector[name])
        )


    # ---------------------------------------------------------
    # CREATE MODEL INPUT DATAFRAME
    # ---------------------------------------------------------

    # ML models expect structured input with the same
    # feature names used during training.
    #
    # We wrap the single transaction inside a list because
    # Pandas expects rows of data.
    df_in = pd.DataFrame(
        [features],
        columns=feature_names
    )


    # ---------------------------------------------------------
    # SCALE TIME AND AMOUNT
    # ---------------------------------------------------------

    # Create a copy so the original DataFrame remains unchanged.
    df_in_scaled = df_in.copy()


    # Apply the same scaler that was fitted during training.
    #
    # Only Time and Amount are scaled.
    #
    # V1 to V28 are left unchanged because these features
    # were already preprocessed in the original dataset.
    df_in_scaled[["Time", "Amount"]] = scaler.transform(
        df_in[["Time", "Amount"]]
    )


    # ---------------------------------------------------------
    # XGBOOST FRAUD PREDICTION
    # ---------------------------------------------------------

    # predict_proba() returns probabilities for both classes.
    #
    # Example:
    #
    # [0.92, 0.08]
    #
    # Index 0 -> Probability of legitimate transaction
    # Index 1 -> Probability of fraudulent transaction
    #
    # We extract the fraud probability at [0, 1]:
    #
    # First 0 -> First transaction in the batch
    # Second 1 -> Probability of fraud
    prob_xgb = float(
        xgb.predict_proba(df_in_scaled)[0, 1]
    )


    # ---------------------------------------------------------
    # ISOLATION FOREST ANOMALY DETECTION
    # ---------------------------------------------------------

    # Get the anomaly decision score.
    #
    # Generally:
    # - Higher / positive values -> More normal
    # - Lower / negative values  -> More anomalous
    if_decision = float(
        iforest.decision_function(df_in_scaled)[0]
    )


    # Convert the Isolation Forest decision value into
    # a probability-like anomaly score using a sigmoid function.
    #
    # Formula:
    #
    # anomaly_score = 1 / (1 + e^(decision * 10))
    #
    # Multiplying by 10 makes the sigmoid transition sharper.
    #
    # Because anomalous transactions generally have lower
    # decision scores, this transformation produces a higher
    # value for more suspicious transactions.
    prob_iforest = 1.0 / (
        1.0 + np.exp(if_decision * 10.0)
    )


    # ---------------------------------------------------------
    # COMBINE BOTH MODEL SCORES
    # ---------------------------------------------------------

    # Combine:
    #
    # 80% -> Supervised XGBoost fraud probability
    # 20% -> Unsupervised Isolation Forest anomaly score
    #
    # This hybrid approach allows the system to use:
    #
    # XGBoost:
    #   Learns known fraud patterns from labeled data.
    #
    # Isolation Forest:
    #   Detects unusual or previously unseen patterns.
    prob_combined = (
        0.8 * prob_xgb
        + 0.2 * prob_iforest
    )


    # ---------------------------------------------------------
    # ENSURE PROBABILITY IS VALID
    # ---------------------------------------------------------

    # Force the final value to remain between:
    #
    # 0.0 -> No fraud risk
    # 1.0 -> Maximum fraud risk
    prob_combined = float(
        np.clip(prob_combined, 0.0, 1.0)
    )


    # Convert probability into a more user-friendly
    # fraud score between 0 and 100.
    #
    # Example:
    #
    # 0.87 -> 87
    fraud_score = int(
        round(prob_combined * 100)
    )


    # ---------------------------------------------------------
    # DETERMINE THE FINAL MODEL DECISION
    # ---------------------------------------------------------

    # Compare the combined fraud probability with
    # configurable thresholds.

    # Low fraud probability:
    #
    # Transaction is considered safe.
    if prob_combined < THRESHOLD_CLEAR:
        decision = "clear"


    # Medium fraud probability:
    #
    # Transaction is suspicious and should be reviewed
    # by a fraud analyst.
    elif prob_combined <= THRESHOLD_BLOCK:
        decision = "flag_for_review"


    # High fraud probability:
    #
    # Transaction is considered highly suspicious
    # and should be blocked.
    else:
        decision = "block"


    # ---------------------------------------------------------
    # RETURN FINAL FRAUD ASSESSMENT
    # ---------------------------------------------------------

    return {

        # Integer score between 0 and 100
        "fraud_score": fraud_score,

        # Combined fraud probability between 0.0 and 1.0
        "fraud_probability": prob_combined,

        # Final system decision
        #
        # Possible values:
        # clear
        # flag_for_review
        # block
        "model_decision": decision
    }