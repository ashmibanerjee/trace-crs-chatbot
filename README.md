# 🌍 Sustainable Tourism CRS Chatbot

A modular Conversational Recommender System (CRS) for sustainable tourism, built with Chainlit and Firebase Firestore, featuring automatic conversation storage for model training.

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
│  - Coordinator Agent                │
│  - Clarification Agent              │
│  - Intent Agent                     │
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

### Running the Application

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

docker build -t crs-backend:test -f backend/Dockerfile .

# Run locally
docker run -p 8080:8080 \
  -e PORT=8080 \
  -v $(pwd)/crs-chatbot-application-secret.json:/app/crs-chatbot-application-secret.json \
  crs-backend:test

# Test the health endpoint
curl http://localhost:8080/health
```