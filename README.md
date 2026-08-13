# FraudSense — Real-Time Transaction Fraud Detection & Risk Monitoring

FraudSense is a full-stack, production-oriented fraud detection platform designed to simulate the internal fraud monitoring systems used by banks, payment processors, and card networks.

The system evaluates credit card transactions in real time, assigns a **0–100 risk score**, explains model decisions using **SHAP**, and automatically triggers appropriate actions such as **hold, review, or block**. It also provides analysts with live transaction monitoring, case management, portfolio analytics, and human-in-the-loop feedback.

---

## 🏗️ System Architecture

FraudSense consists of four major layers:

**Frontend → FastAPI Backend → ML Risk Engine → Database**

The application also uses **WebSockets** to stream newly processed transactions to connected analyst dashboards in real time.

---

## 🤖 Machine Learning Pipeline

### 1. Deterministic Dataset Splitting

The original `creditcard.csv` dataset (~150 MB) is deterministically divided into three subsets while preserving the fraud/non-fraud class distribution:

- **60% — Training Set:** Used exclusively for model training.
- **15% — Validation Set:** Used for model evaluation and parameter validation.
- **25% — Incoming Transaction Pool:** Completely excluded from training and stored at:
  `backend/models_store/incoming_pool.csv`

The incoming pool acts as the sole source of transactions for the application's **live fraud simulation**.

### 2. Feature Engineering & Class Balancing

The dataset contains the PCA-transformed features `V1–V28`, along with `Time` and `Amount`.

- `Time` and `Amount` are standardized using a fitted `StandardScaler`.
- `V1–V28` are already PCA-transformed and approximately standardized.
- **SMOTE** is applied only to the training set to address the severe class imbalance, where fraudulent transactions represent approximately **0.172%** of the dataset.

This prevents information from the validation or incoming pool from leaking into model training.

### 3. Hybrid Fraud Detection Model

FraudSense combines supervised classification with unsupervised anomaly detection.

#### XGBoost — Supervised Detection

The XGBoost classifier learns patterns associated with known fraudulent transactions and produces a probability representing the likelihood of fraud.

#### Isolation Forest — Anomaly Detection

Isolation Forest identifies transactions that deviate significantly from the normal transaction distribution, allowing the system to detect unusual patterns that may not have been explicitly observed during supervised training.

#### Combined Risk Score

The two model outputs are combined into a single risk score:

```text
Risk = 0.8 × XGBoost Score
     + 0.2 × Isolation Forest Score
```

The resulting score is transformed into a **0–100 risk scale**, which is then used to determine the transaction's risk level and recommended action.

### 4. SHAP Explainability

FraudSense uses **SHAP TreeExplainer** to make XGBoost predictions interpretable.

For each transaction, the system identifies the features that contributed most strongly to the model's decision, including:

- `V1–V28`
- `Time`
- `Amount`

These contributions are presented through interactive visualizations so analysts can understand **why a transaction received a particular risk score** rather than relying on a black-box prediction.

---

# 🖥️ Technology Stack

### Frontend

- React 18
- TypeScript
- Vite
- Tailwind CSS
- Lucide React
- Recharts
- React Hook Form
- Zod

### Backend

- Python 3.11
- FastAPI
- REST APIs
- WebSockets
- SQLAlchemy
- SQLite — local development fallback
- PostgreSQL — Docker deployment
- Joblib
- SHAP

### Machine Learning

- XGBoost
- Isolation Forest
- SMOTE
- Scikit-learn
- SHAP
- Pandas / NumPy

### Infrastructure

- Docker
- Docker Compose
- PostgreSQL 15

---

# 🔄 Real-Time Transaction Flow

A typical live transaction follows this flow:

```text
Incoming Transaction
        ↓
FastAPI Backend
        ↓
Feature Preprocessing
        ↓
XGBoost ─────────┐
                 ├──→ Hybrid Risk Engine
Isolation Forest ┘
        ↓
Risk Score (0–100)
        ↓
Risk Classification
        ↓
SHAP Explanation
        ↓
Database
        ↓
WebSocket Broadcast
        ↓
Analyst Dashboard
```

For simulated transactions, the backend randomly selects an unused transaction from the unseen `incoming_pool.csv`, evaluates it, stores the result, and broadcasts the processed transaction to connected analyst dashboards.

---

# ⚡ Live Transaction Simulation

The **Simulation Console** provides a real-time fraud monitoring experience.

When an analyst clicks **Simulate Live Transaction**:

1. The frontend calls the `/simulate-live` endpoint.
2. FastAPI selects an unused transaction from `incoming_pool.csv`.
3. The transaction is preprocessed using the trained scaler.
4. XGBoost and Isolation Forest generate their respective scores.
5. The hybrid risk engine calculates the final risk score.
6. SHAP generates feature-level explanations.
7. The transaction and prediction are persisted in the database.
8. The backend broadcasts the result through WebSockets.
9. All connected analyst dashboards receive the transaction instantly.

This creates a realistic simulation of a continuously running fraud-monitoring system.

---

# 🔍 Explainable Fraud Detection

Every scored transaction can be inspected through its corresponding case.

The case view provides:

- Overall risk score
- Risk classification
- Recommended action
- Model prediction
- Top contributing features
- SHAP contribution values
- Transaction metadata

