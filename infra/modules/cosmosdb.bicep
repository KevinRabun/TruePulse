// TruePulse Infrastructure - Azure Cosmos DB Serverless
// Stores users, polls, votes, and achievements in a document database
// Uses Serverless capacity mode for cost-effective pay-per-request billing

// ============================================================================
// Parameters
// ============================================================================

@description('Cosmos DB account name')
param name string

@description('Location for resources')
param location string

@description('Resource tags')
param tags object

@description('Log Analytics workspace resource ID')
param logAnalyticsWorkspaceId string

@description('Subnet ID for private endpoint')
param subnetId string

@description('Environment name for configuration')
param environmentName string

@description('Shared Cosmos DB DNS zone resource ID')
param cosmosDnsZoneId string = ''

@description('Principal ID for data plane RBAC access (Container App managed identity)')
param dataPlanePrincipalId string = ''

@description('Enable Customer Managed Keys (CMK) for encryption')
param enableCMK bool = false

@description('Key Vault resource ID for CMK')
param keyVaultResourceId string = ''

@description('CMK key name in Key Vault')
param cmkKeyName string = ''

@description('Skip container deployment (used when CMK is enabled to deploy containers separately)')
param skipContainers bool = false

@description('User-Assigned Managed Identity resource ID for CMK (required for CMK with continuous backup)')
param cmkUserAssignedIdentityId string = ''

// ============================================================================
// Variables
// ============================================================================

// Database name
var databaseName = 'truepulse'

// Container definitions with partition keys
// Design rationale:
// - users: partition by /id for efficient point reads
// - polls: partition by /id for efficient point reads
// - votes: partition by /poll_id for efficient queries per poll
// - achievements: partition by /user_id for efficient user queries
// - email-lookup: secondary index for email -> user_id lookups
// - username-lookup: secondary index for username -> user_id lookups
var containers = [
  {
    name: 'users'
    partitionKey: '/id'
    uniqueKeys: [
      { paths: [ '/email' ] }
      { paths: [ '/username' ] }
    ]
    indexingPolicy: {
      indexingMode: 'consistent'
      includedPaths: [
        { path: '/email/?' }
        { path: '/username/?' }
        { path: '/is_active/?' }
        { path: '/created_at/?' }
      ]
      excludedPaths: [
        { path: '/*' }
        { path: '/_etag/?' }
      ]
    }
  }
  {
    name: 'polls'
    partitionKey: '/id'
    uniqueKeys: []
    indexingPolicy: {
      indexingMode: 'consistent'
      includedPaths: [
        { path: '/status/?' }
        { path: '/poll_type/?' }
        { path: '/scheduled_start/?' }
        { path: '/scheduled_end/?' }
        { path: '/created_at/?' }
        { path: '/category/?' }
        { path: '/is_active/?' }
      ]
      excludedPaths: [
        { path: '/*' }
        { path: '/_etag/?' }
      ]
      compositeIndexes: [
        [
          { path: '/status', order: 'ascending' }
          { path: '/scheduled_start', order: 'ascending' }
        ]
        [
          { path: '/status', order: 'ascending' }
          { path: '/poll_type', order: 'ascending' }
        ]
      ]
    }
  }
  {
    name: 'votes'
    partitionKey: '/poll_id'
    uniqueKeys: [
      { paths: [ '/vote_hash' ] }
    ]
    indexingPolicy: {
      indexingMode: 'consistent'
      includedPaths: [
        { path: '/vote_hash/?' }
        { path: '/choice_id/?' }
        { path: '/created_at/?' }
        { path: '/demographics_bucket/?' }
      ]
      excludedPaths: [
        { path: '/*' }
        { path: '/_etag/?' }
      ]
    }
  }
  {
    name: 'achievements'
    partitionKey: '/id'
    uniqueKeys: []
    indexingPolicy: {
      indexingMode: 'consistent'
      includedPaths: [
        { path: '/action_type/?' }
        { path: '/category/?' }
        { path: '/tier/?' }
      ]
      excludedPaths: [
        { path: '/*' }
        { path: '/_etag/?' }
      ]
    }
  }
  {
    name: 'user-achievements'
    partitionKey: '/user_id'
    uniqueKeys: []
    indexingPolicy: {
      indexingMode: 'consistent'
      includedPaths: [
        { path: '/achievement_id/?' }
        { path: '/is_unlocked/?' }
        { path: '/period_key/?' }
        { path: '/unlocked_at/?' }
      ]
      excludedPaths: [
        { path: '/*' }
        { path: '/_etag/?' }
      ]
    }
  }
  {
    name: 'email-lookup'
    partitionKey: '/email'
    uniqueKeys: []
    indexingPolicy: {
      indexingMode: 'consistent'
      includedPaths: [
        { path: '/*' }
      ]
      excludedPaths: [
        { path: '/_etag/?' }
      ]
    }
  }
  {
    name: 'username-lookup'
    partitionKey: '/username'
    uniqueKeys: []
    indexingPolicy: {
      indexingMode: 'consistent'
      includedPaths: [
        { path: '/*' }
      ]
      excludedPaths: [
        { path: '/_etag/?' }
      ]
    }
  }
  {
    name: 'auth-challenges'
    partitionKey: '/user_id'
    uniqueKeys: []
    // TTL enabled - challenges auto-expire after 5 minutes
    defaultTtl: 300
    indexingPolicy: {
      indexingMode: 'consistent'
      includedPaths: [
        { path: '/operation/?' }
        { path: '/expires_at/?' }
      ]
      excludedPaths: [
        { path: '/*' }
        { path: '/_etag/?' }
      ]
    }
  }
]

