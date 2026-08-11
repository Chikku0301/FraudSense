from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from backend.app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # merchant | analyst | admin
    full_name = Column(String, nullable=False)
    merchant_name = Column(String, nullable=True)  # only for merchant role
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    assigned_cases = relationship("Case", back_populates="assigned_analyst")
    audit_logs = relationship("AuditLog", back_populates="actor")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    source_row_id = Column(Integer, nullable=True)  # References incoming_pool.csv row index
    time_offset = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    raw_features = Column(JSON, nullable=False)  # Contains V1-V28 vectors
    status = Column(String, nullable=False)  # pending | cleared | flagged | confirmed_fraud | confirmed_legit
    true_class = Column(Integer, nullable=False)  # Ground truth: 1 for fraud, 0 for legit
    ingested_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    merchant = relationship("User", foreign_keys=[merchant_id])
    fraud_assessment = relationship("FraudAssessment", back_populates="transaction", uselist=False)
    case = relationship("Case", back_populates="transaction", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="transaction")


class FraudAssessment(Base):
    __tablename__ = "fraud_assessments"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    fraud_score = Column(Integer, nullable=False)  # 0 to 100
    fraud_probability = Column(Float, nullable=False)  # 0.0 to 1.0
    model_decision = Column(String, nullable=False)  # clear | flag_for_review | block
    shap_explanation = Column(JSON, nullable=False)  # Top contributing features
    model_version = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    transaction = relationship("Transaction", back_populates="fraud_assessment")


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    assigned_analyst_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="open")  # open | investigating | resolved
    resolution = Column(String, nullable=True)  # fraud_confirmed | false_positive
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    transaction = relationship("Transaction", back_populates="case")
    assigned_analyst = relationship("User", back_populates="assigned_cases")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    action = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    actor = relationship("User", back_populates="audit_logs")
    transaction = relationship("Transaction", back_populates="audit_logs")
