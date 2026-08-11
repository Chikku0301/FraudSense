# FraudSense — Real-Time Transaction Fraud Detection & Risk Monitoring

FraudSense is a full-stack, production-grade web application representing internal fraud engineering systems used by card networks, payment processors, and banks. It evaluates incoming credit card transactions in real-time, generates human-interpretable feature explanations using SHAP, and triggers automated hold/block responses.

---

## Technical Architecture

### Machine Learning Pipeline
1. **Deterministic Splitting**: Splits the real 150MB credit card transaction dataset (`creditcard.csv`) stratified on class:
   - **60% Train**: Core model training.
   - **15% Validation**: Validation parameters, metrics evaluation.
   - **25% Incoming Pool**: Kept unseen during training; stored at `backend/models_store/incoming_pool.csv` and serves as the sole source of "live simulated" transactions.
2. **Feature Engineering & Balancing**:
   - `Amount` and `Time` are scaled using a fitted `StandardScaler` (V1–V28 are PCA-transformed and already scaled).
   - **SMOTE** is applied only to the Train split to resolve the extreme 0.172% minority class imbalance.
3. **Hybrid Ensemble Scoring**:
   - **XGBoost Classifier** (Supervised): Predicts probability of transaction being fraudulent.
   - **Isolation Forest** (Unsupervised Anomaly Detector): Scores pattern outliers.
   - **Combined Risk Score**: Calculated as `0.8 * XGBoost + 0.2 * Isolation Forest` (Sigmoid-scaled decision boundaries), mapped to a 0-100 range.
4. **SHAP TreeExplainability**: Evaluates tree log-odds contribution weights for top-contributing features (V1-V28, Time, Amount).

### System Stack
- **Frontend**: React (v18), TypeScript, Vite, TailwindCSS, Lucide-React, Recharts, React Hook Form + Zod.
- **Backend**: Python 3.11, FastAPI, WebSockets (for live transaction stream), SQLAlchemy, SQLite (local fallback) / PostgreSQL (Docker-compose), joblib, shap.
- **Orchestration**: Docker Compose.

---

## Setup & Execution

### Method 1: Local Docker Compose (Recommended)
Verify that Docker Desktop is running, then execute from the root directory:
```bash
docker compose up --build
```
This automatically boots:
1. `db`: PostgreSQL 15 database on `localhost:5432`.
2. `backend`: FastAPI API server on `localhost:8000` (automatically runs migrations, splits dataset, trains ML model, and seeds database on first boot).
3. `frontend`: React Vite application running on `http://localhost:5173`.

### Method 2: Manual Local Fallback (No Docker)
If Docker is unavailable, you can start frontend and backend services directly on your local shell:

#### 1. Setup & Train Backend
```bash
cd backend
# Install dependencies
pip install -r requirements.txt

# Run dataset splitting & model training (takes ~1.5 mins)
python -m app.ml.train_fraud_model

# Run database table migrations and seed user accounts
python -m app.seed

# Start FastAPI server (runs SQLite fallback)
python -m uvicorn app.main:app --reload --port 8000
```

#### 2. Start Frontend console
```bash
cd frontend
# Install packages
npm install

# Start Vite React server
npm run dev
```

---

## Port Map & Credentials

- **Frontend Interface**: [http://localhost:5173](http://localhost:5173)
- **Backend API & Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Database Engine**: PostgreSQL on `localhost:5432` / SQLite local fallback at `backend/fraudsense.db`

### Seed Credentials
| User Type | Email | Password | Role / Views |
|---|---|---|---|
| **Analyst** | `analyst1@fraudsense.com` | `password123` | Full dashboard, cases review, raw SHAP bar charts, batch upload, live simulator |
| **Merchant** | `merchant1@fraudsense.com` | `password123` | Own transactions, basic stats, sanitized risk badges (Low/Medium/High) |

---

## Key Interface Differentiators
- **Simulation Console**: Pressing **Simulate Live Transaction** on the Analyst Feed calls `/simulate-live` to randomly pull an unused row from `incoming_pool.csv`, score it, and instantly broadcast it to all connected analyst monitors using WebSockets.
- **Visual Explainability (SHAP)**: Clicking into any case renders a customized horizontal bar chart showing how raw PCA factors and transaction amounts affected the threat score.
- **Human-in-the-Loop MLOps**: Resolving cases as either a "False Positive" or "Confirmed Fraud" automatically recalculates overall model Precision and Recall coefficients inside Portfolio Analytics.
