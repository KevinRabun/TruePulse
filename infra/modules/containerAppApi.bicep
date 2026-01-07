// TruePulse Infrastructure - Container App API
// FastAPI backend for the polling platform

// ============================================================================
// Parameters
// ============================================================================

@description('Container App name')
param name string

@description('Location for resources')
param location string

@description('Resource tags')
param tags object

@description('Container Apps Environment resource ID')
param containerAppsEnvId string

@description('Container Registry login server')
param containerRegistryLoginServer string

@description('Key Vault name')
param keyVaultName string

@description('Key Vault URI')
param keyVaultUri string

@description('Storage Account name for Azure Tables')
param storageAccountName string

@description('Storage Account table endpoint')
param storageAccountTableEndpoint string

@description('Azure OpenAI endpoint')
param azureOpenAIEndpoint string

@description('Azure OpenAI deployment name')
param azureOpenAIDeployment string

@description('Azure Storage Account blob endpoint URL')
param storageAccountUrl string

@description('Azure Cosmos DB endpoint URL')
param cosmosDbEndpoint string = ''

@description('Azure Cosmos DB database name')
param cosmosDbDatabaseName string = 'truepulse'

@description('Environment name')
param environmentName string

@description('Azure Communication Services name')
param communicationServicesName string = ''

@description('Azure Email Communication Services name')
param emailServiceName string = ''

@description('Email sender address for verification emails')
param emailSenderAddress string = ''

@description('Custom domain name (for CORS configuration)')
param customDomain string = ''

@description('Use placeholder image (for initial deployment before ACR has images)')
param usePlaceholderImage bool = true

@description('Enable Cloudflare IP restrictions (false for dev to allow direct testing)')
param enableCloudflareIpRestrictions bool = true

// ============================================================================
// Variables
// ============================================================================

// Use a placeholder image from MCR for initial deployment (doesn't require ACR auth)
// The actual image will be deployed via GitHub Actions after ACR push
var containerImage = usePlaceholderImage 
  ? 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
  : '${containerRegistryLoginServer}/truepulse-api:latest'
// Port depends on whether we use the placeholder image (80) or our app (8000)
var targetPort = usePlaceholderImage ? 80 : 8000
// COST OPTIMIZATION: Scale-to-zero for dev, warm instance for staging, HA for prod
// Dev: scale to 0 when idle = $0 cost when not in use
// Staging: keep 1 warm for testing availability
// Prod: min 2 for high availability across zones
var minReplicas = usePlaceholderImage ? 1 : (environmentName == 'prod' ? 2 : (environmentName == 'staging' ? 1 : 0))
// COST OPTIMIZATION: Lower max replicas since each is now smaller (0.25 vCPU)
// With right-sized containers, we can scale out more efficiently
var maxReplicas = environmentName == 'prod' ? 20 : (environmentName == 'staging' ? 5 : 3)

// Cloudflare IP ranges for security restrictions
// https://www.cloudflare.com/ips-v4
var cloudflareIpRestrictions = [
  { name: 'AllowCloudflare1', ipAddressRange: '173.245.48.0/20', action: 'Allow' }
  { name: 'AllowCloudflare2', ipAddressRange: '103.21.244.0/22', action: 'Allow' }
  { name: 'AllowCloudflare3', ipAddressRange: '103.22.200.0/22', action: 'Allow' }
  { name: 'AllowCloudflare4', ipAddressRange: '103.31.4.0/22', action: 'Allow' }
  { name: 'AllowCloudflare5', ipAddressRange: '141.101.64.0/18', action: 'Allow' }
  { name: 'AllowCloudflare6', ipAddressRange: '108.162.192.0/18', action: 'Allow' }
  { name: 'AllowCloudflare7', ipAddressRange: '190.93.240.0/20', action: 'Allow' }
  { name: 'AllowCloudflare8', ipAddressRange: '188.114.96.0/20', action: 'Allow' }
  { name: 'AllowCloudflare9', ipAddressRange: '197.234.240.0/22', action: 'Allow' }
  { name: 'AllowCloudflare10', ipAddressRange: '198.41.128.0/17', action: 'Allow' }
  { name: 'AllowCloudflare11', ipAddressRange: '162.158.0.0/15', action: 'Allow' }
  { name: 'AllowCloudflare12', ipAddressRange: '104.16.0.0/13', action: 'Allow' }
  { name: 'AllowCloudflare13', ipAddressRange: '104.24.0.0/14', action: 'Allow' }
  { name: 'AllowCloudflare14', ipAddressRange: '172.64.0.0/13', action: 'Allow' }
  { name: 'AllowCloudflare15', ipAddressRange: '131.0.72.0/22', action: 'Allow' }
]

