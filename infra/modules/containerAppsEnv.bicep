// TruePulse Infrastructure - Container Apps Environment
// Managed Kubernetes environment for the API backend

// ============================================================================
// Parameters
// ============================================================================

@description('Container Apps Environment name')
param name string

@description('Location for resources')
param location string

@description('Resource tags')
param tags object

@description('Infrastructure subnet ID for Container Apps')
param infrastructureSubnetId string

@description('Platform reserved CIDR')
param platformReservedCidr string

@description('Platform reserved DNS IP')
param platformReservedDnsIP string

@description('Docker bridge CIDR')
param dockerBridgeCidr string

// ============================================================================
// Resources
// ============================================================================

// Using Azure Verified Module: br/public:avm/res/app/managed-environment
// Updated to AVM 0.11.0 with external access for Cloudflare integration
module containerAppsEnv 'br/public:avm/res/app/managed-environment:0.11.0' = {
  name: 'container-apps-env'
  params: {
    name: name
    location: location
    tags: tags
    // VNet integration - External for Cloudflare access with IP restrictions at Container App level
    internal: false
    infrastructureSubnetResourceId: infrastructureSubnetId
    infrastructureResourceGroupName: 'ME_${name}'
    platformReservedCidr: platformReservedCidr
    platformReservedDnsIP: platformReservedDnsIP
    dockerBridgeCidr: dockerBridgeCidr
    // Zone redundancy
    zoneRedundant: true
    // Logging configuration - using azure-monitor destination (no shared key required)
    appLogsConfiguration: {
      destination: 'azure-monitor'
    }
    // Workload profiles for production workloads
    workloadProfiles: [
      {
        name: 'CAW01'
        workloadProfileType: 'D4'
        minimumCount: 0
        maximumCount: 10
      }
    ]
    // Peer traffic encryption
    peerTrafficEncryption: true
    // Managed identity
    managedIdentities: {
      systemAssigned: true
    }
  }
}

// ============================================================================
// Outputs
// ============================================================================

output resourceId string = containerAppsEnv.outputs.resourceId
output name string = containerAppsEnv.outputs.name
output defaultDomain string = containerAppsEnv.outputs.defaultDomain
output staticIp string = containerAppsEnv.outputs.staticIp
