# TruePulse Infrastructure

This directory contains the Azure infrastructure as code (IaC) using Bicep templates following the Azure Well-Architected Framework (WAF) best practices.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Azure Subscription                                 │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Resource Group (rg-truepulse-{env})                │  │
│  │                                                                       │  │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐   │  │
│  │  │  Static Web App │───▶│  Container App  │───▶│   PostgreSQL    │   │  │
│  │  │    (Frontend)   │    │     (API)       │    │  Flexible Server│   │  │
│  │  └─────────────────┘    └────────┬────────┘    │   🔐 CMK        │   │  │
│  │                                  │             └─────────────────┘   │  │
│  │                    ┌─────────────┼─────────────┐                     │  │
│  │                    ▼             ▼             ▼                     │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │  │
│  │  │ Storage Account │  │  Azure OpenAI   │  │   Key Vault     │      │  │
│  │  │ (Tables+Blobs)  │  │(Poll Generator) │  │(Secrets + CMK)  │      │  │
│  │  │   🔐 CMK        │  └─────────────────┘  │   Premium SKU   │      │  │
│  │  └─────────────────┘                       └─────────────────┘      │  │
│  │                                                                       │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │  │
│  │  │ Communication   │  │  Email Service  │  │ Container Reg   │      │  │
│  │  │ Services (SMS)  │  │  (Verification) │  │     (ACR)       │      │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘      │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────┐     │  │
│  │  │                    Virtual Network                          │     │  │
│  │  │  ┌─────────────────────┐  ┌─────────────────────────────┐  │     │  │
│  │  │  │ Container Apps      │  │  Private Endpoints Subnet   │  │     │  │
│  │  │  │ Subnet (/23)        │  │  (PostgreSQL, Storage, etc.)│  │     │  │
│  │  │  └─────────────────────┘  └─────────────────────────────┘  │     │  │
│  │  └─────────────────────────────────────────────────────────────┘     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Security: Customer Managed Keys (CMK)

TruePulse uses **Customer Managed Keys** for encryption at rest, ensuring maximum protection for voting data:

| Service | Data Protected | Key Rotation |
|---------|----------------|--------------|
| **Storage Account** | Vote records, tokens, rate limits | 90 days (automatic) |
| **PostgreSQL** | User accounts, polls, achievements | 90 days (automatic) |

### CMK Benefits for a Voting Platform:
- **Key custody control** - You own and control encryption keys
- **Audit trail** - All key access logged in Key Vault
- **Revocation capability** - Disable keys to immediately render data unreadable
- **Compliance** - Meets HIPAA, PCI-DSS, and SOC 2 requirements

### Disabling CMK (cost optimization for dev)
```bash
az deployment sub create \
  --parameters enableCMK=false
```

## Resources Deployed

| Resource | Purpose | Module |
|----------|---------|--------|
| **Static Web App** | React frontend hosting | `staticWebApp.bicep` |
| **Container App** | FastAPI backend | `containerAppApi.bicep` |
| **PostgreSQL Flexible** | User data, polls, gamification | `postgres.bicep` |
| **Storage Account** | Votes (Azure Tables), blob storage, token management | `storageAccount.bicep` |
| **Azure OpenAI** | AI-powered poll generation | `azureOpenAI.bicep` |
| **Key Vault** | Secrets management | `keyVault.bicep` |
| **Container Registry** | Docker images | `containerRegistry.bicep` |
| **Communication Services** | SMS notifications | `communicationServices.bicep` |
| **Email Services** | Email verification | `emailServices.bicep` |
| **DNS Zone** | Custom domain management | `dnsZone.bicep` |
| **Log Analytics** | Centralized logging | `logAnalytics.bicep` |
| **Virtual Network** | Network isolation | `network.bicep` |

## Prerequisites

1. **Azure CLI** (v2.50+)
2. **Bicep CLI** (v0.22+) or Azure CLI with Bicep extension
3. **Azure Subscription** with Contributor access
4. **Service Principal** or Azure CLI authentication

## Deployment

### Option 1: Azure CLI

