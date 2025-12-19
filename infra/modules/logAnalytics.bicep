// TruePulse Infrastructure - Log Analytics Workspace
// Centralized logging for all Azure resources

// ============================================================================
// Parameters
// ============================================================================

@description('Log Analytics workspace name')
param name string

@description('Location for resources')
param location string

@description('Resource tags')
param tags object

// ============================================================================
// Resources
// ============================================================================

// Using Azure Verified Module: br/public:avm/res/operational-insights/workspace
module workspace 'br/public:avm/res/operational-insights/workspace:0.9.1' = {
  name: 'log-analytics-workspace'
  params: {
    name: name
    location: location
    tags: tags
    skuName: 'PerGB2018'
    dataRetention: 90
    dailyQuotaGb: 10
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
    managedIdentities: {
      systemAssigned: true
    }
  }
}

// ============================================================================
// Outputs
// ============================================================================

output resourceId string = workspace.outputs.resourceId
output name string = workspace.outputs.name
output customerId string = workspace.outputs.logAnalyticsWorkspaceId
