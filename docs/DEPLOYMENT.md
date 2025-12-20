# TruePulse Deployment Guide

This guide covers deploying TruePulse to Azure using Infrastructure as Code (Bicep).

## Prerequisites

- **Azure CLI** (version 2.50+)
- **Azure Subscription** with Owner or Contributor role
- **GitHub Account** (for CI/CD)
- **Domain** (optional, for custom domain setup)

## Architecture Overview

TruePulse deploys the following Azure resources:

| Resource | Purpose |
|----------|---------|
| **Container Apps** | Hosts the FastAPI backend |
| **Static Web App** | Hosts the Next.js frontend |
| **PostgreSQL Flexible Server** | Primary database for users, polls |
| **Storage Account (Tables)** | Privacy-preserving vote storage |
| **Storage Account (Blobs)** | Static assets and exports |
| **Azure OpenAI** | AI poll generation (GPT-4o-mini) |
| **Key Vault** | Secrets management |
| **Communication Services** | SMS verification |
| **Email Communication Services** | Email verification |
| **Container Registry** | Docker image storage |
| **Log Analytics** | Monitoring and diagnostics |
| **Virtual Network** | Network isolation |

## Deployment Methods

### Option 1: GitHub Actions (Recommended)

The repository includes CI/CD workflows that automatically deploy based on these rules:

| Trigger | Target Environment | Requirements |
|---------|-------------------|--------------|
| Push to `main` branch | **dev** | All CI tests must pass |
| Release published | **prod** | All CI tests must pass |
| Manual dispatch | Selected environment | N/A (can force deploy) |

#### Deployment Flow

```
┌─────────────┐     ┌─────────┐     ┌─────────────────┐
│ Push to     │────▶│ CI      │────▶│ Deploy to DEV   │
│ main        │     │ Passes  │     │ (automatic)     │
└─────────────┘     └─────────┘     └─────────────────┘

┌─────────────┐     ┌─────────┐     ┌─────────────────┐
│ Create      │────▶│ CI      │────▶│ Deploy to PROD  │
│ Release     │     │ Passes  │     │ (automatic)     │
└─────────────┘     └─────────┘     └─────────────────┘
```

#### Creating a Production Release

To deploy to production, create a GitHub release:

```bash
# Tag the release
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# Then create a release in GitHub UI or CLI:
gh release create v1.0.0 --title "v1.0.0" --notes "Release notes here"
```

#### 1. Configure GitHub Secrets

Add the following secrets to your GitHub repository:

| Secret | Description |
|--------|-------------|
| `AZURE_CLIENT_ID` | Service principal (app registration) client ID |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Your Azure subscription ID |
| `POSTGRES_PASSWORD` | PostgreSQL admin password (secure, 16+ chars) |
| `JWT_SECRET_KEY` | Secret for JWT token signing (32+ chars) |
| `VOTE_HASH_SECRET` | Secret for vote hashing (32+ chars) |
| `NEWSDATA_API_KEY` | NewsData.io API key (optional) |
| `NEWSAPI_ORG_KEY` | NewsAPI.org API key (optional) |
| `COMMUNICATION_SENDER_NUMBER` | Azure Communication Services phone number |

#### 2. Create Azure Service Principal (Federated Credentials)

The workflow uses OIDC federation for passwordless authentication:

```bash
# Create app registration
az ad app create --display-name "truepulse-github"

# Get the app ID
APP_ID=$(az ad app list --display-name "truepulse-github" --query "[0].appId" -o tsv)

# Create service principal
az ad sp create --id $APP_ID

# Get service principal object ID
SP_OBJECT_ID=$(az ad sp show --id $APP_ID --query "id" -o tsv)

# Grant Contributor role on subscription
az role assignment create \
  --assignee $SP_OBJECT_ID \
  --role "Contributor" \
  --scope /subscriptions/<subscription-id>

# Grant User Access Administrator role (for role assignments)
az role assignment create \
  --assignee $SP_OBJECT_ID \
  --role "User Access Administrator" \
  --scope /subscriptions/<subscription-id>

# Create federated credential for GitHub Actions
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:<owner>/TruePulse:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# Create federated credential for environment (optional, for environment protection)
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "github-dev-env",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:<owner>/TruePulse:environment:dev",
    "audiences": ["api://AzureADTokenExchange"]
  }'

echo "Add these to GitHub Secrets:"
echo "AZURE_CLIENT_ID: $APP_ID"
echo "AZURE_TENANT_ID: $(az account show --query tenantId -o tsv)"
echo "AZURE_SUBSCRIPTION_ID: $(az account show --query id -o tsv)"
```

#### 3. Create GitHub Environment

1. Go to Repository Settings → Environments
2. Create environment: `dev` (and optionally `staging`, `prod`)
3. Add environment-specific secrets if needed

#### 4. Trigger Deployment

Push to `main` branch or manually trigger the workflow:

```bash
git push origin main

# Or use GitHub CLI
gh workflow run deploy.yml -f environment=dev
```

### Option 2: Azure CLI Deployment

#### 1. Login to Azure

```bash
az login
az account set --subscription <subscription-id>
```

#### 2. Create Resource Group

```bash
az group create \
  --name truepulse-rg \
  --location eastus2
```

#### 3. Deploy Infrastructure

```bash
cd infra

# Deploy with parameter file
az deployment group create \
  --resource-group truepulse-rg \
  --template-file main.bicep \
  --parameters main.parameters.dev.json \
  --parameters postgresAdminPassword='<secure-password>'
```

#### 4. Build and Push Container Image

