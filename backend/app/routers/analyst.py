import os
import io
import random
import pandas as pd
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, WebSocket, WebSocketDisconnect
from sqlalchemy import func, desc
from sqlalchemy.orm import Session, joinedload

from backend.app.database import get_db
from backend.app.models import Transaction, FraudAssessment, Case, AuditLog, User
from backend.app.schemas import (
    TransactionOut,
    AnalystTransactionDetailOut,
    CaseOut,
    CaseResolve,
    AnalystPortfolioStats,
    FraudRateTrend,
    ScoreDistributionBucket
)
from backend.app.auth.auth import get_analyst_user
from backend.app.ml.predict import score_transaction
from backend.app.ml.explain import explain_transaction
from backend.app.services.streaming import manager
from backend.app.config import POOL_CSV_PATH

router = APIRouter(prefix="/analyst", tags=["Analyst Operations"])

@router.get("/transactions", response_model=List[TransactionOut])
def get_transactions(
    status_filter: Optional[str] = None,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    current_user: User = Depends(get_analyst_user),
    db: Session = Depends(get_db)
):
    """
    Returns all transactions, optionally filtered by status, and fraud score range.
    Accessible only to analyst and admin roles.
    """
    query = db.query(Transaction).outerjoin(FraudAssessment)
    
    if status_filter:
        query = query.filter(Transaction.status == status_filter)
        
    if min_score is not None:
        query = query.filter(FraudAssessment.fraud_score >= min_score)
        
    if max_score is not None:
        query = query.filter(FraudAssessment.fraud_score <= max_score)

    transactions = query.order_by(desc(Transaction.ingested_at)).all()

    # Convert to schema format
    results = []
    for tx in transactions:
        score = tx.fraud_assessment.fraud_score if tx.fraud_assessment else None
        decision = tx.fraud_assessment.model_decision if tx.fraud_assessment else None
        results.append(TransactionOut(
            id=tx.id,
            merchant_id=tx.merchant_id,
            source_row_id=tx.source_row_id,
            time_offset=tx.time_offset,
            amount=tx.amount,
            status=tx.status,
            ingested_at=tx.ingested_at,
            fraud_score=score,
            model_decision=decision
        ))
    return results


@router.get("/transactions/{id}", response_model=AnalystTransactionDetailOut)
def get_transaction_detail(
    id: int,
    current_user: User = Depends(get_analyst_user),
    db: Session = Depends(get_db)
):
    """
    Returns full transaction details, including raw PCA V1-V28 vector,
    detailed fraud assessments (with SHAP explanation details), and active cases.
    """
    tx = db.query(Transaction).options(
        joinedload(Transaction.fraud_assessment),
        joinedload(Transaction.case)
    ).filter(Transaction.id == id).first()

    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found."
        )

    # Convert to expected schema formats
    assessment_out = None
    if tx.fraud_assessment:
        assessment_out = tx.fraud_assessment

    case_out = None
    if tx.case:
        case_out = tx.case

    return AnalystTransactionDetailOut(
        id=tx.id,
        merchant_id=tx.merchant_id,
        source_row_id=tx.source_row_id,
        time_offset=tx.time_offset,
        amount=tx.amount,
        raw_features=tx.raw_features,
        status=tx.status,
        true_class=tx.true_class,
        ingested_at=tx.ingested_at,
        fraud_assessment=assessment_out,
        case=case_out
    )


