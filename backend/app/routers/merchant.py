# Import FastAPI utilities:
# - APIRouter → creates a group of related API endpoints
# - Depends → dependency injection for authentication and database sessions
# - HTTPException → used to return HTTP errors
# - status → provides readable HTTP status codes
from fastapi import APIRouter, Depends, HTTPException, status

# SQLAlchemy's func provides SQL aggregate functions such as:
# COUNT(), SUM(), AVG(), etc.
from sqlalchemy import func

# SQLAlchemy Session represents a database session/connection
from sqlalchemy.orm import Session

# Used for typing the API response as a list
from typing import List


# ---------------------------------------------------------------------------
# PROJECT IMPORTS
# ---------------------------------------------------------------------------

# Dependency that provides a database session to each API request
from backend.app.database import get_db

# SQLAlchemy database models
#
# Transaction       → stores transaction information
# FraudAssessment   → stores fraud detection results
# User              → represents application users
from backend.app.models import Transaction, FraudAssessment, User

# Pydantic response schemas.
#
# These control what data is returned by the API.
from backend.app.schemas import (
    TransactionOut,
    MerchantTransactionDetailOut,
    MerchantStats
)

# Authentication dependency.
#
# get_merchant_user() verifies that the currently logged-in
# user is authenticated AND has the merchant role.
from backend.app.auth.auth import get_merchant_user


# ---------------------------------------------------------------------------
# ROUTER CONFIGURATION
# ---------------------------------------------------------------------------

# Create a FastAPI router specifically for merchant-related APIs.
#
# prefix="/merchant" means every endpoint below automatically
# starts with /merchant.
#
# For example:
#
# @router.get("/transactions")
#
# becomes:
#
# GET /merchant/transactions
#
# tags=["Merchant Interface"] groups these endpoints together
# in the Swagger/OpenAPI documentation.
router = APIRouter(
    prefix="/merchant",
    tags=["Merchant Interface"]
)


# ===========================================================================
# 1. GET MERCHANT TRANSACTIONS
# ===========================================================================

@router.get(
    "/transactions",
    response_model=List[TransactionOut]
)
def get_merchant_transactions(
    # -----------------------------------------------------------------------
    # AUTHENTICATION / AUTHORIZATION
    # -----------------------------------------------------------------------
    #
    # FastAPI calls get_merchant_user() before executing this endpoint.
    #
    # It ensures:
    # 1. The request contains valid authentication credentials.
    # 2. The authenticated user exists.
    # 3. The user has the merchant role.
    #
    # The returned User object is stored in current_user.
    current_user: User = Depends(get_merchant_user),

    # -----------------------------------------------------------------------
    # DATABASE DEPENDENCY
    # -----------------------------------------------------------------------
    #
    # FastAPI creates/provides a SQLAlchemy database session.
    #
    # After the request finishes, the dependency can close
    # the database session appropriately.
    db: Session = Depends(get_db)
):
    """
    Returns a list of transactions belonging to the logged-in merchant.

    Only transactions owned by the authenticated merchant are returned.
    Raw model features and other sensitive fraud-detection information
    are intentionally excluded from the response.
    """

    # -----------------------------------------------------------------------
    # QUERY TRANSACTIONS
    # -----------------------------------------------------------------------

    # Query the Transaction table.
    #
    # IMPORTANT:
    # We filter using current_user.id.
    #
    # This prevents Merchant A from requesting Merchant B's transactions.
    #
    # SQL equivalent:
    #
    # SELECT *
    # FROM transactions
    # WHERE merchant_id = current_user.id
    # ORDER BY ingested_at DESC;
    transactions = db.query(Transaction).filter(
        Transaction.merchant_id == current_user.id
    ).order_by(
        Transaction.ingested_at.desc()
    ).all()


    # List that will contain the sanitized response objects.
    #
    # We don't directly return the SQLAlchemy Transaction objects because
    # we want to control exactly which fields the merchant is allowed to see.
    results = []


    # -----------------------------------------------------------------------
    # CONVERT DATABASE MODELS → RESPONSE SCHEMAS
    # -----------------------------------------------------------------------

    # Process each transaction returned from the database.
    for tx in transactions:

        # Default fraud-related values.
        #
        # A transaction might not have a FraudAssessment yet.
        score = None
        decision = None


        # Check whether this transaction has an associated
        # fraud assessment.
        if tx.fraud_assessment:

            # Fraud score generated by the fraud detection model.
            score = tx.fraud_assessment.fraud_score

            # Model decision such as:
            # "approve"
            # "review"
            # "block"
            decision = tx.fraud_assessment.model_decision


        # Create a sanitized TransactionOut object.
        #
        # Only fields explicitly included here are exposed through
        # this merchant API.
        #
        # This is important because the underlying Transaction model
        # may contain sensitive/internal ML features.
        results.append(
            TransactionOut(
                id=tx.id,
                merchant_id=tx.merchant_id,
                source_row_id=tx.source_row_id,
                time_offset=tx.time_offset,
                amount=tx.amount,
                status=tx.status,
                ingested_at=tx.ingested_at,

                # Fraud model information
                fraud_score=score,
                model_decision=decision
            )
        )


    # Return the list of sanitized transaction objects.
    #
    # FastAPI will serialize these according to TransactionOut.
    return results


# ===========================================================================
# 2. GET SINGLE TRANSACTION DETAILS
# ===========================================================================

