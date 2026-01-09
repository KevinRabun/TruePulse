// TruePulse Infrastructure - Environment-Specific Deployment
// Deploys environment-specific resources and references shared services
// Requires shared.bicep to be deployed first

targetScope = 'subscription'

// ============================================================================
// Parameters
// ============================================================================

@description('Environment name (dev, staging, prod)')
@allowed(['dev', 'staging', 'prod'])
param environmentName string = 'dev'

@description('Primary Azure region for resources')
param location string = 'eastus2'

@description('Resource name prefix')
param prefix string = 'truepulse'

@description('Current timestamp for budget start date (defaults to deployment time, format: yyyy-MM-dd)')
param deploymentTimestamp string = utcNow('yyyy-MM-dd')

@description('Tags to apply to all resources')
param tags object = {
  project: 'TruePulse'
  environment: environmentName
  managedBy: 'bicep'
}

// Secrets
@description('JWT secret key for API authentication')
@minLength(32)
@secure()
param jwtSecretKey string

@description('Vote hash secret for privacy')
@minLength(16)
@secure()
param voteHashSecret string

@description('NewsData.io API key for news aggregation')
@secure()
param newsDataApiKey string = ''

@description('NewsAPI.org API key for news aggregation')
@secure()
param newsApiOrgKey string = ''

@description('Frontend API secret for frontend-only access validation')
@secure()
param frontendApiSecret string = ''

@description('Field-level encryption key for PII (base64-encoded 256-bit key)')
@secure()
param fieldEncryptionKey string = ''

// Email settings
@description('Email sender address for verification emails')
param emailSenderAddress string = ''

// Domain settings
@description('Custom domain name for the application')
param customDomain string = 'truepulse.net'

@description('Enable custom domain configuration')
param enableCustomDomain bool = true

// Security settings
@description('Enable Customer Managed Keys (CMK) for data encryption')
param enableCMK bool = true

// ============================================================================
// Shared Resources References (from shared.bicep outputs)
// ============================================================================

@description('Resource ID of shared Log Analytics Workspace')
param sharedLogAnalyticsWorkspaceId string

@description('Name of shared Container Registry')
param sharedContainerRegistryName string

@description('Login server of shared Container Registry')
param sharedContainerRegistryLoginServer string

@description('Connection string for shared Communication Services')
@secure()
param sharedCommunicationServiceConnectionString string

@description('Name of shared Communication Services')
param sharedCommunicationServiceName string

// Shared Private DNS Zone IDs
@description('Resource ID of shared blob storage DNS zone')
param sharedBlobDnsZoneId string

@description('Resource ID of shared table storage DNS zone')
param sharedTableDnsZoneId string

@description('Resource ID of shared OpenAI DNS zone')
param sharedOpenaiDnsZoneId string

@description('Resource ID of shared Key Vault DNS zone')
param sharedKeyVaultDnsZoneId string

@description('Resource ID of shared ACR DNS zone')
param sharedAcrDnsZoneId string

@description('Resource ID of shared Cosmos DB DNS zone')
param sharedCosmosDnsZoneId string

@description('Resource ID of shared Container Registry')
param sharedContainerRegistryResourceId string

// ============================================================================
// Variables
// ============================================================================

var resourceGroupName = 'rg-${prefix}-${environmentName}'
var uniqueSuffix = uniqueString(subscription().subscriptionId, resourceGroupName, location)
var shortUniqueSuffix = substring(uniqueSuffix, 0, 6)

