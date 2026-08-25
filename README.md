# FraudSense — Real-Time Transaction Fraud Detection & Risk Monitoring

FraudSense is a full-stack, production-oriented fraud detection platform that simulates the workflow of fraud monitoring systems used by banks, payment processors, and card networks.

The platform evaluates credit card transactions in real time, assigns a **0–100 risk score**, explains model decisions using **SHAP**, and recommends automated actions such as **Hold, Review, or Block**.

Fraud analysts can monitor transactions through a live dashboard, investigate suspicious cases, inspect model explanations, provide human feedback, and analyze portfolio-level fraud performance.

---

## 🚀 Key Capabilities

- Real-time transaction fraud detection
- Hybrid ML fraud detection using **XGBoost + Isolation Forest**
- 0–100 transaction risk scoring
- SHAP-based explainable AI
- Real-time transaction streaming using WebSockets
- Analyst case management
- Role-based access for Analysts and Merchants
- Live transaction simulation
- Batch transaction processing
- Human-in-the-loop fraud classification
- Portfolio-level Precision and Recall monitoring
- PostgreSQL/SQLite database support
- Dockerized deployment using Docker Compose
- RESTful APIs with FastAPI
- Interactive API documentation through Swagger

---

# 🏗️ System Architecture

FraudSense follows a layered architecture:

```text
┌─────────────────────────────────────┐
│          React Frontend             │
│     React + TypeScript + Vite       │
└──────────────────┬──────────────────┘
                   │
            REST / WebSocket
                   │
                   ▼
┌─────────────────────────────────────┐
│           FastAPI Backend           │
│ Authentication + Business Logic    │
│ API Endpoints + Case Management     │
└───────────────┬───────────┬─────────┘
                │           │
                ▼           ▼
       ┌─────────────┐  ┌─────────────┐
       │  ML Engine  │  │  Database   │
       │             │  │             │
       │ XGBoost     │  │ PostgreSQL  │
       │ Isolation   │  │ / SQLite    │
       │ Forest      │  │             │
       │ SHAP        │  │             │
       └─────────────┘  └─────────────┘
                │
                ▼
       ┌─────────────────┐
       │ WebSocket Live  │
       │ Transaction Feed│
       └─────────────────┘
```

The major components are:

### Frontend

Provides the analyst and merchant interfaces for:

- Live transaction monitoring
- Transaction investigation
- Case management
- SHAP explanations
- Portfolio analytics
- Transaction simulation
- Merchant transaction views

### Backend

The FastAPI backend is responsible for:

- Authentication
- Authorization
- REST APIs
- Transaction processing
- ML inference
- SHAP explanations
- Case management
- Database persistence
- WebSocket communication

### ML Risk Engine

The ML layer combines supervised classification and unsupervised anomaly detection to produce a unified transaction risk score.

### Database

Stores:

- Users
- Transactions
- Model predictions
- Risk scores
- Fraud cases
- Analyst decisions
- Audit information

SQLite is supported for local development, while PostgreSQL is used for the containerized deployment environment.

---

# 🤖 Machine Learning Pipeline

## 1. Dataset

FraudSense uses the widely used credit-card fraud dataset containing transaction information such as:

- `Time`
- `Amount`
- `V1`–`V28`
- `Class`

where:

```text
Class = 0 → Legitimate transaction
Class = 1 → Fraudulent transaction
```

The dataset contains a severe class imbalance, with fraudulent transactions representing approximately **0.172%** of the total dataset.

---

## 2. Deterministic Dataset Splitting

The original dataset is deterministically divided into three subsets:

| Dataset       | Percentage | Purpose                     |
| ------------- | ---------: | --------------------------- |
| Training      |        60% | Model training              |
| Validation    |        15% | Model evaluation            |
| Incoming Pool |        25% | Live transaction simulation |

The incoming pool is completely excluded from model training.

```text
Original Dataset
       │
       ├──────────────► 60% Training
       │
       ├──────────────► 15% Validation
       │
       └──────────────► 25% Incoming Pool
                              │
                              ▼
                       Live Simulation
```

The incoming transaction pool is stored at:

```text
backend/models_store/incoming_pool.csv
```

This ensures that transactions used during live simulation represent unseen data from the perspective of the trained model.

---

# ⚙️ Feature Engineering

The dataset contains PCA-transformed features `V1–V28`, along with `Time` and `Amount`.

### Standardization

`Time` and `Amount` are standardized using a fitted `StandardScaler`.

The scaler is fitted using training data and reused during validation and inference.

This prevents information from the validation or incoming transaction pool from leaking into model training.

### PCA Features

The `V1–V28` features are already PCA-transformed and approximately standardized.

---

# ⚖️ Handling Class Imbalance

Because fraudulent transactions are extremely rare compared with legitimate transactions, directly training a classifier on the original distribution can lead to poor fraud detection performance.

FraudSense uses **SMOTE (Synthetic Minority Oversampling Technique)** on the training data.

```text
Training Data
     │
     ▼
Feature Preprocessing
     │
     ▼
SMOTE
     │
     ▼
Balanced Training Data
     │
     ▼
XGBoost Training
```

