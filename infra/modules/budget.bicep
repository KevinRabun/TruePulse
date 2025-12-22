// Azure Budget Alerts Module
// Creates cost management budgets with email alerts at configurable thresholds

@description('Name of the budget')
param budgetName string

@description('Total budget amount in USD')
param budgetAmount int

@description('Start date for budget (first of month, YYYY-MM-DD)')
param budgetStartDate string

@description('Email addresses to receive budget alerts')
param contactEmails array

@description('Tags to apply to resources')
param tags object = {}

@description('Resource group scope (optional - if not provided, uses subscription scope)')
param resourceGroupScope string = ''

// Budget thresholds - alert at these percentages
var thresholds = [
  {
    name: 'Threshold50'
    threshold: 50
    operator: 'GreaterThanOrEqualTo'
  }
  {
    name: 'Threshold80'
    threshold: 80
    operator: 'GreaterThanOrEqualTo'
  }
  {
    name: 'Threshold100'
    threshold: 100
    operator: 'GreaterThanOrEqualTo'
  }
  {
    name: 'ForecastThreshold100'
    threshold: 100
    operator: 'GreaterThanOrEqualTo'
  }
]

// Budget resource - subscription scope
resource budget 'Microsoft.Consumption/budgets@2023-11-01' = {
  name: budgetName
  properties: {
    category: 'Cost'
    amount: budgetAmount
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: budgetStartDate
      // No end date - budget continues indefinitely
    }
    filter: !empty(resourceGroupScope) ? {
      dimensions: {
        name: 'ResourceGroup'
        operator: 'In'
        values: [resourceGroupScope]
      }
    } : null
    notifications: {
      actual50Percent: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 50
        contactEmails: contactEmails
        thresholdType: 'Actual'
        locale: 'en-us'
      }
      actual80Percent: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 80
        contactEmails: contactEmails
        thresholdType: 'Actual'
        locale: 'en-us'
      }
      actual100Percent: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 100
        contactEmails: contactEmails
        thresholdType: 'Actual'
        locale: 'en-us'
      }
      forecast100Percent: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 100
        contactEmails: contactEmails
        thresholdType: 'Forecasted'
        locale: 'en-us'
      }
    }
  }
}

output budgetId string = budget.id
output budgetName string = budget.name
