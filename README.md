# ⚔️ THE VESSEL SYSTEM
### Production-Grade Personal Progression & Capability Architecture
*Inspired by the sovereign progression mechanics of Solo Leveling, forged for real-world human mastery.*

---

## 🏛️ System Overview

The **Vessel System** is an authoritative, persistent backend progression engine that treats human development as a measurable, RPG-style vessel matrix. 

Unlike superficial habit trackers, the Vessel System is governed by the iron law:
> **THE SYSTEM MUST ALWAYS TRAIN THE WEAKEST LINK.**

The system evaluates cognitive capability, physical conditioning, discipline, technical craft, resilience, and adaptability to diagnose the user's primary bottleneck and continuously prescribe targeted progression quests.

```text
                    ┌───────────────────────────┐
                    │          CHATGPT          │
                    │   System Orchestrator     │
                    └─────────────┬─────────────┘
                                  │
                                 MCP (SSE / Streamable HTTP)
                                  │
                    ┌─────────────▼─────────────┐
                    │     VESSEL SYSTEM MCP     │
                    │  FastAPI + MCP 2.x Server │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │       SYSTEM ENGINE       │
                    │  Deterministic XP / Stats │
                    │  Weakest Link / Quests    │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │    FIREBASE ADMIN SDK     │
                    │  (Bypasses client rules)  │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │       FIRESTORE DB        │
                    │  Persistent State Store   │
                    └───────────────────────────┘
```

---

## 🛠️ Tech Stack & Requirements

- **Runtime:** Python 3.11+
- **Protocol:** Model Context Protocol (MCP Python SDK 2.x)
- **Web / ASGI Layer:** FastAPI, Starlette, Uvicorn
- **Data Validation:** Pydantic v2
- **Persistent Database:** Google Cloud Firestore via Firebase Admin SDK
- **Testing:** Pytest & Pytest-AsyncIO

---

## 📂 Repository Structure

```text
vessel-system/
├── vessel_system/
│   ├── __init__.py           # Package marker
│   ├── models.py             # Pydantic schemas (PlayerState, Stats, Quest, Rank, etc.)
│   ├── progression.py        # Deterministic non-linear XP curve & rank algorithms
│   ├── weakest_link.py       # Multi-factor bottleneck diagnosis engine
│   ├── quest_engine.py       # Safe, realistic quest & boss challenge generator
│   ├── firebase.py           # Lazy, safe Firebase initialization with newline unescaping
│   ├── repository.py         # Persistent Firestore repository with in-memory test fallback
│   ├── events.py             # Immutable system event factory
│   ├── auth.py               # Bearer token verification & constant-time security
│   ├── engine.py             # Authoritative state orchestrator (idempotent completion)
│   ├── service.py            # High-level business logic service layer
│   └── server.py             # MCP tools registration and FastAPI ASGI server
├── api/
│   └── index.py              # Serverless entry point for Vercel / Cloud Functions
├── tests/
│   ├── test_auth.py          # Bearer auth verification tests
│   ├── test_engine.py        # Player initialization, quest completion & failure tests
│   ├── test_progression.py   # Non-linear XP math & rank threshold tests
│   ├── test_repository.py    # Activity logging & event audit trail tests
│   └── test_weakest_link.py  # Bottleneck detection & failure adaptation tests
├── firestore.rules           # Security rules denying direct client access (Admin SDK only)
├── firestore.indexes.json    # Firestore composite index definitions
├── requirements.txt          # Production dependencies
├── pyproject.toml            # Build metadata & pytest configuration
├── vercel.json               # Vercel deployment configuration
├── .env.example              # Environment variables template
├── .gitignore                # Security-hardened Git ignore rules
├── SYSTEM_PROMPT.md          # ChatGPT System prompt & response formatting guide
└── README.md                 # Complete documentation & operational manual
```

---

## 🚀 Quickstart & Local Setup

### 1. Clone & Install Dependencies
```bash
# Clone the repository
cd "Solo Levelling"

# Install packages
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Set the values in `.env`:
```env
FIREBASE_PROJECT_ID=vessel-system-5fff1
FIREBASE_CLIENT_EMAIL=your-service-account@vessel-system-5fff1.iam.gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"

# MCP Bearer Token (Secure random token)
VESSEL_MCP_AUTH_TOKEN=your-random-token-here

PORT=8000
HOST=0.0.0.0
```

> **Note on Local Development without Firebase:**  
> If Firebase credentials are not provided, the server gracefully activates its built-in `InMemoryRepository` mock so you can develop and run tests locally immediately.

### 3. Run Automated Tests
```bash
python -m pytest -v
```
All 12 test suites (progression, idempotency, streak resets, auth, weakest-link analyzer) will execute.

### 4. Start the MCP Server Locally
```bash
python -m vessel_system.server
# or
uvicorn vessel_system.server:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🛡️ Firebase & Firestore Setup Guide

1. Log in to the [Firebase Console](https://console.firebase.google.com/) with project:
   ```text
   vessel-system-5fff1
   ```
2. Navigate to **Firestore Database** and ensure Firestore is created in Production mode.
3. Apply the security rules from `firestore.rules`:
   ```bash
   firebase deploy --only firestore:rules
   ```
   *(All direct client reads/writes are denied because the backend uses Firebase Admin SDK).*
4. Navigate to **Project Settings** ➔ **Service accounts** ➔ **Generate new private key**.
5. Copy the `client_email` and `private_key` into your production environment variables (`FIREBASE_CLIENT_EMAIL` and `FIREBASE_PRIVATE_KEY`).

---

## 🌐 Production Deployment

### Option A: Render / Railway / Cloud Run (Recommended for MCP Long-lived Connections)
1. Push this repository to your Git provider (GitHub / GitLab).
2. Create a new **Web Service** pointing to the repository.
3. Configure:
   - **Environment:** Python 3.11+
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn vessel_system.server:app --host 0.0.0.0 --port $PORT`
4. In the service's **Environment Variables**, configure:
   - `FIREBASE_PROJECT_ID=vessel-system-5fff1`
   - `FIREBASE_CLIENT_EMAIL=<your-service-account-email>`
   - `FIREBASE_PRIVATE_KEY=<your-unescaped-private-key>`
   - `VESSEL_MCP_AUTH_TOKEN=<your-secret-token>`

### Option B: Vercel (Serverless ASGI)
1. Import the repository into Vercel.
2. Vercel automatically detects `vercel.json` and routes to `api/index.py`.
3. In Vercel Project Settings ➔ **Environment Variables**, set:
   - `FIREBASE_PROJECT_ID`
   - `FIREBASE_CLIENT_EMAIL`
   - `FIREBASE_PRIVATE_KEY`
   - `VESSEL_MCP_AUTH_TOKEN`
4. Deploy.

---

## 🔌 Connecting to ChatGPT / Custom GPTs

1. In ChatGPT Custom GPT Editor or Developer Actions:
2. Add Action / MCP Server Endpoint:
   - **Endpoint URL:** `https://your-service.onrender.com/sse` (or `/mcp`)
   - **Authentication:** Bearer Token
   - **Token:** The exact token configured in `VESSEL_MCP_AUTH_TOKEN`.
3. Set the GPT Instructions to the contents of `SYSTEM_PROMPT.md`.
4. Test with:
   ```text
   System, initialize.
   ```
   ChatGPT will call `get_player_state` and output the sovereign Vessel HUD!
