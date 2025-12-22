# TruePulse API - Internal Reference

> ⚠️ **Not a Public API**: The TruePulse API is designed exclusively for the official frontend application. Direct API access from third-party applications is blocked by middleware.

## Access Restrictions

The backend enforces frontend-only access through multiple layers:

1. **CORS Policy**: Only allows requests from configured origins
2. **FrontendOnlyMiddleware**: Validates Origin/Referer headers and requires `X-Frontend-Secret` header
3. **JWT Authentication**: User sessions managed through secure HTTP-only cookies

Attempts to call the API directly (e.g., via curl, Postman, or third-party apps) will receive `403 Forbidden`.

---

## Internal Endpoint Reference

This documentation is for **TruePulse developers only** to understand the frontend-backend contract.

### Health Check

```
GET /health
```

Exempt from authentication. Used for container orchestration health probes.

---

## Authentication Endpoints

### Login

```
POST /api/v1/auth/login
```

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password"
}
```

**Response:** Sets HTTP-only cookie with JWT token.

### Register

```
POST /api/v1/auth/register
```

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure_password",
  "display_name": "JohnDoe",
  "phone_number": "+15551234567"
}
```

> **Note:** Phone number is **mandatory** for registration. TruePulse enforces a "one person = one vote" policy, and phone verification is required to prevent duplicate accounts and ensure vote integrity. Users must verify their phone number via SMS before they can participate in polls.

### Logout

```
POST /api/v1/auth/logout
```

Invalidates the current session token.

### Email Verification

```
POST /api/v1/auth/verify-email/request
POST /api/v1/auth/verify-email/confirm
```

### Phone Verification (SMS)

```
POST /api/v1/auth/verify-phone/request
POST /api/v1/auth/verify-phone/confirm
```

---

## Poll Endpoints

### List Active Polls

```
GET /api/v1/polls
```

**Query Parameters:**
- `page` (int): Page number
- `limit` (int): Items per page
- `category` (string): Filter by category

### Get Poll Details

```
GET /api/v1/polls/{poll_id}
```

### Get Poll Results (Public)

```
GET /api/v1/polls/{poll_id}/results
```

Returns aggregated results only. Individual votes cannot be traced.

### Submit Vote (Authenticated)

```
POST /api/v1/polls/{poll_id}/vote
```

**Request:**
```json
{
  "option_id": 1
}
```

---

## User Endpoints

### Get Current User

```
GET /api/v1/users/me
```

### Update Profile

```
PATCH /api/v1/users/me
```

---

## Gamification Endpoints

### Get Progress

```
GET /api/v1/gamification/progress
```

### Get Leaderboard

```
GET /api/v1/gamification/leaderboard
```

**Query Parameters:**
- `period`: "daily", "weekly", "monthly", "all_time"
- `limit`: Number of entries

### List Achievements

```
GET /api/v1/gamification/achievements
```

---

## Error Responses

All errors follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message"
  }
}
```

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Not authenticated |
| `FORBIDDEN` | 403 | Access denied (includes non-frontend requests) |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 422 | Invalid request data |

---

## Development Notes

### Running Locally

During local development, set `APP_ENV=development` to relax frontend validation:

```bash
# Backend will accept requests from localhost origins
APP_ENV=development uvicorn main:app --reload
```

### Frontend Integration

The frontend must include:

1. **Credentials**: `credentials: 'include'` for cookie-based auth
2. **Secret Header**: `X-Frontend-Secret` header with the shared secret
3. **Origin Header**: Automatically set by browser

```typescript
// Example fetch configuration in frontend
const response = await fetch(`${API_URL}/api/v1/polls`, {
  credentials: 'include',
  headers: {
    'X-Frontend-Secret': process.env.NEXT_PUBLIC_FRONTEND_SECRET,
  },
});
```