The SHAP results are displayed as an interactive horizontal bar chart, allowing analysts to quickly identify which features pushed the transaction toward or away from a fraud classification.

---

# 👥 Role-Based Access

FraudSense provides separate experiences for different users.

| User         | Capabilities                                                                                              |
| ------------ | --------------------------------------------------------------------------------------------------------- |
| **Analyst**  | Full fraud dashboard, case review, SHAP explanations, batch uploads, live simulation, portfolio analytics |
| **Merchant** | Own transactions, basic transaction statistics, and simplified Low/Medium/High risk indicators            |

### Seed Credentials

| Role     | Email                      | Password      |
| -------- | -------------------------- | ------------- |
| Analyst  | `analyst1@fraudsense.com`  | `password123` |
| Merchant | `merchant1@fraudsense.com` | `password123` |

---

# 🧑‍💻 Human-in-the-Loop MLOps

FraudSense incorporates analyst feedback into its monitoring workflow.

When an analyst reviews a detected case, they can classify it as:

- **Confirmed Fraud**
- **False Positive**

These decisions are persisted and used to recalculate portfolio-level model performance metrics such as:

- Precision
- Recall
- Fraud detection performance

This creates a simplified **human-in-the-loop MLOps feedback cycle**, where analyst decisions become part of the system's ongoing model evaluation.

---

# 🗄️ Database Architecture

FraudSense supports two database configurations.

### Docker Environment

```text
PostgreSQL 15
localhost:5432
```

Docker Compose automatically starts the PostgreSQL service alongside the backend and frontend.

### Local Development

When Docker/PostgreSQL is unavailable, the backend falls back to:

```text
backend/fraudsense.db
```

using SQLite.

---

# 🚀 Running with Docker Compose

Docker Compose is the recommended way to run the complete application.

First, ensure **Docker Desktop is running**, then execute from the project root:

```bash
docker compose up --build
```

This starts three services:

```text
┌─────────────────────────────┐
│        Frontend             │
│    React + Vite             │
│    localhost:5173           │
└──────────────┬──────────────┘
               │
               ↓
┌─────────────────────────────┐
│        Backend              │
│   FastAPI + ML Pipeline     │
│    localhost:8000           │
└──────────────┬──────────────┘
               │
               ↓
┌─────────────────────────────┐
│        PostgreSQL           │
│    localhost:5432           │
└─────────────────────────────┘
```

On the first backend startup, the application automatically:

1. Creates database tables.
2. Splits the dataset.
3. Trains the ML models.
4. Saves the trained artifacts.
5. Seeds the initial user accounts.
6. Starts the FastAPI server.

---

# 🧪 Running Without Docker

## Backend

```bash
cd backend

pip install -r requirements.txt

python -m app.ml.train_fraud_model

python -m app.seed

python -m uvicorn app.main:app --reload --port 8000
```

The backend will be available at:

```text
http://localhost:8000
```

## Frontend

Open another terminal:

```bash
cd frontend

npm install

npm run dev
```

The frontend will be available at:

```text
http://localhost:5173
```

---

# 🌐 Application Endpoints

| Service                   | URL                          |
| ------------------------- | ---------------------------- |
| Frontend                  | `http://localhost:5173`      |
| FastAPI Backend           | `http://localhost:8000`      |
| Swagger API Documentation | `http://localhost:8000/docs` |
| PostgreSQL                | `localhost:5432`             |

The Swagger interface can be used to explore and test the backend REST API interactively.

---

# ⭐ Key Features

### Real-Time Fraud Detection

Processes transactions and generates risk scores in real time.

### Hybrid ML Detection

Combines supervised fraud classification with unsupervised anomaly detection.

### Explainable AI

Uses SHAP to show analysts why a transaction was considered suspicious.

### WebSocket-Based Monitoring

Pushes newly detected transactions to connected analyst dashboards without requiring continuous polling.

### Automated Risk Actions

Maps transaction risk to actions such as hold, review, or block.

### Role-Based Dashboards

Provides different levels of information and functionality for analysts and merchants.

### Case Management

Allows analysts to investigate and classify suspicious transactions.

### Batch Processing

Supports batch transaction uploads for large-scale evaluation.

### Human-in-the-Loop Feedback

Uses analyst case decisions to update portfolio-level Precision and Recall metrics.

### Dockerized Deployment

Provides a reproducible multi-service environment using Docker Compose.

---

# 📌 Project Architecture at a Glance

```text
                    ┌──────────────────┐
                    │   React Client   │
                    │ React + TS/Vite  │
                    └────────┬─────────┘
                             │
                     REST / WebSocket
                             │
                             ▼
                    ┌──────────────────┐
                    │   FastAPI API    │
                    │ Authentication   │
                    │ Business Logic   │
                    └───────┬──────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
       ┌────────────┐ ┌────────────┐ ┌────────────┐
       │ ML Engine  │ │ PostgreSQL │ │ WebSockets │
       │ XGBoost    │ │ / SQLite   │ │ Live Feed  │
       │ IsoForest  │ └────────────┘ └────────────┘
       │ SHAP       │
       └────────────┘
```

FraudSense therefore combines **machine learning, explainable AI, REST APIs, real-time WebSockets, database persistence, role-based access, and containerized deployment** into a single end-to-end fraud detection platform.
