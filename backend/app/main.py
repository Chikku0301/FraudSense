import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.database import Base, engine
from backend.app.config import XGB_MODEL_PATH, IFOREST_MODEL_PATH
from backend.app.ml.train_fraud_model import run_training_pipeline
from backend.app.seed import seed_db
from backend.app.routers import auth, merchant, analyst

app = FastAPI(
    title="FraudSense API",
    description="Real-time transaction fraud detection and risk monitoring API.",
    version="1.0.0"
)

# CORS configuration to allow local React frontend client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(merchant.router, prefix="/api/v1")
app.include_router(analyst.router, prefix="/api/v1")

@app.on_event("startup")
def on_startup():
    print("[Startup] Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    # Automatically trigger model training if model files do not exist
    if not (os.path.exists(XGB_MODEL_PATH) and os.path.exists(IFOREST_MODEL_PATH)):
        print("[Startup] Model artifacts not found. Running training pipeline...")
        try:
            run_training_pipeline()
        except Exception as e:
            print(f"[Startup] Failed to run training pipeline automatically: {e}")
            raise e
            
    # Automatically seed database
    print("[Startup] Seeding database...")
    try:
        seed_db()
    except Exception as e:
        print(f"[Startup] Seeding failed: {e}")

@app.get("/")
def read_root():
    return {
        "name": "FraudSense API",
        "status": "healthy",
        "docs_url": "/docs",
        "version": "1.0.0"
    }
