# SystemAssist — AI Log Intelligence Extension

A universal, framework-agnostic micro-service for log intelligence and user interaction analysis. Integrate with **any system** using a single API key. No internal user accounts — your system owns the users, SystemAssist owns the intelligence layer.

---

## Features

- **Extension-style design** — attach to any existing system via API key; no auth migration needed
- **Flexible `user_id`** — pass any identifier (UUID, PK, JWT subject, session token) — SystemAssist stores and queries by whatever your system provides
- **Semantic log search** — FAISS + `all-MiniLM-L6-v2` embeddings for intent-aware retrieval
- **AI-powered chat** — local Llama 3.2 3B answers questions about user activity from log context
- **Session follow-ups** — persist `session_id` across chat calls to maintain conversation context
- **Activity summaries** — structured 5-section summaries with patterns, errors, and recommendations
- **Batch logging** — submit up to 100 log entries in a single request
- **Strict user isolation** — every query is scoped to the provided `user_id`; no cross-user leakage
- **Prompt injection protection** — guardrails block adversarial queries before they reach the model
- **CPU-first** — runs without a GPU; Llama and embeddings both pre-loaded at startup

---

## Quick Start

```bash
cd ai_log_system
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — set MONGODB_URI and API_KEY

# Seed sample data
python -m scripts.seed_data

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Run the full integration test suite
python -m scripts.test_chat
```

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `MONGODB_URI` | MongoDB connection string | `mongodb://localhost:27017` |
| `MONGODB_DB_NAME` | Database name | `ai_log_system` |
| `API_KEY` | Secret key sent by calling systems | `change-me` |
| `LLAMA_MODEL_DIR` | Path to local Llama 3.2 3B weights | *(required)* |
| `EMBEDDING_MODEL` | Sentence-transformer model name | `all-MiniLM-L6-v2` |
| `FAISS_INDEX_PATH` | Path to persist FAISS index | `./data/faiss_index` |
| `SESSION_TTL_HOURS` | Auto-expire idle sessions | `24` |

---

## API Reference

All endpoints require the header:
```
X-Api-Key: <your-api-key>
```

### Logging

#### `POST /api/logs` — Create a log entry
```json
{
  "user_id": "usr_abc123",
  "module": "orders",
  "action": "create_order",
  "entity": "order",
  "category": "CRUD",
  "description": "Customer placed order ORD-5001 for $129.99",
  "metadata": { "order_id": "ORD-5001", "total": 129.99 }
}
```
Response: `{ "status": "ok", "log_id": "<uuid>" }`

#### `POST /api/logs/batch` — Create up to 100 log entries
```json
{
  "logs": [
    { "user_id": "usr_abc123", "module": "auth", "action": "user_login", "category": "AUTH" },
    { "user_id": "usr_abc123", "module": "payments", "action": "charge_failed", "category": "ERROR",
      "metadata": { "reason": "insufficient_funds" } }
  ]
}
```

#### `GET /api/logs?user_id=usr_abc123&limit=50` — Fetch logs for a user

Query params: `user_id` (required), `module`, `category`, `start_date`, `end_date`, `limit`, `skip`

---

### AI Chat

#### `POST /api/chat` — Ask a question about a user's activity
```json
{
  "user_id": "usr_abc123",
  "query": "What errors have I experienced recently?",
  "limit": 10
}
```
Response:
```json
{
  "status": "ok",
  "session_id": "6eec2a0b-...",
  "query": "What errors have I experienced recently?",
  "response": "You experienced 3 errors in the last 7 days: ..."
}
```

#### Follow-up in the same session
Pass `session_id` from the previous response to maintain conversation context:
```json
{
  "user_id": "usr_abc123",
  "query": "Which of those happened in the payments module?",
  "session_id": "6eec2a0b-..."
}
```

---

### Summary

#### `POST /api/summary` — Generate an activity summary
```json
{
  "user_id": "usr_abc123",
  "days": 14,
  "module": "orders"
}
```
Returns a structured analysis covering: Activity Overview, Key Actions, Patterns, Issues, and Recommendations.

---

### Admin

#### `POST /api/reindex` — Rebuild the FAISS semantic search index
Rebuilds from all logs in MongoDB. Call after bulk data imports or index corruption.

#### `GET /health` — Service health check

---

## Log Categories

| Category | When to use |
|---|---|
| `AUTH` | Login, logout, token events |
| `CRUD` | Create, read, update, delete operations |
| `QUERY` | Searches, reports, data reads |
| `API` | External API calls, webhooks |
| `ERROR` | Failures, exceptions, timeouts |
| `SYSTEM` | Background jobs, backups, health checks |

---

## Integration Example

```python
import httpx

BASE = "http://localhost:8000"
HEADERS = {"X-Api-Key": "your-api-key"}

# 1. Log an event from your system
httpx.post(f"{BASE}/api/logs", headers=HEADERS, json={
    "user_id": current_user.id,   # your system's user identifier
    "module": "inventory",
    "action": "update_stock",
    "category": "CRUD",
    "description": f"Stock updated for product {product.id}",
    "metadata": {"product_id": product.id, "old": 50, "new": 45},
})

# 2. Chat: ask about this user's activity
resp = httpx.post(f"{BASE}/api/chat", headers=HEADERS, json={
    "user_id": current_user.id,
    "query": "What did I do with inventory today?",
}, timeout=120)
print(resp.json()["response"])
print("session_id:", resp.json()["session_id"])  # save for follow-ups
```

---

## Architecture

```
ai_log_system/
├── app/
│   ├── main.py                 # FastAPI entry, startup model pre-loading
│   ├── config.py               # Settings & env
│   ├── models/
│   │   ├── log.py              # LogEntry, LogCreateRequest, LogBatchRequest
│   │   └── user.py             # Session, ChatRequest, SummaryRequest
│   ├── services/
│   │   ├── database.py         # Async MongoDB connection & indexes
│   │   ├── log_service.py      # Log CRUD, batch insert, user-scoped queries
│   │   ├── session_service.py  # Chat session create/update/history
│   │   ├── embedding_service.py# FAISS index build, search, incremental add
│   │   └── ai_service.py       # Llama inference, prompt engineering
│   ├── api/
│   │   ├── logs.py             # /api/logs, /api/logs/batch
│   │   └── ai.py               # /api/chat, /api/summary, /api/reindex
│   ├── middleware/logger.py    # HTTP access logging
│   └── security/
│       ├── rbac.py             # API key verification
│       └── guardrails.py       # Prompt injection detection & sanitization
├── scripts/
│   ├── seed_data.py            # Populate sample logs for 3 test users
│   └── test_chat.py            # Full integration test suite
├── data/                       # FAISS index files (auto-created)
├── requirements.txt
└── .env.example
```
