# NEST — Production Deployment Guide

This guide details how to deploy the NEST platform for a real-world MVP using free-tier cloud services and containerized environments.

---

## 1. System Architecture Overview

```
                      ┌──────────────────────────────────────────────┐
                      │             Client Browser / SPA             │
                      │  (Vercel / Cloudflare Pages / Nginx Port 80) │
                      └───────┬───────────────────────────────▲──────┘
                              │                               │
                HTTPS REST API│                               │WSS WebSocket
               /api/* requests│                               │/ws/conversations/*
                              │                               │
                      ┌───────▼───────────────────────────────┴──────┐
                      │             FastAPI Backend                  │
                      │       (Render / Railway / Docker Port 8000)   │
                      └───┬───────────────────────────────┬──────────┘
                          │                               │
            pgvector Cosine│                               │Places API (New)
            SQLAlchemy 2.0 │                               │Server API Key
                          │                               │
            ┌─────────────▼───────────────┐ ┌─────────────▼──────────────┐
            │   PostgreSQL 16 + pgvector   │ │  Google Cloud Platform     │
            │(Supabase / Neon / Docker DB)│ │  (Places API, Google Auth) │
            └─────────────────────────────┘ └────────────────────────────┘
```

---

## 2. Free-Tier Cloud Deployment Recommended Stack

| Component | Recommended Free-Tier Service | Notes |
| :--- | :--- | :--- |
| **Frontend SPA** | **Vercel** or **Cloudflare Pages** | Zero-config SPA fallback routing, global CDN, instant HTTPS. |
| **Backend API** | **Render.com** (Web Service) or **Railway** | Native Python/FastAPI support, automatic HTTPS, WebSocket support. |
| **Database** | **Supabase** or **Neon.tech** | Managed PostgreSQL 16 with native `pgvector` support on free tier. |
| **Transactional Email** | **Resend** (3,000 emails/month free) | API-based email verification, sandbox mode for instant testing. |
| **Container Self-Host** | **Docker Compose** on free cloud VM (e.g., Oracle Cloud Free Tier) | Single command full-stack deployment (`docker compose up -d`). |

---

## 3. Environment Variables Reference

### Backend Configuration (`backend/.env` or Cloud Service Environment)

| Variable | Required | Default | Description |
| :--- | :---: | :--- | :--- |
| `ENVIRONMENT` | Yes | `development` | Set to `production` in live deployments. |
| `DATABASE_URL` | Yes | — | PostgreSQL connection string. Supports `postgresql://` and `postgres://`. |
| `JWT_SECRET` | Yes | — | Secret key for signing auth tokens (generate via `openssl rand -hex 32`). |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `1440` | Session lifetime (default 24 hours). |
| `FRONTEND_URL` | Yes | `http://localhost:5173` | Public URL of deployed frontend (e.g., `https://nest-app.vercel.app`). Auto-synced to CORS. |
| `BACKEND_CORS_ORIGINS` | No | Localhost ports | Comma-separated or JSON list of allowed origins (e.g. `https://nest.vercel.app,http://localhost:3000`). |
| `GOOGLE_MAPS_SERVER_API_KEY` | Yes | — | Dedicated server key for Google Places API (New). IP-restricted where practical. |
| `GOOGLE_CLIENT_ID` | Yes | — | Google OAuth Client ID matching the frontend client ID. |
| `EMAIL_PROVIDER` | No | `resend` | Email driver: `resend`, `smtp`, `sendgrid`, or `test`. |
| `RESEND_API_KEY` | Conditional | — | API key from Resend (required if `EMAIL_PROVIDER=resend`). |
| `EMAIL_FROM` | No | `NEST Verification <onboarding@resend.dev>` | From address for verification emails. |
| `ENABLE_DOCS` | No | `True` | Set to `False` to disable `/docs` and `/redoc` in production. |

### Frontend Configuration (`frontend/.env` or Vercel/Cloudflare Environment)

| Variable | Required | Default | Description |
| :--- | :---: | :--- | :--- |
| `VITE_API_URL` | Yes | `http://127.0.0.1:8000` | Backend API base URL (e.g., `https://nest-api.onrender.com`). |
| `VITE_WS_URL` | No | Automatic | Dedicated WebSocket URL (auto-derives `wss://` from `VITE_API_URL` if omitted). |
| `VITE_GOOGLE_MAPS_API_KEY` | Yes | — | Client-side Google Maps browser key (restricted by HTTP Referrer). |
| `VITE_GOOGLE_CLIENT_ID` | Yes | — | Google Identity Services OAuth Client ID. |

---

## 4. Google Maps & Google Auth Platform Setup

NEST strictly separates browser-facing Google services from server-side services:

