# FraudSense — Setup & Installation Guide

This guide explains how to install, configure, train, run, and test FraudSense locally.

The project contains three primary components:

```text
FraudSense
│
├── frontend/       → React application
├── backend/        → FastAPI + ML application
└── Docker           → Containerized deployment
```

---

# 1. Prerequisites

Install the following software before setting up the project.

### Required

- Python 3.11
- Node.js 18+
- npm
- Git

### Optional

- Docker Desktop
- Docker Compose

Verify the installations:

```bash
python --version
node --version
npm --version
git --version
docker --version
docker compose version
```

---

# 2. Clone the Repository

Clone the project and move into the project directory:

```bash
git clone <repository-url>
cd FraudSense
```

The repository should contain:

```text
FraudSense/
├── backend/
├── frontend/
├── docker-compose.yml
├── Dockerfile
├── README.md
└── SETUP.md
```

---

# 3. Backend Setup

Move into the backend directory:

```bash
cd backend
```

## Create a Virtual Environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

Linux/macOS/WSL:

```bash
python3 -m venv venv
source venv/bin/activate
```

---

# 4. Install Python Dependencies

Install the backend dependencies:

```bash
pip install -r requirements.txt
```

The backend uses packages including:

```text
FastAPI
Uvicorn
SQLAlchemy
Pandas
NumPy
Scikit-learn
XGBoost
imbalanced-learn
SHAP
Joblib
```

The exact versions should be taken from the project's `requirements.txt`.

---

# 5. Dataset Setup

FraudSense requires the original credit-card transaction dataset.

Place the dataset in the location expected by the backend.

For example:

```text
backend/
└── data/
    └── creditcard.csv
```

> Use the exact dataset path configured by the project's training/data-loading code if it differs from the example above.

The dataset should contain:

```text
Time
V1
V2
...
V28
Amount
Class
```

where:

```text
Class = 0 → Legitimate
Class = 1 → Fraud
```

---

# 6. Dataset Splitting

The original dataset is divided deterministically into:

```text
60% → Training
15% → Validation
25% → Incoming Pool
```

The incoming pool is stored as:

```text
backend/models_store/incoming_pool.csv
```

The incoming pool is important because it provides the transactions used by the live simulation system.

### Important

The incoming pool must **not** be included in model training.

The intended pipeline is:

```text
creditcard.csv
      │
      ▼
Deterministic Split
      │
      ├──────────────┐
      ▼              ▼
 Training        Validation
      │
      ▼
     SMOTE
      │
      ▼
 Model Training

Incoming Pool
      │
      ▼
Live Simulation
```

---

# 7. ML Model Artifacts

FraudSense requires trained ML artifacts before live inference can be performed.

The training pipeline should generate and store the required artifacts, such as:

```text
XGBoost model
Isolation Forest model
StandardScaler
SHAP-compatible model
```

These artifacts should be stored under the project's configured model directory:

```text
backend/models_store/
```

A typical structure may look like:

```text
backend/
└── models_store/
    ├── xgboost_model.*
    ├── isolation_forest.*
    ├── scaler.*
    └── incoming_pool.csv
```

The exact filenames depend on the implementation.

---

# 8. Model Training

If the required model artifacts do not exist, the backend can initialize the ML pipeline according to the project's training implementation.

The general training workflow is:

```text
Dataset
   │
   ▼
Train / Validation / Incoming Split
   │
   ├───────────────┐
   ▼               ▼
Training        Validation
   │
   ▼
Preprocessing
   │
   ▼
SMOTE
   │
   ▼
XGBoost Training
   │
   ▼
Isolation Forest Training
   │
   ▼
Model Evaluation
   │
   ▼
Save Artifacts
```

Before starting the application, verify that the expected artifacts exist.

---

# 9. Local Database

For local development, FraudSense can use SQLite.

The database is stored as:

```text
backend/fraudsense.db
```

The application initializes the required database tables during startup.

The database stores information such as:

```text
Users
Transactions
Predictions
Risk Scores
Cases
Analyst Decisions
Audit Information
```

If the database does not exist, the application can initialize it according to the configured startup logic.

---

# 10. Environment Variables

If the application uses environment variables, create a `.env` file inside the backend directory.

Example:

```env
DATABASE_URL=sqlite:///./fraudsense.db

# Application configuration
APP_ENV=development

# Authentication / security
SECRET_KEY=replace-with-a-secure-development-secret

# CORS
FRONTEND_URL=http://localhost:5173
```

For Docker/PostgreSQL, the database configuration can be changed to the PostgreSQL connection string used by the Docker Compose configuration.

### Important

Do not commit production secrets to Git.

