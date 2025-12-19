# TruePulse API Documentation

## Base URL

```
Development: http://localhost:8000
Production: https://api.truepulse.net
```

## Authentication

TruePulse uses JWT (JSON Web Tokens) for authentication. Include the token in the `Authorization` header:

```
Authorization: Bearer <your_jwt_token>
```

### Obtaining a Token

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your_password"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

## Polls

### List Active Polls

Returns all currently active polls available for voting.

```http
GET /api/v1/polls
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `limit` | integer | 20 | Items per page (max 100) |
| `category` | string | - | Filter by category |

**Response (200 OK):**
```json
{
  "items": [
    {
      "id": "uuid-string",
      "question": "Should the minimum wage be increased?",
      "category": "economics",
      "poll_type": "binary",
      "options": [
        { "id": 1, "text": "Yes" },
        { "id": 2, "text": "No" }
      ],
      "created_at": "2025-01-15T10:30:00Z",
      "expires_at": "2025-01-22T10:30:00Z",
      "total_votes": 15432
    }
  ],
  "total": 45,
  "page": 1,
  "limit": 20
}
```

### Get Poll Details

```http
GET /api/v1/polls/{poll_id}
```

**Response (200 OK):**
```json
{
  "id": "uuid-string",
  "question": "Should the minimum wage be increased?",
  "description": "Context about the minimum wage debate...",
  "category": "economics",
  "poll_type": "binary",
  "options": [
    { "id": 1, "text": "Yes" },
    { "id": 2, "text": "No" }
  ],
  "source_events": [
    {
      "title": "Congress debates minimum wage bill",
      "source": "Associated Press",
      "date": "2025-01-14"
    }
  ],
  "created_at": "2025-01-15T10:30:00Z",
  "expires_at": "2025-01-22T10:30:00Z"
}
```

### Get Poll Results

Returns aggregated voting results. Individual votes cannot be traced.

```http
GET /api/v1/polls/{poll_id}/results
```

**Response (200 OK):**
```json
{
  "poll_id": "uuid-string",
  "total_votes": 15432,
  "results": [
    { "option_id": 1, "text": "Yes", "votes": 8234, "percentage": 53.4 },
    { "option_id": 2, "text": "No", "votes": 7198, "percentage": 46.6 }
  ],
  "demographics": {
    "age_groups": {
      "18-24": { "Yes": 62.1, "No": 37.9 },
      "25-34": { "Yes": 58.3, "No": 41.7 },
      "35-44": { "Yes": 51.2, "No": 48.8 },
      "45-54": { "Yes": 45.6, "No": 54.4 },
      "55+": { "Yes": 42.1, "No": 57.9 }
    }
  },
  "last_updated": "2025-01-15T14:30:00Z"
}
```

### Submit Vote

Submit a vote for a poll. Requires authentication.

```http
POST /api/v1/polls/{poll_id}/vote
Authorization: Bearer <token>
Content-Type: application/json

{
  "option_id": 1
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "message": "Vote recorded successfully",
  "points_earned": 10
}
```

**Error Responses:**
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: Already voted on this poll
- `404 Not Found`: Poll not found
- `410 Gone`: Poll has expired

---

## Users

### Register New User

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password",
  "display_name": "JohnDoe",
  "date_of_birth": "1990-05-15"
}
```

**Response (201 Created):**
```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "display_name": "JohnDoe",
  "email_verified": false,
  "created_at": "2025-01-15T10:00:00Z"
}
```

### Get Current User

```http
GET /api/v1/users/me
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "display_name": "JohnDoe",
  "email_verified": true,
  "phone_verified": false,
  "created_at": "2025-01-15T10:00:00Z",
  "total_votes": 47,
  "current_streak": 5
}
```

### Request Email Verification

```http
POST /api/v1/auth/verify-email/request
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "message": "Verification email sent"
}
```

### Request Phone Verification (SMS)

```http
POST /api/v1/auth/verify-phone/request
Authorization: Bearer <token>
Content-Type: application/json

{
  "phone_number": "+1234567890"
}
```

**Response (200 OK):**
```json
{
  "message": "Verification code sent via SMS"
}
```

---

## Gamification

### Get User Progress

```http
GET /api/v1/gamification/progress
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "user_id": "uuid-string",
  "level": 5,
  "current_points": 2450,
  "points_to_next_level": 550,
  "total_votes": 47,
  "current_streak": 5,
  "longest_streak": 12,
  "badges": [
    {
      "id": "first_vote",
      "name": "First Vote",
      "description": "Cast your first vote",
      "earned_at": "2025-01-10T15:00:00Z"
    },
    {
      "id": "streak_7",
      "name": "Week Warrior",
      "description": "Vote 7 days in a row",
      "earned_at": "2025-01-12T09:00:00Z"
    }
  ]
}
```

### Get Leaderboard

```http
GET /api/v1/gamification/leaderboard
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `period` | string | "weekly" | "daily", "weekly", "monthly", "all_time" |
| `limit` | integer | 10 | Number of entries (max 100) |

**Response (200 OK):**
```json
{
  "period": "weekly",
  "entries": [
    {
      "rank": 1,
      "display_name": "TopVoter",
      "points": 450,
      "votes": 42
    },
    {
      "rank": 2,
      "display_name": "PollMaster",
      "points": 380,
      "votes": 35
    }
  ],
  "current_user_rank": 156
}
```

### List All Achievements

```http
GET /api/v1/gamification/achievements
```

**Response (200 OK):**
```json
{
  "achievements": [
    {
      "id": "first_vote",
      "name": "First Vote",
      "description": "Cast your first vote",
      "points": 10,
      "icon": "vote"
    },
    {
      "id": "streak_7",
      "name": "Week Warrior",
      "description": "Vote 7 days in a row",
      "points": 50,
      "icon": "fire"
    },
    {
      "id": "verified_voter",
      "name": "Verified Voter",
      "description": "Verify your email and phone",
      "points": 100,
      "icon": "shield-check"
    }
  ]
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {}
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Missing or invalid authentication |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 422 | Invalid request data |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Rate Limiting

API requests are rate limited per user:

| Endpoint Type | Limit |
|---------------|-------|
| Authentication | 10 requests/minute |
| Read (GET) | 100 requests/minute |
| Write (POST/PUT) | 30 requests/minute |

Rate limit headers are included in all responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705325400
```

---

## Pagination

List endpoints support cursor-based pagination:

```http
GET /api/v1/polls?page=2&limit=20
```

Response includes pagination metadata:
```json
{
  "items": [...],
  "total": 245,
  "page": 2,
  "limit": 20,
  "has_next": true,
  "has_prev": true
}
```