@router.get(
    "/transactions/{id}",
    response_model=MerchantTransactionDetailOut
)
def get_merchant_transaction_detail(
    # Transaction ID comes from the URL.
    #
    # Example:
    # GET /merchant/transactions/42
    #
    # id = 42
    id: int,

    # Verify that the user is an authenticated merchant.
    current_user: User = Depends(get_merchant_user),

    # Database session
    db: Session = Depends(get_db)
):
    """
    Returns sanitized details for a specific transaction.

    Sensitive fraud-detection features such as V1-V28 PCA vectors
    and internal SHAP/model parameters are intentionally hidden.
    """


    # -----------------------------------------------------------------------
    # FIND TRANSACTION
    # -----------------------------------------------------------------------

    # Search for a transaction using TWO conditions:
    #
    # 1. Transaction ID must match the requested ID.
    # 2. merchant_id must match the currently logged-in merchant.
    #
    # The second condition is critical for authorization.
    #
    # Without it, a merchant could potentially request:
    #
    # /merchant/transactions/999
    #
    # and access another merchant's transaction.
    tx = db.query(Transaction).filter(
        Transaction.id == id,
        Transaction.merchant_id == current_user.id
    ).first()


    # -----------------------------------------------------------------------
    # HANDLE MISSING / UNAUTHORIZED TRANSACTION
    # -----------------------------------------------------------------------

    # If no transaction was found, return HTTP 404.
    #
    # Notice that we intentionally don't reveal whether the transaction
    # exists for another merchant.
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found or unauthorized access."
        )


    # -----------------------------------------------------------------------
    # CALCULATE RISK LEVEL
    # -----------------------------------------------------------------------

    # Default risk level.
    #
    # If there is no fraud assessment, we treat it as Low here.
    risk_level = "Low"


    # Check whether a fraud assessment exists.
    if tx.fraud_assessment:

        # Get the numerical fraud score.
        score = tx.fraud_assessment.fraud_score


        # Score >= 70 → High risk
        if score >= 70:
            risk_level = "High"

        # Score between 30 and 69 → Medium risk
        elif score >= 30:
            risk_level = "Medium"

        # Score below 30 remains Low.


    # -----------------------------------------------------------------------
    # RETURN SANITIZED TRANSACTION DETAILS
    # -----------------------------------------------------------------------

    # Construct the response using MerchantTransactionDetailOut.
    #
    # Again, we explicitly choose which fields the merchant receives.
    #
    # Sensitive ML/model information is not included.
    return MerchantTransactionDetailOut(
        id=tx.id,
        merchant_id=tx.merchant_id,
        time_offset=tx.time_offset,
        amount=tx.amount,
        status=tx.status,
        ingested_at=tx.ingested_at,
        risk_level=risk_level
    )


# ===========================================================================
# 3. GET MERCHANT STATISTICS
# ===========================================================================

@router.get(
    "/stats",
    response_model=MerchantStats
)
def get_merchant_stats(
    # Only authenticated merchants can access these statistics.
    current_user: User = Depends(get_merchant_user),

    # Database session
    db: Session = Depends(get_db)
):
    """
    Returns aggregate statistics for the logged-in merchant.

    Statistics include:

    - Total number of transactions
    - Number of flagged transactions
    - Total monetary value of blocked transactions
    """


    # -----------------------------------------------------------------------
    # TOTAL TRANSACTION COUNT
    # -----------------------------------------------------------------------

    # Count all transactions belonging to the current merchant.
    #
    # SQL equivalent:
    #
    # SELECT COUNT(id)
    # FROM transactions
    # WHERE merchant_id = current_user.id;
    #
    # scalar() extracts the single numerical result.
    total_tx = db.query(
        func.count(Transaction.id)
    ).filter(
        Transaction.merchant_id == current_user.id
    ).scalar() or 0


    # -----------------------------------------------------------------------
    # FLAGGED TRANSACTION COUNT
    # -----------------------------------------------------------------------

    # Count transactions belonging to this merchant
    # whose status is "flagged".
    #
    # SQL equivalent:
    #
    # SELECT COUNT(id)
    # FROM transactions
    # WHERE merchant_id = current_user.id
    # AND status = 'flagged';
    flagged_tx = db.query(
        func.count(Transaction.id)
    ).filter(
        Transaction.merchant_id == current_user.id,
        Transaction.status == "flagged"
    ).scalar() or 0


    # -----------------------------------------------------------------------
    # BLOCKED AMOUNT / MONEY SAVED
    # -----------------------------------------------------------------------

    # Calculate the total monetary value of transactions
    # that the fraud model decided to block.
    #
    # We need data from TWO tables:
    #
    # Transaction
    #      |
    #      | transaction_id
    #      ↓
    # FraudAssessment
    #
    # Therefore, we JOIN the two tables.
    blocked_amount = db.query(
        func.sum(Transaction.amount)
    ).join(
        FraudAssessment,
        Transaction.id == FraudAssessment.transaction_id
    ).filter(

        # Only transactions belonging to the logged-in merchant
        Transaction.merchant_id == current_user.id,

        # Only transactions where the fraud model decided to block
        FraudAssessment.model_decision == "block"

    ).scalar() or 0.0


    # -----------------------------------------------------------------------
    # RETURN STATISTICS
    # -----------------------------------------------------------------------

    # Convert the database results into the MerchantStats
    # response schema.
    #
    # FastAPI will serialize this object into JSON.
    return MerchantStats(
        total_transactions=total_tx,
        flagged_count=flagged_tx,
        blocked_amount_saved=float(blocked_amount)
    )