```bash
# Login to Azure
az login

# Set subscription
az account set --subscription "<subscription-id>"

# Deploy to dev environment
az deployment sub create \
  --location eastus \
  --template-file main.bicep \
  --parameters environmentName=dev \
               postgresAdminUsername=truepulseadmin \
               postgresAdminPassword="<secure-password>" \
               jwtSecretKey="<32-char-secret>" \
               voteHashSecret="<32-char-secret>"
```

### Option 2: Azure Developer CLI (azd)

```bash
# Initialize project
azd init

# Provision infrastructure
azd provision

# Deploy application
azd deploy
```

### Option 3: GitHub Actions (CI/CD)

See `.github/workflows/infra.yml` for automated deployment.

## Parameters

### Required Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `postgresAdminUsername` | PostgreSQL admin username | `truepulseadmin` |
| `postgresAdminPassword` | PostgreSQL admin password | Secure string |
| `jwtSecretKey` | JWT signing key (32+ chars) | Secure string |
| `voteHashSecret` | Vote anonymization secret | Secure string |

### Optional Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `environmentName` | `dev` | Environment (dev/staging/prod) |
| `location` | `eastus` | Azure region |
| `prefix` | `truepulse` | Resource name prefix |
| `deployAzureOpenAI` | `true` | Deploy Azure OpenAI (set false if using external AI) |
| `newsDataApiKey` | `""` | NewsData.io API key |
| `newsApiOrgKey` | `""` | NewsAPI.org API key |
| `communicationSenderNumber` | `""` | SMS sender phone number (see post-deployment) |
| `emailSenderAddress` | `""` | Email sender address (auto-configured) |
| `customDomain` | `truepulse.net` | Custom domain for the application |
| `enableCustomDomain` | `true` | Enable custom domain configuration |
| `enableCMK` | `true` | Enable Customer Managed Keys for data encryption |

---

## Custom Domain Configuration

When `enableCustomDomain` is set to `true`, the infrastructure provisions:

- **Azure DNS Zone** for `truepulse.net` with:
  - `truepulse.net` → Static Web App (apex domain via alias record)
  - `www.truepulse.net` → Static Web App (CNAME)
  - `api.truepulse.net` → Container App API (CNAME)

> **Note:** The domain must be purchased separately from a registrar (e.g., Cloudflare, Namecheap, GoDaddy). Azure DNS Zone provides DNS hosting, not domain registration.

### DNS Setup (Post-Deployment)

After deployment, transfer DNS hosting from your registrar to Azure:

1. **Get the Azure nameservers from deployment output:**
   ```bash
   # From deployment output
   az deployment sub show \
     --name "main" \
     --query "properties.outputs.dnsZoneNameServers.value" -o tsv
   ```
   
   You'll get 4 nameservers like:
   ```
   ns1-03.azure-dns.com
   ns2-03.azure-dns.net
   ns3-03.azure-dns.org
   ns4-03.azure-dns.info
   ```

2. **Update nameservers at Cloudflare:**
   
   Since Cloudflare is the registrar (not just DNS), you need to change nameservers:
   
   a. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com)
   b. Select your domain (`truepulse.net`)
   c. Go to **DNS** → **Records**
   d. At the bottom, click **Advanced** → **Change Nameservers**
   e. Select **Custom nameservers**
   f. Enter the 4 Azure nameservers from step 1
   g. Save changes
   
   > ⚠️ This transfers DNS management from Cloudflare to Azure. You'll lose Cloudflare's proxy/CDN features but gain unified Azure management.

3. **Wait for DNS propagation** (typically 1-24 hours, can take up to 48 hours)

4. **Verify DNS is working:**
   ```bash
   # Check nameservers are updated
   nslookup -type=NS truepulse.net
   
   # Check records resolve
   nslookup truepulse.net
   nslookup www.truepulse.net
   nslookup api.truepulse.net
   ```

### Custom Domain URLs

Once configured, your application will be accessible at:
- **Frontend:** https://truepulse.net and https://www.truepulse.net
- **API:** https://api.truepulse.net

---

## Post-Deployment Steps

