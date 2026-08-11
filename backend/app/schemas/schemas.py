from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field

# --- AUTH SCHEMAS ---

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str
    role: str = Field(..., description="merchant | analyst | admin")
    merchant_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: str
    full_name: str
    merchant_name: Optional[str] = None
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
    user_id: Optional[int] = None


# --- FRAUD ASSESSMENT SCHEMAS ---

class FraudAssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_id: int
    fraud_score: int
    fraud_probability: float
    model_decision: str
    shap_explanation: List[Dict[str, Any]]
    model_version: str
    created_at: datetime


# --- CASE SCHEMAS ---

class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_id: int
    assigned_analyst_id: Optional[int] = None
    status: str
    resolution: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None


class CaseResolve(BaseModel):
    resolution: str = Field(..., description="fraud_confirmed | false_positive")
    notes: Optional[str] = None


# --- TRANSACTION SCHEMAS ---

class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    merchant_id: Optional[int] = None
    source_row_id: Optional[int] = None
    time_offset: float
    amount: float
    status: str
    ingested_at: datetime
    fraud_score: Optional[int] = None  # Populated from assessment if available
    model_decision: Optional[str] = None


# Extended detail schema for Merchant (no V1-V28 raw features, no SHAP)
class MerchantTransactionDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    merchant_id: Optional[int] = None
    time_offset: float
    amount: float
    status: str
    ingested_at: datetime
    risk_level: str  # Low | Medium | High risk band derived from score


# Extended detail schema for Analyst (contains all features, assessment, case, etc.)
class AnalystTransactionDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    merchant_id: Optional[int] = None
    source_row_id: Optional[int] = None
    time_offset: float
    amount: float
    raw_features: Dict[str, Any]
    status: str
    true_class: int
    ingested_at: datetime
    fraud_assessment: Optional[FraudAssessmentOut] = None
    case: Optional[CaseOut] = None


# --- AUDIT LOG SCHEMAS ---

class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int
    transaction_id: Optional[int] = None
    action: str
    notes: Optional[str] = None
    created_at: datetime


# --- DASHBOARD & ANALYTICS SCHEMAS ---

class MerchantStats(BaseModel):
    total_transactions: int
    flagged_count: int
    blocked_amount_saved: float


class FraudRateTrend(BaseModel):
    date: str  # YYYY-MM-DD
    rate: float


class ScoreDistributionBucket(BaseModel):
    bucket: str  # "0-10", "10-20", etc.
    count: int


class AnalystPortfolioStats(BaseModel):
    fraud_rate_trend: List[FraudRateTrend]
    score_distribution: List[ScoreDistributionBucket]
    total_flagged_volume: float
    model_precision: float
    model_recall: float
