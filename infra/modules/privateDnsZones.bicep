// TruePulse Infrastructure - Private DNS Zones Module
// Creates centralized private DNS zones for Azure services
// These zones are shared across all environments, with VNet links added per environment

@description('Tags to apply to resources')
param tags object

// ============================================================================
// Private DNS Zones
// Each zone handles resolution for a specific Azure service's private endpoints
// ============================================================================

// Storage - Blob
resource blobDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.blob.${environment().suffixes.storage}'
  location: 'global'
  tags: tags
}

// Storage - Table
resource tableDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.table.${environment().suffixes.storage}'
  location: 'global'
  tags: tags
}

// Azure OpenAI
resource openaiDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.openai.azure.com'
  location: 'global'
  tags: tags
}

// PostgreSQL Flexible Server
resource postgresDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.postgres.database.azure.com'
  location: 'global'
  tags: tags
}

// Key Vault
resource keyVaultDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.vaultcore.azure.net'
  location: 'global'
  tags: tags
}

// Azure Container Registry
resource acrDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.azurecr.io'
  location: 'global'
  tags: tags
}

// ============================================================================
// Outputs
// ============================================================================

output blobDnsZoneId string = blobDnsZone.id
output blobDnsZoneName string = blobDnsZone.name

output tableDnsZoneId string = tableDnsZone.id
output tableDnsZoneName string = tableDnsZone.name

output openaiDnsZoneId string = openaiDnsZone.id
output openaiDnsZoneName string = openaiDnsZone.name

output postgresDnsZoneId string = postgresDnsZone.id
output postgresDnsZoneName string = postgresDnsZone.name

output keyVaultDnsZoneId string = keyVaultDnsZone.id
output keyVaultDnsZoneName string = keyVaultDnsZone.name

output acrDnsZoneId string = acrDnsZone.id
output acrDnsZoneName string = acrDnsZone.name
