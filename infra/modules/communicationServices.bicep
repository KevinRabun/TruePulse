// Azure Communication Services for SMS notifications
// Uses Azure Verified Module (AVM) pattern

@description('Name of the communication service')
param name string

@description('Location for the resource (Communication Services uses global)')
param location string = 'global'

@description('Tags to apply to resources')
param tags object = {}

@description('The location where data is stored at rest')
@allowed([
  'Africa'
  'Asia Pacific'
  'Australia'
  'Brazil'
  'Canada'
  'Europe'
  'France'
  'Germany'
  'India'
  'Japan'
  'Korea'
  'Norway'
  'Switzerland'
  'UAE'
  'UK'
  'United States'
])
param dataLocation string = 'United States'

@description('Log Analytics Workspace ID for diagnostics')
param logAnalyticsWorkspaceId string = ''

// ============================================================================
// Communication Service using Azure Verified Module
// ============================================================================

module communicationService 'br/public:avm/res/communication/communication-service:0.3.1' = {
  name: 'communication-service-deployment'
  params: {
    name: name
    dataLocation: dataLocation
    location: location
    tags: tags
    managedIdentities: {
      systemAssigned: true
    }
    diagnosticSettings: !empty(logAnalyticsWorkspaceId) ? [
      {
        workspaceResourceId: logAnalyticsWorkspaceId
        metricCategories: [
          {
            category: 'AllMetrics'
          }
        ]
        logCategoriesAndGroups: [
          {
            categoryGroup: 'allLogs'
          }
        ]
      }
    ] : []
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('The name of the communication service')
output name string = communicationService.outputs.name

@description('The resource ID of the communication service')
output resourceId string = communicationService.outputs.resourceId

@description('The principal ID of the system assigned identity')
output principalId string = communicationService.outputs.?systemAssignedMIPrincipalId  ?? ''

@description('The resource group name')
output resourceGroupName string = communicationService.outputs.resourceGroupName
