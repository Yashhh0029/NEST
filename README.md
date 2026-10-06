<div align="center">

# NEST
### *Find Your People. Find Your Place.*

**AI-powered community intelligence and hyper-local matching platform connecting newcomers with verified local helpers based on context, semantics, and geographic proximity.**

<br />

[![Live Demo](https://img.shields.io/badge/Demo-nest--seven--silk.vercel.app-0D9488?style=for-the-badge&logo=vercel&logoColor=white)](https://nest-seven-silk.vercel.app)
[![API Status](https://img.shields.io/badge/API-Render%20Production-46E3B7?style=for-the-badge&logo=render&logoColor=black)](https://nest-backend-re88.onrender.com/api/health)
[![API Docs](https://img.shields.io/badge/Docs-Swagger%20OpenAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://nest-backend-re88.onrender.com/docs)
[![GitHub](https://img.shields.io/badge/GitHub-Yashhh0029%2FNEST-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Yashhh0029/NEST)

<br />

```
   Need          Understand        Find Local Help        Match           Connect          Chat           Assist          Resolve
 ┌──────┐       ┌───────────┐       ┌─────────────┐     ┌───────┐       ┌─────────┐      ┌──────┐       ┌────────┐       ┌─────────┐
 │ Need │ ────> │ Analyze   │ ────> │ Geographic  │ ──> │ Multi │ ────> │ Mutual  │ ───> │ Real │ ───> │ Safe   │ ────> │ Problem │
 │ Post │       │ Semantics │       │ Proximity   │     │ Radar │       │ Consent │      │ Time │       │ Action │       │ Solved  │
 └──────┘       └───────────┘       └─────────────┘     └───────┘       └─────────┘      └──────┘       └────────┘       └─────────┘
```

<br />

| Metric | Status | Verification |
| :--- | :--- | :--- |
| **Backend Test Suite** | `260 / 260 Passing` | Complete Pytest suite across auth, location, matching, chat & safety |
| **Frontend Test Suite** | `111 / 111 Passing` | Complete Vitest suite across 17 component and page modules |
| **Type Integrity** | `0 Errors` | Strict TypeScript compiler check (`tsc --noEmit`) |
| **Production Build** | `Clean (0 Errors)` | Vite + Rolldown production bundle optimization |
| **Production Stack** | `Live & Healthy` | Vercel (Frontend) + Render (FastAPI) + Neon (PostgreSQL 16) |

</div>

---

## 🧭 The Problem & Philosophy

### The Relocation Dilemma
Moving to a new city is overwhelming. Newcomers face high-friction challenges:
- Securing rental housing without predatory broker practices
- Navigating local transport networks, auto routes, and commute corridors
- Finding reliable domestic help, medical facilities, and administrative services
- Overcoming language barriers and cultural isolation

Existing platforms act as either **commercial directories** (yelp-style listings full of ads) or **generic social networks** (where requests get buried in endless feeds).

### The NEST Differentiator

<div align="center">

> ### **"The need first. The person second."**

</div>

```
Traditional Social Networks:   Browse People  ──>  Filter Profiles  ──>  Reach Out Cold  ──>  Uncertain Outcome
NEST Problem Resolution:      Post Need      ──>  AI Understands   ──>  Vector Match   ──>  Targeted Connect  ──>  Resolution
```

NEST inverts the discovery paradigm. Rather than forcing newcomers to scroll through hundreds of user profiles, users simply express what they need in plain English. NEST extracts semantic intent, isolates geographic targets, runs dense vector similarity matching in PostgreSQL, and pairs them directly with experienced, verified local residents.

---

## 🔄 Complete Lifecycle Architecture

NEST models real-world community assistance through an explicit, deterministic state machine:

```
                  ┌──────────────────────────────────────────────┐
                  │                 UNRESOLVED                   │
                  │   Request created; semantic vectors indexed  │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │                 EXPLORING                    │
                  │  AI radar matching active; helpers evaluated │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │                 CONNECTED                    │
                  │ Connection accepted; real-time chat unlocked │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │            RESOLUTION_PENDING                │
                  │ Assistance session held; outcome review sent │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │                  RESOLVED                    │
                  │     Mutually certified; reputation updated   │
                  └──────────────────────────────────────────────┘
```

---

## ⚡ Core Platform Capabilities

### 🤖 1. AI & Semantic Intelligence
- **Natural Language Parsing**: Extracts core needs, target neighborhoods, budget constraints, currency indicators, and urgency levels from conversational input.
- **Dense Vector Embeddings**: Embeds user capabilities, community background, and newcomer requests into 384-dimensional dense vectors using `sentence-transformers` (`all-MiniLM-L6-v2`) locally on CPU without third-party API dependencies.
- **Native pgvector Cosine Search**: Indexes embeddings directly in PostgreSQL using `pgvector` for fast cosine similarity nearest-neighbor lookup.

### 📍 2. Location Intelligence & Geographic Isolation
- **Device vs. Target Location Decoupling**: A user's physical browser coordinates (`navigator.geolocation`) are strictly decoupled from the relocation request's destination:
  ```
  CURRENT_LOCATION (Physical device in Pune)
         │
         ├────────────────────────┐
         │                        │
         ▼                        ▼
  TARGET_LOCATION           REQUEST_LOCATION (Relocating to Whitefield, Bengaluru)
                                  │
                                  ▼
                           Matching Engine (20 km Boundary)
                                  ▲
                                  │
                           HELPER_LOCATION (Verified resident in Whitefield)
  ```
- **Reverse Geocoding Without POI Distortion**: GPS coordinate resolution filters out commercial establishments (shops, restaurants, transit hubs) to prevent saving an arbitrary business as a user's home locality.
- **Duplicate Name Disambiguation**: Location autocomplete identifies and presents distinguishing administrative parent regions (e.g. *Whitefield, Bengaluru, Karnataka* vs. other homonymous localities).
- **Privacy Masking**: Candidate helpers' exact street numbers and coordinates are masked to ~1.1 km privacy zones.

### 🤝 3. Multi-Dimensional Hybrid Matching Engine
Matches are scored via a multi-factor normalized algorithm:

$$\text{Final Score} = 0.40 \times S_{\text{semantic}} + 0.25 \times S_{\text{location}} + 0.15 \times S_{\text{experience}} + 0.10 \times S_{\text{reputation}} + 0.10 \times S_{\text{availability}}$$

| Dimension | Weight | Metric Evaluated |
| :--- | :---: | :--- |
| **Semantic Compatibility** | **40%** | Cosine similarity between request vector and helper profile/skills |
| **Geographic Proximity** | **25%** | Haversine distance with exponential decay within 20 km canonical boundary |
| **Experience & Tenure** | **15%** | Verified months residing in local area + domain skill badges |
| **Reputation & Reviews** | **10%** | Average score from completed interactions with Wilson score dampening |
| **Active Availability** | **10%** | Slot availability and responsive assistance status |

### 💬 4. Real-Time Communication & Reactivation
- **Dual WebSocket & REST Architecture**: Low-latency bidirectional WebSocket connection with automatic exponential-backoff fallback to REST polling when network conditions degrade.
- **In-Chat Translation**: Powered by automatic source language detection, translating messages across 11 regional and international languages.
- **Message Editing & Soft-Delete**: Participants can edit messages or soft-delete content while preserving audit records.
- **Safe Conversation Reactivation**: If either participant completes an interaction, the conversation can be reactivated without creating duplicate connections, losing messages, or resetting reputation scores.

### 🛡️ 5. Safety, Trust & Moderation
- **Bidirectional Blocking**: Instant block enforcement preventing message exchange, connection attempts, and recommendation visibility.
- **Structured Reporting**: In-app reporting for harassment, scam, spam, or safety concerns with direct link to messages or connections.
- **Precedence Over Reactivation**: Suspended accounts, blocked relationships, and connections under active moderation review are strictly barred from conversation reactivation (HTTP 403 Forbidden).

### ⚡ 6. Smart Auto-Refresh Coordinator
- Centralized frontend synchronization coordinator managing request feeds, notifications, and connections.
- Suspends background polling when the browser tab is hidden to conserve device resources and bandwidth.
- Automatically triggers optimistic re-fetching when tabs regain focus or device recovers from an offline state.

---

## 🏛️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER (Vercel)                            │
│  React 19 • TypeScript • Vite • Tailwind CSS • Framer Motion • Lucide   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     │ HTTPS / WSS
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        API LAYER (Render)                               │
│            FastAPI (Python 3.14) • Pydantic v2 • Starlette              │
│                                                                         │
│   ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐   │
│   │   Auth & OAuth    │  │ Matching Engine   │  │ WebSocket Gateway │   │
│   │   (JWT / bcrypt)  │  │ (Hybrid Scorer)   │  │ (Real-Time Chat)  │   │
│   └───────────────────┘  └───────────────────┘  └───────────────────┘   │
│   ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐   │
│   │ NLP Understanding │  │ Location Service  │  │ Safety & Reports  │   │
│   │ (MiniLM Embedder) │  │ (Google Maps API) │  │ (Audit & Blocks)  │   │
│   └───────────────────┘  └───────────────────┘  └───────────────────┘   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     │ SQLAlchemy ORM
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     DATABASE LAYER (Neon Serverless)                    │
│                        PostgreSQL 16 + pgvector                         │
│                                                                         │
│   ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐   │
│   │ Users & Profiles  │  │ Requests & Locs   │  │ Connections/Chats │   │
│   └───────────────────┘  └───────────────────┘  └───────────────────┘   │
│   ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐   │
│   │  384-d Embeddings │  │ Reviews & Scores  │  │ Moderation Logs   │   │
│   │  (HNSW Indexing)  │  │ (Wilson Ratings)  │  │ (Safety Records)  │   │
│   └───────────────────┘  └───────────────────┘  └───────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Complete Tech Stack

| Domain | Technology | Purpose in NEST |
| :--- | :--- | :--- |
| **Frontend Framework** | **React 19** | Dynamic reactive component architecture |
| **Language** | **TypeScript 5.9** | Strict type safety and interface contracts |
| **Build Tooling** | **Vite + Rolldown** | Fast HMR and production bundle optimization |
| **Styling** | **Tailwind CSS 3.4** | Design system with light/dark theme support |
| **State Management** | **Zustand** | Global authentication, theme, and session stores |
| **Icons & Motion** | **Lucide React + Framer Motion** | Accessible UI primitives and transitions |
| **Backend Framework** | **FastAPI** | High-performance asynchronous Python REST & WebSocket API |
| **Language** | **Python 3.12 / 3.14** | Core business logic and data processing |
| **Database** | **PostgreSQL 16** | ACID-compliant relational persistence |
| **Vector Engine** | **pgvector** | High-dimensional vector storage and cosine similarity search |
| **ORM & Migrations** | **SQLAlchemy 2.0 + Alembic** | Schema migrations and object-relational mapping |
| **AI / NLP** | **sentence-transformers (`all-MiniLM-L6-v2`)** | 384-dimensional dense semantic embedding generation |
| **Maps & Geo** | **Google Maps Platform** | Places API (New), Geocoding, Routes API distance computation |
| **Authentication** | **OAuth 2.0 + JWT + bcrypt** | Google Sign-In and secure password hashing |
| **Email Service** | **Resend** | Transactional verification and notification emails |
| **Deployment** | **Vercel + Render** | Global edge CDN frontend + Containerized cloud backend |

---

## 📂 Repository Layout

```text
NEST/
├── backend/
│   ├── alembic/                      # Database schema migration scripts
│   ├── app/
│   │   ├── api/                      # FastAPI endpoint routers
│   │   │   ├── auth.py               # Authentication and registration
│   │   │   ├── chat.py               # REST conversation endpoints
│   │   │   ├── ws_chat.py            # WebSocket real-time messaging gateway
│   │   │   ├── connections.py        # Connection lifecycle and reactivation
│   │   │   ├── location.py           # Geocoding and Places API endpoints
│   │   │   ├── matching.py           # Candidate discovery and match radar
│   │   │   ├── requests.py           # Newcomer request management
│   │   │   ├── reviews.py            # Reputation and rating submissions
│   │   │   ├── safety.py             # User blocking and safety reporting
│   │   │   └── sessions.py           # In-person and remote assistance booking
│   │   ├── core/                     # Configuration, JWT security, dependencies
│   │   ├── db/                       # Database engine and base declarations
│   │   ├── models/                   # SQLAlchemy relational data models
│   │   ├── schemas/                  # Pydantic v2 validation contracts
│   │   └── services/                 # Business logic and domain services
│   │       ├── chat_service.py       # Message persistence and verification
│   │       ├── connection_service.py # Connection state machine logic
│   │       ├── embedding_service.py  # Local sentence-transformers pipeline
│   │       ├── google_maps.py        # Places and Routes API integration
│   │       ├── matching_service.py   # Hybrid multi-factor scoring engine
│   │       ├── nlp_service.py        # Entity and intent extraction
│   │       └── safety_service.py     # Blocks, audit logs, and safety checks
│   ├── tests/                        # 260 automated Pytest test suites
│   ├── Dockerfile                    # Containerization specification
│   └── requirements.txt              # Production Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── components/               # Modular UI components
│   │   │   ├── common/               # Modals, status badges, refresh controls
│   │   │   ├── location/             # Google Maps picker and autocomplete
│   │   │   ├── match/                # Helper cards and radar visualizations
│   │   │   ├── review/               # Rating modals and feedback forms
│   │   │   ├── safety/               # Block and report modals
│   │   │   └── ui/                   # Buttons, cards, badges, inputs
│   │   ├── hooks/                    # WebSocket, debounce, toast hooks
│   │   ├── pages/                    # Application page views
│   │   │   ├── ChatPage.tsx          # Real-time chat & reactivation view
│   │   │   ├── ConnectionsPage.tsx   # Incoming, sent, and active connections
│   │   │   ├── HomePage.tsx          # Newcomer dashboard and request feed
│   │   │   ├── ResultsPage.tsx       # Helper match recommendations
│   │   │   └── SessionsPage.tsx      # Assistance session scheduler
│   │   ├── services/                 # Axios clients and auto-refresh coordinator
│   │   ├── store/                    # Zustand auth and theme state stores
│   │   ├── test/                     # 111 automated Vitest unit & integration tests
│   │   └── types/                    # Strict TypeScript type definitions
│   ├── package.json
│   ├── vite.config.ts
│   └── vitest.config.ts
│
├── docker-compose.yml                # Local multi-container orchestration
├── render.yaml                       # Render cloud deployment blueprint
└── README.md                         # Project documentation
```

---

## 🧪 Verified Test & Quality Suite

The platform is backed by extensive automated test suites with complete test isolation:

```text
========================================================================================
                               VERIFIED TEST SUITE SUMMARY
========================================================================================
  Backend Pytest Suite:       260 / 260 PASSED  (100%)
  Frontend Vitest Suite:      111 / 111 PASSED  (100%)
  TypeScript Verification:    0 ERRORS          (tsc --noEmit)
  Production Build:           SUCCESSFUL        (vite build)
  Database Integrity:         ISOLATED          (Dedicated test schema)
========================================================================================
```

### Running Backend Tests
```bash
# Uses isolated PostgreSQL instance with pgvector
export TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5433/nest_test"
cd backend
python -m pytest -v
```

### Running Frontend Tests
```bash
cd frontend
npm run test
```

### Type Checking & Build Verification
```bash
cd frontend
npm run typecheck
npm run build
```

---

## 🚀 Live Production Deployments

| Component | Platform | URL | Health Check |
| :--- | :--- | :--- | :--- |
| **Frontend Application** | **Vercel** | [nest-seven-silk.vercel.app](https://nest-seven-silk.vercel.app) | `HTTP 200 OK` |
| **Backend REST & WS** | **Render** | [nest-backend-re88.onrender.com](https://nest-backend-re88.onrender.com) | [`/api/health`](https://nest-backend-re88.onrender.com/api/health) |
| **Interactive API Docs** | **Render** | [Swagger UI](https://nest-backend-re88.onrender.com/docs) | [`/docs`](https://nest-backend-re88.onrender.com/docs) |
| **Source Repository** | **GitHub** | [Yashhh0029/NEST](https://github.com/Yashhh0029/NEST) | `main branch` |

---

## 🔒 Security & Data Privacy Principles

- **No Plaintext Passwords**: Cryptographic hashing via `bcrypt` with automatic per-user salt generation.
- **Signed Session Tokens**: Stateless authentication using signed JWT access tokens with strict expiration windows.
- **Strict CORS Isolation**: Cross-Origin Resource Sharing is strictly constrained to authorized client origins.
- **Zero API Key Leakage**: Third-party keys (Google Maps Platform, Resend) are managed securely via environment secrets; client-side keys are restricted by HTTP referrer in Google Cloud Console.
- **Candidate Privacy Protection**: Candidate helpers' exact street addresses and GPS points are never exposed; coordinates are mapped to approximate ~1.1 km area zones.
- **Data Integrity Guarantee**: Production database transactions follow ACID compliance without synthetic or dummy data pollution.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