Importantly, SMOTE is applied **only to the training set**.

The validation set and incoming transaction pool remain untouched.

---

# 🧠 Hybrid Fraud Detection

FraudSense combines two different approaches to fraud detection.

## XGBoost — Supervised Detection

XGBoost is trained using labeled transaction data.

It learns patterns associated with previously observed fraudulent transactions and produces a fraud probability.

Conceptually:

```text
Transaction Features
        │
        ▼
     XGBoost
        │
        ▼
Fraud Probability
```

This allows the system to detect transactions that resemble known fraud patterns.

---

## Isolation Forest — Anomaly Detection

Isolation Forest provides an unsupervised anomaly-detection component.

Instead of learning specifically from fraud labels, it identifies transactions that are unusual compared with the normal transaction distribution.

```text
Transaction Features
        │
        ▼
Isolation Forest
        │
        ▼
Anomaly Score
```

This complements the supervised XGBoost model by providing an additional signal for unusual transactions.

---

# 📊 Hybrid Risk Score

The outputs of the two models are combined into a unified risk score:

```text
Risk Score =
    0.8 × XGBoost Score
  + 0.2 × Isolation Forest Score
```

The resulting value is mapped to a **0–100 risk scale**.

A higher score indicates greater transaction risk.

The risk score is then used to classify transactions and determine the recommended action.

Conceptually:

```text
                 ┌──────────────┐
                 │  Transaction │
                 └───────┬──────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        ┌───────────┐         ┌──────────────┐
        │  XGBoost  │         │ Isolation    │
        │   80%     │         │ Forest 20%   │
        └─────┬─────┘         └──────┬───────┘
              │                      │
              └──────────┬───────────┘
                         ▼
                 Hybrid Risk Engine
                         │
                         ▼
                  Risk Score 0–100
                         │
                         ▼
                Risk Classification
                         │
                         ▼
                 Recommended Action
```

---

# 🔎 Explainable AI with SHAP

A fraud detection system should not only determine that a transaction is suspicious—it should also help analysts understand **why**.

FraudSense uses **SHAP TreeExplainer** to interpret XGBoost predictions.

For each transaction, SHAP identifies feature contributions from:

- `V1`–`V28`
- `Time`
- `Amount`

A positive SHAP contribution pushes the prediction toward fraud, while a negative contribution pushes it away from fraud.

The case interface presents these contributions using an interactive horizontal bar chart.

Example:

```text
Feature     Contribution

V14         ████████████  +0.42
V10         ████████      +0.31
Amount      █████         +0.19
V4          ███           +0.08
V12         ██            -0.05
```

This allows analysts to move beyond a simple prediction and investigate the factors influencing the model's decision.

---

# 🔄 Transaction Processing Flow

A transaction processed by FraudSense follows this pipeline:

```text
Incoming Transaction
        │
        ▼
   FastAPI Backend
        │
        ▼
Feature Preprocessing
        │
        ├───────────────┐
        ▼               ▼
    XGBoost       Isolation Forest
        │               │
        └───────┬───────┘
                ▼
        Hybrid Risk Engine
                │
                ▼
          Risk Score 0–100
                │
                ▼
        Risk Classification
                │
                ▼
        SHAP Explanation
                │
                ▼
          Database Storage
                │
                ▼
       WebSocket Broadcast
                │
                ▼
       Analyst Dashboard
```

---

# ⚡ Real-Time Transaction Simulation

FraudSense includes a live transaction simulation system.

When an analyst selects **Simulate Live Transaction**, the following process occurs:

1. The frontend sends a request to the backend.
2. FastAPI selects an unused transaction from the incoming transaction pool.
3. The transaction is preprocessed using the trained scaler.
4. XGBoost calculates the supervised fraud score.
5. Isolation Forest calculates the anomaly score.
6. The hybrid risk engine calculates the final risk score.
7. The transaction is assigned a risk classification and recommended action.
8. SHAP generates feature-level explanations.
9. The transaction and prediction are stored in the database.
10. The backend broadcasts the processed transaction through WebSockets.
11. Connected analyst dashboards receive the transaction in real time.

This simulates the behavior of a continuously running fraud monitoring system.

---

# 🌐 REST API + WebSockets

FraudSense uses REST APIs for normal application operations and WebSockets for real-time transaction streaming.

### REST

Used for:

- Authentication
- Transaction processing
- Case management
- Batch uploads
- Analytics
- User operations
- Simulation requests

### WebSockets

Used for:

- Live transaction feed
- Real-time analyst dashboard updates
- Push-based transaction notifications

Live WebSocket endpoint:

```text
ws://localhost:8000/api/v1/analyst/live-feed
```

Unlike traditional polling, WebSockets allow the backend to push newly processed transactions to connected clients immediately.

---

# 👥 Role-Based Access

FraudSense supports two primary user roles.

| Role         | Capabilities                                                                                                        |
| ------------ | ------------------------------------------------------------------------------------------------------------------- |
| **Analyst**  | Full fraud dashboard, case investigation, SHAP explanations, batch processing, live simulation, portfolio analytics |
| **Merchant** | Own transactions, basic transaction statistics, simplified risk indicators                                          |

