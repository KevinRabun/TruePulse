// Azure DNS Zone for truepulse.net
// Manages DNS records for the custom domain
// Uses Azure Verified Module (AVM) pattern

@description('DNS zone name (domain name)')
param name string = 'truepulse.net'

@description('Resource tags')
param tags object = {}

@description('Static Web App default hostname for CNAME')
param staticWebAppHostname string = ''

@description('Container App API FQDN for CNAME')
param containerAppApiFqdn string = ''

@description('Static Web App resource ID for TXT validation')
param staticWebAppResourceId string = ''

// ============================================================================
// DNS Zone using Azure Verified Module
// ============================================================================

module dnsZone 'br/public:avm/res/network/dns-zone:0.5.4' = {
  name: 'dns-zone-deployment'
  params: {
    name: name
    location: 'global'
    tags: tags
    
    // CNAME records for subdomains
    cname: [
      // www.truepulse.net -> Static Web App
      {
        name: 'www'
        ttl: 3600
        cnameRecord: {
          cname: staticWebAppHostname
        }
      }
      // api.truepulse.net -> Container App
      {
        name: 'api'
        ttl: 3600
        cnameRecord: {
          cname: containerAppApiFqdn
        }
      }
    ]
    
    // TXT records for domain validation
    txt: [
      // Static Web App domain validation (if provided)
      // Note: The actual validation token needs to be obtained after SWA creation
      // and set via the staticWebAppCustomDomains module
      {
        name: '@'
        ttl: 3600
        txtRecords: [
          {
            value: [
              'v=spf1 include:spf.protection.outlook.com -all'  // SPF for email
            ]
          }
        ]
      }
    ]
    
    // A record alias for apex domain (truepulse.net) -> Static Web App
    // Note: Static Web Apps support apex domains via alias records
    a: !empty(staticWebAppResourceId) ? [
      {
        name: '@'
        ttl: 3600
        targetResourceId: staticWebAppResourceId
      }
    ] : []
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('The name of the DNS zone')
output name string = dnsZone.outputs.name

@description('The resource ID of the DNS zone')
output resourceId string = dnsZone.outputs.resourceId

@description('The name servers for this DNS zone (update at your registrar)')
output nameServers array = dnsZone.outputs.nameServers

@description('The resource group name')
output resourceGroupName string = dnsZone.outputs.resourceGroupName
