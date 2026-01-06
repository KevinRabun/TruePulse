// TruePulse Infrastructure - Azure OpenAI Role Assignment Module
// Grants Cognitive Services OpenAI User role to Container App managed identity

@description('Azure OpenAI resource ID')
param openaiResourceId string

@description('Principal ID of the managed identity to grant access to')
param principalId string

// Cognitive Services OpenAI User - allows using chat completions, embeddings, etc.
// https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles#cognitive-services-openai-user
var cognitiveServicesOpenAIUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

// Reference existing Azure OpenAI resource
resource openAI 'Microsoft.CognitiveServices/accounts@2023-10-01-preview' existing = {
  name: last(split(openaiResourceId, '/'))
}

// Grant Cognitive Services OpenAI User role
resource openaiRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openaiResourceId, principalId, cognitiveServicesOpenAIUserRoleId)
  scope: openAI
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUserRoleId)
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}
