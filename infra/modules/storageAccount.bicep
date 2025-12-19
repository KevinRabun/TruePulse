// TruePulse Infrastructure - Azure Storage Account Module
// Uses Azure Verified Modules (AVM) for Storage
// Encrypted with Customer Managed Keys (CMK) for vote data protection

@description('Storage account name')
param name string

@description('Azure region for the storage account')
param location string

@description('Tags to apply to the resource')
param tags object

@description('Log Analytics workspace resource ID for diagnostics')
param logAnalyticsWorkspaceId string

@description('Subnet ID for private endpoint')
param subnetId string

@description('Environment name for SKU selection')
@allowed(['dev', 'staging', 'prod'])
param environmentName string = 'dev'

@description('Key Vault resource ID for CMK')
param keyVaultResourceId string = ''

@description('CMK key name for encryption')
param cmkKeyName string = ''

@description('Enable Customer Managed Keys (CMK) for encryption')
param enableCMK bool = true

@description('Shared blob DNS zone resource ID')
param blobDnsZoneId string

@description('Shared table DNS zone resource ID')
param tableDnsZoneId string

// SKU selection based on environment
var skuName = environmentName == 'prod' ? 'Standard_ZRS' : 'Standard_LRS'

// ============================================================================
// User-assigned managed identity for CMK access (when CMK is enabled)
// ============================================================================
resource storageIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = if (enableCMK) {
  name: '${name}-identity'
  location: location
  tags: tags
}

// Role assignment for Key Vault Crypto Service Encryption User
resource keyVaultCryptoUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (enableCMK) {
  name: guid(keyVaultResourceId, storageIdentity.id, 'e147488a-f6f5-4113-8e2d-b22465e65bf6')
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'e147488a-f6f5-4113-8e2d-b22465e65bf6')
    principalId: storageIdentity!.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// ============================================================================
// Storage Account using Azure Verified Module
// ============================================================================
module storageAccount 'br/public:avm/res/storage/storage-account:0.18.0' = {
  name: '${name}-deployment'
  params: {
    name: name
    location: location
    tags: tags
    kind: 'StorageV2'
    skuName: skuName
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowCrossTenantReplication: false
    allowSharedKeyAccess: true
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    publicNetworkAccess: 'Disabled'
    requireInfrastructureEncryption: true
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Deny'
    }
    // Customer Managed Key configuration (when enabled)
    managedIdentities: enableCMK ? {
      userAssignedResourceIds: [
        storageIdentity.id
      ]
    } : null
    customerManagedKey: enableCMK ? {
      keyVaultResourceId: keyVaultResourceId
      keyName: cmkKeyName
      userAssignedIdentityResourceId: storageIdentity.id
    } : null
    // Blob services configuration
    blobServices: {
      containerDeleteRetentionPolicyEnabled: true
      containerDeleteRetentionPolicyDays: 7
      deleteRetentionPolicyEnabled: true
      deleteRetentionPolicyDays: 7
      containers: [
        {
          name: 'poll-assets'
          publicAccess: 'None'
        }
        {
          name: 'user-profiles'
          publicAccess: 'None'
        }
        {
          name: 'exports'
          publicAccess: 'None'
        }
      ]
      diagnosticSettings: [
        {
          name: '${name}-blob-diagnostics'
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
    }
    // Table services configuration
    tableServices: {
      tables: [
        { name: 'votes' }
        { name: 'tokenblacklist' }
        { name: 'resettokens' }
        { name: 'ratelimits' }
      ]
    }
    // Private endpoints configuration (uses shared DNS zones)
    privateEndpoints: [
      {
        name: 'pe-${name}-blob'
        service: 'blob'
        subnetResourceId: subnetId
        privateDnsZoneGroup: {
          privateDnsZoneGroupConfigs: [
            {
              privateDnsZoneResourceId: blobDnsZoneId
            }
          ]
        }
        tags: tags
      }
      {
        name: 'pe-${name}-table'
        service: 'table'
        subnetResourceId: subnetId
        privateDnsZoneGroup: {
          privateDnsZoneGroupConfigs: [
            {
              privateDnsZoneResourceId: tableDnsZoneId
            }
          ]
        }
        tags: tags
      }
    ]
    // Diagnostic settings
    diagnosticSettings: [
      {
        name: '${name}-diagnostics'
        workspaceResourceId: logAnalyticsWorkspaceId
        metricCategories: [
          {
            category: 'AllMetrics'
            enabled: true
          }
        ]
      }
    ]
  }
  dependsOn: enableCMK ? [keyVaultCryptoUserRole] : []
}

// ============================================================================
// Outputs
// ============================================================================
@description('The resource ID of the storage account')
output resourceId string = storageAccount.outputs.resourceId

@description('The name of the storage account')
output name string = storageAccount.outputs.name

@description('The primary blob endpoint')
output primaryBlobEndpoint string = storageAccount.outputs.primaryBlobEndpoint

@description('The primary blob endpoint URL for configuration')
output blobEndpointUrl string = storageAccount.outputs.primaryBlobEndpoint

@description('The primary table endpoint')
output primaryTableEndpoint string = storageAccount.outputs.serviceEndpoints.table
