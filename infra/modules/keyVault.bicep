// TruePulse Infrastructure - Key Vault
// Secure storage for secrets, keys, and certificates
// Provides Customer Managed Keys (CMK) for data encryption

// ============================================================================
// Parameters
// ============================================================================

@description('Key Vault name')
param name string

@description('Location for resources')
param location string

@description('Resource tags')
param tags object

@description('Log Analytics workspace resource ID')
param logAnalyticsWorkspaceId string

@description('Subnet ID for private endpoint')
param subnetId string

@description('Secrets to store in Key Vault - array of objects with name and value properties')
#disable-next-line secure-secrets-in-params
param secrets array = []

@description('Create CMK encryption keys for data services')
param createEncryptionKeys bool = true

@description('Shared Key Vault DNS zone resource ID')
param keyVaultDnsZoneId string = ''

// ============================================================================
// Resources
// ============================================================================

// Using Azure Verified Module: br/public:avm/res/key-vault/vault
module keyVault 'br/public:avm/res/key-vault/vault:0.11.1' = {
  name: 'key-vault'
  params: {
    name: name
    location: location
    tags: tags
    enableRbacAuthorization: true
    enablePurgeProtection: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    // Premium SKU required for HSM-backed keys (CMK)
    sku: 'premium'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Deny'
    }
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
    privateEndpoints: !empty(keyVaultDnsZoneId) ? [
      {
        name: '${name}-pe'
        subnetResourceId: subnetId
        service: 'vault'
        privateDnsZoneGroup: {
          privateDnsZoneGroupConfigs: [
            {
              privateDnsZoneResourceId: keyVaultDnsZoneId
            }
          ]
        }
      }
    ] : [
      {
        name: '${name}-pe'
        subnetResourceId: subnetId
        service: 'vault'
      }
    ]
  }
}

// ============================================================================
// Customer Managed Keys (CMK) for Data Encryption
// ============================================================================

// CMK for Storage Account encryption (votes, tokens, assets)
resource storageEncryptionKey 'Microsoft.KeyVault/vaults/keys@2023-07-01' = if (createEncryptionKeys) {
  name: '${name}/cmk-storage'
  properties: {
    kty: 'RSA'
    keySize: 4096
    keyOps: [
      'encrypt'
      'decrypt'
      'wrapKey'
      'unwrapKey'
    ]
    attributes: {
      enabled: true
      exportable: false
    }
    rotationPolicy: {
      lifetimeActions: [
        {
          action: {
            type: 'rotate'
          }
          trigger: {
            timeAfterCreate: 'P90D' // Rotate every 90 days
          }
        }
        {
          action: {
            type: 'notify'
          }
          trigger: {
            timeBeforeExpiry: 'P30D' // Notify 30 days before expiry
          }
        }
      ]
      attributes: {
        expiryTime: 'P2Y' // Key expires after 2 years
      }
    }
  }
  dependsOn: [keyVault]
}

// ============================================================================
// Secrets
// ============================================================================

// Store secrets - done separately due to AVM module limitations with secure params
@batchSize(1)
resource secretResources 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = [for secret in secrets: {
  name: '${name}/${secret.name}'
  properties: {
    value: secret.value
    contentType: 'text/plain'
    attributes: {
      enabled: true
    }
  }
  dependsOn: [keyVault]
}]

// ============================================================================
// Outputs
// ============================================================================

output resourceId string = keyVault.outputs.resourceId
output name string = keyVault.outputs.name
output uri string = keyVault.outputs.uri

// CMK outputs for data encryption
// Note: storageEncryptionKey.name returns 'vaultName/keyName', so we extract just the key name
output storageEncryptionKeyName string = createEncryptionKeys ? 'cmk-storage' : ''
output storageEncryptionKeyUri string = createEncryptionKeys ? storageEncryptionKey!.properties.keyUriWithVersion : ''
