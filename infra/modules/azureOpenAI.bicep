// TruePulse Infrastructure - Azure OpenAI Module
// Uses Azure Verified Modules (AVM) for Cognitive Services

@description('Azure OpenAI service name')
param name string

@description('Azure region for the service')
param location string

@description('Tags to apply to the resource')
param tags object

@description('Log Analytics workspace resource ID for diagnostics')
param logAnalyticsWorkspaceId string

@description('Subnet ID for private endpoint')
param subnetId string

@description('Key Vault resource ID for storing API keys')
param keyVaultResourceId string

@description('Environment name for capacity configuration')
@allowed(['dev', 'staging', 'prod'])
param environmentName string = 'dev'

@description('Shared OpenAI DNS zone resource ID')
param openaiDnsZoneId string

// Capacity based on environment (GPT-4o-mini supports higher capacity at lower cost)
var modelCapacity = environmentName == 'prod' ? 50 : 20

// ============================================================================
// Azure OpenAI using Azure Verified Module
// ============================================================================
module openAI 'br/public:avm/res/cognitive-services/account:0.10.1' = {
  name: '${name}-deployment'
  params: {
    name: name
    location: location
    tags: tags
    kind: 'OpenAI'
    sku: 'S0'
    customSubDomainName: name
    publicNetworkAccess: 'Disabled'
    disableLocalAuth: false
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
    }
    managedIdentities: {
      systemAssigned: true
    }
    deployments: [
      {
        name: 'gpt-4o-mini'
        model: {
          format: 'OpenAI'
          name: 'gpt-4o-mini'
          version: '2024-07-18'
        }
        sku: {
          name: 'Standard'
          capacity: modelCapacity
        }
        versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
        raiPolicyName: 'Microsoft.Default'
      }
    ]
    privateEndpoints: [
      {
        name: 'pe-${name}'
        subnetResourceId: subnetId
        privateDnsZoneGroup: {
          privateDnsZoneGroupConfigs: [
            {
              privateDnsZoneResourceId: openaiDnsZoneId
            }
          ]
        }
        tags: tags
      }
    ]
    diagnosticSettings: [
      {
        name: '${name}-diagnostics'
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
    secretsExportConfiguration: {
      keyVaultResourceId: keyVaultResourceId
      accessKey1Name: 'azure-openai-api-key'
    }
  }
}

// ============================================================================
// Outputs
// ============================================================================
@description('The resource ID of the Azure OpenAI service')
output resourceId string = openAI.outputs.resourceId

@description('The name of the Azure OpenAI service')
output name string = openAI.outputs.name

@description('The endpoint URL of the Azure OpenAI service')
output endpoint string = openAI.outputs.endpoint

@description('The principal ID of the system-assigned managed identity')
output principalId string = openAI.outputs.?systemAssignedMIPrincipalId  ?? ''

@description('The GPT-4o-mini deployment name')
output deploymentName string = 'gpt-4o-mini'
