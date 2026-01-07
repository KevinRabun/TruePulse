// TruePulse Infrastructure - Cosmos DB CMK Managed Identity
// Creates a User-Assigned Managed Identity for Cosmos DB CMK encryption
// This MI must be created and granted Key Vault access before Cosmos DB creation

// ============================================================================
// Parameters
// ============================================================================

@description('Managed Identity name')
param name string

@description('Location for resources')
param location string

@description('Resource tags')
param tags object

@description('Key Vault resource ID to grant CMK access')
param keyVaultResourceId string

// ============================================================================
// Resources
// ============================================================================

// User-Assigned Managed Identity for Cosmos DB CMK
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: name
  location: location
  tags: tags
}

// Grant MI access to Key Vault for CMK
// Key Vault Crypto Service Encryption User role - allows using keys for encryption
var keyVaultCryptoServiceEncryptionUserRoleId = 'e147488a-f6f5-4113-8e2d-b22465e65bf6'

// Extract Key Vault name from resource ID for scoping
var keyVaultName = last(split(keyVaultResourceId, '/'))

// Reference existing Key Vault for role assignment scope
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource keyVaultRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(managedIdentity.id, keyVaultResourceId, keyVaultCryptoServiceEncryptionUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultCryptoServiceEncryptionUserRoleId)
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// ============================================================================
// Outputs
// ============================================================================

output id string = managedIdentity.id
output principalId string = managedIdentity.properties.principalId
output clientId string = managedIdentity.properties.clientId