Add the following to `.gitignore` if they are not already present:

```gitignore
.env
*.db
venv/
__pycache__/
node_modules/
```

---

# 11. Start the Backend

From the `backend` directory:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

The backend should now be available at:

```text
http://localhost:8000
```

---

# 12. Verify the Backend

Open the Swagger documentation:

```text
http://localhost:8000/docs
```

You can use Swagger to:

- Inspect available endpoints
- Authenticate
- Send test requests
- Process transactions
- Trigger simulations
- Test case-management APIs
- Inspect API schemas

---

# 13. Frontend Setup

Open another terminal.

Move to the frontend directory:

```bash
cd frontend
```

Install the JavaScript dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

The frontend should be available at:

```text
http://localhost:5173
```

---

# 14. Login

Use one of the seeded development accounts.

### Analyst

```text
Email:
analyst1@fraudsense.com

Password:
password123
```

### Merchant

```text
Email:
merchant1@fraudsense.com

Password:
password123
```

The Analyst account provides access to the full fraud-monitoring workflow.

The Merchant account provides a simplified transaction view.

> These credentials are for development/demo purposes only.

---

# 15. Test Live Transaction Simulation

After logging in as an Analyst:

1. Open the fraud monitoring dashboard.
2. Navigate to the Simulation Console.
3. Select **Simulate Live Transaction**.
4. The frontend calls the simulation endpoint.
5. The backend selects an unused transaction from the incoming pool.
6. The transaction is preprocessed.
7. XGBoost calculates its fraud score.
8. Isolation Forest calculates its anomaly score.
9. The hybrid risk engine produces the final risk score.
10. SHAP generates the explanation.
11. The transaction is stored in the database.
12. The result is broadcast through WebSockets.
13. The dashboard updates in real time.

The complete flow is:

```text
Click "Simulate Live Transaction"
             │
             ▼
      POST /simulate-live
             │
             ▼
     Select Incoming Data
             │
             ▼
        Preprocessing
             │
       ┌─────┴─────┐
       ▼           ▼
    XGBoost    Isolation Forest
       │           │
       └─────┬─────┘
             ▼
       Hybrid Risk Score
             │
             ▼
          SHAP
             │
             ▼
        Save to DB
             │
             ▼
       WebSocket Push
             │
             ▼
     Analyst Dashboard
```

---

# 16. WebSocket Live Feed

The live transaction feed uses:

```text
ws://localhost:8000/api/v1/analyst/live-feed
```

The frontend maintains a WebSocket connection to receive newly processed transactions.

This allows the dashboard to update without continuously polling the backend.

---

# 17. Testing SHAP Explanations

After processing a transaction, open its corresponding case.

The case should contain:

- Overall risk score
- Risk classification
- Recommended action
- Model prediction
- Transaction metadata
- Top contributing features
- SHAP contribution values

The SHAP visualization helps identify which features increased or decreased the predicted fraud probability.

---

# 18. Case Review

Analysts can review suspicious transactions and provide a final classification.

Available decisions:

```text
Confirmed Fraud
False Positive
```

The decision is persisted in the database.

These decisions can then contribute to portfolio-level metrics such as:

```text
Precision
Recall
Fraud Detection Performance
```

---

# 19. Batch Processing

FraudSense also supports batch transaction evaluation.

The general workflow is:

```text
CSV Upload
    │
    ▼
FastAPI
    │
    ▼
Validation
    │
    ▼
Preprocessing
    │
    ▼
ML Inference
    │
    ▼
Risk Scores
    │
    ▼
Database
    │
    ▼
Analytics
```

Use the batch-processing endpoint exposed by the FastAPI application through Swagger:

```text
http://localhost:8000/docs
```

---

# 20. Docker Setup

Docker provides a reproducible environment containing the application services.

A typical deployment consists of:

```text
┌──────────────────────────┐
│       Frontend            │
│       React/Vite          │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│       Backend             │
│       FastAPI             │
│       ML Engine           │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│       PostgreSQL          │
│       PostgreSQL 15       │
└──────────────────────────┘
```

---

# 21. Build and Start Docker Containers

From the project root:

```bash
docker compose build
```

Then start the services:

```bash
docker compose up
```

To run in detached mode:

```bash
docker compose up -d
```

Check running containers:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs
```

View backend logs:

```bash
docker compose logs backend
```

Stop the services:

```bash
docker compose down
```

---

# 22. PostgreSQL in Docker

The Docker environment uses PostgreSQL 15 instead of the local SQLite database.

Conceptually:

```text
Local Development

FastAPI
   │
   ▼
