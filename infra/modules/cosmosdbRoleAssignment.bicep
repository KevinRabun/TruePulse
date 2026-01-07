// TruePulse Infrastructure - Cosmos DB Role Assignment
// Grants data plane access to a principal (Container App managed identity)

// ============================================================================
// Parameters
// ============================================================================

@description('Cosmos DB account name')
param cosmosAccountName string

@description('Principal ID to grant access to (managed identity)')
param principalId string

// ============================================================================
// Variables
// ============================================================================

// Built-in Cosmos DB Data Contributor role
// Allows read/write data operations on Cosmos DB
var cosmosDbDataContributorRoleId = '00000000-0000-0000-0000-000000000002'

// ============================================================================
// Existing Resources
// ============================================================================

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' existing = {
  name: cosmosAccountName
}

// ============================================================================
// Role Assignment
// ============================================================================

resource dataContributorRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = {
  parent: cosmosAccount
  name: guid(cosmosAccount.id, principalId, cosmosDbDataContributorRoleId)
  properties: {
    roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/${cosmosDbDataContributorRoleId}'
    principalId: principalId
    scope: cosmosAccount.id
  }
}
