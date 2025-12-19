// TruePulse Infrastructure - ACR Role Assignment
// Grants AcrPull role to a managed identity for cross-resource-group ACR access

@description('Container Registry name')
param containerRegistryName string

@description('Principal ID to grant access to')
param principalId string

@description('Principal type (ServicePrincipal or User)')
param principalType string = 'ServicePrincipal'

// Reference the existing ACR in this resource group
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-06-01-preview' existing = {
  name: containerRegistryName
}

// Grant ACR pull permission
resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistryName, principalId, 'acrpull')
  scope: containerRegistry
  properties: {
    principalId: principalId
    principalType: principalType
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
  }
}