@router.post("/cases/{id}/resolve", response_model=CaseOut)
def resolve_case(
    id: int,
    resolution_data: CaseResolve,
    current_user: User = Depends(get_analyst_user),
    db: Session = Depends(get_db)
):
    """
    Resolves an open investigation case, updating transaction status,
    creating an audit log entry, and closing the case.
    """
    case = db.query(Case).filter(Case.id == id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found."
        )

    if case.status == "resolved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Case is already resolved."
        )

    tx = db.query(Transaction).filter(Transaction.id == case.transaction_id).first()
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated transaction not found."
        )

    # Update case resolution details
    case.status = "resolved"
    case.resolution = resolution_data.resolution  # fraud_confirmed | false_positive
    case.notes = resolution_data.notes
    case.assigned_analyst_id = current_user.id
    case.resolved_at = datetime.utcnow()

    # Update transaction status
    if resolution_data.resolution == "fraud_confirmed":
        tx.status = "confirmed_fraud"
    elif resolution_data.resolution == "false_positive":
        tx.status = "confirmed_legit"

    # Log action to Audit Log
    audit = AuditLog(
        actor_id=current_user.id,
        transaction_id=tx.id,
        action="RESOLVE_CASE",
        notes=f"Resolved case ID {case.id} as {resolution_data.resolution.upper()}. Notes: {resolution_data.notes or 'None'}"
    )
    db.add(audit)
    db.commit()
    db.refresh(case)
    
    return case


