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

@description('PostgreSQL host')
param postgresHost string

@description('PostgreSQL database name')
param postgresDatabase string

@description('PostgreSQL username')
param postgresUsername string

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

@description('Environment name')
param environmentName string

@description('Azure Communication Services name')
param communicationServicesName string = ''

@description('Azure Communication Services sender phone number')
param communicationSenderNumber string = ''

@description('Azure Email Communication Services name')
param emailServiceName string = ''

@description('Email sender address for verification emails')
param emailSenderAddress string = ''

@description('Custom domain name (for CORS configuration)')
param customDomain string = ''

@description('Use placeholder image (for initial deployment before ACR has images)')
param usePlaceholderImage bool = true

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
// Dev: scale to 0 when idle to save costs. Staging: keep 1 warm. Prod: min 2 for HA
var minReplicas = environmentName == 'prod' ? 2 : (environmentName == 'staging' ? 1 : 0)
var maxReplicas = environmentName == 'prod' ? 10 : 3

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

// Grant Key Vault Secrets User role to the managed identity
resource keyVaultSecretsRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVaultName, managedIdentity.id, 'keyvault-secrets-user')
  scope: keyVault
  properties: {
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6') // Key Vault Secrets User
  }
}

// Grant Storage Table Data Contributor role to the managed identity
resource storageTableDataContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountName, managedIdentity.id, 'storage-table-data-contributor')
  scope: storageAccount
  properties: {
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3') // Storage Table Data Contributor
  }
}

// Grant Storage Blob Data Contributor role to the managed identity
resource storageBlobDataContributorRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountName, managedIdentity.id, 'storage-blob-data-contributor')
  scope: storageAccount
  properties: {
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe') // Storage Blob Data Contributor
  }
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2024-01-01' existing = {
  name: storageAccountName
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

// Using Azure Verified Module: br/public:avm/res/app/container-app
module containerApp 'br/public:avm/res/app/container-app:0.12.1' = {
  name: 'container-app-api'
  params: {
    name: name
    location: location
    tags: tags
    environmentResourceId: containerAppsEnvId
    // Container configuration
    containers: [
      {
        name: 'api'
        image: containerImage
        resources: {
          cpu: json('0.5')
          memory: '1Gi'
        }
        env: [
          // Database configuration
          {
            name: 'DATABASE_URL'
            value: 'postgresql+asyncpg://${postgresUsername}@${postgresHost}/${postgresDatabase}'
          }
          {
            name: 'POSTGRES_PASSWORD'
            secretRef: 'postgres-password'
          }
          // Azure Storage Tables configuration (replaces Cosmos DB and Redis)
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
          // Environment
          {
            name: 'ENVIRONMENT'
            value: environmentName
          }
          {
            name: 'LOG_LEVEL'
            value: environmentName == 'prod' ? 'INFO' : 'DEBUG'
          }
          // Azure Communication Services (SMS)
          {
            name: 'AZURE_COMMUNICATION_SERVICE_NAME'
            value: communicationServicesName
          }
          {
            name: 'AZURE_COMMUNICATION_SENDER_NUMBER'
            value: communicationSenderNumber
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
    // Secrets from Key Vault
    secrets: {
      secureList: [
        {
          name: 'postgres-password'
          keyVaultUrl: '${keyVaultUri}secrets/postgres-password'
          identity: managedIdentity.id
        }
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
      ]
    }
    // Ingress configuration
    ingressExternal: true
    ingressTargetPort: targetPort
    ingressTransport: 'http'
    corsPolicy: {
      allowedOrigins: !empty(customDomain) ? [
        'https://${customDomain}'
        'https://www.${customDomain}'
        'https://*.azurestaticapps.net'
      ] : [
        'https://*.azurestaticapps.net'
      ]
      allowedMethods: [
        'GET'
        'POST'
        'PUT'
        'DELETE'
        'OPTIONS'
      ]
      allowedHeaders: [
        '*'
      ]
      exposeHeaders: [
        'X-Request-ID'
      ]
      allowCredentials: true
      maxAge: 86400
    }
    // Scaling configuration
    scaleMinReplicas: minReplicas
    scaleMaxReplicas: maxReplicas
    scaleRules: [
      {
        name: 'http-scaling'
        http: {
          metadata: {
            concurrentRequests: '100'
          }
        }
      }
    ]
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

output resourceId string = containerApp.outputs.resourceId
output name string = containerApp.outputs.name
output fqdn string = containerApp.outputs.fqdn
output managedIdentityId string = managedIdentity.id
output managedIdentityPrincipalId string = managedIdentity.properties.principalId