SQLite
```

while the containerized environment uses:

```text
FastAPI Container
       │
       ▼
PostgreSQL Container
```

The PostgreSQL connection configuration should be defined through the Docker Compose environment variables.

Do not hard-code production database credentials inside application source code.

---

# 23. Useful Development Commands

### Backend

Start backend:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Freeze installed packages:

```bash
pip freeze > requirements.txt
```

### Frontend

Install dependencies:

```bash
npm install
```

Run development server:

```bash
npm run dev
```

Build frontend:

```bash
npm run build
```

Preview production build:

```bash
npm run preview
```

### Docker

Build:

```bash
docker compose build
```

Start:

```bash
docker compose up
```

Start in background:

```bash
docker compose up -d
```

Stop:

```bash
docker compose down
```

View logs:

```bash
docker compose logs -f
```

---

# 24. Troubleshooting

## Backend does not start

Check that the virtual environment is active:

```bash
python --version
```

Then reinstall dependencies:

```bash
pip install -r requirements.txt
```

Try starting Uvicorn manually:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

---

## Frontend cannot connect to backend

Verify that the backend is running:

```text
http://localhost:8000
```

Then verify the frontend configuration points to the correct backend URL.

The expected development configuration is typically:

```text
Frontend → http://localhost:8000
```

---

## Live feed is not updating

Check:

1. Backend is running.
2. Frontend is connected.
3. WebSocket endpoint is correct.
4. Browser console contains no WebSocket errors.
5. The simulation endpoint is successfully processing transactions.

WebSocket endpoint:

```text
ws://localhost:8000/api/v1/analyst/live-feed
```

---

## Model artifacts are missing

Check:

```text
backend/models_store/
```

Verify that the trained model artifacts and scaler exist.

If they do not exist, run the project's training/initialization workflow before attempting live inference.

---

## Incoming pool is missing

Verify that:

```text
backend/models_store/incoming_pool.csv
```

exists.

The live simulation depends on this file.

---

## Database problems

For local SQLite development, check:

```text
backend/fraudsense.db
```

If the application is configured to initialize the database automatically, restarting the backend should recreate the required tables.

For Docker, verify the PostgreSQL container:

```bash
docker compose ps
```

and inspect its logs:

```bash
docker compose logs postgres
```

---

# 25. Development Workflow

A recommended development workflow is:

```text
1. Start Database
       │
       ▼
2. Start FastAPI
       │
       ▼
3. Verify /docs
       │
       ▼
4. Start React Frontend
       │
       ▼
5. Login as Analyst
       │
       ▼
6. Simulate Transaction
       │
       ▼
7. Verify Risk Score
       │
       ▼
8. Inspect SHAP Explanation
       │
       ▼
9. Review Case
       │
       ▼
10. Submit Analyst Decision
       │
       ▼
11. Verify Portfolio Metrics
```

---

# 26. Production Considerations

The local setup is intended for development and demonstration.

Before deploying FraudSense to a production environment, consider implementing:

- Production-grade authentication
- Secure password hashing
- JWT/token security
- HTTPS/TLS
- Secret management
- Database migrations
- PostgreSQL backups
- Redis or another message broker for scalable WebSocket/event processing
- API rate limiting
- Structured logging
- Monitoring and alerting
- Model versioning
- Feature/data drift monitoring
- Automated model evaluation
- Model retraining pipelines
- Comprehensive test coverage

---

# 27. Final Verification Checklist

Before considering the local installation complete, verify:

- [ ] Python environment is working
- [ ] Backend dependencies are installed
- [ ] Dataset is available
- [ ] Training/validation/incoming split is generated
- [ ] `incoming_pool.csv` exists
- [ ] ML model artifacts exist
- [ ] Database initializes successfully
- [ ] FastAPI starts on port `8000`
- [ ] Swagger documentation loads
- [ ] Frontend dependencies are installed
- [ ] React application starts on port `5173`
- [ ] Analyst login works
- [ ] Merchant login works
- [ ] Live transaction simulation works
- [ ] Risk score is generated
- [ ] SHAP explanation is generated
- [ ] Transaction is persisted
- [ ] WebSocket live feed updates
- [ ] Analyst case review works
- [ ] Human feedback is stored
- [ ] Portfolio metrics update
- [ ] Docker Compose deployment works

---

# 28. Application URLs

After starting the application locally:

```text
Frontend
http://localhost:5173

FastAPI
http://localhost:8000

Swagger
http://localhost:8000/docs

WebSocket
ws://localhost:8000/api/v1/analyst/live-feed
```

FraudSense is ready for development once the frontend, backend, ML artifacts, database, and incoming transaction pool are successfully initialized.
