import sys
import os

# Ensure both backend directory and project root directory are on sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_current_dir)
_root_dir = os.path.dirname(_backend_dir)

for _p in [_root_dir, _backend_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import database metadata and database engine.
try:
    from backend.app.database import Base, engine
    from backend.app.config import XGB_MODEL_PATH, IFOREST_MODEL_PATH
    from backend.app.ml.train_fraud_model import run_training_pipeline
    from backend.app.seed import seed_db
    from backend.app.routers import auth, merchant, analyst
except ImportError:
    from app.database import Base, engine
    from app.config import XGB_MODEL_PATH, IFOREST_MODEL_PATH
    from app.ml.train_fraud_model import run_training_pipeline
    from app.seed import seed_db
    from app.routers import auth, merchant, analyst


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