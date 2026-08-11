import os

# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_STORE_DIR = os.path.join(BASE_DIR, "models_store")

# Database Configuration - defaults to SQLite for local dev; PostgreSQL for Docker
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fraudsense.db")

# JWT authentication configuration
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-fraud-sense-key-123456789")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")) # 24 hours

# ML Decision Thresholds
THRESHOLD_CLEAR = float(os.getenv("THRESHOLD_CLEAR", "0.3"))
THRESHOLD_BLOCK = float(os.getenv("THRESHOLD_BLOCK", "0.7"))

# Setup paths for models
SCALER_PATH = os.path.join(MODEL_STORE_DIR, "scaler.pkl")
XGB_MODEL_PATH = os.path.join(MODEL_STORE_DIR, "xgboost_model.pkl")
IFOREST_MODEL_PATH = os.path.join(MODEL_STORE_DIR, "iforest_model.pkl")
SHAP_EXPLAINER_PATH = os.path.join(MODEL_STORE_DIR, "shap_explainer.pkl")
METRICS_PATH = os.path.join(MODEL_STORE_DIR, "metrics.json")
POOL_CSV_PATH = os.path.join(MODEL_STORE_DIR, "incoming_pool.csv")
