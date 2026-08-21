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


from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all database tables defined using SQLAlchemy models.
    print("[Startup] Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    # Check whether the trained ML model files already exist.
    if not (
        os.path.exists(XGB_MODEL_PATH)
        and os.path.exists(IFOREST_MODEL_PATH)
    ):
        print(
            "[Startup] Model artifacts not found. "
            "Running training pipeline..."
        )
        try:
            run_training_pipeline()
        except Exception as e:
            print(f"[Startup] Failed to run training pipeline automatically: {e}")
            raise e

    # Seed the database with initial data.
    print("[Startup] Seeding database...")
    try:
        seed_db()
    except Exception as e:
        print(f"[Startup] Seeding failed: {e}")

    yield


# Create the main FastAPI application instance.
app = FastAPI(
    title="FraudSense API",
    description="Real-time transaction fraud detection and risk monitoring API.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API endpoints
app.include_router(auth.router, prefix="/api/v1")
app.include_router(merchant.router, prefix="/api/v1")
app.include_router(analyst.router, prefix="/api/v1")



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