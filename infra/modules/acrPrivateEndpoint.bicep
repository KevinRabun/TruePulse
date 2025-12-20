// TruePulse Infrastructure - ACR Private Endpoint Module
// Creates a private endpoint for accessing shared ACR from an environment's VNet

@description('Name of the private endpoint')
param name string

@description('Location for resources')
param location string

@description('Resource tags')
param tags object

@description('Subnet ID for the private endpoint')
param subnetId string

@description('Resource ID of the shared Container Registry')
param containerRegistryResourceId string

@description('Resource ID of the ACR private DNS zone')
param acrDnsZoneId string

// ============================================================================
// Private Endpoint for ACR
// ============================================================================

resource privateEndpoint 'Microsoft.Network/privateEndpoints@2023-11-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: '${name}-connection'
        properties: {
          privateLinkServiceId: containerRegistryResourceId
          groupIds: [
            'registry'
          ]
        }
      }
    ]
  }
}

// DNS Zone Group - automatically creates A records in the private DNS zone
resource privateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-11-01' = {
  parent: privateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'privatelink-azurecr-io'
        properties: {
          privateDnsZoneId: acrDnsZoneId
        }
      }
    ]
  }
}

// ============================================================================
// Outputs
// ============================================================================

output privateEndpointId string = privateEndpoint.id
output privateEndpointName string = privateEndpoint.name
