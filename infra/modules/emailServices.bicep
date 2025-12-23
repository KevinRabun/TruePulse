// Azure Email Communication Services for email verification and notifications
// Uses Azure Verified Module (AVM) pattern
// 
// IMPORTANT: Email Services work differently than phone numbers:
// - Azure-managed domains (*.azurecomm.net) are provisioned automatically
// - Custom domains require DNS verification post-deployment
// - Email sending is available immediately with Azure-managed domain

@description('Name of the email service')
param name string

@description('Resource tags')
param tags object = {}

@description('The location where data is stored at rest')
@allowed([
  'Africa'
  'Asia Pacific'
  'Australia'
  'Brazil'
  'Canada'
  'Europe'
  'France'
  'Germany'
  'India'
  'Japan'
  'Korea'
  'Norway'
  'Switzerland'
  'UAE'
  'UK'
  'United States'
])
param dataLocation string = 'United States'

@description('Enable user engagement tracking (open/click tracking)')
param enableUserEngagementTracking bool = false

@description('Custom domain name for email sending (must be verified in DNS)')
param customDomain string = ''

// ============================================================================
// Email Service using Azure Verified Module
// ============================================================================

// Build domains array - always include Azure-managed, optionally add custom domain
var azureManagedDomain = {
  name: 'AzureManagedDomain'
  domainManagement: 'AzureManaged'
  userEngagementTracking: enableUserEngagementTracking ? 'Enabled' : 'Disabled'
  senderUsernames: [
    {
      name: 'donotreply'
      username: 'DoNotReply'
      displayName: 'TruePulse'
    }
    {
      name: 'verification'
      username: 'verification'
      displayName: 'TruePulse Verification'
    }
  ]
  tags: tags
}

var customDomainConfig = !empty(customDomain) ? {
  name: customDomain
  domainManagement: 'CustomerManaged'
  userEngagementTracking: enableUserEngagementTracking ? 'Enabled' : 'Disabled'
  senderUsernames: [
    {
      name: 'donotreply'
      username: 'DoNotReply'
      displayName: 'TruePulse'
    }
  ]
  tags: tags
} : {}

var domains = !empty(customDomain) ? [azureManagedDomain, customDomainConfig] : [azureManagedDomain]

module emailService 'br/public:avm/res/communication/email-service:0.3.0' = {
  name: 'email-service-deployment'
  params: {
    name: name
    dataLocation: dataLocation
    location: 'global'
    tags: tags
    domains: domains
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('The name of the email service')
output name string = emailService.outputs.name

@description('The resource ID of the email service')
output resourceId string = emailService.outputs.resourceId

@description('The resource group name')
output resourceGroupName string = emailService.outputs.resourceGroupName

@description('The domain names configured for this email service')
output domainNames array = emailService.outputs.domainNamess

@description('The domain resource IDs')
output domainResourceIds array = emailService.outputs.domainResourceIds
