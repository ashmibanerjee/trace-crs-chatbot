---
title: Sustainable Tourism CRS Chatbot
emoji: 🌍
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# 🌍 Sustainable Tourism CRS Chatbot

A modular Conversational Recommender System (CRS) for sustainable European city tourism, featuring interactive sustainability nudging via counterfactual explanations.

## 📄 Paper

> **TRACE: A Transparent and Reproducible Evaluation Framework for Conversational Recommender Systems in Sustainable Tourism**  
> Ashmi Banerjee, Miroslav Kindl, Sebastian Eilert, Wolfgang Wörndl  
> *Proceedings of the 49th International ACM SIGIR Conference on Research and Development in Information Retrieval (SIGIR 2026)*  
> [arxiv.org/abs/2604.14223](https://arxiv.org/abs/2604.14223)

If you use this work, please cite:
```bibtex
@inproceedings{banerjee2026trace,
  title     = {TRACE: A Transparent and Reproducible Evaluation Framework for
               Conversational Recommender Systems in Sustainable Tourism},
  author    = {Banerjee, Ashmi and Kindl, Miroslav and Eilert, Sebastian and W\"{o}rndl, Wolfgang},
  booktitle = {Proceedings of the 49th International ACM SIGIR Conference on
               Research and Development in Information Retrieval},
  series    = {SIGIR '26},
  year      = {2026},
  publisher = {ACM},
  url       = {https://arxiv.org/abs/2604.14223}
}
```

---

## 📋 Overview

This project implements a three-layer architecture for a sustainable tourism chatbot:

```
┌─────────────────────────────────────┐
│  Frontend (Chainlit UI)             │  ← User interaction layer
│  - Chat interface                   │
│  - Profile selector (Gemma / Gemini)│
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
│  - Clarification Question Generator │
│  - Intent Classifier Agent          │
│  - Recommendation Agent             │
│  - Counterfactual Explanation (CFE) │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Storage                            │  ← Data persistence layer
│  - Sessions (active chats)          │
│  - Conversations (HF Dataset repo)  │
└─────────────────────────────────────┘
```

---

## 🤖 Model Profiles

Two profiles are available at the start of each session:

| Profile | Model | Key required? |
|---|---|---|
| **Gemma (Free)** | `google/gemma-3-27b-it` via 🤗 HF Serverless Inference API | No |
| **Gemini (Your Key)** | `gemini-2.5-flash` via Google AI Studio | Yes (free tier available) |

The Gemma profile is recommended for the demo — no sign-up needed.
The Gemini profile uses Google ADK multi-agent pipeline (CQ Generator → Intent Classifier → RecSys → CFE agents running in parallel/sequence).

---

## ⚠️ Deployment History & Security Note

The original production backend was deployed on **Google Cloud Run** and used **Chainlit 2.3.0** as the frontend server.
After a security vulnerability was disclosed in Chainlit 2.3.0 (dependency-level CVE), that Cloud Run deployment was **taken offline**.

This HF Spaces version was built as a replacement demo:
- Chainlit is pinned to **2.11.1** (patched)
- The full ADK multi-agent pipeline is preserved for the Gemini profile
- A lighter Gemma pipeline handles the free tier without requiring a Google account
- Firestore is **disabled by default** (`USE_FIRESTORE=false`); conversations are stored in a private HF Dataset repo instead
- API routes are prefixed at `/api/` and Chainlit is mounted at `/` (no redirect chain)

---

## 🏗️ Architecture Details

### Gemma pipeline (free tier)
Direct structured LLM calls to `google/gemma-3-27b-it`:
1. **Clarifying Question Generator** — extracts up to 3 questions from the user query
2. **Answer collection** — user responds conversationally
3. **Full pipeline** — IC + RecSys + CFE run sequentially, results formatted and displayed

### Gemini pipeline (ADK)
Google Agent Development Kit multi-agent graph:
1. `cq_generator` agent → clarifying questions
2. `intent_classification` agent → travel persona + query anchors
3. `recsys` agent (parallel) → top-k city recommendations
4. `cfe` agent → counterfactual sustainable-alternative explanation

### Storage
- **Sessions**: in-memory (per process)
- **Conversations**: HF Dataset repo `ashmib/trace-conversations` (private), uploaded asynchronously via daemon thread; falls back to in-memory if HF credentials are absent

---

## 🧩 Prerequisites

- Python ≥ 3.10
- Docker ≥ 24.x (for containerised setup)
- `pip` / `virtualenv`

For the **Gemini** profile locally:
- A Google AI Studio API key (free tier at [aistudio.google.com](https://aistudio.google.com/apikey))

For **Firestore** persistence (optional, disabled by default):
- GCP project with Firestore (Native mode) enabled
- Service account JSON key with `Cloud Datastore User` role
- Set `USE_FIRESTORE=true` in your environment

---

## 🚀 Running Locally

### Without Docker

```bash
# Install dependencies
pip install -r requirements.txt

# Set HF token for Gemma (free) profile
export HF_TOKEN=hf_...

# Optional: point to a private HF dataset for conversation storage
export HF_DATASET_REPO=your-username/your-dataset-repo

# Start the app (FastAPI + Chainlit on same process)
python -m backend.server.api
# or
uvicorn backend.server.api:app --host 0.0.0.0 --port 8001
```

The chatbot will be available at `http://localhost:8001`.

### With Docker

```bash
docker build -t crs-chatbot -f Dockerfile .

docker run -p 7860:7860 \
  -e HF_TOKEN=hf_... \
  -e HF_DATASET_REPO=your-username/your-dataset-repo \
  crs-chatbot
```

### Health check

```bash
curl http://localhost:7860/api/health
```

---

## 🔐 Security

- The Gemini API key is held **only in server-side session memory** (`cl.user_session`) for the duration of the chat — it is never written to disk, logged, or stored in any database.
- No credentials are committed to this repository.
- `USE_FIRESTORE` defaults to `false`; set it to `true` only when a valid service account is available.
