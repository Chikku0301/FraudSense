import os
import random
import pandas as pd

# Used for generating timestamps for seeded transactions and cases
from datetime import datetime, timedelta

# SQLAlchemy session type for database interaction
from sqlalchemy.orm import Session


# Import database components:
# Base -> contains metadata for all SQLAlchemy models
# engine -> database connection engine
# SessionLocal -> creates a new database session
from backend.app.database import Base, engine, SessionLocal


# Import database models
from backend.app.models import (
    User,
    Transaction,
    FraudAssessment,
    Case,
    AuditLog
)


# Import password hashing function so seeded users do not store plain-text passwords
from backend.app.auth.auth import get_password_hash


# Import ML functions:
# score_transaction -> predicts fraud risk
# explain_transaction -> generates an explanation for the prediction
from backend.app.ml.predict import score_transaction
from backend.app.ml.explain import explain_transaction


# Path to the CSV file containing transactions that will be seeded
from backend.app.config import POOL_CSV_PATH


def seed_db():
    """
    Seed the database with initial application data.

    The function performs the following steps:

    1. Creates database tables if they do not exist.
    2. Checks whether the database has already been seeded.
    3. Creates analyst, admin, and merchant users.
    4. Loads transaction data from incoming_pool.csv.
    5. Scores each transaction using the fraud detection models.
    6. Generates fraud explanations.
    7. Creates fraud assessments and investigation cases.
    8. Resolves some cases to simulate realistic analyst activity.
    9. Creates audit logs for resolved cases.
    """

    # Ensure all database tables defined in the models exist
    print("[Seed] Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    # Create a new database session
    db: Session = SessionLocal()

    try:
        # ---------------------------------------------------------
        # CHECK WHETHER THE DATABASE HAS ALREADY BEEN SEEDED
        # ---------------------------------------------------------

        # If an analyst already exists, assume the seed data
        # has already been inserted and avoid creating duplicates.
        if db.query(User).filter(User.role == "analyst").first() is not None:
            print("[Seed] Database already seeded. Skipping.")
            return


        # ---------------------------------------------------------
        # CREATE ANALYST AND ADMIN USERS
        # ---------------------------------------------------------

        print("[Seed] Seeding users...")

        # Define the initial analyst and admin accounts
        analysts_data = [
            {
                "email": "analyst1@fraudsense.com",
                "full_name": "Sarah Jenkins",
                "role": "analyst"
            },
            {
                "email": "analyst2@fraudsense.com",
                "full_name": "David Miller",
                "role": "analyst"
            },
            {
                "email": "admin@fraudsense.com",
                "full_name": "System Administrator",
                "role": "admin"
            }
        ]

        # Store created analyst/admin objects for later use
        analysts = []

        # Create a User object for each analyst/admin
        for data in analysts_data:

            user = User(
                email=data["email"],
                full_name=data["full_name"],
                role=data["role"],

                # Store a hashed password instead of plain text
                hashed_password=get_password_hash("password123")
            )

            # Add the user to the current database session
            db.add(user)

            # Keep a reference to the created user
            analysts.append(user)


        # ---------------------------------------------------------
        # CREATE MERCHANT USERS
        # ---------------------------------------------------------

        # Define initial merchant accounts
        merchants_data = [
            {
                "email": "merchant1@fraudsense.com",
                "full_name": "Apex Retailer",
                "merchant_name": "Apex Retailers"
            },
            {
                "email": "merchant2@fraudsense.com",
                "full_name": "Nova Shop Owner",
                "merchant_name": "Nova Electronics"
            },
            {
                "email": "merchant3@fraudsense.com",
                "full_name": "Quick Payments",
                "merchant_name": "Quick Food Services"
            },
            {
                "email": "merchant4@fraudsense.com",
                "full_name": "Elite Travel Manager",
                "merchant_name": "Elite Travel Group"
            },
            {
                "email": "merchant5@fraudsense.com",
                "full_name": "Secure Goods Clerk",
                "merchant_name": "Secure Goods Corp"
            }
        ]

        # Store created merchant objects
        merchants = []

        # Create a User record for each merchant
        for data in merchants_data:

            user = User(
                email=data["email"],
                full_name=data["full_name"],

                # All users in this section have the merchant role
                role="merchant",

                # Store the business/merchant name
                merchant_name=data["merchant_name"],

                # Hash the default password before storing it
                hashed_password=get_password_hash("password123")
            )

            # Add the merchant to the database session
            db.add(user)

            # Keep a reference for assigning transactions later
            merchants.append(user)


        # Save users and merchants to the database.
        # After commit, SQLAlchemy assigns database IDs to these objects.
        db.commit()

        print(
            f"[Seed] Successfully seeded "
            f"{len(analysts)} analysts/admins and "
            f"{len(merchants)} merchants."
        )


        # ---------------------------------------------------------
        # LOAD TRANSACTIONS FROM incoming_pool.csv
        # ---------------------------------------------------------

        print(
            "[Seed] Loading incoming_pool.csv "
            "to ingest seed transactions..."
        )

        # Check whether the transaction pool file exists
        if not os.path.exists(POOL_CSV_PATH):

            print(
                f"[Seed] Warning: {POOL_CSV_PATH} not found. "
                "Cannot seed transactions. "
                "Run training pipeline first!"
            )

            return


        # Load the transaction dataset into a Pandas DataFrame
        pool_df = pd.read_csv(POOL_CSV_PATH)


        # Stop if the CSV contains no transactions
        if pool_df.empty:

            print(
                "[Seed] Warning: incoming_pool.csv is empty. "
                "Cannot seed transactions."
            )

            return


        # ---------------------------------------------------------
        # DETERMINE HOW MANY TRANSACTIONS TO SEED
        # ---------------------------------------------------------

        # Seed a maximum of 200 transactions.
        # If the dataset contains fewer rows, use all available rows.
        seed_count = min(200, len(pool_df))

        print(
            f"[Seed] Ingesting and scoring "
            f"{seed_count} seed transactions..."
        )


        # ---------------------------------------------------------
        # MAKE RANDOM BEHAVIOR REPRODUCIBLE
        # ---------------------------------------------------------

        # Setting a fixed random seed ensures that random choices,
        # such as merchant assignment and timestamps, are reproducible.
        random.seed(42)


        # Get the current UTC time.
        # Seeded transactions will be distributed over the previous 7 days.
        now = datetime.utcnow()


        # Extract database IDs of all merchants.
        # Transactions will be randomly assigned to these merchants.
        merchant_ids = [m.id for m in merchants]


        # ---------------------------------------------------------
        # CREATE AND PROCESS SEED TRANSACTIONS
        # ---------------------------------------------------------

        # Iterate through the selected rows from the CSV
        for idx in range(seed_count):

            # Get the current transaction row
            row = pool_df.iloc[idx]


            # -----------------------------------------------------
            # PREPARE THE ML FEATURE VECTOR
            # -----------------------------------------------------

            # The fraud models expect:
            # - Time
            # - Amount
            # - V1 to V28
            #
            # Convert all values to float before sending them
            # to the prediction and explanation functions.
            feature_vector = {
                col: float(row[col])
                for col in (
                    ["Time", "Amount"]
                    + [f"V{i}" for i in range(1, 29)]
                )
            }


            # Get the original fraud label from the dataset.
            #
            # Typically:
            # 0 -> legitimate transaction
            # 1 -> fraudulent transaction
            true_cls = int(row["Class"])


            # -----------------------------------------------------
            # SCORE THE TRANSACTION USING THE ML MODELS
            # -----------------------------------------------------

            # Generate the fraud prediction.
            #
            # Expected output may contain:
            # - fraud_score
            # - fraud_probability
            # - model_decision
            assessment_res = score_transaction(feature_vector)


            # Generate an explanation for the model prediction,
            # such as important features contributing to fraud risk.
            explanations = explain_transaction(feature_vector)


            # -----------------------------------------------------
            # ASSIGN MERCHANT AND TIMESTAMP
            # -----------------------------------------------------

            # Randomly assign the transaction to one of the merchants
            assigned_merchant = random.choice(merchant_ids)


            # Generate a timestamp within the previous 7 days.
            tx_time = now - timedelta(
                days=random.randint(0, 6),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )


            # -----------------------------------------------------
            # CREATE THE TRANSACTION RECORD
            # -----------------------------------------------------

            tx = Transaction(

                # Associate the transaction with a merchant
                merchant_id=assigned_merchant,

                # Store the original row index from the CSV
                source_row_id=idx,

                # Store the dataset's time feature
                time_offset=feature_vector["Time"],

                # Store transaction amount
                amount=feature_vector["Amount"],

                # Store the anonymized V1-V28 features as JSON/dict
                raw_features={
                    f"V{i}": feature_vector[f"V{i}"]
                    for i in range(1, 29)
                },

                # Determine the transaction status based on
                # the ML model's decision.
                status=(
                    "cleared"
                    if assessment_res["model_decision"] == "clear"
                    else "flagged"
                ),

                # Store the actual dataset label for evaluation purposes
                true_class=true_cls,

                # Store the simulated transaction ingestion time
                ingested_at=tx_time
            )


            # Add the transaction to the database session
            db.add(tx)


            # Force SQLAlchemy to send the INSERT operation
            # to the database so that tx.id becomes available.
            db.flush()


            # -----------------------------------------------------
            # CREATE FRAUD ASSESSMENT
            # -----------------------------------------------------

            # Store the ML model's prediction and explanation
            # for this transaction.
            assessment = FraudAssessment(

                # Link assessment to the transaction
                transaction_id=tx.id,

                # Fraud risk score generated by the model
                fraud_score=assessment_res["fraud_score"],

                # Probability that the transaction is fraudulent
                fraud_probability=assessment_res["fraud_probability"],

                # Final model decision, such as:
                # clear / flag_for_review / block
                model_decision=assessment_res["model_decision"],

                # Store feature-based explanation
                shap_explanation=explanations,

                # Version of the fraud detection model
                model_version="1.0.0",

                # Use the transaction's simulated timestamp
                created_at=tx_time
            )

            # Add the fraud assessment to the session
            db.add(assessment)


            # -----------------------------------------------------
            # CREATE FRAUD INVESTIGATION CASES
            # -----------------------------------------------------

            # Only create a case if the model considers the
            # transaction suspicious enough to review or block.
            if assessment_res["model_decision"] in [
                "flag_for_review",
                "block"
            ]:

                case = Case(

                    # Link the case to the suspicious transaction
                    transaction_id=tx.id,

                    # New cases start as open
                    status="open",

                    # Store a description explaining why
                    # the case was automatically created.
                    notes=(
                        "Seeded transaction flagged. "
                        f"Model decision: "
                        f"{assessment_res['model_decision']}"
                    ),

                    # Set the simulated creation time
                    created_at=tx_time
                )

                # Add the case to the database session
                db.add(case)


                # -------------------------------------------------
                # SIMULATE ANALYST RESOLUTION FOR SOME CASES
                # -------------------------------------------------

                # Resolve approximately one-third of the flagged cases.
                # This creates historical data for dashboard metrics.
                if idx % 3 == 0:

                    # Change case status from open to resolved
                    case.status = "resolved"


                    # Simulate the analyst resolving the case
                    # between 1 and 12 hours after it was created.
                    case.resolved_at = (
                        tx_time
                        + timedelta(hours=random.randint(1, 12))
                    )


                    # Use the actual dataset label to determine
                    # whether the flagged transaction was truly fraud.
                    case.resolution = (
                        "fraud_confirmed"
                        if true_cls == 1
                        else "false_positive"
                    )


                    # Randomly assign one of the analysts
                    # to the resolved case.
                    case.assigned_analyst_id = random.choice(
                        [
                            a.id
                            for a in analysts
                            if a.role == "analyst"
                        ]
                    )


                    # Replace the original note with the
                    # simulated analyst review result.
                    case.notes = (
                        "Reviewed and resolved based on "
                        "mock transaction verification."
                    )


                    # -------------------------------------------------
                    # UPDATE THE TRANSACTION STATUS
                    # -------------------------------------------------

                    # Update the transaction according to the
                    # analyst's final decision.
                    tx.status = (
                        "confirmed_fraud"
                        if case.resolution == "fraud_confirmed"
                        else "confirmed_legit"
                    )


                    # -------------------------------------------------
                    # CREATE AN AUDIT LOG
                    # -------------------------------------------------

                    # Record the case resolution action.
                    # This provides a history of important actions
                    # performed in the fraud monitoring system.
                    audit = AuditLog(

                        # The analyst who resolved the case
                        actor_id=case.assigned_analyst_id,

                        # Related transaction
                        transaction_id=tx.id,

                        # Type of action performed
                        action="RESOLVE_CASE",

                        # Human-readable description of the action
                        notes=(
                            f"Resolved case ID {case.id} as "
                            f"{case.resolution.upper()} "
                            "(Seed data)."
                        ),

                        # Time when the action occurred
                        created_at=case.resolved_at
                    )

                    # Add the audit log to the database session
                    db.add(audit)


        # ---------------------------------------------------------
        # SAVE ALL TRANSACTIONS, ASSESSMENTS, CASES, AND AUDIT LOGS
        # ---------------------------------------------------------

        # Commit all pending database operations.
        db.commit()

        print(
            f"[Seed] Successfully ingested and scored "
            f"{seed_count} seed transactions."
        )


    except Exception as e:

        # If any error occurs, undo all uncommitted changes
        # from the current transaction.
        db.rollback()

        # Print the error for debugging
        print(f"[Seed] Error seeding database: {e}")

        # Re-raise the exception so the caller knows seeding failed
        raise e


    finally:

        # Always close the database session,
        # regardless of success or failure.
        db.close()


# Allow this file to be executed directly.
# Example:
# python seed.py
if __name__ == "__main__":
    seed_db()