### Seed Accounts

| Role     | Email                      | Password      |
| -------- | -------------------------- | ------------- |
| Analyst  | `analyst1@fraudsense.com`  | `password123` |
| Merchant | `merchant1@fraudsense.com` | `password123` |

> These credentials are intended for local/demo environments only and should not be used in production.

---

# 🧑‍💻 Human-in-the-Loop MLOps

Fraud detection systems operate in an environment where model predictions may not always be correct.

FraudSense therefore allows analysts to provide feedback after reviewing a case.

An analyst can classify a case as:

- **Confirmed Fraud**
- **False Positive**

These decisions are stored and used to calculate portfolio-level performance metrics such as:

- Precision
- Recall
- Fraud detection performance

The resulting workflow creates a simplified human-in-the-loop MLOps cycle:

```text
ML Prediction
      │
      ▼
Analyst Review
      │
      ├──── Confirmed Fraud
      │
      └──── False Positive
              │
              ▼
        Stored Feedback
              │
              ▼
      Performance Metrics
              │
              ▼
       Model Monitoring
```

This provides a foundation for future model monitoring and retraining workflows.

---

# 📁 Project Structure

A typical project structure is:

```text
FraudSense/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models/
│   │   ├── routes/
│   │   ├── services/
│   │   └── ...
│   │
│   ├── models_store/
│   │   └── incoming_pool.csv
│   │
│   ├── fraudsense.db
│   ├── requirements.txt
│   └── ...
│
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── vite.config.ts
│   └── ...
│
├── docker-compose.yml
├── Dockerfile
├── README.md
└── SETUP.md
```

---

# 🖥️ Technology Stack

## Frontend

- React 18
- TypeScript
- Vite
- Tailwind CSS
- Lucide React
- Recharts
- React Hook Form
- Zod

## Backend

- Python 3.11
- FastAPI
- REST APIs
- WebSockets
- SQLAlchemy
- SQLite
- PostgreSQL
- Joblib
- SHAP

## Machine Learning

- XGBoost
- Isolation Forest
- SMOTE
- Scikit-learn
- SHAP
- Pandas
- NumPy

## Infrastructure

- Docker
- Docker Compose
- PostgreSQL 15

---

# 📡 Application Endpoints

| Service               | Address                                        |
| --------------------- | ---------------------------------------------- |
| Frontend              | `http://localhost:5173`                        |
| FastAPI Backend       | `http://localhost:8000`                        |
| Swagger Documentation | `http://localhost:8000/docs`                   |
| WebSocket Live Feed   | `ws://localhost:8000/api/v1/analyst/live-feed` |

The Swagger interface provides an interactive way to explore and test the available REST APIs.

---

# ⭐ Core Features

### Real-Time Fraud Detection

Processes transactions and generates risk scores with low-latency inference.

### Hybrid Machine Learning

Combines supervised learning through XGBoost with unsupervised anomaly detection through Isolation Forest.

### Explainable AI

Uses SHAP to identify the features contributing to each model prediction.

### Real-Time Monitoring

Uses WebSockets to stream newly processed transactions to analyst dashboards.

### Automated Risk Actions

Maps risk levels to actions such as Hold, Review, or Block.

### Role-Based Dashboards

Provides different experiences for fraud analysts and merchants.

### Case Management

Allows analysts to investigate suspicious transactions and record final decisions.

### Batch Processing

Supports evaluation of multiple transactions.

### Human-in-the-Loop Feedback

Uses analyst decisions to calculate ongoing portfolio-level model performance.

### Containerized Deployment

Provides a reproducible deployment environment using Docker Compose and PostgreSQL.

---

# 🔐 Security Considerations

FraudSense is designed as a production-oriented simulation and should be further hardened before handling real financial data.

Production deployments should additionally implement:

- Strong password hashing
- Secure secret management
- HTTPS/TLS
- Proper JWT/session management
- Database encryption
- Rate limiting
- Input validation
- Audit logging
- Access-control enforcement
- Secure CORS configuration
- Production-grade monitoring

---

# 🚀 Quick Start

For complete installation and configuration instructions, see:

**`SETUP.md`**

For a quick local run:

```bash
# Backend
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

Then open:

```text
Frontend:
http://localhost:5173

Backend:
http://localhost:8000

Swagger:
http://localhost:8000/docs
```

---

# 📌 Project Summary

FraudSense brings together multiple components of a modern ML-powered backend system:

```text
                 FraudSense
                     │
     ┌───────────────┼────────────────┐
     │               │                │
     ▼               ▼                ▼
 Machine Learning   Backend        Frontend
     │               │                │
 XGBoost          FastAPI          React
 IsoForest        REST API         TypeScript
 SHAP             WebSockets       Recharts
 SMOTE            SQLAlchemy       Tailwind
     │               │                │
     └───────────────┼────────────────┘
                     ▼
                Database
             PostgreSQL/SQLite
                     │
                     ▼
              Docker Deployment
```

FraudSense demonstrates an end-to-end architecture combining **machine learning, explainable AI, real-time communication, REST APIs, database persistence, role-based access, human feedback, and containerized deployment** into a single fraud-monitoring platform.
