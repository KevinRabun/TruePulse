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

The repository includes CI/CD workflows that automatically deploy on push to `main`.

#### 1. Configure GitHub Secrets

Add the following secrets to your GitHub repository:

| Secret | Description |
|--------|-------------|
| `AZURE_CREDENTIALS` | Service principal JSON for Azure auth |
| `AZURE_SUBSCRIPTION_ID` | Your Azure subscription ID |
| `AZURE_RESOURCE_GROUP` | Target resource group name |
| `JWT_SECRET` | Secret for JWT token signing |
| `API_SECRET_KEY` | Backend API secret |
| `POSTGRES_ADMIN_PASSWORD` | PostgreSQL admin password |
| `OPENAI_API_KEY` | Azure OpenAI API key |

#### 2. Create Azure Service Principal

```bash
# Create service principal with Contributor role
az ad sp create-for-rbac \
  --name "truepulse-github" \
  --role Contributor \
  --scopes /subscriptions/<subscription-id> \
  --sdk-auth

# Copy the JSON output to AZURE_CREDENTIALS secret
```

#### 3. Trigger Deployment

Push to `main` branch or manually trigger the workflow:

```bash
git push origin main
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

```bash
cd src/frontend
npm run build

# Use SWA CLI
npx @azure/static-web-apps-cli deploy \
  --deployment-token <swa-deployment-token> \
  --app-location ./out
```

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
| `NEXT_PUBLIC_API_URL` | Backend API URL | Yes |
| `NEXT_PUBLIC_APP_URL` | Frontend URL | Yes |

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
