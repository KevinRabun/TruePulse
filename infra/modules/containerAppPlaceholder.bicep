// TruePulse Infrastructure - Placeholder Container App
// Minimal Container App for initial infrastructure deployment
// This gets replaced by the actual API during the Build Backend job

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

// ============================================================================
// Resources
// ============================================================================

// User-assigned managed identity for ACR access
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${name}-identity'
  location: location
  tags: tags
}

// Minimal Container App using Azure Verified Module
module containerApp 'br/public:avm/res/app/container-app:0.12.1' = {
  name: 'container-app-api'
  params: {
    name: name
    location: location
    tags: tags
    environmentResourceId: containerAppsEnvId
    // Simple container configuration with placeholder image
    containers: [
      {
        name: 'api'
        image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
        resources: {
          cpu: json('0.25')
          memory: '0.5Gi'
        }
        // No environment variables, no secrets, no probes
      }
    ]
    // Ingress configuration
    ingressExternal: true
    ingressTargetPort: 80
    ingressTransport: 'http'
    // Scaling - single instance
    scaleMinReplicas: 1
    scaleMaxReplicas: 1
    // Managed identity
    managedIdentities: {
      systemAssigned: true
      userAssignedResourceIds: [
        managedIdentity.id
      ]
    }
    // Registry configuration (for later use)
    registries: [
      {
        server: containerRegistryLoginServer
        identity: managedIdentity.id
      }
    ]
    // Workload profile
    workloadProfileName: 'Consumption'
  }
}

// ============================================================================
// Outputs
// ============================================================================

output resourceId string = containerApp.outputs.resourceId
output name string = containerApp.outputs.name
output fqdn string = containerApp.outputs.fqdn
output managedIdentityId string = managedIdentity.id
output managedIdentityPrincipalId string = managedIdentity.properties.principalId
