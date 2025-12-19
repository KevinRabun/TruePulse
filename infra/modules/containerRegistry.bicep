// TruePulse Infrastructure - Container Registry
// Azure Container Registry for storing API container images

// ============================================================================
// Parameters
// ============================================================================

@description('Container Registry name')
param name string

@description('Location for resources')
param location string

@description('Resource tags')
param tags object

@description('Log Analytics workspace resource ID')
param logAnalyticsWorkspaceId string

@description('Subnet ID for private endpoint (optional for shared ACR)')
param subnetId string = ''

// ============================================================================
// Resources
// ============================================================================

// Using Azure Verified Module: br/public:avm/res/container-registry/registry
module acr 'br/public:avm/res/container-registry/registry:0.8.0' = {
  name: 'container-registry'
  params: {
    name: name
    location: location
    tags: tags
    acrSku: 'Premium'
    acrAdminUserEnabled: false
    zoneRedundancy: 'Enabled'
    networkRuleBypassOptions: 'AzureServices'
    // Shared ACR: Allow Azure services (Container Apps use managed identity)
    // Per-env ACR: Deny public, use private endpoint
    networkRuleSetDefaultAction: empty(subnetId) ? 'Allow' : 'Deny'
    publicNetworkAccess: empty(subnetId) ? 'Enabled' : 'Disabled'
    azureADAuthenticationAsArmPolicyStatus: 'enabled'
    quarantinePolicyStatus: 'enabled'
    trustPolicyStatus: 'enabled'
    retentionPolicyStatus: 'enabled'
    retentionPolicyDays: 30
    // Export policy can only be disabled when public network access is disabled
    exportPolicyStatus: empty(subnetId) ? 'enabled' : 'disabled'
    // Enable managed identity for pull access (more secure than admin credentials)
    managedIdentities: {
      systemAssigned: true
    }
    diagnosticSettings: [
      {
        name: 'send-to-log-analytics'
        workspaceResourceId: logAnalyticsWorkspaceId
        logCategoriesAndGroups: [
          {
            categoryGroup: 'allLogs'
            enabled: true
          }
        ]
        metricCategories: [
          {
            category: 'AllMetrics'
            enabled: true
          }
        ]
      }
    ]
    // Only create private endpoint if subnetId is provided
    privateEndpoints: empty(subnetId) ? [] : [
      {
        name: '${name}-pe'
        subnetResourceId: subnetId
        service: 'registry'
      }
    ]
  }
}

// ============================================================================
// Outputs
// ============================================================================

output resourceId string = acr.outputs.resourceId
output name string = acr.outputs.name
output loginServer string = acr.outputs.loginServer
