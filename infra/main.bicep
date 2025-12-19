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

@description('Tags to apply to all resources')
param tags object = {
  project: 'TruePulse'
  environment: environmentName
  managedBy: 'bicep'
}

// Database credentials
@description('Administrator username for PostgreSQL')
param postgresAdminUsername string

@description('Administrator password for PostgreSQL')
@secure()
param postgresAdminPassword string

// Secrets
@description('JWT secret key for API authentication')
@secure()
param jwtSecretKey string

@description('Vote hash secret for privacy')
@secure()
param voteHashSecret string

@description('NewsData.io API key for news aggregation')
@secure()
param newsDataApiKey string = ''

@description('NewsAPI.org API key for news aggregation')
@secure()
param newsApiOrgKey string = ''

// Communication settings
@description('Azure Communication Services sender phone number')
param communicationSenderNumber string = ''

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
var postgresServerName = 'psql-${prefix}-${environmentName}-${shortUniqueSuffix}'
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
        name: 'postgres-password'
        value: postgresAdminPassword
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
    ]
  }
}

// PostgreSQL - isolated database per environment
module postgres 'modules/postgres.bicep' = {
  scope: resourceGroup
  name: 'postgres-deployment'
  params: {
    name: postgresServerName
    location: location
    tags: tags
    administratorLogin: postgresAdminUsername
    administratorLoginPassword: postgresAdminPassword
    logAnalyticsWorkspaceId: sharedLogAnalyticsWorkspaceId
    subnetId: vnet.outputs.privateEndpointsSubnetId
    environmentName: environmentName
    enableCMK: enableCMK
    keyVaultName: enableCMK ? keyVault.outputs.name : ''
    keyVaultResourceId: enableCMK ? keyVault.outputs.resourceId : ''
    cmkKeyUri: enableCMK ? keyVault.outputs.postgresEncryptionKeyUri : ''
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
    cmkKeyName: enableCMK ? 'storage-encryption-key' : ''
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
  }
}

// Container Apps Environment - isolated compute per environment
module containerAppsEnv 'modules/containerAppsEnv.bicep' = {
  scope: resourceGroup
  name: 'container-apps-env-deployment'
  params: {
    name: containerAppsEnvName
    location: location
    tags: tags
    logAnalyticsWorkspaceResourceId: sharedLogAnalyticsWorkspaceId
    infrastructureSubnetId: vnet.outputs.containerAppsSubnetId
    platformReservedCidr: platformReservedCidr
    platformReservedDnsIP: platformReservedDnsIP
    dockerBridgeCidr: dockerBridgeCidr
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
    containerRegistryName: sharedContainerRegistryName
    containerRegistryLoginServer: sharedContainerRegistryLoginServer
    keyVaultName: keyVault.outputs.name
    keyVaultUri: keyVault.outputs.uri
    postgresHost: postgres.outputs.fqdn
    postgresDatabase: 'truepulse'
    postgresUsername: postgresAdminUsername
    storageAccountName: storageAccount.outputs.name
    storageAccountTableEndpoint: storageAccount.outputs.primaryTableEndpoint
    azureOpenAIEndpoint: azureOpenAI.outputs.endpoint
    azureOpenAIDeployment: azureOpenAI.outputs.deploymentName
    storageAccountUrl: storageAccount.outputs.primaryBlobEndpoint
    environmentName: environmentName
    communicationServicesName: sharedCommunicationServiceName
    communicationSenderNumber: communicationSenderNumber
    emailServiceName: ''  // Email handled via shared services
    emailSenderAddress: emailSenderAddress
    customDomain: enableCustomDomain ? customDomain : ''
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
output postgresServerFqdn string = postgres.outputs.fqdn

// Shared resource references (for convenience)
output sharedContainerRegistryLoginServer string = sharedContainerRegistryLoginServer
output azureOpenAIEndpoint string = azureOpenAI.outputs.endpoint
