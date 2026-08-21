import os
import io
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models import User, Transaction, FraudAssessment, Case, AuditLog
from backend.app.ml.predict import score_transaction
from backend.app.ml.explain import explain_transaction

client = TestClient(app)

def test_root_endpoint():
    """Verify health endpoint returns healthy status and metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "FraudSense API"
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"


def test_auth_login_analyst():
    """Verify analyst user login produces valid JWT token."""
    response = client.post("/api/v1/auth/login", json={
        "email": "analyst1@fraudsense.com",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_auth_login_merchant():
    """Verify merchant user login produces valid JWT token."""
    response = client.post("/api/v1/auth/login", json={
        "email": "merchant1@fraudsense.com",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


def test_auth_invalid_credentials():
    """Verify invalid password returns 401 Unauthorized."""
    response = client.post("/api/v1/auth/login", json={
        "email": "analyst1@fraudsense.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401


def test_role_based_access_control():
    """Verify merchant cannot access analyst endpoints and vice versa."""
    # Merchant token
    merchant_res = client.post("/api/v1/auth/login", json={
        "email": "merchant1@fraudsense.com",
        "password": "password123"
    })
    merchant_token = merchant_res.json()["access_token"]
    merchant_headers = {"Authorization": f"Bearer {merchant_token}"}

    # Merchant trying to access Analyst endpoint -> 403
    res_forbidden = client.get("/api/v1/analyst/transactions", headers=merchant_headers)
    assert res_forbidden.status_code == 403

    # Analyst token
    analyst_res = client.post("/api/v1/auth/login", json={
        "email": "analyst1@fraudsense.com",
        "password": "password123"
    })
    analyst_token = analyst_res.json()["access_token"]
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}

    # Analyst trying to access Merchant endpoint -> 403
    res_merchant_forbidden = client.get("/api/v1/merchant/transactions", headers=analyst_headers)
    assert res_merchant_forbidden.status_code == 403


def test_merchant_transactions_and_stats():
    """Verify merchant transactions and stats endpoints return valid sanitized data."""
    merchant_res = client.post("/api/v1/auth/login", json={
        "email": "merchant1@fraudsense.com",
        "password": "password123"
    })
    token = merchant_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get merchant transactions
    tx_res = client.get("/api/v1/merchant/transactions", headers=headers)
    assert tx_res.status_code == 200
    txs = tx_res.json()
    assert isinstance(txs, list)

    # Get merchant stats
    stats_res = client.get("/api/v1/merchant/stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert "total_transactions" in stats
    assert "flagged_count" in stats
    assert "blocked_amount_saved" in stats

    # If transactions exist, verify single transaction detail
    if len(txs) > 0:
        first_tx_id = txs[0]["id"]
        detail_res = client.get(f"/api/v1/merchant/transactions/{first_tx_id}", headers=headers)
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert "risk_level" in detail
        assert detail["risk_level"] in ["Low", "Medium", "High"]
        # Merchant must NOT see raw PCA features
        assert "raw_features" not in detail
        assert "shap_explanation" not in detail


def test_analyst_transactions_and_portfolio_stats():
    """Verify analyst transactions, portfolio analytics, and SHAP explainability."""
    analyst_res = client.post("/api/v1/auth/login", json={
        "email": "analyst1@fraudsense.com",
        "password": "password123"
    })
    token = analyst_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get all transactions
    tx_res = client.get("/api/v1/analyst/transactions", headers=headers)
    assert tx_res.status_code == 200
    txs = tx_res.json()
    assert isinstance(txs, list)
    assert len(txs) > 0

    # Get portfolio analytics
    analytics_res = client.get("/api/v1/analyst/portfolio/stats", headers=headers)
    assert analytics_res.status_code == 200
    analytics = analytics_res.json()
    assert "fraud_rate_trend" in analytics
    assert "score_distribution" in analytics
    assert "total_flagged_volume" in analytics
    assert "model_precision" in analytics
    assert "model_recall" in analytics

    # Inspect transaction details with SHAP
    first_tx_id = txs[0]["id"]
    detail_res = client.get(f"/api/v1/analyst/transactions/{first_tx_id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert "raw_features" in detail
    assert "fraud_assessment" in detail
    if detail["fraud_assessment"]:
        assert "shap_explanation" in detail["fraud_assessment"]
        assert isinstance(detail["fraud_assessment"]["shap_explanation"], list)
        if len(detail["fraud_assessment"]["shap_explanation"]) > 0:
            item = detail["fraud_assessment"]["shap_explanation"][0]
            assert "feature" in item
            assert "shap_contribution" in item


def test_live_simulation_and_case_resolution():
    """Verify simulate-live pulls an unseen transaction, scores it, and allows case resolution."""
    analyst_res = client.post("/api/v1/auth/login", json={
        "email": "analyst1@fraudsense.com",
        "password": "password123"
    })
    token = analyst_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Trigger live simulation
    sim_res = client.post("/api/v1/analyst/simulate-live", headers=headers)
    assert sim_res.status_code == 200
    sim_tx = sim_res.json()
    assert "id" in sim_tx
    assert "fraud_score" in sim_tx
    assert "model_decision" in sim_tx
    assert sim_tx["model_decision"] in ["clear", "flag_for_review", "block"]

    # Check the simulated transaction detail
    sim_detail_res = client.get(f"/api/v1/analyst/transactions/{sim_tx['id']}", headers=headers)
    assert sim_detail_res.status_code == 200
    sim_detail = sim_detail_res.json()
    assert sim_detail["id"] == sim_tx["id"]

    # Check case resolution if there's an open case in the DB
    db = SessionLocal()
    try:
        open_case = db.query(Case).filter(Case.status == "open").first()
        if open_case:
            case_id = open_case.id
            resolve_res = client.post(
                f"/api/v1/analyst/cases/{case_id}/resolve",
                headers=headers,
                json={
                    "resolution": "fraud_confirmed",
                    "notes": "Verified fraudulent activity on card network via test."
                }
            )
            assert resolve_res.status_code == 200
            resolved_data = resolve_res.json()
            assert resolved_data["status"] == "resolved"
            assert resolved_data["resolution"] == "fraud_confirmed"

            # Check audit log entry was created
            audit = db.query(AuditLog).filter(
                AuditLog.action == "RESOLVE_CASE",
                AuditLog.actor_id == resolved_data["assigned_analyst_id"]
            ).first()
            assert audit is not None
    finally:
        db.close()


def test_batch_csv_ingestion():
    """Verify batch CSV ingestion endpoint processes multiple transactions."""
    analyst_res = client.post("/api/v1/auth/login", json={
        "email": "analyst1@fraudsense.com",
        "password": "password123"
    })
    token = analyst_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create small mock CSV dataframe
    data = {
        "Time": [100.0, 200.0],
        "Amount": [25.50, 1500.00],
        "Class": [0, 1]
    }
    for i in range(1, 29):
        data[f"V{i}"] = [0.05 * i, -0.05 * i]

    df = pd.DataFrame(data)
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    files = {"file": ("batch_sample.csv", io.BytesIO(csv_bytes), "text/csv")}
    response = client.post("/api/v1/analyst/ingest/batch", headers=headers, files=files)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["status"] == "success"
    assert "Successfully ingested 2 transactions" in res_json["message"]


def test_ml_scoring_and_explanation():
    """Verify direct ML score and SHAP explanation functions."""
    sample_feature_vector = {"Time": 500.0, "Amount": 75.0}
    for i in range(1, 29):
        sample_feature_vector[f"V{i}"] = 0.0

    # Test scoring
    assessment = score_transaction(sample_feature_vector)
    assert "fraud_score" in assessment
    assert 0 <= assessment["fraud_score"] <= 100
    assert 0.0 <= assessment["fraud_probability"] <= 1.0
    assert assessment["model_decision"] in ["clear", "flag_for_review", "block"]

    # Test SHAP explainability
    shap_factors = explain_transaction(sample_feature_vector)
    assert isinstance(shap_factors, list)
    assert len(shap_factors) > 0
    assert "feature" in shap_factors[0]
    assert "shap_contribution" in shap_factors[0]