// Built-in Cosmos DB Data Contributor role
// This role allows read/write access to data plane operations
var cosmosDbDataContributorRoleId = '00000000-0000-0000-0000-000000000002'

// ============================================================================
// Resources
// ============================================================================

// Cosmos DB Account - Serverless
resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: toLower(name)
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  // Use User-Assigned Managed Identity for CMK - required for CMK + Continuous backup
  identity: enableCMK && !empty(cmkUserAssignedIdentityId) ? {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${cmkUserAssignedIdentityId}': {}
    }
  } : null
  properties: {
    databaseAccountOfferType: 'Standard'
    // Enable Serverless capacity mode - pay per request, no provisioned throughput
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
    // Session consistency provides good balance of performance and consistency
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    // Single region for serverless (multi-region not supported in serverless)
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: environmentName == 'prod'
      }
    ]
    // Disable key-based authentication in favor of RBAC
    disableLocalAuth: true
    // SECURITY: Disable public network access for ALL environments
    // Dev environments should use Azure VPN, Bastion, or emulator
    publicNetworkAccess: 'Disabled'
    // Backup policy - continuous backup for point-in-time restore
    backupPolicy: {
      type: 'Continuous'
      continuousModeProperties: {
        tier: environmentName == 'prod' ? 'Continuous30Days' : 'Continuous7Days'
      }
    }
    // Customer Managed Keys (CMK) for encryption at rest
    // User-Assigned Identity is required for CMK with Continuous backup during initial provisioning
    keyVaultKeyUri: enableCMK && !empty(keyVaultResourceId) && !empty(cmkKeyName) ? '${reference(keyVaultResourceId, '2023-07-01').vaultUri}keys/${cmkKeyName}' : null
    defaultIdentity: enableCMK && !empty(cmkUserAssignedIdentityId) ? 'UserAssignedIdentity=${cmkUserAssignedIdentityId}' : null
  }
}

// Database
resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: cosmosAccount
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
    // No throughput options for serverless - throughput is per-request
  }
}

// Containers - skip when CMK is enabled (deployed separately to avoid CMK update conflicts)
resource cosmosContainers 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = [for container in containers: if (!skipContainers) {
  parent: database
  name: container.name
  properties: {
    resource: union(
      {
        id: container.name
        partitionKey: {
          paths: [
            container.partitionKey
          ]
          kind: 'Hash'
        }
        indexingPolicy: container.indexingPolicy
        uniqueKeyPolicy: length(container.uniqueKeys) > 0 ? {
          uniqueKeys: container.uniqueKeys
        } : null
      },
      // Only add defaultTtl if specified in container config
      contains(container, 'defaultTtl') ? { defaultTtl: container.defaultTtl } : {}
    )
    // No throughput options for serverless containers
  }
}]

// RBAC Role Assignment - Data Contributor for Container App
// Allows the Container App's managed identity to read/write data
resource dataContributorRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = if (!empty(dataPlanePrincipalId)) {
  parent: cosmosAccount
  name: guid(cosmosAccount.id, dataPlanePrincipalId, cosmosDbDataContributorRoleId)
  properties: {
    roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/${cosmosDbDataContributorRoleId}'
    principalId: dataPlanePrincipalId
    scope: cosmosAccount.id
  }
}

// Note: Key Vault role assignment for CMK is done in main.bicep before Cosmos DB creation
// The User-Assigned MI must have Key Vault access before Cosmos DB can use it for CMK

// Private Endpoint (for all environments - public access is disabled)
// Dev environment uses emulator locally, but Azure resources still need private endpoints
resource privateEndpoint 'Microsoft.Network/privateEndpoints@2023-09-01' = {
  name: 'pe-${name}'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'cosmos-connection'
        properties: {
          privateLinkServiceId: cosmosAccount.id
          groupIds: [
            'Sql'
          ]
        }
      }
    ]
  }
}

// Private DNS Zone Group (links to shared Cosmos DNS zone)
resource privateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-09-01' = if (!empty(cosmosDnsZoneId)) {
  parent: privateEndpoint
  name: 'cosmos-dns-group'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'cosmos-config'
        properties: {
          privateDnsZoneId: cosmosDnsZoneId
        }
      }
    ]
  }
}

// Diagnostic Settings
resource diagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: cosmosAccount
  name: 'cosmos-diagnostics'
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        category: 'DataPlaneRequests'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
      {
        category: 'QueryRuntimeStatistics'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
      {
        category: 'PartitionKeyStatistics'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
      {
        category: 'PartitionKeyRUConsumption'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
      {
        category: 'ControlPlaneRequests'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
    ]
    metrics: [
      {
        category: 'Requests'
        enabled: true
        retentionPolicy: {
          enabled: false
          days: 0
        }
      }
    ]
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('Cosmos DB account name')
output name string = cosmosAccount.name

@description('Cosmos DB account resource ID')
output resourceId string = cosmosAccount.id

@description('Cosmos DB account endpoint')
output endpoint string = cosmosAccount.properties.documentEndpoint

@description('Database name')
output databaseName string = databaseName

@description('Container names')
output containerNames array = [for (container, i) in containers: cosmosContainers[i].name]
