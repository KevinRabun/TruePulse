# TruePulse Backend

FastAPI-based backend services for the TruePulse polling platform.

## Structure

```
backend/
├── api/                 # API routes
│   ├── v1/             # API version 1
│   │   ├── polls.py    # Poll endpoints
│   │   ├── votes.py    # Vote endpoints
│   │   ├── users.py    # User endpoints
│   │   ├── auth.py     # Authentication endpoints
│   │   └── enterprise.py # Enterprise API endpoints
│   └── deps.py         # Shared dependencies
├── core/               # Core functionality
│   ├── config.py       # Configuration management
│   ├── security.py     # Security utilities
│   └── events.py       # Event handlers
├── models/             # Database models
│   ├── user.py         # User model
│   ├── poll.py         # Poll model
│   ├── vote.py         # Vote model (privacy-preserving)
│   └── achievement.py  # Gamification models
├── schemas/            # Pydantic schemas
├── services/           # Business logic
│   ├── poll_service.py
│   ├── vote_service.py
│   ├── user_service.py
│   └── gamification_service.py
├── ai/                 # AI components
│   ├── event_aggregator.py
│   └── poll_generator.py
├── db/                 # Database utilities
│   ├── session.py
│   └── repositories/
└── main.py             # Application entry point
```

## Quick Start

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Unix

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn main:app --reload --port 8000
```

## Environment Variables

See `.env.example` for required environment variables.

## API Documentation

When running locally, access:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