### ⚠️ Important: SMS and Email Configuration

Azure Communication Services (ACS) has a **chicken-and-egg** situation:
- Phone numbers must be **purchased after** the ACS resource is created
- The phone number cannot be known at deployment time

### Step 1: Purchase a Phone Number (SMS)

After deployment, purchase a phone number via Azure Portal or CLI:

```bash
# Get the communication service name from deployment output
RESOURCE_GROUP="rg-truepulse-dev"
ACS_NAME=$(az communication service list -g $RESOURCE_GROUP --query "[0].name" -o tsv)

# List available phone numbers (US toll-free example)
az communication phonenumber list-available \
  --country-code US \
  --phone-plan-type TollFree \
  --assignment-type Application \
  --capabilities "SMS=Outbound" \
  --resource-group $RESOURCE_GROUP \
  --connection-string "$(az communication service list-key -n $ACS_NAME -g $RESOURCE_GROUP --query primaryConnectionString -o tsv)"

# Purchase a phone number (via Azure Portal is easier)
# Navigate to: Communication Services > Phone numbers > Get > Select number

# After purchase, note the phone number (e.g., +18001234567)
```

**Via Azure Portal:**
1. Navigate to your Communication Services resource
2. Go to **Phone numbers** → **Get**
3. Select country, number type (Toll-Free recommended)
4. Ensure **SMS** capability is enabled
5. Complete purchase
6. Note the phone number

### Step 2: Configure Email Domain (Email Verification)

Email Services deploys with an **Azure-managed domain** automatically provisioned:

```bash
# Get the email sender address from deployment
EMAIL_SERVICE_NAME="ecs-truepulse-<suffix>"
DOMAIN=$(az communication email domain list \
  --email-service-name $EMAIL_SERVICE_NAME \
  -g $RESOURCE_GROUP \
  --query "[0].mailFromSenderDomain" -o tsv)

# Your sender email will be: DoNotReply@$DOMAIN
# Example: DoNotReply@xxxxxxxx-xxxx-xxxx-xxxx.azurecomm.net
```

**For Custom Domain (Optional):**
1. Navigate to Email Communication Services in Portal
2. Add a custom domain
3. Configure DNS records (TXT, SPF, DKIM)
4. Wait for verification (can take 24-48 hours)

### Step 3: Update Container App Configuration

After obtaining the phone number, update the Container App environment variables:

```bash
# Update the Container App with SMS sender number
az containerapp update \
  --name ca-truepulse-api \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars "AZURE_COMMUNICATION_SENDER_NUMBER=+18001234567"

# For email, the domain is auto-configured but you can verify:
az containerapp show \
  --name ca-truepulse-api \
  --resource-group $RESOURCE_GROUP \
  --query "properties.template.containers[0].env" -o table
```

### Step 4: Link Email Service to Communication Services

```bash
# Link the email domain to ACS for unified sending
az communication email domain link \
  --domain-name "AzureManagedDomain" \
  --email-service-name $EMAIL_SERVICE_NAME \
  --communication-service-name $ACS_NAME \
  --resource-group $RESOURCE_GROUP
```

---

## Environment-Specific Configuration

| Environment | SKU Tier | Replicas | Features |
|-------------|----------|----------|----------|
| `dev` | Basic/Standard | 1 | Debug logging |
| `staging` | Standard | 1-2 | Integration testing |
| `prod` | Premium | 2-10 | Auto-scaling, HA |

## Security Considerations

1. **Secrets**: All sensitive values stored in Key Vault
2. **Network**: Private endpoints for databases
3. **Identity**: Managed identities for service-to-service auth
4. **CORS**: Configured for Static Web App domain only
5. **TLS**: Enforced on all endpoints

## Cost Estimation

### Dev Environment (Optimized for Low Cost)

The dev environment is configured with serverless/minimal SKUs. Note: Redis and Cosmos DB were intentionally excluded from the architecture in favor of Azure Table Storage for simplicity and cost-effectiveness.

