# NEST — FRONTEND TO BACKEND API MAPPING

This document maps all frontend screens and features to their backend endpoints, payloads, response schemas, and explicitly catalogs future backend requirements.

---

## 1. Supported Live Endpoints (Active in Phase 1–4 Backend)

### Authentication
| Frontend Screen | Action | HTTP Method | Endpoint | Request Schema | Response Schema |
|---|---|---|---|---|---|
| `/register` | Create Account | `POST` | `/api/auth/register` | `{ name, email, password, role }` | `UserResponse` (`id`, `name`, `email`, `role`, `created_at`) |
| `/login` | Authenticate | `POST` | `/api/auth/login` | `{ email, password }` | `TokenResponse` (`access_token`, `token_type: "bearer"`) |
| App Startup / Guards | Validate Session | `GET` | `/api/auth/me` | *None (Bearer Token)* | `UserResponse` |

### Profile, Location & Skills
| Frontend Screen | Action | HTTP Method | Endpoint | Request Schema | Response Schema |
|---|---|---|---|---|---|
| `/profile`, `/onboarding` | Fetch Profile | `GET` | `/api/profile/me` | *None (Bearer Token)* | `FullProfileResponse` (`user`, `profile`, `location`, `skills`) |
| `/profile/edit`, `/onboarding` | Update Profile | `PUT` | `/api/profile/me` | `ProfileUpdate` (`headline`, `bio`, `occupation`, `organization`, `years_experience`, `languages`, `availability`) | `ProfileResponse` |
| `/onboarding`, `/profile/edit` | Set Location | `PUT` | `/api/profile/me/location` | `LocationCreate` (`city`, `area`, `state`, `country`, `latitude`, `longitude`) | `LocationResponse` |
| `/profile` | Get Location | `GET` | `/api/profile/me/location` | *None* | `LocationResponse` |
| `/profile/edit` | Add Skill | `POST` | `/api/profile/me/skills` | `SkillCreate` (`name`, `proficiency`, `years_experience`) | `UserSkillResponse` |
| `/profile/edit` | Delete Skill | `DELETE` | `/api/profile/me/skills/{id}` | *None (Path Parameter)* | `{ detail: "Skill removed successfully" }` |

### Requests & NLP Intelligence
| Frontend Screen | Action | HTTP Method | Endpoint | Request Schema | Response Schema |
|---|---|---|---|---|---|
| `/home` (Debounced) | Preview Extraction | `POST` | `/api/requests/parse` | `{ text }` | `RequestParseResponse` (`raw_text`, `extracted`) |
| `/home` | Submit Request | `POST` | `/api/requests` | `{ text }` | `RequestResponse` (`id`, `raw_text`, `city`, `area`, `needs`, `budget_amount`, `preferences`) |
| `/requests` | List Requests | `GET` | `/api/requests` | *None (Bearer Token)* | `List[RequestResponse]` |
| `/requests/:id` | View Request | `GET` | `/api/requests/{id}` | *None (Path Parameter)* | `RequestResponse` |
| `/requests/:id` | Edit & Re-parse | `PATCH` | `/api/requests/{id}` | `RequestUpdate` (`text`, `status`) | `RequestResponse` |
| `/requests/:id`, `/requests` | Delete Request | `DELETE` | `/api/requests/{id}` | *None (Path Parameter)* | `204 No Content` |

### Semantic Vector Embeddings
| Feature | HTTP Method | Endpoint | Request Schema | Response Schema |
|---|---|---|---|---|
| Profile Vectorization | `POST` | `/api/embeddings/profile/me` | *None* | `EmbeddingResponse` (384-dim, SHA-256 hash) |
| Request Vectorization | `POST` | `/api/embeddings/request/{id}` | *None* | `EmbeddingResponse` (384-dim, SHA-256 hash) |
| Semantic Profile Search | `POST` | `/api/embeddings/search/profiles` | `{ query_text, limit, min_similarity }` | `SemanticSearchResponse` (pgvector cosine matches) |

### Phase 5 — Hybrid Matching Engine
| Frontend Screen | Action | HTTP Method | Endpoint | Request Schema | Response Schema |
|---|---|---|---|---|---|
| `/results/:requestId` | Find Matches | `POST` | `/api/matching/find-matches` | `{ request_id, limit, weights, min_score }` | `MatchingResponse` (`request_id`, `total_candidates_evaluated`, `matches`, `weights_used`, `generated_at`) |

---

## 2. Future Backend Endpoints (Strictly Isolated — Zero Fake Data)

The following endpoints are scheduled for subsequent development phases. Frontend UI components are already typed and prepared to consume these schemas as soon as deployed:
```json
{
  "request_id": "uuid",
  "helpers": [
    {
      "user_id": "uuid",
      "name": "string",
      "role": "helper",
      "headline": "string",
      "distance_km": 1.4,
      "skills": ["Housing", "Food"],
      "scores": {
        "semantic_score": 0.88,
        "location_score": 0.92,
        "experience_score": 0.80,
        "reputation_score": 0.95,
        "availability_score": 1.00,
        "final_score": 0.89
      },
      "reasons": [
        { "category": "semantic", "title": "Housing & PG Guidance", "explanation": "Matches your request for PG in Whitefield" }
      ]
    }
  ],
  "resources": []
}
```

### Phase 6 — Direct Real-Time Messaging
- **Endpoint**: `WS /ws/chat/{connectionId}`
- **Endpoint**: `GET /api/connections`
- **Endpoint**: `GET /api/messages/{connectionId}`

### Phase 7 — Community Hubs
- **Endpoint**: `GET /api/community/posts`
- **Endpoint**: `POST /api/community/posts`

### Phase 8 — Resource Directories
- **Endpoint**: `GET /api/resources`
- **Endpoint**: `GET /api/resources/{id}`
