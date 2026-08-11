from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List

from backend.app.database import get_db
from backend.app.models import Transaction, FraudAssessment, User
from backend.app.schemas import TransactionOut, MerchantTransactionDetailOut, MerchantStats
from backend.app.auth.auth import get_merchant_user

router = APIRouter(prefix="/merchant", tags=["Merchant Interface"])

@router.get("/transactions", response_model=List[TransactionOut])
def get_merchant_transactions(
    current_user: User = Depends(get_merchant_user),
    db: Session = Depends(get_db)
):
    """
    Returns a list of transactions belonging to the logged-in merchant.
    Filters out raw features and sensitive details.
    """
    transactions = db.query(Transaction).filter(
        Transaction.merchant_id == current_user.id
    ).order_by(Transaction.ingested_at.desc()).all()

    # Populate fraud_score and model_decision fields on schemas from joined assessment
    results = []
    for tx in transactions:
        score = None
        decision = None
        if tx.fraud_assessment:
            score = tx.fraud_assessment.fraud_score
            decision = tx.fraud_assessment.model_decision

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


@router.get("/transactions/{id}", response_model=MerchantTransactionDetailOut)
def get_merchant_transaction_detail(
    id: int,
    current_user: User = Depends(get_merchant_user),
    db: Session = Depends(get_db)
):
    """
    Returns sanitized details for a specific transaction.
    Protects V1-V28 PCA vectors and SHAP parameters.
    """
    tx = db.query(Transaction).filter(
        Transaction.id == id,
        Transaction.merchant_id == current_user.id
    ).first()

    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found or unauthorized access."
        )

    # Determine risk level band
    risk_level = "Low"
    if tx.fraud_assessment:
        score = tx.fraud_assessment.fraud_score
        if score >= 70:
            risk_level = "High"
        elif score >= 30:
            risk_level = "Medium"

    return MerchantTransactionDetailOut(
        id=tx.id,
        merchant_id=tx.merchant_id,
        time_offset=tx.time_offset,
        amount=tx.amount,
        status=tx.status,
        ingested_at=tx.ingested_at,
        risk_level=risk_level
    )


@router.get("/stats", response_model=MerchantStats)
def get_merchant_stats(
    current_user: User = Depends(get_merchant_user),
    db: Session = Depends(get_db)
):
    """
    Returns aggregate stats for the logged-in merchant:
    - Total transaction volume count
    - Count of transactions flagged for review
    - Saved volume (sum of transactions blocked by the model)
    """
    # Total count
    total_tx = db.query(func.count(Transaction.id)).filter(
        Transaction.merchant_id == current_user.id
    ).scalar() or 0

    # Flagged count
    flagged_tx = db.query(func.count(Transaction.id)).filter(
        Transaction.merchant_id == current_user.id,
        Transaction.status == "flagged"
    ).scalar() or 0

    # Blocked amount saved
    blocked_amount = db.query(func.sum(Transaction.amount)).join(
        FraudAssessment, Transaction.id == FraudAssessment.transaction_id
    ).filter(
        Transaction.merchant_id == current_user.id,
        FraudAssessment.model_decision == "block"
    ).scalar() or 0.0

    return MerchantStats(
        total_transactions=total_tx,
        flagged_count=flagged_tx,
        blocked_amount_saved=float(blocked_amount)
    )
