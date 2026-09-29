# NEST Frontend ("Find Your People. Find Your Place.")

Modern, mobile-first React + TypeScript frontend for the NEST community matching platform, connected to the FastAPI + PostgreSQL 16 + pgvector backend.

---

## 1. Tech Stack
- **Framework**: React 18/19 with Vite
- **Language**: TypeScript (strict mode, zero `any`)
- **Styling**: Tailwind CSS with custom design tokens (`#0F766E` primary, `#F59E0B` accent, `#FAFAF7` light background, `#0B1210` dark background)
- **State Management**: Zustand (`useAuthStore`, `useThemeStore`)
- **Server Cache**: TanStack React Query v5
- **Routing**: React Router v6 with `ProtectedRoute` and `PublicOnlyRoute`
- **Forms & Validation**: React Hook Form + Zod
- **API Client**: Axios with request/response Bearer JWT interceptors
- **Icons**: Lucide React
- **Testing**: Vitest + React Testing Library (17 tests passing)

---

## 2. Environment Variables
Copy `.env.example` to `.env`:
```env
VITE_API_URL=http://127.0.0.1:8000
```

---

## 3. Development & Build Commands

### Install Dependencies
```bash
npm install
```

### Run Local Development Server
```bash
npm run dev
# Starts on http://127.0.0.1:5173
```

### Run Unit & Component Tests
```bash
npm run test
# Runs 17 Vitest tests across Landing, Auth, Requests, Profile, and Navigation
```

### Typecheck & Production Build
```bash
npm run typecheck
npm run build
```

---

## 4. Authentication Flow
1. User registers via `POST /api/auth/register` with role (`newcomer`, `helper`, or `both`).
2. Authentication is completed via `POST /api/auth/login`.
3. The returned JWT `access_token` is stored securely in `sessionStorage` (cleared upon tab close, avoiding pretending an httpOnly cookie exists while the backend uses Bearer JWT headers).
4. Axios automatically attaches `Authorization: Bearer <token>` to all authenticated requests.
5. On startup, `useAuthStore` verifies session validity with `GET /api/auth/me`. If a 401 is received, credentials are wiped and the user is redirected to `/login`.

---

## 5. Current Backend-Supported Features (Phase 1–4)
- **Authentication**: Registration, Login, Token storage, User profile retrieval.
- **Profile Management**: Profile headline, bio, occupation, experience, languages, availability toggle.
- **Location**: Primary city, area, state, country, privacy-preserving approximate coordinates.
- **Skills**: Expertise tags (Housing, Food, Metro, etc.) added and deleted on demand.
- **Natural Language Parsing**: Authoritative backend extraction via `POST /api/requests/parse` and live debounced preview.
- **Request CRUD**: Request creation, user history listing, detailed extracted criteria viewing, inline editing via PATCH, and deletion.
- **Semantic Vector Storage**: All profiles and requests vectorized into 384 dimensions on PostgreSQL 16 via `all-MiniLM-L6-v2` and `pgvector`.

---

## 6. Future Backend-Dependent Features (Strict No-Fake-Data Policy)
In strict compliance with the platform specification, unbuilt backend features render honest, isolated `FeatureUnavailable` states without mock profiles, fake similarity scores, or simulated chat:
- **Phase 5 (Hybrid Matching Engine)**: `GET /api/matches/{requestId}` (Weighted 40% Semantic + 25% Location + 15% Experience + 10% Reputation + 10% Availability).
- **Phase 6 (Direct Messaging)**: `WS /ws/chat/{connectionId}` and `GET /api/messages`.
- **Phase 7 (Community Hubs)**: `GET /api/community/posts`.
- **Phase 8 (Resource Directories)**: `GET /api/resources`.
