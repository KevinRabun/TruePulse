# TruePulse Deployment Guide

This guide covers deploying TruePulse to Azure using the provided Bicep templates and GitHub Actions workflows.

## Prerequisites

### Azure Resources
- Azure subscription with sufficient permissions
- Azure CLI installed and configured
- Owner or Contributor role on the subscription

### GitHub
- GitHub repository with Actions enabled
- Repository secrets configured

### Local Tools
- Azure CLI 2.50+
- Bicep CLI (or Azure CLI with Bicep extension)
- Docker (for local testing)

## Deployment Architecture

```
Production Environment
├── Resource Group: rg-truepulse-prod
│   ├── Virtual Network (Private networking)
│   ├── Log Analytics Workspace (Centralized logging)
│   ├── Key Vault (Secrets management)
│   ├── Container Registry (Docker images)
│   ├── Container Apps Environment
│   │   └── Container App: API
│   ├── PostgreSQL Flexible Server
│   ├── Cosmos DB Account
│   ├── Redis Cache
│   └── Static Web App (Frontend)
```

## Step-by-Step Deployment

### 1. Configure Azure Service Principal

Create a service principal for GitHub Actions:

```bash
# Create service principal
az ad sp create-for-rbac \
  --name "sp-truepulse-cicd" \
  --role contributor \
  --scopes /subscriptions/<subscription-id> \
  --sdk-auth
```

Save the JSON output for GitHub secrets.

### 2. Configure GitHub Secrets

Navigate to your repository → Settings → Secrets and variables → Actions.

Add the following secrets:

| Secret Name | Description |
|-------------|-------------|
| `AZURE_CLIENT_ID` | Service principal client ID |
| `AZURE_CLIENT_SECRET` | Service principal secret |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `POSTGRES_PASSWORD` | PostgreSQL admin password |
| `JWT_SECRET_KEY` | JWT signing secret (32+ chars) |
| `VOTE_HASH_SECRET` | Vote anonymization secret |
| `AI_FOUNDRY_API_KEY` | Azure AI Foundry API key |
| `AI_FOUNDRY_ENDPOINT` | Azure AI Foundry endpoint URL |

### 3. Configure GitHub Environments

Create the following environments in GitHub:

1. **dev** - Development environment
2. **staging** - Staging environment  
3. **prod** - Production environment (with required reviewers)

### 4. Initial Infrastructure Deployment

For the first deployment, run manually:

```bash
# Login to Azure
az login

# Set subscription
az account set --subscription <subscription-id>

# Deploy infrastructure
az deployment sub create \
  --location eastus2 \
  --template-file infra/main.bicep \
  --parameters environmentName=dev \
  --parameters postgresAdminPassword='<your-password>' \
  --parameters jwtSecretKey='<your-jwt-secret>' \
  --parameters voteHashSecret='<your-vote-secret>' \
  --parameters aiFoundryApiKey='<your-ai-key>' \
  --parameters aiFoundryEndpoint='<your-ai-endpoint>'
```

### 5. Build and Push Initial Container Image

```bash
# Get ACR login server
ACR_SERVER=$(az acr list -g rg-truepulse-dev --query '[0].loginServer' -o tsv)

# Login to ACR
az acr login --name ${ACR_SERVER%.azurecr.io}

# Build and push
cd src/backend
docker build -t $ACR_SERVER/truepulse-api:latest .
docker push $ACR_SERVER/truepulse-api:latest
```

### 6. Run Database Migrations

```bash
# Get Container App name
CA_NAME=$(az containerapp list -g rg-truepulse-dev --query '[0].name' -o tsv)

# Execute migrations
az containerapp exec \
  --name $CA_NAME \
  --resource-group rg-truepulse-dev \
  --command "alembic upgrade head"
```

### 7. Deploy Frontend

```bash
# Get Static Web App deployment token
SWA_TOKEN=$(az staticwebapp secrets list \
  --name <swa-name> \
  --resource-group rg-truepulse-dev \
  --query 'properties.apiKey' -o tsv)

# Build frontend
cd src/frontend
npm ci
npm run build

# Deploy using SWA CLI
npx @azure/static-web-apps-cli deploy out \
  --deployment-token $SWA_TOKEN
```

## Environment Configuration

### Development (`dev`)

| Resource | SKU/Config |
|----------|------------|
| PostgreSQL | B2s (Burstable) |
| Redis | Basic C0 |
| Container App | Min: 1, Max: 3 |
| Cosmos DB | Serverless |

### Staging (`staging`)

| Resource | SKU/Config |
|----------|------------|
| PostgreSQL | D2ds_v5 |
| Redis | Standard C1 |
| Container App | Min: 1, Max: 5 |
| Cosmos DB | Provisioned 400 RU/s |

### Production (`prod`)