@router.get("/portfolio/stats", response_model=AnalystPortfolioStats)
def get_portfolio_analytics(
    current_user: User = Depends(get_analyst_user),
    db: Session = Depends(get_db)
):
    """
    Returns aggregated portfolio metrics for analysts:
    - Fraud rate trend over time
    - Score distribution buckets for assessments
    - Total volume of active flagged transactions
    - Model metrics (Precision and Recall) based on resolved cases vs true class
    """
    # 1. Total Flagged Volume (Active)
    total_flagged = db.query(func.sum(Transaction.amount)).filter(
        Transaction.status == "flagged"
    ).scalar() or 0.0

    # 2. Score Distribution (Histogram buckets: 0-10, 10-20, ..., 90-100)
    buckets = [f"{i}-{i+10}" for i in range(0, 100, 10)]
    distribution = {b: 0 for b in buckets}
    
    assessments = db.query(FraudAssessment.fraud_score).all()
    for (score,) in assessments:
        bucket_index = min(int(score // 10), 9)  # 100 goes into 90-100
        bucket_key = buckets[bucket_index]
        distribution[bucket_key] += 1
        
    score_dist_buckets = [
        ScoreDistributionBucket(bucket=k, count=v) for k, v in distribution.items()
    ]

    # 3. Fraud rate over time (Python-level grouping for DB-agnostic dates)
    transactions = db.query(Transaction.ingested_at, Transaction.true_class).all()
    date_group = {}
    for tx_date, is_fraud in transactions:
        date_str = tx_date.strftime("%Y-%m-%d")
        if date_str not in date_group:
            date_group[date_str] = {"total": 0, "fraud": 0}
        date_group[date_str]["total"] += 1
        if is_fraud == 1:
            date_group[date_str]["fraud"] += 1

    trend_list = []
    for d_str, counts in sorted(date_group.items()):
        rate = counts["fraud"] / counts["total"] if counts["total"] > 0 else 0.0
        trend_list.append(FraudRateTrend(date=d_str, rate=float(rate)))

    # 4. Precision & Recall from analyst-resolved cases (and model decisions on ingested items)
    # Precision: TP / (TP + FP) on resolved cases
    # True Positive (TP): Case resolved as fraud_confirmed
    # False Positive (FP): Case resolved as false_positive
    tp_resolved = db.query(func.count(Case.id)).filter(
        Case.status == "resolved", Case.resolution == "fraud_confirmed"
    ).scalar() or 0

    fp_resolved = db.query(func.count(Case.id)).filter(
        Case.status == "resolved", Case.resolution == "false_positive"
    ).scalar() or 0

    precision = float(tp_resolved / (tp_resolved + fp_resolved)) if (tp_resolved + fp_resolved) > 0 else 1.0

    # Recall: TP / (TP + FN) over all ingested items
    # True Positive (TP): Model flagged/blocked (>=0.3) and true class is 1
    # False Negative (FN): Model cleared (<0.3) and true class is 1
    tp_total = db.query(func.count(Transaction.id)).join(
        FraudAssessment, Transaction.id == FraudAssessment.transaction_id
    ).filter(
        Transaction.true_class == 1,
        FraudAssessment.fraud_probability >= 0.3
    ).scalar() or 0

    fn_total = db.query(func.count(Transaction.id)).join(
        FraudAssessment, Transaction.id == FraudAssessment.transaction_id
    ).filter(
        Transaction.true_class == 1,
        FraudAssessment.fraud_probability < 0.3
    ).scalar() or 0

    recall = float(tp_total / (tp_total + fn_total)) if (tp_total + fn_total) > 0 else 1.0

    return AnalystPortfolioStats(
        fraud_rate_trend=trend_list,
        score_distribution=score_dist_buckets,
        total_flagged_volume=float(total_flagged),
        model_precision=precision,
        model_recall=recall
    )


@router.post("/ingest/batch")
async def ingest_batch(
    file: UploadFile = File(...),
    current_user: User = Depends(get_analyst_user),
    db: Session = Depends(get_db)
):
    """
    Ingests and scores a batch of transactions uploaded as a CSV.
    Computes predictions and SHAP values for each row, persisting to database.
    """
    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse CSV file: {str(e)}"
        )

    required_cols = ["Time", "Amount", "Class"] + [f"V{i}" for i in range(1, 29)]
    for col in required_cols:
        if col not in df.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"CSV is missing required column: {col}"
            )

    # Query all merchants in the database to assign merchant_ids randomly
    merchants = db.query(User).filter(User.role == "merchant").all()
    merchant_ids = [m.id for m in merchants] if merchants else [None]

    success_count = 0
    flagged_count = 0
    blocked_count = 0

    for idx, row in df.iterrows():
        feature_vector = {col: float(row[col]) for col in ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]}
        true_cls = int(row["Class"])
        
        # 1. Core scoring
        assessment_res = score_transaction(feature_vector)
        # 2. SHAP explanation
        explanations = explain_transaction(feature_vector)
        
        assigned_merchant_id = random.choice(merchant_ids)

        tx = Transaction(
            merchant_id=assigned_merchant_id,
            source_row_id=None,  # batch upload rows
            time_offset=feature_vector["Time"],
            amount=feature_vector["Amount"],
            raw_features={f"V{i}": feature_vector[f"V{i}"] for i in range(1, 29)},
            status="cleared" if assessment_res["model_decision"] == "clear" else "flagged",
            true_class=true_cls
        )
        db.add(tx)
        db.flush()  # gets transaction ID

        assessment = FraudAssessment(
            transaction_id=tx.id,
            fraud_score=assessment_res["fraud_score"],
            fraud_probability=assessment_res["fraud_probability"],
            model_decision=assessment_res["model_decision"],
            shap_explanation=explanations,
            model_version="1.0.0"
        )
        db.add(assessment)

        # Create investigation case if flagged or blocked
        if assessment_res["model_decision"] in ["flag_for_review", "block"]:
            flagged_count += 1
            if assessment_res["model_decision"] == "block":
                blocked_count += 1
            case = Case(
                transaction_id=tx.id,
                status="open",
                notes=f"Automated ingestion flagged transaction. Model decision: {assessment_res['model_decision']}"
            )
            db.add(case)

        success_count += 1

    db.commit()

    return {
        "status": "success",
        "message": f"Successfully ingested {success_count} transactions.",
        "flagged": flagged_count,
        "blocked": blocked_count
    }


