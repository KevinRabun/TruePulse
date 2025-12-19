// TruePulse Infrastructure - Static Web App
// Next.js frontend hosted on Azure Static Web Apps

// ============================================================================
// Parameters
// ============================================================================

@description('Static Web App name')
param name string

@description('Location for resources')
param location string

@description('Resource tags')
param tags object

@description('API backend URL')
param apiUrl string

@description('Custom domain name (optional)')
param customDomain string = ''

// ============================================================================
// Resources
// ============================================================================

// Using Azure Verified Module: br/public:avm/res/web/static-site
module staticWebApp 'br/public:avm/res/web/static-site:0.6.0' = {
  name: 'static-web-app'
  params: {
    name: name
    location: location
    tags: tags
    sku: 'Standard'
    // Staging environments
    stagingEnvironmentPolicy: 'Enabled'
    // Build configuration will be set via GitHub Actions
    buildProperties: {
      appLocation: 'src/frontend'
      outputLocation: 'out'
      skipGithubActionWorkflowGeneration: true
    }
    // Managed identity
    managedIdentities: {
      systemAssigned: true
    }
    // App settings
    appSettings: {
      NEXT_PUBLIC_API_URL: apiUrl
      NEXT_PUBLIC_SITE_URL: !empty(customDomain) ? 'https://${customDomain}' : ''
    }
  }
}

// Custom domain configuration (apex and www)
// Note: Domain validation happens automatically when DNS is properly configured
resource customDomainApex 'Microsoft.Web/staticSites/customDomains@2023-01-01' = if (!empty(customDomain)) {
  name: '${name}/${customDomain}'
  properties: {}
  dependsOn: [staticWebApp]
}

resource customDomainWww 'Microsoft.Web/staticSites/customDomains@2023-01-01' = if (!empty(customDomain)) {
  name: '${name}/www.${customDomain}'
  properties: {}
  dependsOn: [
    staticWebApp
    customDomainApex
  ]
}

// ============================================================================
// Outputs
// ============================================================================

output resourceId string = staticWebApp.outputs.resourceId
output name string = staticWebApp.outputs.name
output defaultHostname string = staticWebApp.outputs.defaultHostname
// Deployment token can only be obtained after creation, provide script to get it
@description('Instructions to get deployment token')
output deploymentTokenInfo string = 'Run: az staticwebapp secrets list --name ${name} --query "properties.apiKey" -o tsv'
