# NEST — Find Your People. Find Your Place.

NEST is an AI-powered local community problem-solving platform designed to help newcomers settle into new Indian cities by matching them with verified, experienced local helpers. Rather than being a generic chatbot, NEST understands unstructured natural-language requests, isolates relocation targets, computes dense vector embeddings locally, and executes a multi-dimensional hybrid matching algorithm backed by PostgreSQL and pgvector.

---

## Key Features

- **Natural Language Requirement Extraction**: Parses complex newcomer relocation requests into structured requirements (target city, neighborhood, needs, budget, currency, and lifestyle preferences) using deterministic local NLP.
- **Local Semantic Vector Embeddings**: Converts user profiles, skills, and newcomer requests into 384-dimensional dense vector embeddings using `sentence-transformers` (`all-MiniLM-L6-v2`) with zero external LLM API dependency.
- **Native pgvector Cosine Search**: Persists dense vector representations in PostgreSQL using the `pgvector` extension for sub-millisecond semantic indexing.
- **Hybrid Matching Engine**: Scores candidate helpers across multiple mathematically normalized dimensions:
  - **Semantic Similarity** (40%): Cosine alignment between request needs and candidate backgrounds.
  - **Location Compatibility** (25%): Haversine baseline distance and exponential decay scoring.
  - **Experience & Skills** (15%): Local community tenure and tagged skill proficiencies.
  - **Reputation & Availability** (10% each): Tracked transparently with explicit active/unavailable indicators.
- **India-Wide Location Intelligence (Google Maps Platform)**:
  - Supports all Indian localities, neighborhoods, and cities via Google Places API (New).
  - Forward address geocoding and reverse GPS coordinate resolution.
  - Estimated travel times and driving distances for Top-K candidate helpers via Google Routes API (`computeRoutes`).
  - **Strict Scope Isolation**: Isolates user home location (`locations` table), request destination (`request_locations` table), and browser device coordinates (`navigator.geolocation`).
  - **Candidate Privacy Protection**: Exact GPS coordinates and residential street addresses are never exposed to other users; candidate helpers are mapped to approximate ~1.1 km area zones.
  - **Resilient Fallback**: Operates cleanly offline or in keyless mode using local Haversine distance calculations and textual locality hierarchy.

---

## Architecture & Tech Stack

```
NEST/
├── frontend/                     # React 18/19 + TypeScript + Vite + Tailwind CSS
│   ├── src/
│   │   ├── components/           # UI, layout, map, request, profile, and match components
│   │   ├── hooks/                # Custom React hooks (debounce, toast)
│   │   ├── lib/                  # Google Maps loader and utilities
│   │   ├── pages/                # Application routes and pages
│   │   ├── services/             # Axios API clients
│   │   ├── store/                # Zustand stores (auth, theme)
│   │   └── types/                # TypeScript interfaces
│   ├── public/                   # Static assets
│   ├── package.json
│   ├── vite.config.ts
│   └── vitest.config.ts
│
├── backend/                      # Python 3 + FastAPI + SQLAlchemy + Alembic
│   ├── alembic/                  # Database migration scripts
│   ├── app/
│   │   ├── api/                  # FastAPI routers (auth, profile, requests, matching, location)
│   │   ├── core/                 # Configuration, security, dependencies
│   │   ├── db/                   # Database session, base model
│   │   ├── models/               # SQLAlchemy models (User, Profile, Location, Skill, Request, Embedding)
│   │   ├── schemas/              # Pydantic validation schemas
│   │   └── services/             # Business logic (Google Maps, matching, embeddings, NLP)
│   ├── tests/                    # Pytest test suite (91 automated tests)
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml            # Multi-container orchestration (FastAPI + PostgreSQL with pgvector)
├── README.md                     # Platform documentation
└── .gitignore                    # Project-level git ignore
```

---

## Getting Started

### Prerequisites

- **Python**: 3.10, 3.11, or 3.12+
- **Node.js**: 18.x or 20.x+
- **PostgreSQL**: 16 with the `pgvector` extension installed
- **Git**

---

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set your local database connection and configuration:
   ```env
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/nest_db
   JWT_SECRET=YOUR_SECURE_JWT_SECRET
   GOOGLE_MAPS_API_KEY=YOUR_GOOGLE_MAPS_SERVER_KEY
   ```

5. Run database migrations:
   ```bash
   alembic upgrade head
   ```

6. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   The backend API documentation is available at `http://127.0.0.1:8000/docs`.

---

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit `.env`:
   ```env
   VITE_API_URL=http://127.0.0.1:8000
   VITE_GOOGLE_MAPS_API_KEY=YOUR_GOOGLE_MAPS_BROWSER_KEY
   ```

4. Start the frontend development server:
   ```bash
   npm run dev
   ```
   Access the web application at `http://localhost:5173`.

---

## Docker Compose Setup

Run the entire platform including PostgreSQL 16 with `pgvector` and the FastAPI backend using Docker:

```bash
docker-compose up --build
```

---

## Testing

### Backend Unit & Integration Tests (Pytest)
```bash
cd backend
pytest -v
```
*Current test coverage: 91 automated tests passing across authentication, profiles, skills, requests, semantic embeddings, hybrid matching, and location intelligence.*

### Frontend Component & Integration Tests (Vitest)
```bash
cd frontend
npm run test
```
*Current test coverage: 24 automated tests passing across authentication, onboarding, requests, matching radar, and location components.*

### Frontend Production Build Verification
```bash
cd frontend
npm run build
```

---

## Security & Privacy Guidelines

- **No Secrets in Version Control**: `.env` files are excluded by `.gitignore`. Example files (`.env.example`) provide placeholder templates only.
- **Database Credentials**: Database connection strings are loaded via environment variables and never hardcoded in source files.
- **Google Maps API Key Restrictions**:
  - The frontend browser key (`VITE_GOOGLE_MAPS_API_KEY`) should be restricted by HTTP referrer in the Google Cloud Console.
  - The backend server key (`GOOGLE_MAPS_API_KEY`) should be restricted by server IP and API scope (Places, Geocoding, Routes).
- **Candidate Privacy**: Matching candidate responses strictly omit raw GPS coordinates and exact residential addresses to prevent user tracking.

---

## License

This project is licensed under the MIT License.
