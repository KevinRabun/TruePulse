# TruePulse API Reference

## Base URL

- **Development**: `http://localhost:8000/api/v1`
- **Staging**: `https://api-staging.truepulse.dev/api/v1`
- **Production**: `https://api.truepulse.dev/api/v1`

## Authentication

TruePulse uses JWT (JSON Web Tokens) for authentication.

### Obtaining a Token

**Register:**
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "display_name": "JohnDoe"
}
```

**Login:**
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response:**
```json
{
  "access_token": "<jwt-token>",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "<refresh-token>"
}
```

### Using the Token

Include the token in the Authorization header:
```http
GET /polls/today
Authorization: Bearer <jwt-token>
```

---

## Endpoints

### Polls

#### Get Today's Poll
```http
GET /polls/today
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "question": "What is your opinion on renewable energy?",
  "category": "Environment",
  "choices": [
    {
      "id": "choice-1-uuid",
      "text": "Strongly support",
      "vote_count": 1234
    },
    {
      "id": "choice-2-uuid",
      "text": "Somewhat support",
      "vote_count": 567
    }
  ],
  "start_time": "2024-01-15T00:00:00Z",
  "end_time": "2024-01-16T00:00:00Z",
  "total_votes": 2345,
  "ai_generated": true,
  "user_has_voted": false
}
```

#### Get Poll by ID
```http
GET /polls/{poll_id}
```

#### List Polls
```http
GET /polls?limit=10&offset=0&status=active
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | integer | Max results (default: 10, max: 100) |
| `offset` | integer | Skip N results |
| `status` | string | Filter by status: `active`, `closed`, `all` |
| `category` | string | Filter by category |

#### Vote on a Poll
```http
POST /polls/{poll_id}/vote
Authorization: Bearer <token>
Content-Type: application/json

{
  "choice_id": "choice-1-uuid"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "message": "Vote recorded successfully",
  "points_earned": 10,
  "new_total_points": 150,
  "streak_bonus": 5
}
```

**Error Responses:**
- `400`: Already voted on this poll
- `401`: Not authenticated
- `404`: Poll or choice not found
- `410`: Poll has ended

#### Get Poll Results
```http
GET /polls/{poll_id}/results
```

**Response:**
```json
{
  "poll_id": "550e8400-e29b-41d4-a716-446655440000",
  "question": "What is your opinion on renewable energy?",
  "total_votes": 5678,
  "results": [
    {
      "choice_id": "choice-1-uuid",
      "text": "Strongly support",
      "vote_count": 2500,
      "percentage": 44.0
    },
    {
      "choice_id": "choice-2-uuid",
      "text": "Somewhat support",
      "vote_count": 1800,
      "percentage": 31.7
    }
  ],
  "demographics": {
    "age_groups": { ... },
    "regions": { ... }
  }
}
```

---

### User Profile

#### Get Current User
```http
GET /users/me
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": "user-uuid",
  "email": "user@example.com",
  "display_name": "JohnDoe",
  "points": 1250,
  "total_votes": 125,
  "current_streak": 7,
  "longest_streak": 15,
  "achievements_count": 5,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### Update Profile
```http
PATCH /users/me
Authorization: Bearer <token>
Content-Type: application/json

{
  "display_name": "NewDisplayName"
}
```

#### Get User Achievements
```http
GET /users/me/achievements
Authorization: Bearer <token>
```

**Response:**
```json
{
  "achievements": [
    {
      "id": "ach-1",
      "name": "First Vote",
      "description": "Cast your first vote",
      "type": "first_vote",
      "unlocked": true,
      "unlocked_at": "2024-01-01T12:00:00Z"
    },
    {
      "id": "ach-2",
      "name": "Week Warrior",
      "description": "Vote 7 days in a row",
      "type": "streak_7",
      "unlocked": false,
      "progress": 5,
      "target": 7
    }
  ]
}
```

---

### Leaderboard

#### Get Leaderboard
```http
GET /leaderboard?timeframe=weekly&limit=50
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `timeframe` | string | `daily`, `weekly`, `monthly`, `all_time` |
| `limit` | integer | Max results (default: 50, max: 100) |