### 1. Frontend Browser Key (`VITE_GOOGLE_MAPS_API_KEY`)
* **Target Audience**: Browser clients only.
* **API Restrictions**:
  * Maps JavaScript API
  * Places API (New)
* **Application Restrictions** (HTTP Referrers):
  * Local Dev: `http://localhost:3000/*`, `http://localhost:5173/*`, `http://127.0.0.1:3000/*`
  * Production: `https://your-frontend-domain.vercel.app/*`, `https://your-custom-domain.com/*`

### 2. Backend Server Key (`GOOGLE_MAPS_SERVER_API_KEY`)
* **Target Audience**: FastAPI server only.
* **API Restrictions**:
  * Places API (New)
* **Application Restrictions**:
  * IP address restriction (set to your backend server's static IP if available).
* **Important**: NEST does **NOT** use or require Google Geocoding API or Nominatim/OSM fallbacks.

### 3. Google OAuth Client ID (`GOOGLE_CLIENT_ID` / `VITE_GOOGLE_CLIENT_ID`)
* In Google Cloud Console -> **Credentials** -> **OAuth 2.0 Client IDs**:
  * **Authorized JavaScript origins**:
    * `http://localhost:3000`
    * `http://localhost:5173`
    * `https://your-frontend-domain.vercel.app`
  * **Authorized redirect URIs**:
    * Same as origin, or your app's callback path.

---

## 5. Database Migration & Initialization

NEST uses Alembic with PostgreSQL 16 and native `pgvector`.

### 1. Enable `pgvector`
If setting up a fresh PostgreSQL database manually, ensure the extension is enabled:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```
*(Alembic migration `7411d6f5e980` also executes this automatically).*

### 2. Run Migrations
Run the following from the `backend/` directory:
```bash
# Apply all pending schema migrations up to the current head
alembic upgrade head
```

To verify the current migration status:
```bash
alembic current
```

---

## 6. Health Checks & Monitoring

NEST exposes dual health check endpoints:

* **`GET /health`** (Root level for container orchestrators and load balancers):
  * Verifies backend runtime and executes `SELECT 1` on PostgreSQL.
  * Returns `HTTP 200` with `status: ok` when healthy.
  * Returns `HTTP 503` with `status: degraded` if the database disconnects.
* **`GET /api/health`** (API namespace):
  * Standard JSON response:
    ```json
    {
      "status": "ok",
      "environment": "production",
      "database": "connected",
      "api": "online"
    }
    ```

---

## 7. Real-Time WebSockets Behind HTTPS / Reverse Proxy

* NEST chat uses standard WebSockets mounted at:
  `/ws/conversations/{conversation_id}?token={jwt_token}`
* **Automatic Protocol Switching**:
  * In local development (`http://`): connects via `ws://`.
  * In production (`https://`): automatically connects via `wss://`.
* **Reverse Proxy Note (Nginx / Cloudflare)**:
  Ensure `Upgrade` and `Connection "Upgrade"` headers are forwarded:
  ```nginx
  location /ws/ {
      proxy_pass http://backend:8000;
      proxy_http_version 1.1;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection "upgrade";
      proxy_set_header Host $host;
      proxy_read_timeout 86400;
  }
  ```

---

## 8. Docker Deployment (Local & Self-Hosted)

### Full Stack via Docker Compose:
```bash
# 1. Copy and configure root environment variables if desired
# 2. Build and start services in the background
docker compose up -d --build

# 3. View live logs
docker compose logs -f backend

# 4. Check container health status
docker compose ps
```

* Frontend: `http://localhost:3000`
* Backend API: `http://localhost:8000/docs`
* Backend Health: `http://localhost:8000/health`
* PostgreSQL: `localhost:5433`

---

## 9. Production Security Checklist

- [x] **Zero Hardcoded Secrets**: Verified via `git grep "AIzaSy"` (0 occurrences).
- [x] **Ignored Environment Files**: `backend/.env`, `frontend/.env`, and `.env` are in `.gitignore`.
- [x] **Docker Image Cleanliness**: Dedicated `.dockerignore` files prevent local credentials or build caches from leaking into images.
- [x] **Unprivileged Container User**: Backend Docker container runs under unprivileged `nestuser` (UID 1000).
- [x] **PostgreSQL Pooling**: Backend uses SQLAlchemy connection pooling with `pool_pre_ping=True`.
- [x] **CORS Protection**: Configured via `BACKEND_CORS_ORIGINS` and `FRONTEND_URL`.
- [x] **IDOR & Authorization**: All connections, chat messages, and assistance sessions strictly enforce participant ownership.
- [x] **Coarse Public Privacy**: Public profile endpoints suppress raw coordinates and Place IDs, exposing only generalized city and area.
