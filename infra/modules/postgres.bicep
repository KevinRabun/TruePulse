// TruePulse Infrastructure - PostgreSQL Flexible Server
// Stores user accounts, profiles, achievements, and subscriptions
// Encrypted with Customer Managed Keys (CMK) for user data protection

// ============================================================================
// Parameters
// ============================================================================

@description('PostgreSQL server name')
param name string

@description('Location for resources')
param location string

@description('Resource tags')
param tags object

@description('Administrator login name')
param administratorLogin string

@description('Administrator password')
@secure()
param administratorLoginPassword string

@description('Log Analytics workspace resource ID')
param logAnalyticsWorkspaceId string

@description('Subnet ID for private endpoint')
param subnetId string

@description('Environment name for SKU selection')
param environmentName string

@description('Key Vault name for CMK')
#disable-next-line no-unused-params
param keyVaultName string = ''

@description('Key Vault resource ID for CMK')
param keyVaultResourceId string = ''

@description('CMK key URI (with version) for encryption')
param cmkKeyUri string = ''

@description('Enable Customer Managed Keys (CMK) for encryption')
param enableCMK bool = true

@description('Shared PostgreSQL DNS zone resource ID')
param postgresDnsZoneId string = ''

// ============================================================================
// Variables
// ============================================================================

var skuConfig = {
  dev: {
    name: 'Standard_B2s'
    tier: 'Burstable'
    storageSizeGB: 32
    backupRetentionDays: 7
    highAvailability: 'Disabled'
  }
  staging: {
    name: 'Standard_D2ds_v5'
    tier: 'GeneralPurpose'
    storageSizeGB: 64
    backupRetentionDays: 14
    highAvailability: 'SameZone'
  }
  prod: {
    name: 'Standard_D4ds_v5'
    tier: 'GeneralPurpose'
    storageSizeGB: 128
    backupRetentionDays: 35
    highAvailability: 'ZoneRedundant'
  }
}

var selectedSku = skuConfig[environmentName]

// CMK is only supported on GeneralPurpose and MemoryOptimized tiers, not Burstable
// See: https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/concepts-data-encryption
var cmkSupported = selectedSku.tier != 'Burstable'
var effectiveEnableCMK = enableCMK && cmkSupported

// ============================================================================
// Resources
// ============================================================================

// User-assigned managed identity for CMK access
resource postgresIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = if (effectiveEnableCMK) {
  name: '${name}-identity'
  location: location
  tags: tags
}

// Reference to existing Key Vault for role assignment scope
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = if (effectiveEnableCMK) {
  name: last(split(keyVaultResourceId, '/'))
}

// Role assignment for Key Vault Crypto Service Encryption User
// Required for PostgreSQL to use CMK from Key Vault
// CRITICAL: Must be scoped to Key Vault, not resource group
// Note: GUID includes 'kv-scope' to differentiate from old resource-group-scoped assignment
resource keyVaultCryptoUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (effectiveEnableCMK) {
  name: guid(keyVaultResourceId, postgresIdentity.id, 'Key Vault Crypto Service Encryption User', 'postgres-cmk-kv-scope')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'e147488a-f6f5-4113-8e2d-b22465e65bf6') // Key Vault Crypto Service Encryption User
    principalId: postgresIdentity!.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Using Azure Verified Module: br/public:avm/res/db-for-postgre-sql/flexible-server
module postgres 'br/public:avm/res/db-for-postgre-sql/flexible-server:0.14.0' = {
  name: 'postgres-server'
  params: {
    name: name
    location: location
    tags: tags
    skuName: selectedSku.name
    tier: selectedSku.tier
    version: '16'
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorLoginPassword
    storageSizeGB: selectedSku.storageSizeGB
    backupRetentionDays: selectedSku.backupRetentionDays
    geoRedundantBackup: environmentName == 'prod' ? 'Enabled' : 'Disabled'
    highAvailability: selectedSku.highAvailability
    availabilityZone: 1
    // Security settings - CRITICAL: Disable public network access
    // All access must go through private endpoints only
    publicNetworkAccess: 'Disabled'
    // Authentication configuration
    authConfig: {
      activeDirectoryAuth: 'Enabled'
      passwordAuth: 'Enabled'
    }
    // Customer Managed Key (CMK) configuration
    // Note: CMK only supported on GeneralPurpose and MemoryOptimized tiers, not Burstable
    customerManagedKey: effectiveEnableCMK ? {
      keyVaultResourceId: keyVaultResourceId
      keyName: 'cmk-postgres'
      keyVersion: last(split(cmkKeyUri, '/'))
      userAssignedIdentityResourceId: postgresIdentity.id
    } : null
    managedIdentities: effectiveEnableCMK ? {
      userAssignedResourceIds: [
        postgresIdentity.id
      ]
    } : null
    // Performance settings
    configurations: [
      {
        name: 'max_connections'
        source: 'user-override'
        value: '200'
      }
      {
        name: 'shared_preload_libraries'
        source: 'user-override'
        value: 'pg_stat_statements'
      }
    ]
    databases: [
      {
        name: 'truepulse'
        charset: 'UTF8'
        collation: 'en_US.utf8'
      }
    ]
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
    privateEndpoints: !empty(postgresDnsZoneId) ? [
      {
        name: '${name}-pe'
        subnetResourceId: subnetId
        service: 'postgresqlServer'
        privateDnsZoneGroup: {
          privateDnsZoneGroupConfigs: [
            {
              privateDnsZoneResourceId: postgresDnsZoneId
            }
          ]
        }
      }
    ] : [
      {
        name: '${name}-pe'
        subnetResourceId: subnetId
        service: 'postgresqlServer'
      }
    ]
  }
  dependsOn: effectiveEnableCMK ? [keyVaultCryptoUserRole] : []
}

// ============================================================================
// Outputs
// ============================================================================

output resourceId string = postgres.outputs.resourceId
output name string = postgres.outputs.name
output fqdn string = postgres.outputs.?fqdn ?? ''