| Resource | SKU | Monthly Cost | Notes |
|----------|-----|--------------|-------|
| Container App | 0.25 vCPU, 0.5GB | ~$15-20 | Scale to 0 when idle |
| PostgreSQL Flexible | B2s (1 vCore) | ~$15 | Burstable, cost-effective |
| Storage Account (Tables) | Standard | ~$5-10 | Token blacklist, rate limiting |
| Static Web App | Free | $0 | 2 custom domains included |
| Log Analytics | Pay per GB | ~$5 | Minimal logs in dev |
| Key Vault | Standard | ~$1 | Per operation pricing |
| Container Registry | Basic | ~$5 | 10GB storage |
| Private Endpoints (4) | Per endpoint | ~$30 | Network charges |
| Communication Services | Pay per use | ~$5 | SMS/Email as needed |
| DNS Zone | Per zone + queries | ~$1 | Minimal cost |
| **Total Dev Estimate** | | **~$85-95/month** | Low-traffic workload |

### Production Environment

| Resource | SKU | Monthly Cost | Notes |
|----------|-----|--------------|-------|
| Container App | 1-4 vCPU, 2-8GB | ~$50-200 | Auto-scale with traffic |
| PostgreSQL Flexible | D4s (4 vCores) | ~$150-400 | Zone redundant, HA |
| Storage Account (Tables) | Standard | ~$10-50 | Scales with usage |
| Static Web App | Standard | ~$9 | Enterprise features |
| **Total Prod Estimate** | | **~$300-700/month** | Scales with usage |

### Cost Optimization Tips

1. **Storage Tables**: Uses serverless pricing - pay per transaction and storage. Very cost-effective for token/rate-limit data.
2. **Container Apps**: Scales to 0 when idle. Set `minReplicas: 0` in dev.
3. **PostgreSQL**: B2s is burstable - sufficient for dev/low traffic.
4. **Private Endpoints**: Each costs ~$7.50/month. Consider reducing for dev if security allows.

## Monitoring & Alerts

All resources send logs to Log Analytics. Set up alerts for:

```bash
# Example: High error rate alert
az monitor metrics alert create \
  --name "high-error-rate" \
  --resource-group $RESOURCE_GROUP \
  --scopes "/subscriptions/{sub}/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/ca-truepulse-api" \
  --condition "avg Requests where ResponseCode >= 500 > 10" \
  --window-size 5m
```

## Troubleshooting

### Common Issues

1. **Deployment fails with naming conflict**
   - Resources may already exist. Use unique prefix or delete existing resources.

2. **Container App unhealthy**
   - Check logs: `az containerapp logs show -n ca-truepulse-api -g $RESOURCE_GROUP`

3. **Database connection fails**
   - Verify private endpoint DNS resolution
   - Check firewall rules

4. **SMS not sending**
   - Verify phone number is purchased and linked
   - Check ACS connection string in Key Vault

5. **Email not sending**
   - Verify email domain is provisioned
   - Check sender address format: `DoNotReply@<domain>`

## Module Reference

Each module follows Azure Verified Modules (AVM) patterns:

```
modules/
├── network.bicep           # VNet + subnets
├── logAnalytics.bicep      # Logging workspace
├── keyVault.bicep          # Secrets management
├── keyVaultSecret.bicep    # Individual secret management
├── containerRegistry.bicep # ACR for images
├── postgres.bicep          # PostgreSQL Flexible
├── storageAccount.bicep    # Azure Storage (Blobs + Tables)
├── azureOpenAI.bicep       # Azure OpenAI Service
├── communicationServices.bicep  # SMS (ACS)
├── emailServices.bicep     # Email verification
├── dnsZone.bicep           # Custom domain DNS
├── containerAppsEnv.bicep  # Container Apps Environment
├── containerAppApi.bicep   # API Container App
└── staticWebApp.bicep      # Frontend hosting
```

## Contributing

When modifying infrastructure:
1. Test in `dev` environment first
2. Use `az deployment sub what-if` to preview changes
3. Follow [Bicep best practices](https://learn.microsoft.com/azure/azure-resource-manager/bicep/best-practices)
4. Update this README with any new parameters or resources