**Response:**
```json
{
  "timeframe": "weekly",
  "period_start": "2024-01-08T00:00:00Z",
  "period_end": "2024-01-15T00:00:00Z",
  "entries": [
    {
      "rank": 1,
      "user_id": "user-1-uuid",
      "display_name": "TopVoter",
      "points": 500,
      "total_votes": 50,
      "streak": 7,
      "achievements_count": 8
    }
  ],
  "current_user_rank": 42
}
```

---

### Enterprise API

The Enterprise API requires an API key instead of JWT authentication.

```http
GET /enterprise/polls
X-API-Key: your-enterprise-api-key
```

#### Create Custom Poll
```http
POST /enterprise/polls
X-API-Key: your-enterprise-api-key
Content-Type: application/json

{
  "question": "Your custom poll question?",
  "choices": [
    "Option A",
    "Option B",
    "Option C"
  ],
  "duration_hours": 24,
  "category": "Custom",
  "target_audience": {
    "regions": ["US", "CA"],
    "min_age": 18
  }
}
```

#### Get Poll Analytics
```http
GET /enterprise/polls/{poll_id}/analytics
X-API-Key: your-enterprise-api-key
```

**Response:**
```json
{
  "poll_id": "poll-uuid",
  "total_votes": 10000,
  "unique_voters": 9500,
  "demographics": {
    "age_distribution": {
      "18-24": 2500,
      "25-34": 3500,
      "35-44": 2000,
      "45-54": 1000,
      "55+": 1000
    },
    "geographic_distribution": {
      "US": 7000,
      "CA": 1500,
      "UK": 1000,
      "Other": 500
    }
  },
  "time_series": [
    {
      "timestamp": "2024-01-15T00:00:00Z",
      "votes": 500
    }
  ]
}
```

#### Export Data
```http
GET /enterprise/polls/{poll_id}/export?format=csv
X-API-Key: your-enterprise-api-key
```

---

## Error Handling

All errors follow this format:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ]
  }
}
```

### Error Codes

| HTTP Status | Code | Description |
|-------------|------|-------------|
| 400 | `VALIDATION_ERROR` | Invalid request data |
| 400 | `ALREADY_VOTED` | User has already voted |
| 401 | `UNAUTHORIZED` | Invalid or missing token |
| 403 | `FORBIDDEN` | Insufficient permissions |
| 404 | `NOT_FOUND` | Resource not found |
| 410 | `POLL_ENDED` | Poll voting period has ended |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Server error |

---

## Rate Limiting

| Endpoint Type | Rate Limit |
|---------------|------------|
| Authentication | 10 requests/minute |
| Public endpoints | 100 requests/minute |
| Authenticated endpoints | 300 requests/minute |
| Enterprise API | 1000 requests/minute |

Rate limit headers are included in responses:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705315200
```

---

## Webhooks (Enterprise)

Enterprise customers can configure webhooks for real-time events.

### Events

| Event | Description |
|-------|-------------|
| `poll.created` | A new poll was created |
| `poll.ended` | A poll has ended |
| `poll.milestone` | Vote count reached milestone |

### Payload Example
```json
{
  "event": "poll.ended",
  "timestamp": "2024-01-15T00:00:00Z",
  "data": {
    "poll_id": "poll-uuid",
    "question": "Poll question?",
    "total_votes": 5000,
    "results": [...]
  }
}
```

---

## SDKs

Official SDKs are available for:
- Python: `pip install truepulse`
- JavaScript/TypeScript: `npm install @truepulse/sdk`
- C#: `dotnet add package TruePulse.SDK`

---

## Support

- 📧 API Support: api-support@truepulse.dev
- 📚 Developer Portal: https://developers.truepulse.dev
- 🐛 Report Issues: https://github.com/yourusername/truepulse/issues
