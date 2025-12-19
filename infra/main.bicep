// TruePulse Infrastructure - Main Deployment
// Uses Azure Verified Modules (AVM) following Well-Architected Framework (WAF) best practices

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

@description('Administrator username for PostgreSQL')
param postgresAdminUsername string

@description('Administrator password for PostgreSQL')
@secure()
param postgresAdminPassword string

@description('JWT secret key for API authentication')
@secure()
param jwtSecretKey string

@description('Vote hash secret for privacy')
@secure()
param voteHashSecret string

@description('Deploy Azure OpenAI service (set to false if using external AI Foundry)')
param deployAzureOpenAI bool = true

@description('NewsData.io API key for news aggregation')
@secure()
param newsDataApiKey string = ''

@description('NewsAPI.org API key for news aggregation')
@secure()
param newsApiOrgKey string = ''

@description('Azure Communication Services sender phone number (obtained after deployment)')
param communicationSenderNumber string = ''

@description('Email sender address for verification emails (obtained after deployment)')
param emailSenderAddress string = ''

@description('Custom domain name for the application')
param customDomain string = 'truepulse.net'

@description('Enable custom domain configuration (requires domain to be registered)')
param enableCustomDomain bool = true

@description('Enable Customer Managed Keys (CMK) for data encryption - recommended for voting data protection')
param enableCMK bool = true

// ============================================================================
// Variables
// ============================================================================

var resourceGroupName = 'rg-${prefix}-${environmentName}'
var uniqueSuffix = uniqueString(subscription().subscriptionId, resourceGroupName, location)
var shortUniqueSuffix = substring(uniqueSuffix, 0, 6)

// Networking
var vnetAddressPrefix = '10.0.0.0/16'
var containerAppsSubnetPrefix = '10.0.0.0/23'   // /23 required for Container Apps
var privateEndpointsSubnetPrefix = '10.0.4.0/24'
var platformReservedCidr = '10.0.16.0/24'
var platformReservedDnsIP = '10.0.16.10'
var dockerBridgeCidr = '172.17.0.1/16'

// Resource names
var logAnalyticsName = 'log-${prefix}-${shortUniqueSuffix}'
var keyVaultName = 'kv-${prefix}-${shortUniqueSuffix}'
var containerRegistryName = 'cr${prefix}${shortUniqueSuffix}'
var containerAppsEnvName = 'cae-${prefix}-${environmentName}'
var containerAppApiName = 'ca-${prefix}-api'
var staticWebAppName = 'swa-${prefix}-${environmentName}'
var postgresServerName = 'psql-${prefix}-${shortUniqueSuffix}'
var vnetName = 'vnet-${prefix}-${environmentName}'
var communicationServiceName = 'acs-${prefix}-${shortUniqueSuffix}'
var emailServiceName = 'ecs-${prefix}-${shortUniqueSuffix}'
var storageAccountName = 'st${prefix}${shortUniqueSuffix}'
var azureOpenAIName = 'aoai-${prefix}-${shortUniqueSuffix}'

// Custom domain URLs
var frontendUrl = enableCustomDomain ? 'https://${customDomain}' : 'https://${staticWebAppName}.azurestaticapps.net'
var apiUrl = enableCustomDomain ? 'https://api.${customDomain}' : 'https://${containerAppApiName}.${location}.azurecontainerapps.io'

// ============================================================================
// Resource Group
// ============================================================================

resource resourceGroup 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

// ============================================================================
// Modules
// ============================================================================

// Virtual Network for internal resources
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

// Log Analytics Workspace for centralized logging
module logAnalytics 'modules/logAnalytics.bicep' = {
  scope: resourceGroup
  name: 'log-analytics-deployment'
  params: {
    name: logAnalyticsName
    location: location
    tags: tags
  }
}

// Key Vault for secrets management (with CMK encryption keys)
module keyVault 'modules/keyVault.bicep' = {
  scope: resourceGroup
  name: 'keyvault-deployment'
  params: {
    name: keyVaultName
    location: location
    tags: tags
    logAnalyticsWorkspaceId: logAnalytics.outputs.resourceId
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
    ]
  }
}

// Container Registry for API images
module containerRegistry 'modules/containerRegistry.bicep' = {
  scope: resourceGroup
  name: 'acr-deployment'
  params: {
    name: containerRegistryName
    location: location
    tags: tags
    logAnalyticsWorkspaceId: logAnalytics.outputs.resourceId
    subnetId: vnet.outputs.privateEndpointsSubnetId
  }
}

// PostgreSQL Flexible Server for user data (with CMK encryption)
module postgres 'modules/postgres.bicep' = {
  scope: resourceGroup
  name: 'postgres-deployment'
  params: {
    name: postgresServerName
    location: location
    tags: tags
    administratorLogin: postgresAdminUsername
    administratorLoginPassword: postgresAdminPassword
    logAnalyticsWorkspaceId: logAnalytics.outputs.resourceId
    subnetId: vnet.outputs.privateEndpointsSubnetId
    environmentName: environmentName
    // CMK configuration for user data protection
    enableCMK: enableCMK
    keyVaultName: enableCMK ? keyVault.outputs.name : ''
    keyVaultResourceId: enableCMK ? keyVault.outputs.resourceId : ''
    cmkKeyUri: enableCMK ? keyVault.outputs.postgresEncryptionKeyUri : ''
  }
}