// Networking
var vnetAddressPrefix = environmentName == 'prod' ? '10.2.0.0/16' : (environmentName == 'staging' ? '10.1.0.0/16' : '10.0.0.0/16')
var containerAppsSubnetPrefix = environmentName == 'prod' ? '10.2.0.0/23' : (environmentName == 'staging' ? '10.1.0.0/23' : '10.0.0.0/23')
var privateEndpointsSubnetPrefix = environmentName == 'prod' ? '10.2.4.0/24' : (environmentName == 'staging' ? '10.1.4.0/24' : '10.0.4.0/24')
var platformReservedCidr = environmentName == 'prod' ? '10.2.16.0/24' : (environmentName == 'staging' ? '10.1.16.0/24' : '10.0.16.0/24')
var platformReservedDnsIP = environmentName == 'prod' ? '10.2.16.10' : (environmentName == 'staging' ? '10.1.16.10' : '10.0.16.10')
var dockerBridgeCidr = '172.17.0.1/16'

// Environment-specific resource names
var keyVaultName = 'kv-${prefix}-${environmentName}-${shortUniqueSuffix}'
var containerAppsEnvName = 'cae-${prefix}-${environmentName}'
var containerAppApiName = 'ca-${prefix}-api-${environmentName}'
var staticWebAppName = 'swa-${prefix}-${environmentName}'
// Note: v2 suffix added to recreate account with CMK after soft-delete of v1
var cosmosDbAccountName = 'cosmos-${prefix}-${environmentName}-${shortUniqueSuffix}v2'
var vnetName = 'vnet-${prefix}-${environmentName}'
var storageAccountName = 'st${prefix}${environmentName}${shortUniqueSuffix}'
var azureOpenAIName = 'aoai-${prefix}-${environmentName}-${shortUniqueSuffix}'

// URLs
var frontendUrl = enableCustomDomain ? 'https://${environmentName == 'prod' ? '' : '${environmentName}.'}${customDomain}' : 'https://${staticWebAppName}.azurestaticapps.net'
var apiUrl = enableCustomDomain ? 'https://api${environmentName == 'prod' ? '' : '-${environmentName}'}.${customDomain}' : 'https://${containerAppApiName}.${location}.azurecontainerapps.io'

// ============================================================================
// Resource Group
// ============================================================================

resource resourceGroup 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

// ============================================================================
// Environment-Specific Modules
// ============================================================================

// Virtual Network - isolated per environment
module vnet 'modules/network.bicep' = {
  scope: resourceGroup
  name: 'vnet-deployment'
  params: {
    name: vnetName
    location: location
    tags: tags
    vnetAddressPrefix: vnetAddressPrefix
    containerAppsSubnetPrefix: containerAppsSubnetPrefix
    privateEndpointsSubnetPrefix: privateEndpointsSubnetPrefix
  }
}

// Link environment VNet to shared Private DNS Zones
// This enables private endpoint resolution from the environment's VNet
// Deployed to shared resource group where DNS zones exist
module privateDnsZoneLinks 'modules/privateDnsZoneLinks.bicep' = {
  scope: az.resourceGroup(subscription().subscriptionId, 'rg-truepulse-shared')
  name: 'dns-zone-links-${environmentName}'
  params: {
    environmentName: environmentName
    vnetId: vnet.outputs.vnetId
  }
  // Note: Implicit dependency on vnet via vnet.outputs.vnetId reference
}

// ACR Private Endpoint - enables Container Apps to pull images from shared ACR via private network
module acrPrivateEndpoint 'modules/acrPrivateEndpoint.bicep' = {
  scope: resourceGroup
  name: 'acr-private-endpoint-deployment'
  params: {
    name: 'pe-${sharedContainerRegistryName}'
    location: location
    tags: tags
    subnetId: vnet.outputs.privateEndpointsSubnetId
    containerRegistryResourceId: sharedContainerRegistryResourceId
    acrDnsZoneId: sharedAcrDnsZoneId
  }
  dependsOn: [privateDnsZoneLinks]
}

