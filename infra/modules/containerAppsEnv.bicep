// TruePulse Infrastructure - Container Apps Environment
// Managed serverless environment for the API backend
// COST OPTIMIZED: Uses consumption-only model with scale-to-zero capability

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

@description('Environment name (dev, staging, prod)')
@allowed(['dev', 'staging', 'prod'])
param environmentName string = 'dev'

// ============================================================================
// Resources
// ============================================================================

// Using Azure Verified Module: br/public:avm/res/app/managed-environment
// COST OPTIMIZATION: Consumption-only plan with no dedicated workload profiles
// - Consumption plan: Pay only for actual execution time
// - Scale to zero: Zero cost when idle (perfect for dev/staging)
// - Auto-scaling: KEDA-based scaling up to 300 replicas (default), can request up to 1000
module containerAppsEnv 'br/public:avm/res/app/managed-environment:0.11.0' = {
  name: 'container-apps-env'
  params: {
    name: name
    location: location
    tags: tags
    // VNet integration - External for Cloudflare access with IP restrictions at Container App level
    internal: false
    // Enable public network access for external ingress
    publicNetworkAccess: 'Enabled'
    infrastructureSubnetResourceId: infrastructureSubnetId
    infrastructureResourceGroupName: 'ME_${name}'
    platformReservedCidr: platformReservedCidr
    platformReservedDnsIP: platformReservedDnsIP
    dockerBridgeCidr: dockerBridgeCidr
    // Zone redundancy - only enable for production to save costs
    // Zone redundancy provides HA across availability zones but increases base cost
    zoneRedundant: environmentName == 'prod'
    // Logging configuration - using azure-monitor destination (no shared key required)
    appLogsConfiguration: {
      destination: 'azure-monitor'
    }
    // COST OPTIMIZATION: Consumption-only workload profile
    // - No dedicated D4 workload profile = no base compute cost
    // - Consumption profile is automatically included
    // - Pay only for vCPU-seconds and GiB-seconds when containers are running
    // - FastAPI backend is lightweight and doesn't need dedicated compute
    workloadProfiles: []
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
