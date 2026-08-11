import os
import joblib
import pandas as pd
import numpy as np

from backend.app.config import (
    SCALER_PATH,
    SHAP_EXPLAINER_PATH
)

# Global variables for caching explainer artifacts in memory
_scaler = None
_shap_explainer = None

def load_explainer_artifacts():
    global _scaler, _shap_explainer
    
    if _scaler is not None and _shap_explainer is not None:
        return _scaler, _shap_explainer

    if not (os.path.exists(SCALER_PATH) and os.path.exists(SHAP_EXPLAINER_PATH)):
        raise RuntimeError(
            "ML model artifacts not found. Please train the model first."
        )

    _scaler = joblib.load(SCALER_PATH)
    _shap_explainer = joblib.load(SHAP_EXPLAINER_PATH)
    return _scaler, _shap_explainer


def explain_transaction(feature_vector: dict) -> list:
    """
    Computes SHAP explanations for a single transaction.
    
    Parameters:
        feature_vector (dict): A dictionary containing 'Time', 'Amount', and 'V1' through 'V28' keys.
        
    Returns:
        list: A sorted list of the top 6 contributing features, each in the format:
            {
                'feature': str (formatted display name),
                'raw_feature': str (original variable name, e.g., 'V14'),
                'value': float (raw feature value),
                'shap_contribution': float (SHAP log-odds contribution)
            }
    """
    scaler, explainer = load_explainer_artifacts()

    # The order of features MUST match the training order:
    # Time, V1...V28, Amount
    feature_names = ["Time"] + [f"V{i}" for i in range(1, 29)] + ["Amount"]
    
    # Extract features in correct order
    features = []
    for name in feature_names:
        if name not in feature_vector:
            raise ValueError(f"Missing required feature: {name}")
        features.append(float(feature_vector[name]))

    # Create a DataFrame for explainer input
    df_in = pd.DataFrame([features], columns=feature_names)

    # Scale Time and Amount
    df_in_scaled = df_in.copy()
    df_in_scaled[['Time', 'Amount']] = scaler.transform(df_in[['Time', 'Amount']])

    # Compute SHAP values
    shap_values = explainer.shap_values(df_in_scaled)

    # Extract contributions robustly based on return type format
    if hasattr(shap_values, "values"):
        # SHAP Explanation Object
        contributions = shap_values.values[0]
    elif isinstance(shap_values, list):
        # Binary classifier list [class_0_shap, class_1_shap]
        contributions = shap_values[1][0] if len(shap_values) > 1 else shap_values[0][0]
    else:
        # Numpy array
        if len(shap_values.shape) == 3: # (samples, features, classes)
            contributions = shap_values[0, :, 1]
        elif len(shap_values.shape) == 2: # (samples, features)
            contributions = shap_values[0]
        else:
            contributions = shap_values

    # Construct the explanation results
    explanation_list = []
    for i, name in enumerate(feature_names):
        val = float(df_in.iloc[0][name])
        shap_val = float(contributions[i])

        # Label formatting: V1-V28 are PCA components; Amount and Time are real variables
        if name == "Time":
            display_name = "Transaction Time"
        elif name == "Amount":
            display_name = "Transaction Amount ($)"
        else:
            display_name = f"Feature {name} (anonymized)"

        explanation_list.append({
            "feature": display_name,
            "raw_feature": name,
            "value": val,
            "shap_contribution": shap_val
        })

    # Sort by absolute contribution and return top 6
    explanation_list.sort(key=lambda x: abs(x["shap_contribution"]), reverse=True)
    return explanation_list[:6]