| Resource | SKU/Config |
|----------|------------|
| PostgreSQL | D4ds_v5 + Zone-redundant HA |
| Redis | Premium P1 + Zone-redundant |
| Container App | Min: 2, Max: 10 |
| Cosmos DB | Provisioned autoscale |

## CI/CD Pipeline

### Workflow: `ci.yml`

Triggers on pull requests:
- Backend linting (Ruff)
- Backend type checking (MyPy)
- Backend tests (Pytest)
- Frontend linting (ESLint)
- Frontend type checking (TypeScript)
- Frontend tests (Jest)
- Infrastructure validation (Bicep)
- Security scanning (Trivy, Gitleaks)

### Workflow: `deploy.yml`

Triggers on push to `main` or manual dispatch:

1. **Infrastructure** - Deploys/updates Bicep templates
2. **Build Backend** - Builds and pushes Docker image
3. **Deploy Backend** - Updates Container App
4. **Deploy Frontend** - Builds and deploys to SWA
5. **Run Migrations** - Executes Alembic migrations
6. **Integration Tests** - Validates deployment

## Monitoring & Observability

### Log Analytics Queries

**API Errors:**
```kusto
ContainerAppConsoleLogs_CL
| where Log_s contains "ERROR"
| project TimeGenerated, ContainerName_s, Log_s
| order by TimeGenerated desc
| take 100
```

**Request Latency:**
```kusto
ContainerAppConsoleLogs_CL
| where Log_s contains "request completed"
| extend latency = extract("latency=([0-9.]+)", 1, Log_s)
| summarize avg(todouble(latency)), percentile(todouble(latency), 95) by bin(TimeGenerated, 5m)
```

### Alerts

Configure Azure Monitor alerts for:
- Container App restart count > 3
- Response latency P95 > 2s
- Error rate > 5%
- Database connection failures

### Application Insights (Optional)

Enable Application Insights integration:

```python
# In backend main.py
from azure.monitor.opentelemetry import configure_azure_monitor

configure_azure_monitor(
    connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
)
```

## Scaling

### Horizontal Scaling

Container Apps auto-scaling is configured based on:
- HTTP concurrency: 100 concurrent requests per replica
- Memory usage: 80% threshold
- Custom metrics via KEDA

Adjust in `containerAppApi.bicep`:
```bicep
scale: {
  minReplicas: environmentName == 'prod' ? 2 : 1
  maxReplicas: environmentName == 'prod' ? 10 : 3
  rules: [
    {
      name: 'http-scaling'
      http: {
        metadata: {
          concurrentRequests: '100'
        }
      }
    }
  ]
}
```

### Vertical Scaling

Upgrade PostgreSQL:
```bash
az postgres flexible-server update \
  --resource-group rg-truepulse-prod \
  --name <server-name> \
  --sku-name Standard_D8ds_v5
```

## Disaster Recovery

### Backup Strategy

| Resource | Backup | Retention |
|----------|--------|-----------|
| PostgreSQL | Geo-redundant automatic | 35 days |
| Cosmos DB | Continuous backup | 7 days |
| Key Vault | Soft-delete + purge protection | 90 days |

### Recovery Procedures

**PostgreSQL Point-in-Time Restore:**
```bash
az postgres flexible-server restore \
  --resource-group rg-truepulse-prod \
  --name <new-server-name> \
  --source-server <source-server-name> \
  --restore-time "2024-01-15T00:00:00Z"
```

**Cosmos DB Restore:**
```bash
az cosmosdb restore \
  --account-name <new-account-name> \
  --resource-group rg-truepulse-prod \
  --target-database-account-name <source-account> \
  --restore-timestamp "2024-01-15T00:00:00Z"
```

## Security Checklist

- [ ] All secrets stored in Key Vault
- [ ] Managed identities used for Azure service auth
- [ ] Private endpoints enabled for data services
- [ ] Network isolation via VNet
- [ ] TLS 1.2+ enforced everywhere
- [ ] WAF enabled for public endpoints
- [ ] Security scanning in CI pipeline
- [ ] Dependency updates automated (Dependabot)
- [ ] Access logs enabled and monitored
- [ ] Incident response plan documented

## Troubleshooting

### Common Issues

**Container App won't start:**
```bash
# Check logs
az containerapp logs show \
  --name <app-name> \
  --resource-group <rg-name> \
  --follow
```

**Database connection errors:**
```bash
# Verify firewall rules
az postgres flexible-server firewall-rule list \
  --resource-group <rg-name> \
  --name <server-name>

# Test connectivity
az postgres flexible-server connect \
  --name <server-name> \
  --admin-user <admin>
```

**Static Web App deployment fails:**
```bash
# Check deployment logs
az staticwebapp show \
  --name <swa-name> \
  --resource-group <rg-name>
```

## Support

For deployment issues:
- 📧 devops@truepulse.dev
- 📚 [Azure Documentation](https://docs.microsoft.com/azure)
- 🐛 [GitHub Issues](https://github.com/yourusername/truepulse/issues)
