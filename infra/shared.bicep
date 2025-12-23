// TruePulse Infrastructure - Shared Services
// These resources are shared across all environments (dev, staging, prod)
// Deploy once and reference from environment-specific deployments
//
// SHARED RESOURCES (stateless, no private data):
// - Log Analytics: Centralized logging
// - Container Registry: Shared image storage (accessed via managed identity)
// - Communication Services: SMS API (stateless, pay-per-use)
// - Email Services: Email API (stateless, pay-per-use)  
// - DNS Zone: Single zone for all subdomains
//
// PER-ENVIRONMENT RESOURCES (require private endpoints or data isolation):
// - Azure OpenAI: Requires private endpoint per VNet
// - PostgreSQL: Data isolation per environment
// - Key Vault: Secrets isolation per environment
// - Storage Account: Data isolation per environment

targetScope = 'subscription'

// ============================================================================
// Parameters
// ============================================================================

@description('Primary Azure region for resources')
param location string = 'eastus2'

@description('Resource name prefix')
param prefix string = 'truepulse'

@description('Tags to apply to all resources')
param tags object = {
  project: 'TruePulse'
  environment: 'shared'
  managedBy: 'bicep'
}

@description('Custom domain name for the application')
param customDomain string = 'truepulse.net'

// ============================================================================
// Variables
// ============================================================================

var resourceGroupName = 'rg-${prefix}-shared'
var uniqueSuffix = uniqueString(subscription().subscriptionId, resourceGroupName, location)
var shortUniqueSuffix = substring(uniqueSuffix, 0, 6)

// Resource names (shared across all environments)
var logAnalyticsName = 'log-${prefix}-${shortUniqueSuffix}'
var containerRegistryName = 'cr${prefix}${shortUniqueSuffix}'
var communicationServiceName = 'acs-${prefix}-${shortUniqueSuffix}'
var emailServiceName = 'ecs-${prefix}-${shortUniqueSuffix}'
var dnsZoneName = customDomain

// ============================================================================
// Resource Group
// ============================================================================

resource resourceGroup 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

// ============================================================================
// Shared Modules
// ============================================================================

// Log Analytics Workspace - centralized logging for all environments
module logAnalytics 'modules/logAnalytics.bicep' = {
  scope: resourceGroup
  name: 'shared-log-analytics'
  params: {
    name: logAnalyticsName
    location: location
    tags: tags
  }
}

// Container Registry - stores images for all environments with tags (:dev, :staging, :prod)
module containerRegistry 'modules/containerRegistry.bicep' = {
  scope: resourceGroup
  name: 'shared-acr'
  params: {
    name: containerRegistryName
    location: location
    tags: tags
    logAnalyticsWorkspaceId: logAnalytics.outputs.resourceId
    // No private endpoint for shared ACR - needs to be accessible from all env VNets
    subnetId: ''
  }
}

// Azure Communication Services - SMS API (stateless, pay-per-use)
module communicationServices 'modules/communicationServices.bicep' = {
  scope: resourceGroup
  name: 'shared-communication-services'
  params: {
    name: communicationServiceName
    tags: tags
    // Link to the custom email domain for sending emails
    // The domain must exist in the email service before linking
    linkedDomains: [
      '${emailServices.outputs.resourceId}/domains/${customDomain}'
    ]
  }
  dependsOn: [
    emailServices
  ]
}

// Email Communication Services - Email API (stateless, pay-per-use)
module emailServices 'modules/emailServices.bicep' = {
  scope: resourceGroup
  name: 'shared-email-services'
  params: {
    name: emailServiceName
    tags: tags
    customDomain: customDomain
  }
}

// DNS Zone - single zone with subdomains for all environments
module dnsZone 'modules/dnsZone.bicep' = {
  scope: resourceGroup
  name: 'shared-dns-zone'
  params: {
    name: dnsZoneName
    tags: tags
  }
}

// Private DNS Zones - centralized for all private endpoint resolution
// VNet links are created per environment when those environments deploy
module privateDnsZones 'modules/privateDnsZones.bicep' = {
  scope: resourceGroup
  name: 'shared-private-dns-zones'
  params: {
    tags: tags
  }
}

// ============================================================================
// Outputs - Used by environment-specific deployments
// ============================================================================

output resourceGroupName string = resourceGroup.name
output logAnalyticsWorkspaceId string = logAnalytics.outputs.resourceId
output logAnalyticsWorkspaceName string = logAnalytics.outputs.name

output containerRegistryName string = containerRegistry.outputs.name
output containerRegistryLoginServer string = containerRegistry.outputs.loginServer
output containerRegistryResourceId string = containerRegistry.outputs.resourceId

output communicationServiceName string = communicationServices.outputs.name
output communicationServiceResourceId string = communicationServices.outputs.resourceId

output emailServiceName string = emailServices.outputs.name

output dnsZoneName string = dnsZone.outputs.name
output dnsZoneResourceId string = dnsZone.outputs.resourceId

// Private DNS Zone outputs for environment deployments
output blobDnsZoneId string = privateDnsZones.outputs.blobDnsZoneId
output tableDnsZoneId string = privateDnsZones.outputs.tableDnsZoneId
output openaiDnsZoneId string = privateDnsZones.outputs.openaiDnsZoneId
output postgresDnsZoneId string = privateDnsZones.outputs.postgresDnsZoneId
output keyVaultDnsZoneId string = privateDnsZones.outputs.keyVaultDnsZoneId
output acrDnsZoneId string = privateDnsZones.outputs.acrDnsZoneId