@router.post("/simulate-live", response_model=TransactionOut)
async def simulate_live(
    current_user: User = Depends(get_analyst_user),
    db: Session = Depends(get_db)
):
    """
    Pulls ONE random unused row from the incoming_pool.csv, scores it,
    saves it to the database, and broadcasts it to connected clients via WebSockets.
    """
    if not os.path.exists(POOL_CSV_PATH):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incoming pool file not found. Train the ML model first."
        )

    # Load incoming pool
    pool_df = pd.read_csv(POOL_CSV_PATH)
    if pool_df.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The incoming pool is empty."
        )

    # Find row indices that have already been simulated/ingested from pool
    used_indices = [
        val[0] for val in db.query(Transaction.source_row_id).filter(
            Transaction.source_row_id.isnot(None)
        ).all()
    ]

    # Pick a random index not already used, fallback to any random if all are used
    available_indices = list(set(range(len(pool_df))) - set(used_indices))
    if not available_indices:
        print("[Simulator] All pool rows have been ingested. Resetting and reusing indices.")
        available_indices = list(range(len(pool_df)))

    chosen_idx = random.choice(available_indices)
    row = pool_df.iloc[chosen_idx]

    feature_vector = {col: float(row[col]) for col in ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]}
    true_cls = int(row["Class"])

    # Score transaction & generate explanation
    assessment_res = score_transaction(feature_vector)
    explanations = explain_transaction(feature_vector)

    # Fetch merchants to assign
    merchants = db.query(User).filter(User.role == "merchant").all()
    merchant_ids = [m.id for m in merchants] if merchants else [None]
    assigned_merchant_id = random.choice(merchant_ids)

    # Save to db
    tx = Transaction(
        merchant_id=assigned_merchant_id,
        source_row_id=chosen_idx,
        time_offset=feature_vector["Time"],
        amount=feature_vector["Amount"],
        raw_features={f"V{i}": feature_vector[f"V{i}"] for i in range(1, 29)},
        status="cleared" if assessment_res["model_decision"] == "clear" else "flagged",
        true_class=true_cls
    )
    db.add(tx)
    db.flush()

    assessment = FraudAssessment(
        transaction_id=tx.id,
        fraud_score=assessment_res["fraud_score"],
        fraud_probability=assessment_res["fraud_probability"],
        model_decision=assessment_res["model_decision"],
        shap_explanation=explanations,
        model_version="1.0.0"
    )
    db.add(assessment)

    case_id = None
    if assessment_res["model_decision"] in ["flag_for_review", "block"]:
        case = Case(
            transaction_id=tx.id,
            status="open",
            notes=f"Simulated live transaction flagged. Model decision: {assessment_res['model_decision']}"
        )
        db.add(case)
        db.flush()
        case_id = case.id

    db.commit()
    db.refresh(tx)

    # Format data for WebSocket broadcast
    ws_payload = {
        "event": "transaction_ingested",
        "data": {
            "id": tx.id,
            "merchant_id": tx.merchant_id,
            "merchant_name": db.query(User.merchant_name).filter(User.id == tx.merchant_id).scalar() or "Unknown Merchant",
            "time_offset": tx.time_offset,
            "amount": tx.amount,
            "status": tx.status,
            "ingested_at": tx.ingested_at.isoformat(),
            "fraud_score": assessment_res["fraud_score"],
            "model_decision": assessment_res["model_decision"],
            "case_id": case_id
        }
    }
    
    # Broadcast to websocket feed
    await manager.broadcast(ws_payload)

    # Return output format TransactionOut
    return TransactionOut(
        id=tx.id,
        merchant_id=tx.merchant_id,
        source_row_id=tx.source_row_id,
        time_offset=tx.time_offset,
        amount=tx.amount,
        status=tx.status,
        ingested_at=tx.ingested_at,
        fraud_score=assessment_res["fraud_score"],
        model_decision=assessment_res["model_decision"]
    )


@router.websocket("/live-feed")
async def live_feed_ws(websocket: WebSocket):
    """
    WebSocket feed broadcasting new live transactions to analysts.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection open. Read dummy messages from client if any.
            data = await websocket.receive_text()
            # Respond with pong to verify link if needed
            await websocket.send_json({"event": "pong", "timestamp": datetime.utcnow().isoformat()})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[WebSocket] Unexpected disconnect error: {e}")
        manager.disconnect(websocket)
