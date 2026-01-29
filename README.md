# 🌍 Sustainable Tourism CRS Chatbot

A modular Conversational Recommender System (CRS) for sustainable tourism, built with Chainlit (frontend), Google Agent Development Kit (ADK) (backend) and Firebase Firestore (storage) to to promote sustainable tourism
practices through interactive nudging.
It uses `gemini-2.5-flash` in the backend as the LLM agent.
## 📋 Overview

This project implements a three-layer architecture for a tourism chatbot with Firestore backend:

```
┌─────────────────────────────────────┐
│  Frontend (Chainlit UI)             │  ← User interaction layer
│  - Chat interface                   │
│  - Rich messages & actions          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Orchestrator (Middleware)          │  ← Business logic layer
│  - Session management               │
│  - Automatic conversation saving    │
│  - Response formatting              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Backend (Agent System)             │  ← AI agent layer           
│  - Clarification Agent              │
│  - Intent Classifier Agent          │      
│  - Recommendation Agent             │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Firestore Database                 │  ← Data persistence layer
│  - Sessions (active chats)          │
│  - Conversations (training data)    │
└─────────────────────────────────────┘
```
## 🧩 Prerequisites

Before running the application, ensure the following requirements are met.

### System requirements
- **Python ≥ 3.10**
- **Docker ≥ 24.x** (required for containerized setup)
- **pip / virtualenv**
- **Google Cloud SDK (`gcloud`)** (recommended for managing credentials)

---

### Google Cloud Platform (GCP)
The application uses **Google Firestore** to persist all chatbot conversations.

#### Required GCP setup
1. A **GCP project** with:
   - Firestore enabled (Native mode)
   - Billing enabled
2. A **Service Account** with at least one of the following roles:
   - `Cloud Datastore User`
   - `Firestore Admin` (recommended for development)

---

### Service account credentials
Authentication is handled via a **GCP service account JSON key**.

1. Download the service account key as a JSON file  
   (e.g. `crs-chatbot-application-secret.json`)
2. Store the file **outside of version control**
3. Ensure the file is **never committed** to Git

## 🚀 Running the application

#### Local (non-Docker) setup
Export the credentials path:
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/crs-chatbot-application-secret.json

**Start the Chainlit server:**
```bash
source venv/bin/activate
chainlit run app.py -w
```

**Production mode:**
```bash
chainlit run app.py
```

The chatbot will be available at `http://localhost:8000`

**All conversations are automatically saved to Firestore!**

`docker build -t crs-backend:test -f backend/Dockerfile .`

#### Run locally (using Docker: recommended)
```bash
docker run -p 8080:8080 \
  -e PORT=8080 \
  -v $(pwd)/crs-chatbot-application-secret.json:/app/crs-chatbot-application-secret.json \
  crs-backend:test
```
#### Test the health endpoint
```bash
curl http://localhost:8080/health
```