```bash
# Get ACR credentials
ACR_NAME=$(az acr list -g truepulse-rg --query "[0].name" -o tsv)
az acr login --name $ACR_NAME

# Build and push backend
cd src/backend
docker build -t $ACR_NAME.azurecr.io/truepulse-api:latest .
docker push $ACR_NAME.azurecr.io/truepulse-api:latest
```

#### 5. Deploy Frontend to Static Web App

The frontend uses Next.js static export (`output: 'export'`) for SWA deployment:

```bash
cd src/frontend

# Build with API URL (include /api/v1 suffix!)
NEXT_PUBLIC_API_URL=https://<container-app-fqdn>/api/v1 npm run build

# Deploy using SWA CLI
npx @azure/static-web-apps-cli deploy ./out \
  --deployment-token <swa-deployment-token> \
  --env production

# Or use Azure CLI
az staticwebapp deploy \
  --name <swa-name> \
  --resource-group <rg-name> \
  --app-location ./out
```

> **Important:** The `NEXT_PUBLIC_API_URL` must include the `/api/v1` suffix since the backend API routes are prefixed.

## Environment Configuration

### Backend Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `AZURE_STORAGE_CONNECTION_STRING` | Storage account connection | Yes |
| `AZURE_OPENAI_ENDPOINT` | OpenAI endpoint URL | Yes |
| `AZURE_OPENAI_API_KEY` | OpenAI API key | Yes |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Model deployment name | Yes |
| `JWT_SECRET` | JWT signing secret | Yes |
| `API_SECRET_KEY` | API secret key | Yes |
| `AZURE_KEY_VAULT_URL` | Key Vault URL | Yes |
| `COMMUNICATION_SERVICES_CONNECTION_STRING` | SMS service connection | Yes |
| `EMAIL_CONNECTION_STRING` | Email service connection | Yes |
| `CORS_ORIGINS` | Allowed CORS origins | Yes |

### Frontend Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXT_PUBLIC_API_URL` | Backend API URL (must include `/api/v1` suffix) | Yes |
| `NEXT_PUBLIC_APP_ENV` | Environment name (dev/staging/prod) | Yes |

## Infrastructure Customization

### Parameter File Structure

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "environmentName": { "value": "dev" },
    "location": { "value": "eastus2" },
    "postgresSkuName": { "value": "Standard_B1ms" },
    "containerAppCpu": { "value": "0.5" },
    "containerAppMemory": { "value": "1Gi" }
  }
}
```

### Scaling Configuration

Adjust Container Apps scaling in `main.bicep`:

```bicep
minReplicas: 1      // Minimum instances
maxReplicas: 10     // Maximum instances
```

### Database Sizing

| Environment | SKU | vCores | Storage |
|-------------|-----|--------|---------|
| Development | Standard_B1ms | 1 | 32 GB |
| Staging | Standard_B2s | 2 | 64 GB |
| Production | Standard_D4s_v3 | 4 | 256 GB |

## Post-Deployment Tasks

### 1. Initialize Database

```bash
# Connect to PostgreSQL
psql "host=<server>.postgres.database.azure.com dbname=truepulse user=truepulseadmin"

# Run initialization script
\i scripts/init-db.sql
```

### 2. Seed Initial Data

```bash
# From backend directory with proper environment
python -m scripts.seed_achievements
python -m scripts.seed_locations
```

### 3. Configure Custom Domain (Optional)

```bash
# Add custom domain to Static Web App
az staticwebapp hostname set \
  --name truepulse-swa \
  --resource-group truepulse-rg \
  --hostname app.truepulse.net

# Add custom domain to Container App
az containerapp hostname add \
  --name truepulse-api \
  --resource-group truepulse-rg \
  --hostname api.truepulse.net
```

### 4. Configure DNS

Add the following DNS records:

| Type | Name | Value |
|------|------|-------|
| CNAME | app | `<swa-hostname>.azurestaticapps.net` |
| CNAME | api | `<container-app>.azurecontainerapps.io` |
| TXT | _dnsauth.app | `<validation-token>` |

## Monitoring

### Log Analytics Queries

View backend logs:
```kusto
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "truepulse-api"
| project TimeGenerated, Log_s
| order by TimeGenerated desc
```

View error rates:
```kusto
ContainerAppConsoleLogs_CL
| where Log_s contains "ERROR"
| summarize count() by bin(TimeGenerated, 1h)
```

### Health Checks

- Backend: `GET /health`
- Database: Check connection in Container App logs

## Troubleshooting

### Container App Not Starting

1. Check container logs:
   ```bash
   az containerapp logs show -n truepulse-api -g truepulse-rg
   ```

2. Verify environment variables:
   ```bash
   az containerapp show -n truepulse-api -g truepulse-rg --query "properties.template.containers[0].env"
   ```

### Database Connection Issues

1. Verify firewall rules allow Container App subnet
2. Check connection string format
3. Verify PostgreSQL is running:
   ```bash
   az postgres flexible-server show -n truepulse-pg -g truepulse-rg --query "state"
   ```

### Static Web App Build Failures

1. Check build logs in GitHub Actions
2. Verify `next.config.js` output settings
3. Ensure all environment variables are set

## Cost Optimization

### Development Environment

- Use B-series VMs for PostgreSQL
- Set Container Apps to scale to 0
- Use consumption plan where possible

### Production Considerations

- Enable autoscaling based on load
- Consider reserved capacity for predictable workloads
- Use Azure Hybrid Benefit if applicable

## Security Checklist

- [ ] All secrets stored in Key Vault
- [ ] PostgreSQL SSL enforced
- [ ] Container App ingress restricted
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] Audit logging enabled
- [ ] Managed identities used where possible
