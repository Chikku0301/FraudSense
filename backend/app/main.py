import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import database metadata and database engine.
# Base contains the SQLAlchemy model metadata used to create database tables.
# engine manages the connection between the application and the database.
from backend.app.database import Base, engine

# Import paths where the trained ML model files are stored.
from backend.app.config import XGB_MODEL_PATH, IFOREST_MODEL_PATH

# Import the function responsible for training the fraud detection models.
from backend.app.ml.train_fraud_model import run_training_pipeline

# Import the function used to insert initial/sample data into the database.
from backend.app.seed import seed_db

# Import API routers.
# Each router contains endpoints related to a specific part of the application.
from backend.app.routers import auth, merchant, analyst


# Create the main FastAPI application instance.
# Metadata such as title, description, and version will appear in the
# automatically generated Swagger documentation.
app = FastAPI(
    title="FraudSense API",
    description="Real-time transaction fraud detection and risk monitoring API.",
    version="1.0.0"
)


# Configure CORS (Cross-Origin Resource Sharing).
# This allows the React frontend running on localhost:5173
# to send requests to this FastAPI backend.
app.add_middleware(
    CORSMiddleware,
    
    # Allow requests only from the local React/Vite frontend.
    allow_origins=["http://localhost:5173"],
    
    # Allow cookies and authentication credentials to be sent.
    allow_credentials=True,
    
    # Allow all HTTP methods such as GET, POST, PUT, DELETE, etc.
    allow_methods=["*"],
    
    # Allow all request headers.
    allow_headers=["*"],
)


# Register authentication-related API endpoints.
# Example: /api/v1/login, /api/v1/register
app.include_router(auth.router, prefix="/api/v1")

# Register merchant-related API endpoints.
# Example: /api/v1/transactions
app.include_router(merchant.router, prefix="/api/v1")

# Register analyst-related API endpoints.
# Example: /api/v1/alerts or fraud analysis endpoints
app.include_router(analyst.router, prefix="/api/v1")


# This function runs automatically when the FastAPI application starts.
@app.on_event("startup")
def on_startup():
    
    # Create all database tables defined using SQLAlchemy models.
    # Tables are created only if they do not already exist.
    print("[Startup] Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    
    # Check whether the trained ML model files already exist.
    # If either model is missing, automatically run the training pipeline.
    if not (
        os.path.exists(XGB_MODEL_PATH)
        and os.path.exists(IFOREST_MODEL_PATH)
    ):
        print(
            "[Startup] Model artifacts not found. "
            "Running training pipeline..."
        )

        try:
            # Train the fraud detection models and save them.
            run_training_pipeline()

        except Exception as e:
            # Print the error if model training fails.
            print(
                f"[Startup] Failed to run training pipeline automatically: {e}"
            )

            # Re-raise the exception so the application startup fails visibly.
            raise e


    # Seed the database with initial data.
    # This may include sample users, merchants, transactions, etc.
    print("[Startup] Seeding database...")

    try:
        seed_db()

    except Exception as e:
        # Log the error, but do not stop the entire application.
        print(f"[Startup] Seeding failed: {e}")


# Define the root endpoint of the API.
# A GET request to "/" will return basic API information.
@app.get("/")
def read_root():
    
    # Return a JSON response indicating that the API is running.
    return {
        "name": "FraudSense API",
        "status": "healthy",
        "docs_url": "/docs",
        "version": "1.0.0"
    }