// Azure Storage Account for assets, exports, votes, and token storage (with CMK encryption)
module storageAccount 'modules/storageAccount.bicep' = {
  scope: resourceGroup
  name: 'storage-account-deployment'
  params: {
    name: storageAccountName
    location: location
    tags: tags
    logAnalyticsWorkspaceId: logAnalytics.outputs.resourceId
    subnetId: vnet.outputs.privateEndpointsSubnetId
    environmentName: environmentName
    // CMK configuration for vote data protection
    enableCMK: enableCMK
    keyVaultResourceId: enableCMK ? keyVault.outputs.resourceId : ''
    cmkKeyName: enableCMK ? 'storage-encryption-key' : ''
  }
}

// Azure OpenAI for AI-powered poll generation
module azureOpenAI 'modules/azureOpenAI.bicep' = if (deployAzureOpenAI) {
  scope: resourceGroup
  name: 'azure-openai-deployment'
  params: {
    name: azureOpenAIName
    location: location
    tags: tags
    logAnalyticsWorkspaceId: logAnalytics.outputs.resourceId
    subnetId: vnet.outputs.privateEndpointsSubnetId
    keyVaultResourceId: keyVault.outputs.resourceId
    environmentName: environmentName
  }
}

// Azure Communication Services for SMS notifications
module communicationServices 'modules/communicationServices.bicep' = {
  scope: resourceGroup
  name: 'communication-services-deployment'
  params: {
    name: communicationServiceName
    tags: tags
    dataLocation: 'United States'
    logAnalyticsWorkspaceId: logAnalytics.outputs.resourceId
  }
}

// Azure Email Communication Services for email verification
module emailServices 'modules/emailServices.bicep' = {
  scope: resourceGroup
  name: 'email-services-deployment'
  params: {
    name: emailServiceName
    tags: tags
    dataLocation: 'United States'
    enableUserEngagementTracking: environmentName == 'prod'
  }
}

// Azure DNS Zone for custom domain
module dnsZone 'modules/dnsZone.bicep' = if (enableCustomDomain) {
  scope: resourceGroup
  name: 'dns-zone-deployment'
  params: {
    name: customDomain
    tags: tags
    staticWebAppHostname: staticWebApp.outputs.defaultHostname
    containerAppApiFqdn: containerAppApi.outputs.fqdn
    staticWebAppResourceId: staticWebApp.outputs.resourceId
  }
}

// Container Apps Environment
module containerAppsEnv 'modules/containerAppsEnv.bicep' = {
  scope: resourceGroup
  name: 'container-apps-env-deployment'
  params: {
    name: containerAppsEnvName
    location: location
    tags: tags
    logAnalyticsWorkspaceResourceId: logAnalytics.outputs.resourceId
    infrastructureSubnetId: vnet.outputs.containerAppsSubnetId
    platformReservedCidr: platformReservedCidr
    platformReservedDnsIP: platformReservedDnsIP
    dockerBridgeCidr: dockerBridgeCidr
  }
}

// Container App - API
module containerAppApi 'modules/containerAppApi.bicep' = {
  scope: resourceGroup
  name: 'container-app-api-deployment'
  params: {
    name: containerAppApiName
    location: location
    tags: tags
    containerAppsEnvId: containerAppsEnv.outputs.resourceId
    containerRegistryName: containerRegistry.outputs.name
    containerRegistryLoginServer: containerRegistry.outputs.loginServer
    keyVaultName: keyVault.outputs.name
    keyVaultUri: keyVault.outputs.uri
    postgresHost: postgres.outputs.fqdn
    postgresDatabase: 'truepulse'
    postgresUsername: postgresAdminUsername
    storageAccountName: storageAccount.outputs.name
    storageAccountTableEndpoint: storageAccount.outputs.primaryTableEndpoint
    azureOpenAIEndpoint: deployAzureOpenAI ? azureOpenAI!.outputs.endpoint : ''
    azureOpenAIDeployment: deployAzureOpenAI ? azureOpenAI!.outputs.deploymentName : ''
    storageAccountUrl: storageAccount.outputs.primaryBlobEndpoint
    environmentName: environmentName
    communicationServicesName: communicationServices.outputs.name
    communicationSenderNumber: communicationSenderNumber
    emailServiceName: emailServices.outputs.name
    emailSenderAddress: emailSenderAddress
    customDomain: enableCustomDomain ? customDomain : ''
  }
}

// Static Web App for Frontend
module staticWebApp 'modules/staticWebApp.bicep' = {
  scope: resourceGroup
  name: 'swa-deployment'
  params: {
    name: staticWebAppName
    location: location
    tags: tags
    apiUrl: enableCustomDomain ? 'https://api.${customDomain}' : 'https://${containerAppApi.outputs.fqdn}'
    customDomain: enableCustomDomain ? customDomain : ''
  }
}

// ============================================================================
// Outputs
// ============================================================================

output resourceGroupName string = resourceGroup.name
output containerRegistryLoginServer string = containerRegistry.outputs.loginServer
output containerAppApiFqdn string = containerAppApi.outputs.fqdn
output staticWebAppHostname string = staticWebApp.outputs.defaultHostname
output staticWebAppDeploymentTokenInfo string = staticWebApp.outputs.deploymentTokenInfo
output keyVaultUri string = keyVault.outputs.uri
output communicationServicesName string = communicationServices.outputs.name
output emailServicesName string = emailServices.outputs.name
output emailDomainNames array = emailServices.outputs.domainNames
output dnsZoneNameServers array = dnsZone.?outputs.nameServers ?? []
output frontendUrl string = frontendUrl
output apiUrl string = apiUrl
output customDomain string = customDomain
output storageAccountName string = storageAccount.outputs.name
output storageAccountBlobEndpoint string = storageAccount.outputs.primaryBlobEndpoint
output azureOpenAIEndpoint string = deployAzureOpenAI ? azureOpenAI!.outputs.endpoint : ''
output azureOpenAIDeploymentName string = deployAzureOpenAI ? azureOpenAI!.outputs.deploymentName : ''