// Key Vault - isolated secrets per environment
module keyVault 'modules/keyVault.bicep' = {
  scope: resourceGroup
  name: 'keyvault-deployment'
  params: {
    name: keyVaultName
    location: location
    tags: tags
    logAnalyticsWorkspaceId: sharedLogAnalyticsWorkspaceId
    subnetId: vnet.outputs.privateEndpointsSubnetId
    createEncryptionKeys: enableCMK
    keyVaultDnsZoneId: sharedKeyVaultDnsZoneId
    secrets: [
      {
        name: 'jwt-secret-key'
        value: jwtSecretKey
      }
      {
        name: 'vote-hash-secret'
        value: voteHashSecret
      }
      {
        name: 'newsdata-api-key'
        value: newsDataApiKey
      }
      {
        name: 'newsapi-org-key'
        value: newsApiOrgKey
      }
      {
        name: 'communication-services-connection-string'
        value: sharedCommunicationServiceConnectionString
      }
      {
        name: 'frontend-api-secret'
        value: !empty(frontendApiSecret) ? frontendApiSecret : jwtSecretKey
      }
      {
        name: 'field-encryption-key'
        value: fieldEncryptionKey
      }
    ]
  }
}

// Storage Account - isolated vote storage per environment
module storageAccount 'modules/storageAccount.bicep' = {
  scope: resourceGroup
  name: 'storage-account-deployment'
  params: {
    name: storageAccountName
    location: location
    tags: tags
    logAnalyticsWorkspaceId: sharedLogAnalyticsWorkspaceId
    subnetId: vnet.outputs.privateEndpointsSubnetId
    environmentName: environmentName
    enableCMK: enableCMK
    keyVaultResourceId: enableCMK ? keyVault.outputs.resourceId : ''
    cmkKeyName: enableCMK ? keyVault.outputs.storageEncryptionKeyName : ''
    blobDnsZoneId: sharedBlobDnsZoneId
    tableDnsZoneId: sharedTableDnsZoneId
  }
}

// Azure OpenAI - isolated per environment with private endpoint
module azureOpenAI 'modules/azureOpenAI.bicep' = {
  scope: resourceGroup
  name: 'azure-openai-deployment'
  params: {
    name: azureOpenAIName
    location: location
    tags: tags
    logAnalyticsWorkspaceId: sharedLogAnalyticsWorkspaceId
    subnetId: vnet.outputs.privateEndpointsSubnetId
    keyVaultResourceId: keyVault.outputs.resourceId
    environmentName: environmentName
    openaiDnsZoneId: sharedOpenaiDnsZoneId
  }
}

// User-Assigned Managed Identity for Cosmos DB CMK
// Required for CMK + Continuous backup - must be created and granted Key Vault access before Cosmos DB
module cosmosDbManagedIdentity 'modules/cosmosdbManagedIdentity.bicep' = if (enableCMK) {
  scope: resourceGroup
  name: 'cosmosdb-managed-identity-deployment'
  params: {
    name: 'id-cosmos-${prefix}-${environmentName}'
    location: location
    tags: tags
    keyVaultResourceId: keyVault.outputs.resourceId
  }
}

// Cosmos DB Serverless - unified document database for all data
module cosmosDb 'modules/cosmosdb.bicep' = {
  scope: resourceGroup
  name: 'cosmosdb-deployment'
  params: {
    name: cosmosDbAccountName
    location: location
    tags: tags
    logAnalyticsWorkspaceId: sharedLogAnalyticsWorkspaceId
    subnetId: vnet.outputs.privateEndpointsSubnetId
    environmentName: environmentName
    cosmosDnsZoneId: sharedCosmosDnsZoneId
    // Data plane principal ID will be set after Container App deployment via separate role assignment
    dataPlanePrincipalId: ''
    // Customer Managed Keys (CMK) for encryption
    enableCMK: enableCMK
    keyVaultResourceId: enableCMK ? keyVault.outputs.resourceId : ''
    cmkKeyName: enableCMK ? keyVault.outputs.cosmosEncryptionKeyName : ''
    // User-Assigned MI for CMK (required for CMK + Continuous backup)
    cmkUserAssignedIdentityId: enableCMK ? cosmosDbManagedIdentity!.outputs.id : ''
    // Skip containers in main deployment when CMK is enabled (deployed separately to avoid conflicts)
    skipContainers: enableCMK
  }
}

