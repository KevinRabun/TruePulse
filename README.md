# TruePulse 🗳️

> Unbiased polling powered by AI-driven current events aggregation

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)
[![CI](https://github.com/KevinRabun/TruePulse/actions/workflows/ci.yml/badge.svg)](https://github.com/KevinRabun/TruePulse/actions/workflows/ci.yml)

## Overview

TruePulse is a privacy-first polling platform that automatically generates unbiased poll questions from aggregated current events. The platform enables public viewing of aggregated results while ensuring individual vote privacy.

### Key Features

- 🤖 **AI-Powered Poll Generation**: Automatically aggregates current events and generates unbiased poll questions using Azure OpenAI
- 🔒 **Privacy-First Architecture**: Individual votes cannot be traced back to users
- 🎮 **Gamified Experience**: Earn points and badges for participation
- 📊 **Public Results**: Anyone can view aggregated polling results
- 🔐 **Verified Voting**: Email and phone verification to prevent vote manipulation
- 📱 **Responsive Design**: Works seamlessly across all devices

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TruePulse Architecture                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐                          ┌──────────────────────────────┐ │
│  │   Frontend   │─────────────────────────▶│     Backend API              │ │
│  │  (Next.js)   │                          │     (FastAPI)                │ │
│  │  Static Web  │                          │     Container Apps           │ │
│  └──────────────┘                          └──────────────────────────────┘ │
│                                                        │                     │
│                                                        ▼                     │
│                                            ┌──────────────────────────────┐ │
│                                            │     AI Poll Generator        │ │
│                                            │     (Azure OpenAI)           │ │
│                                            │     GPT-4o-mini              │ │
│                                            └──────────────────────────────┘ │
│                                                        │                     │
│                                                        ▼                     │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                           Data Layer                                  │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │   │
│  │  │Azure Tables│  │ PostgreSQL │  │ Key Vault  │  │  Blob Storage  │  │   │
│  │  │  (Votes)   │  │  (Users,   │  │  (Secrets) │  │   (Assets)     │  │   │
│  │  │            │  │   Polls)   │  │            │  │                │  │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     Supporting Services                               │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │   │
│  │  │Communication│ │   Email    │  │    Log     │  │  Container     │  │   │
│  │  │ Services   │  │  Services  │  │  Analytics │  │  Registry      │  │   │
│  │  │   (SMS)    │  │            │  │            │  │                │  │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Privacy & Security Design

### Vote Privacy Architecture

TruePulse employs a **cryptographic vote separation** model:

1. **Vote Submission**: When a user votes, the system generates a one-way hash combining the user ID and poll ID
2. **Vote Storage**: Only the hash and vote choice are stored in Azure Tables (not the user ID)
3. **Duplicate Prevention**: The hash prevents duplicate voting without tracking who voted what
4. **Demographic Aggregation**: Demographics are linked to aggregated results, not individual votes

```
User Vote → [UserID + PollID + Salt] → SHA-256 Hash → Store(Hash, Choice)
                                              ↓
                                    Cannot reverse to User
```

### Data Security Measures

- **Encryption at Rest**: Azure Storage encryption with optional Customer Managed Keys (CMK)
- **Encryption in Transit**: TLS 1.3 for all communications
- **Key Management**: Azure Key Vault for all secrets and encryption keys
- **Access Control**: Role-based access with Managed Identities
- **Audit Logging**: Complete audit trail in Log Analytics

## Project Structure

```
TruePulse/
├── src/
│   ├── backend/              # FastAPI backend services
│   │   ├── api/             # API routes and endpoints
│   │   ├── core/            # Configuration and security
│   │   ├── models/          # SQLAlchemy database models
│   │   ├── repositories/    # Data access layer
│   │   ├── services/        # Business services
│   │   └── ai/              # AI poll generation
│   └── frontend/            # Next.js frontend
│       ├── app/            # App router pages
│       ├── components/     # React components
│       └── lib/            # Utilities
├── infra/                   # Azure Bicep infrastructure
│   └── modules/            # Modular Bicep templates
├── docs/                    # Documentation
└── .github/                 # GitHub Actions CI/CD
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 16+ (local) or Azure PostgreSQL
- Azure CLI (for deployment)

### Local Development

```bash
# Clone the repository
git clone https://github.com/KevinRabun/TruePulse.git
cd TruePulse

# Backend setup
cd src/backend
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
cp .env.example .env  # Configure your environment

# Frontend setup
cd ../frontend
npm install
cp .env.example .env.local  # Configure your environment

# Start development servers
# Terminal 1: Backend
cd src/backend && uvicorn main:app --reload

# Terminal 2: Frontend
cd src/frontend && npm run dev
```

### Deploy to Azure

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed deployment instructions.

## API Documentation

See [docs/API.md](docs/API.md) for the complete API reference.

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/polls` | GET | List active polls |
| `/api/v1/polls/{id}/results` | GET | Get aggregated results |
| `/api/v1/polls/{id}/vote` | POST | Submit a vote (authenticated) |
| `/api/v1/users/me` | GET | Current user profile |
| `/api/v1/gamification/progress` | GET | User gamification progress |

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)** - see the [LICENSE](LICENSE) file for details.

### Trademark

"TruePulse" is a trademark. While you can freely use, modify, and distribute the code under AGPL, you cannot market your own product or service using the TruePulse name. See [TRADEMARK.md](TRADEMARK.md) for details.

## Security

For security concerns, please see [SECURITY.md](SECURITY.md).
