// TruePulse Infrastructure - Virtual Network
// Uses Azure Verified Modules (AVM) for network resources

// ============================================================================
// Parameters
// ============================================================================

@description('Virtual network name')
param name string

@description('Location for resources')
param location string

@description('Resource tags')
param tags object

@description('VNet address prefix')
param vnetAddressPrefix string

@description('Container Apps subnet prefix')
param containerAppsSubnetPrefix string

@description('Private endpoints subnet prefix')
param privateEndpointsSubnetPrefix string

// ============================================================================
// Public IP for NAT Gateway
// ============================================================================
resource natGatewayPublicIp 'Microsoft.Network/publicIPAddresses@2023-09-01' = {
  name: 'pip-nat-${name}'
  location: location
  tags: tags
  sku: {
    name: 'Standard'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
    publicIPAddressVersion: 'IPv4'
  }
}

// ============================================================================
// NAT Gateway for outbound internet access
// ============================================================================
resource natGateway 'Microsoft.Network/natGateways@2023-09-01' = {
  name: 'nat-${name}'
  location: location
  tags: tags
  sku: {
    name: 'Standard'
  }
  properties: {
    idleTimeoutInMinutes: 4
    publicIpAddresses: [
      {
        id: natGatewayPublicIp.id
      }
    ]
  }
}

// ============================================================================
// Virtual Network using Azure Verified Module
// ============================================================================
module virtualNetwork 'br/public:avm/res/network/virtual-network:0.6.1' = {
  name: '${name}-deployment'
  params: {
    name: name
    location: location
    tags: tags
    addressPrefixes: [
      vnetAddressPrefix
    ]
    subnets: [
      {
        name: 'snet-container-apps'
        addressPrefix: containerAppsSubnetPrefix
        delegation: 'Microsoft.App/environments'
        privateEndpointNetworkPolicies: 'Disabled'
        privateLinkServiceNetworkPolicies: 'Disabled'
        natGatewayResourceId: natGateway.id
      }
      {
        name: 'snet-private-endpoints'
        addressPrefix: privateEndpointsSubnetPrefix
        privateEndpointNetworkPolicies: 'Disabled'
        privateLinkServiceNetworkPolicies: 'Enabled'
      }
    ]
  }
}

// ============================================================================
// Outputs
// ============================================================================

output resourceId string = virtualNetwork.outputs.resourceId
output vnetId string = virtualNetwork.outputs.resourceId
output name string = virtualNetwork.outputs.name
output containerAppsSubnetId string = virtualNetwork.outputs.subnetResourceIds[0]
output privateEndpointsSubnetId string = virtualNetwork.outputs.subnetResourceIds[1]
output natGatewayId string = natGateway.id
output natGatewayPublicIpAddress string = natGatewayPublicIp.properties.ipAddress
