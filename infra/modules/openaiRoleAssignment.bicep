// TruePulse Infrastructure - Azure OpenAI Role Assignment Module
// Grants Cognitive Services OpenAI User role to Container App managed identities
// Both system-assigned and user-assigned identities need access

@description('Azure OpenAI resource ID')
param openaiResourceId string

@description('Principal ID of the user-assigned managed identity')
param userAssignedPrincipalId string

@description('Principal ID of the system-assigned managed identity (optional)')
param systemAssignedPrincipalId string = ''

// Cognitive Services OpenAI User - allows using chat completions, embeddings, etc.
// https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles#cognitive-services-openai-user
var cognitiveServicesOpenAIUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

// Reference existing Azure OpenAI resource
resource openAI 'Microsoft.CognitiveServices/accounts@2023-10-01-preview' existing = {
  name: last(split(openaiResourceId, '/'))
}

// Grant Cognitive Services OpenAI User role to user-assigned identity
resource userAssignedRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openaiResourceId, userAssignedPrincipalId, cognitiveServicesOpenAIUserRoleId)
  scope: openAI
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUserRoleId)
    principalId: userAssignedPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Grant Cognitive Services OpenAI User role to system-assigned identity (if provided)
// DefaultAzureCredential may use system-assigned identity by default
resource systemAssignedRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(systemAssignedPrincipalId)) {
  name: guid(openaiResourceId, systemAssignedPrincipalId, cognitiveServicesOpenAIUserRoleId)
  scope: openAI
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUserRoleId)
    principalId: systemAssignedPrincipalId
    principalType: 'ServicePrincipal'
  }
}
