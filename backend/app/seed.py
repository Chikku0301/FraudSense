import os
import random
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.app.database import Base, engine, SessionLocal
from backend.app.models import User, Transaction, FraudAssessment, Case, AuditLog
from backend.app.auth.auth import get_password_hash
from backend.app.ml.predict import score_transaction
from backend.app.ml.explain import explain_transaction
from backend.app.config import POOL_CSV_PATH

def seed_db():
    print("[Seed] Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        # Check if already seeded
        if db.query(User).filter(User.role == "analyst").first() is not None:
            print("[Seed] Database already seeded. Skipping.")
            return

        print("[Seed] Seeding users...")
        
        # 1. Create Analysts
        analysts_data = [
            {"email": "analyst1@fraudsense.com", "full_name": "Sarah Jenkins", "role": "analyst"},
            {"email": "analyst2@fraudsense.com", "full_name": "David Miller", "role": "analyst"},
            {"email": "admin@fraudsense.com", "full_name": "System Administrator", "role": "admin"}
        ]
        
        analysts = []
        for data in analysts_data:
            user = User(
                email=data["email"],
                full_name=data["full_name"],
                role=data["role"],
                hashed_password=get_password_hash("password123")
            )
            db.add(user)
            analysts.append(user)
            
        # 2. Create Merchants
        merchants_data = [
            {"email": "merchant1@fraudsense.com", "full_name": "Apex Retailer", "merchant_name": "Apex Retailers"},
            {"email": "merchant2@fraudsense.com", "full_name": "Nova Shop Owner", "merchant_name": "Nova Electronics"},
            {"email": "merchant3@fraudsense.com", "full_name": "Quick Payments", "merchant_name": "Quick Food Services"},
            {"email": "merchant4@fraudsense.com", "full_name": "Elite Travel Manager", "merchant_name": "Elite Travel Group"},
            {"email": "merchant5@fraudsense.com", "full_name": "Secure Goods Clerk", "merchant_name": "Secure Goods Corp"}
        ]
        
        merchants = []
        for data in merchants_data:
            user = User(
                email=data["email"],
                full_name=data["full_name"],
                role="merchant",
                merchant_name=data["merchant_name"],
                hashed_password=get_password_hash("password123")
            )
            db.add(user)
            merchants.append(user)
            
        db.commit()
        print(f"[Seed] Successfully seeded {len(analysts)} analysts/admins and {len(merchants)} merchants.")

        # 3. Seed Transactions from incoming_pool.csv
        print("[Seed] Loading incoming_pool.csv to ingest seed transactions...")
        if not os.path.exists(POOL_CSV_PATH):
            print(f"[Seed] Warning: {POOL_CSV_PATH} not found. Cannot seed transactions. Run training pipeline first!")
            return

        pool_df = pd.read_csv(POOL_CSV_PATH)
        if pool_df.empty:
            print("[Seed] Warning: incoming_pool.csv is empty. Cannot seed transactions.")
            return

        # Seed around 200 rows deterministically (reproducible)
        seed_count = min(200, len(pool_df))
        print(f"[Seed] Ingesting and scoring {seed_count} seed transactions...")

        # Keep seeding reproducible
        random.seed(42)
        
        # We'll distribute dates backward from current time
        now = datetime.utcnow()
        merchant_ids = [m.id for m in merchants]

        for idx in range(seed_count):
            row = pool_df.iloc[idx]
            
            # Feature dict for scorer/explainers
            feature_vector = {col: float(row[col]) for col in ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]}
            true_cls = int(row["Class"])
            
            # Score and explain transaction
            assessment_res = score_transaction(feature_vector)
            explanations = explain_transaction(feature_vector)

            # Assign random merchant and timestamp
            assigned_merchant = random.choice(merchant_ids)
            # Transactions spread out over the last 7 days
            tx_time = now - timedelta(
                days=random.randint(0, 6),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )

            tx = Transaction(
                merchant_id=assigned_merchant,
                source_row_id=idx,
                time_offset=feature_vector["Time"],
                amount=feature_vector["Amount"],
                raw_features={f"V{i}": feature_vector[f"V{i}"] for i in range(1, 29)},
                status="cleared" if assessment_res["model_decision"] == "clear" else "flagged",
                true_class=true_cls,
                ingested_at=tx_time
            )
            db.add(tx)
            db.flush()

            assessment = FraudAssessment(
                transaction_id=tx.id,
                fraud_score=assessment_res["fraud_score"],
                fraud_probability=assessment_res["fraud_probability"],
                model_decision=assessment_res["model_decision"],
                shap_explanation=explanations,
                model_version="1.0.0",
                created_at=tx_time
            )
            db.add(assessment)

            # Create case if flagged or blocked
            if assessment_res["model_decision"] in ["flag_for_review", "block"]:
                case = Case(
                    transaction_id=tx.id,
                    status="open",
                    notes=f"Seeded transaction flagged. Model decision: {assessment_res['model_decision']}",
                    created_at=tx_time
                )
                db.add(case)
                
                # Randomly resolve some older cases to provide training metrics for the dashboard
                if idx % 3 == 0:
                    case.status = "resolved"
                    case.resolved_at = tx_time + timedelta(hours=random.randint(1, 12))
                    # Match resolution to true label for realistic precision/recall values
                    case.resolution = "fraud_confirmed" if true_cls == 1 else "false_positive"
                    case.assigned_analyst_id = random.choice([a.id for a in analysts if a.role == "analyst"])
                    case.notes = "Reviewed and resolved based on mock transaction verification."
                    
                    # Update transaction status
                    tx.status = "confirmed_fraud" if case.resolution == "fraud_confirmed" else "confirmed_legit"
                    
                    # Add audit log
                    audit = AuditLog(
                        actor_id=case.assigned_analyst_id,
                        transaction_id=tx.id,
                        action="RESOLVE_CASE",
                        notes=f"Resolved case ID {case.id} as {case.resolution.upper()} (Seed data).",
                        created_at=case.resolved_at
                    )
                    db.add(audit)

        db.commit()
        print(f"[Seed] Successfully ingested and scored {seed_count} seed transactions.")
    except Exception as e:
        db.rollback()
        print(f"[Seed] Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
