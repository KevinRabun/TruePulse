// TruePulse Infrastructure - Cosmos DB Containers
// Deploys containers to an existing Cosmos DB account
// This is separate from cosmosdb.bicep to work around CMK limitations

// ============================================================================
// Parameters
// ============================================================================

@description('Cosmos DB account name')
param accountName string

@description('Database name')
param databaseName string = 'truepulse'

// ============================================================================
// Container Definitions
// ============================================================================

// Container definitions with partition keys
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
        { path: '/poll_type/?' }
        { path: '/is_active/?' }
        { path: '/start_time/?' }
        { path: '/end_time/?' }
        { path: '/created_at/?' }
      ]
      excludedPaths: [
        { path: '/*' }
        { path: '/_etag/?' }
      ]
    }
  }
  {
    name: 'votes'
    partitionKey: '/poll_id'
    uniqueKeys: []
    indexingPolicy: {
      indexingMode: 'consistent'
      includedPaths: [
        { path: '/user_id/?' }
        { path: '/created_at/?' }
        { path: '/vote_hash/?' }
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
        { path: '/user_id/?' }
      ]
      excludedPaths: [
        { path: '/*' }
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
        { path: '/user_id/?' }
      ]
      excludedPaths: [
        { path: '/*' }
        { path: '/_etag/?' }
      ]
    }
  }
  {
    name: 'poll-questions'
    partitionKey: '/poll_id'
    uniqueKeys: []
    indexingPolicy: {
      indexingMode: 'consistent'
      includedPaths: [
        { path: '/created_at/?' }
      ]
      excludedPaths: [
        { path: '/*' }
        { path: '/_etag/?' }
      ]
    }
  }
  {
    name: 'news-events'
    partitionKey: '/id'
    uniqueKeys: []
    indexingPolicy: {
      indexingMode: 'consistent'
      includedPaths: [
        { path: '/category/?' }
        { path: '/event_date/?' }
        { path: '/created_at/?' }
        { path: '/priority_score/?' }
      ]
      excludedPaths: [
        { path: '/*' }
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

// ============================================================================
// Resources (using existing references)
// ============================================================================

// Reference existing Cosmos DB account
resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' existing = {
  name: toLower(accountName)
}

// Reference existing database
resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' existing = {
  parent: cosmosAccount
  name: databaseName
}

// Deploy/update containers
resource cosmosContainers 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = [for container in containers: {
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
  }
}]

// ============================================================================
// Outputs
// ============================================================================

output containerNames array = [for container in containers: container.name]