// ============================================================================
// Resources
// ============================================================================

// User-assigned managed identity for Key Vault access
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${name}-identity'
  location: location
  tags: tags
}

// Note: ACR pull permission is granted via a separate module deployed to the shared resource group
// See main.bicep's acrRoleAssignment module for the cross-resource-group role assignment

// Grant Key Vault Secrets User role to the managed identity (only when not using placeholder)
resource keyVaultSecretsRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!usePlaceholderImage) {
  name: guid(keyVaultName, managedIdentity.id, 'keyvault-secrets-user')
  scope: keyVault
  properties: {
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6') // Key Vault Secrets User
  }
}

// Grant Storage Table Data Contributor role to the managed identity (only when not using placeholder)
resource storageTableDataContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!usePlaceholderImage) {
  name: guid(storageAccountName, managedIdentity.id, 'storage-table-data-contributor')
  scope: storageAccount
  properties: {
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3') // Storage Table Data Contributor
  }
}

// Grant Storage Blob Data Contributor role to the managed identity (only when not using placeholder)
resource storageBlobDataContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!usePlaceholderImage) {
  name: guid(storageAccountName, managedIdentity.id, 'storage-blob-data-contributor')
  scope: storageAccount
  properties: {
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe') // Storage Blob Data Contributor
  }
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2024-01-01' existing = if (!usePlaceholderImage) {
  name: storageAccountName
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = if (!usePlaceholderImage) {
  name: keyVaultName
}

// Placeholder Container App - simple deployment without secrets or ACR for initial infrastructure setup
// Uses MCR image directly - no registry configuration needed (MCR is public)
resource placeholderContainerApp 'Microsoft.App/containerApps@2024-03-01' = if (usePlaceholderImage) {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnvId
    workloadProfileName: 'Consumption'
    configuration: {
      ingress: {
        external: true
        targetPort: 80
        transport: 'http'
      }
      // No registries configuration - MCR is public and doesn't need auth
    }
    template: {
      containers: [
        {
          name: 'api'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

// Full Container App using Azure Verified Module - used after placeholder is replaced
// COST OPTIMIZATION: Right-sized resources for FastAPI backend
// - 0.25 vCPU is sufficient for Python/FastAPI REST API
// - 0.5Gi memory handles typical request loads efficiently
// - Scales horizontally via replicas when needed
module containerApp 'br/public:avm/res/app/container-app:0.19.0' = if (!usePlaceholderImage) {
  name: 'container-app-api'
  params: {
    name: name
    location: location
    tags: tags
    environmentResourceId: containerAppsEnvId
    // Container configuration - optimized for cost
    containers: [
      {
        name: 'api'
        image: containerImage
        resources: {
          // COST OPTIMIZATION: Right-sized for FastAPI
          // 0.25 vCPU handles ~50-100 concurrent requests per replica
          // Horizontal scaling handles load spikes more cost-effectively
          cpu: json('0.25')
          memory: '0.5Gi'
        }
        env: [
          // Azure Storage Tables configuration (for votes)
          {
            name: 'AZURE_STORAGE_ACCOUNT_NAME'
            value: storageAccountName
          }
          {
            name: 'AZURE_STORAGE_TABLE_ENDPOINT'
            value: storageAccountTableEndpoint
          }
          // JWT configuration
          {
            name: 'JWT_SECRET_KEY'
            secretRef: 'jwt-secret-key'
          }
          {
            name: 'JWT_ALGORITHM'
            value: 'HS256'
          }
          {
            name: 'ACCESS_TOKEN_EXPIRE_MINUTES'
            value: '30'
          }
          // Vote privacy configuration
          {
            name: 'VOTE_HASH_SECRET'
            secretRef: 'vote-hash-secret'
          }
          // Azure OpenAI configuration
          {
            name: 'AZURE_OPENAI_ENDPOINT'
            value: azureOpenAIEndpoint
          }
          {
            name: 'AZURE_OPENAI_DEPLOYMENT'
            value: azureOpenAIDeployment
          }
          {
            name: 'AZURE_OPENAI_API_KEY'
            secretRef: 'azure-openai-api-key'
          }
          // Azure Storage configuration
          {
            name: 'AZURE_STORAGE_BLOB_URL'
            value: storageAccountUrl
          }
          // Azure Cosmos DB configuration
          {
            name: 'AZURE_COSMOS_ENDPOINT'
            value: cosmosDbEndpoint
          }
          {
            name: 'AZURE_COSMOS_DATABASE'
            value: cosmosDbDatabaseName
          }
          // Environment
          {
            name: 'ENVIRONMENT'
            value: environmentName
          }
          {
            name: 'LOG_LEVEL'
            value: environmentName == 'prod' ? 'INFO' : 'DEBUG'
          }
          // Azure Communication Services (for email only)
          {
            name: 'AZURE_COMMUNICATION_SERVICE_NAME'
            value: communicationServicesName
          }
          {
            name: 'AZURE_COMMUNICATION_CONNECTION_STRING'
            secretRef: 'communication-services-connection-string'
          }
          // Azure Email Communication Services
          {
            name: 'AZURE_EMAIL_SERVICE_NAME'
            value: emailServiceName
          }
          {
            name: 'AZURE_EMAIL_SENDER_ADDRESS'
            value: emailSenderAddress
          }
          // News API Keys
          {
            name: 'NEWSDATA_API_KEY'
            secretRef: 'newsdata-api-key'
          }
          {
            name: 'NEWSAPI_ORG_API_KEY'
            secretRef: 'newsapi-org-key'
          }
          // CORS and Frontend Access Configuration
          {
            name: 'CORS_ORIGINS'
            value: !empty(customDomain) ? (environmentName == 'prod' 
              ? 'https://${customDomain},https://www.${customDomain}' 
              : 'https://${environmentName}.${customDomain},https://www.${environmentName}.${customDomain},https://${customDomain},https://www.${customDomain}') 
              : 'https://*.azurestaticapps.net'
          }
          {
            name: 'ALLOWED_ORIGINS'
            value: !empty(customDomain) ? (environmentName == 'prod' 
              ? 'https://${customDomain},https://www.${customDomain}' 
              : 'https://${environmentName}.${customDomain},https://www.${environmentName}.${customDomain},https://${customDomain},https://www.${customDomain}') 
              : 'https://*.azurestaticapps.net'
          }
          {
            name: 'FRONTEND_URL'
            value: !empty(customDomain) ? (environmentName == 'prod' 
              ? 'https://${customDomain}' 
              : 'https://${environmentName}.${customDomain}') 
              : 'http://localhost:3000'
          }
          {
            name: 'FRONTEND_API_SECRET'
            secretRef: 'frontend-api-secret'
          }
          {
            name: 'ENFORCE_FRONTEND_ONLY'
            value: 'false'
          }
          {
            name: 'SECRET_KEY'
            secretRef: 'jwt-secret-key'
          }
          // WebAuthn/Passkey configuration - Required for passkey authentication
          // RP ID must match the domain where the frontend is hosted
          {
            name: 'WEBAUTHN_RP_ID'
            value: !empty(customDomain) ? (environmentName == 'prod' 
              ? customDomain 
              : '${environmentName}.${customDomain}') 
              : 'localhost'
          }
          {
            name: 'WEBAUTHN_RP_NAME'
            value: 'TruePulse'
          }
          {
            name: 'WEBAUTHN_ORIGIN'
            value: !empty(customDomain) ? (environmentName == 'prod' 
              ? 'https://${customDomain}' 
              : 'https://${environmentName}.${customDomain}') 
              : 'http://localhost:3000'
          }
        ]
        // Only configure health probes for our actual application, not the placeholder
        probes: usePlaceholderImage ? [] : [
          {
            type: 'Liveness'
            httpGet: {
              path: '/health'
              port: 8000
              scheme: 'HTTP'
            }
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          }
          {
            type: 'Readiness'
            httpGet: {
              path: '/health'
              port: 8000
              scheme: 'HTTP'
            }
            initialDelaySeconds: 10
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3
          }
        ]
      }
    ]
    // Secrets from Key Vault (AVM 0.19.0 uses flat array, not secureList)
    secrets: [
      {
        name: 'jwt-secret-key'
        keyVaultUrl: '${keyVaultUri}secrets/jwt-secret-key'
        identity: managedIdentity.id
      }
      {
        name: 'vote-hash-secret'
        keyVaultUrl: '${keyVaultUri}secrets/vote-hash-secret'
        identity: managedIdentity.id
      }
      {
        name: 'azure-openai-api-key'
        keyVaultUrl: '${keyVaultUri}secrets/azure-openai-api-key'
        identity: managedIdentity.id
      }
      {
        name: 'newsdata-api-key'
        keyVaultUrl: '${keyVaultUri}secrets/newsdata-api-key'
        identity: managedIdentity.id
      }
      {
        name: 'newsapi-org-key'
        keyVaultUrl: '${keyVaultUri}secrets/newsapi-org-key'
        identity: managedIdentity.id
      }
      {
        name: 'frontend-api-secret'
        keyVaultUrl: '${keyVaultUri}secrets/frontend-api-secret'
        identity: managedIdentity.id
      }
      {
        name: 'communication-services-connection-string'
        keyVaultUrl: '${keyVaultUri}secrets/communication-services-connection-string'
        identity: managedIdentity.id
      }
    ]
    // Ingress configuration
    ingressExternal: true
    ingressTargetPort: targetPort
    ingressTransport: 'http'
    corsPolicy: {
      // Include base domain, www subdomain, environment-specific subdomain, and SWA domains
      allowedOrigins: !empty(customDomain) ? concat([
        'https://${customDomain}'
        'https://www.${customDomain}'
        'https://*.azurestaticapps.net'
      ], environmentName != 'prod' ? [
        'https://${environmentName}.${customDomain}'
        'https://www.${environmentName}.${customDomain}'
      ] : []) : [
        'https://*.azurestaticapps.net'
      ]
      allowedMethods: [
        'GET'
        'POST'
        'PUT'
        'PATCH'
        'DELETE'
        'OPTIONS'
      ]
      // Explicit header list instead of wildcard for security
      allowedHeaders: [
        'Authorization'
        'Content-Type'
        'Accept'
        'Origin'
        'X-Requested-With'
        'X-Request-ID'
        'X-Frontend-Secret'
      ]
      exposeHeaders: [
        'X-Request-ID'
      ]
      allowCredentials: true
      maxAge: 86400
    }
    // Scaling configuration (AVM 0.19.0 uses scaleSettings object)
    // COST OPTIMIZATION: Lower concurrency threshold triggers scale-out earlier
    // With 0.25 vCPU containers, 50 concurrent requests is optimal per replica
    // This enables more responsive scaling for bursty traffic patterns
    scaleSettings: {
      minReplicas: minReplicas
      maxReplicas: maxReplicas
      rules: [
        {
          name: 'http-scaling'
          http: {
            metadata: {
              // Scale out at 50 concurrent requests per replica
              // Smaller containers = earlier scale-out = better response times
              concurrentRequests: '50'
            }
          }
        }
      ]
    }
    // IP Security restrictions for Cloudflare-only access (production/staging)
    // Disabled for dev to allow direct testing
    ipSecurityRestrictions: enableCloudflareIpRestrictions ? cloudflareIpRestrictions : []
    // Managed identity
    managedIdentities: {
      systemAssigned: true
      userAssignedResourceIds: [
        managedIdentity.id
      ]
    }
    // Registry configuration
    registries: [
      {
        server: containerRegistryLoginServer
        identity: managedIdentity.id
      }
    ]
    // Workload profile
    workloadProfileName: 'Consumption'
  }
  dependsOn: [
    // Note: acrPullRole is now assigned via a separate module in main.bicep
    keyVaultSecretsRole
  ]
}

// ============================================================================
// Outputs
// ============================================================================

output resourceId string = usePlaceholderImage ? placeholderContainerApp!.id : containerApp!.outputs.resourceId
output name string = usePlaceholderImage ? placeholderContainerApp!.name : containerApp!.outputs.name
output fqdn string = usePlaceholderImage ? placeholderContainerApp!.properties.configuration.ingress.fqdn : containerApp!.outputs.fqdn
output managedIdentityId string = managedIdentity.id
output managedIdentityPrincipalId string = managedIdentity.properties.principalId
// System-assigned identity principal ID (only available when not using placeholder image)
// Placeholder uses UserAssigned only, while full deployment uses both SystemAssigned and UserAssigned
output systemAssignedPrincipalId string = usePlaceholderImage ? '' : (containerApp.?outputs.?systemAssignedMIPrincipalId ?? '')
