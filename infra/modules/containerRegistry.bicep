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

@description('Subnet ID for private endpoint')
param subnetId string

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
    networkRuleSetDefaultAction: 'Deny'
    azureADAuthenticationAsArmPolicyStatus: 'enabled'
    quarantinePolicyStatus: 'enabled'
    trustPolicyStatus: 'enabled'
    retentionPolicyStatus: 'enabled'
    retentionPolicyDays: 30
    exportPolicyStatus: 'disabled'
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
    privateEndpoints: [
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
