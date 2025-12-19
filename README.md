# TruePulse 🗳️

> Unbiased polling powered by AI-driven current events aggregation

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)
[![Azure](https://img.shields.io/badge/Hosted%20on-Azure-0078D4)](https://azure.microsoft.com)

## Overview

TruePulse is a privacy-first polling platform that automatically generates unbiased poll questions from aggregated current events. The platform enables public viewing of aggregated results while ensuring individual vote privacy and data security.

### Key Features

- 🤖 **AI-Powered Poll Generation**: Automatically aggregates current events and generates unbiased poll questions
- 🔒 **Privacy-First Architecture**: Individual votes cannot be traced back to users
- 🎮 **Gamified Experience**: Earn points and badges for participation and demographic enrichment
- 📊 **Public Results**: Anyone can view aggregated polling results
- 🔐 **Authenticated Voting**: Only signed-in users can vote (one vote per poll)
- 🏢 **Enterprise API**: Corporations and governments can subscribe to aggregated polling data
- 📱 **Responsive Design**: Works seamlessly across all devices

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TruePulse Architecture                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────────┐ │
│  │   Frontend   │────▶│   API GW     │────▶│     Backend Services         │ │
│  │  (Next.js)   │     │ (Azure APIM) │     │      (FastAPI)               │ │
│  └──────────────┘     └──────────────┘     └──────────────────────────────┘ │
│         │                    │                          │                    │
│         │                    │                          ▼                    │
│         │                    │              ┌──────────────────────────────┐ │
│         │                    │              │     AI Poll Generator        │ │
│         │                    │              │     (Azure OpenAI)           │ │
│         │                    │              └──────────────────────────────┘ │
│         │                    │                          │                    │
│         ▼                    ▼                          ▼                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        Data Layer                                     │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │   │
│  │  │Azure Tables│  │ PostgreSQL │  │ Key Vault  │  │  Blob Storage  │  │   │
│  │  │  (Votes)   │  │  (Users)   │  │  (Secrets) │  │   (Assets)     │  │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     Security & Identity                               │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │   │
│  │  │ Entra ID   │  │ CMK (HSM)  │  │  WAF/DDoS  │  │  App Insights  │  │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Privacy & Security Design

### Vote Privacy Architecture

TruePulse employs a **cryptographic vote separation** model:

1. **Vote Submission**: When a user votes, the system generates a one-way hash combining the user ID and poll ID
2. **Vote Storage**: Only the hash and the vote choice are stored (not the user ID)
3. **Duplicate Prevention**: The hash prevents duplicate voting without tracking who voted what
4. **Demographic Aggregation**: Demographics are linked to aggregated results, not individual votes

```
User Vote → [UserID + PollID] → SHA-256 Hash → Store(Hash, Choice)
                                      ↓
                            Cannot reverse to User
```

### Data Security Measures

- **Encryption at Rest**: Customer Managed Keys (CMK) with automatic 90-day rotation
- **Encryption in Transit**: TLS 1.3 for all communications
- **Key Management**: Azure Key Vault (Premium SKU) for all secrets and encryption keys
- **Access Control**: Role-based access with Managed Identities
- **Audit Logging**: Complete audit trail in Azure Monitor
- **DDoS Protection**: Azure Front Door with WAF rules
- **Data Residency**: Configurable regional data storage

## Project Structure

```
TruePulse/
├── src/
│   ├── backend/              # FastAPI backend services
│   │   ├── api/             # API routes and endpoints
│   │   ├── core/            # Core business logic
│   │   ├── models/          # Database models
│   │   ├── services/        # Business services
│   │   └── ai/              # AI poll generation
│   ├── frontend/            # Next.js frontend
│   │   ├── app/            # App router pages
│   │   ├── components/     # React components
│   │   └── lib/            # Utilities
│   └── shared/              # Shared types and utilities
├── infra/                   # Azure Bicep infrastructure
├── tests/                   # Test suites
├── docs/                    # Documentation
└── .github/                 # GitHub Actions CI/CD
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- Azure CLI
- Azure Developer CLI (azd)

### Local Development

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/TruePulse.git
cd TruePulse

# Backend setup
cd src/backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Frontend setup
cd ../frontend
npm install

# Start development servers
# Terminal 1: Backend
cd src/backend && uvicorn main:app --reload

# Terminal 2: Frontend
cd src/frontend && npm run dev
```

### Deploy to Azure

```bash
# Initialize Azure Developer CLI
azd init

# Provision and deploy
azd up
```

## API Documentation

### Public Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/polls` | GET | List active polls |
| `/api/polls/{id}/results` | GET | Get aggregated results |
| `/api/events` | GET | Current events feed |

### Authenticated Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/polls/{id}/vote` | POST | Submit a vote |
| `/api/user/profile` | GET/PUT | User profile management |
| `/api/user/achievements` | GET | Gamification achievements |

### Enterprise API (Subscription Required)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analytics/polls` | GET | Aggregated polling data |
| `/api/v1/analytics/demographics` | GET | Demographic insights |
| `/api/v1/analytics/trends` | GET | Trend analysis |

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)** - see the [LICENSE](LICENSE) file for details.

### Trademark

"TruePulse" is a trademark. While you can freely use, modify, and distribute the code under AGPL, you cannot market your own product or service using the TruePulse name. See [TRADEMARK.md](TRADEMARK.md) for details.

## Security

For security concerns, please see [SECURITY.md](SECURITY.md) or contact security@truepulse.io.