// Cosmos DB Containers - deployed separately to avoid CMK update conflicts
// When CMK is enabled, Azure doesn't allow updating CMK settings and containers simultaneously
module cosmosDbContainers 'modules/cosmosdbContainers.bicep' = if (enableCMK) {
  scope: resourceGroup
  name: 'cosmosdb-containers-deployment'
  params: {
    accountName: cosmosDbAccountName
    databaseName: 'truepulse'
  }
  dependsOn: [
    cosmosDb
  ]
}

// Container Apps Environment - isolated compute per environment
// COST OPTIMIZATION: Uses consumption-only plan with scale-to-zero
// Zone redundancy only enabled for production
module containerAppsEnv 'modules/containerAppsEnv.bicep' = {
  scope: resourceGroup
  name: 'container-apps-env-deployment'
  params: {
    name: containerAppsEnvName
    location: location
    tags: tags
    infrastructureSubnetId: vnet.outputs.containerAppsSubnetId
    platformReservedCidr: platformReservedCidr
    platformReservedDnsIP: platformReservedDnsIP
    dockerBridgeCidr: dockerBridgeCidr
    environmentName: environmentName
  }
}

// Container App - API (uses shared ACR)
module containerAppApi 'modules/containerAppApi.bicep' = {
  scope: resourceGroup
  name: 'container-app-api-deployment'
  params: {
    name: containerAppApiName
    location: location
    tags: tags
    containerAppsEnvId: containerAppsEnv.outputs.resourceId
    containerRegistryLoginServer: sharedContainerRegistryLoginServer
    keyVaultName: keyVault.outputs.name
    keyVaultUri: keyVault.outputs.uri
    storageAccountName: storageAccount.outputs.name
    storageAccountTableEndpoint: storageAccount.outputs.primaryTableEndpoint
    azureOpenAIEndpoint: azureOpenAI.outputs.endpoint
    azureOpenAIDeployment: azureOpenAI.outputs.deploymentName
    storageAccountUrl: storageAccount.outputs.primaryBlobEndpoint
    cosmosDbEndpoint: cosmosDb.outputs.endpoint
    cosmosDbDatabaseName: cosmosDb.outputs.databaseName
    environmentName: environmentName
    communicationServicesName: sharedCommunicationServiceName
    emailServiceName: ''  // Email handled via shared services
    emailSenderAddress: emailSenderAddress
    customDomain: enableCustomDomain ? customDomain : ''
    usePlaceholderImage: false  // Use actual ACR image, not placeholder
    // Disable Cloudflare IP restrictions for dev to allow direct testing
    // Enable for staging/prod for security (traffic must go through Cloudflare)
    enableCloudflareIpRestrictions: environmentName != 'dev'
  }
  // Note: OpenAI secrets are stored in Key Vault during azureOpenAI module deployment
  // Container App accesses secrets at runtime via managed identity, not deployment time
}

// Grant ACR pull permission to the Container App's managed identity (cross-resource-group)
module acrRoleAssignment 'modules/acrRoleAssignment.bicep' = {
  scope: az.resourceGroup('rg-truepulse-shared')
  name: 'acr-role-assignment-${environmentName}'
  params: {
    containerRegistryName: sharedContainerRegistryName
    principalId: containerAppApi.outputs.managedIdentityPrincipalId
  }
}

// Grant Azure OpenAI access to the Container App's managed identities
// Required because disableLocalAuth=true on the OpenAI resource (API keys disabled for security)
// Both system-assigned and user-assigned identities need access as DefaultAzureCredential may use either
module openaiRoleAssignment 'modules/openaiRoleAssignment.bicep' = {
  scope: resourceGroup
  name: 'openai-role-assignment-${environmentName}'
  params: {
    openaiResourceId: azureOpenAI.outputs.resourceId
    userAssignedPrincipalId: containerAppApi.outputs.managedIdentityPrincipalId
    systemAssignedPrincipalId: containerAppApi.outputs.systemAssignedPrincipalId
  }
}

// Grant Cosmos DB data access to the Container App's managed identity
// Required because disableLocalAuth=true on Cosmos DB (keys disabled for security)
module cosmosDbRoleAssignment 'modules/cosmosdbRoleAssignment.bicep' = {
  scope: resourceGroup
  name: 'cosmosdb-role-assignment-${environmentName}'
  params: {
    cosmosAccountName: cosmosDb.outputs.name
    principalId: containerAppApi.outputs.managedIdentityPrincipalId
  }
}

// Static Web App - can use slots for staging, but separate instance is cleaner
module staticWebApp 'modules/staticWebApp.bicep' = {
  scope: resourceGroup
  name: 'swa-deployment'
  params: {
    name: staticWebAppName
    location: location
    tags: tags
    apiUrl: apiUrl
    customDomain: enableCustomDomain ? (environmentName == 'prod' ? customDomain : '${environmentName}.${customDomain}') : ''
    enableWwwSubdomain: environmentName == 'prod' // Only enable www for production
  }
}

// Budget Alerts - cost management with email notifications
// Monthly budget with alerts at 50%, 80%, and 100% thresholds
module budget 'modules/budget.bicep' = {
  scope: resourceGroup
  name: 'budget-deployment'
  params: {
    budgetName: 'budget-${prefix}-${environmentName}'
    // Set budget amounts per environment
    // Dev: $300/month, Staging: $500/month, Prod: $1000/month
    budgetAmount: environmentName == 'prod' ? 1000 : (environmentName == 'staging' ? 500 : 300)
    // Budget starts from the first of the current month (deploymentTimestamp is yyyy-MM-dd)
    budgetStartDate: '${substring(deploymentTimestamp, 0, 7)}-01'
    // Contact emails for budget alerts - update this with your actual email
    contactEmails: ['alerts@truepulse.net']
    resourceGroupScope: resourceGroupName
  }
}

// Monitoring and Alerting - SLO-based alerts for service health
// Deploys action groups and metric alerts for Container App and Cosmos DB
module monitoring 'modules/monitoring.bicep' = {
  scope: resourceGroup
  name: 'monitoring-deployment'
  params: {
    environmentName: environmentName
    location: location
    logAnalyticsWorkspaceId: sharedLogAnalyticsWorkspaceId
    containerAppId: containerAppApi.outputs.resourceId
    cosmosDbAccountId: cosmosDb.outputs.resourceId
    alertEmailAddresses: ['alerts@truepulse.net']
    enableAlerts: environmentName != 'dev' // Enable alerts for staging and prod only
  }
}

// ============================================================================
// Outputs
// ============================================================================

output resourceGroupName string = resourceGroup.name
output containerAppApiFqdn string = containerAppApi.outputs.fqdn
output staticWebAppHostname string = staticWebApp.outputs.defaultHostname
output staticWebAppDeploymentTokenInfo string = staticWebApp.outputs.deploymentTokenInfo
output keyVaultUri string = keyVault.outputs.uri
output frontendUrl string = frontendUrl
output apiUrl string = apiUrl
output storageAccountName string = storageAccount.outputs.name
output storageAccountBlobEndpoint string = storageAccount.outputs.primaryBlobEndpoint
output cosmosDbEndpoint string = cosmosDb.outputs.endpoint
output cosmosDbDatabaseName string = cosmosDb.outputs.databaseName

// Shared resource references (for convenience)
output sharedContainerRegistryLoginServer string = sharedContainerRegistryLoginServer
output azureOpenAIEndpoint string = azureOpenAI.outputs.endpoint
