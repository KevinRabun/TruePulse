// Monitoring and alerting infrastructure for TruePulse
// Implements SLO-based alerting as defined in docs/SLA_MONITORING.md

@description('Environment name')
param environmentName string

@description('Azure region')
param location string = resourceGroup().location

@description('Log Analytics Workspace resource ID for queries')
param logAnalyticsWorkspaceId string

@description('Container App resource ID')
param containerAppId string

@description('PostgreSQL server resource ID')
param postgresServerId string

@description('Email addresses for alert notifications')
param alertEmailAddresses array = []

@description('Slack webhook URL for alerts (optional)')
param slackWebhookUrl string = ''

@description('Enable alerts')
param enableAlerts bool = true

// Tags
var tags = {
  Environment: environmentName
  Application: 'TruePulse'
  Component: 'Monitoring'
}

// Action Group for all alerts
resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: 'ag-truepulse-${environmentName}'
  location: 'global'
  tags: tags
  properties: {
    groupShortName: 'TruePulse'
    enabled: enableAlerts
    emailReceivers: [for (email, i) in alertEmailAddresses: {
      name: 'Email-${i}'
      emailAddress: email
      useCommonAlertSchema: true
    }]
    webhookReceivers: !empty(slackWebhookUrl) ? [
      {
        name: 'SlackWebhook'
        serviceUri: slackWebhookUrl
        useCommonAlertSchema: true
      }
    ] : []
  }
}

// High Error Rate Alert using Log Analytics query
resource errorRateAlert 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: 'alert-error-rate-${environmentName}'
  location: location
  tags: tags
  properties: {
    displayName: 'High Error Rate'
    description: 'Alert when error rate exceeds 5%'
    enabled: enableAlerts
    scopes: [logAnalyticsWorkspaceId]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    severity: 1
    criteria: {
      allOf: [
        {
          query: '''
            ContainerAppConsoleLogs_CL
            | where TimeGenerated > ago(15m)
            | where Log_s contains "ERROR" or Log_s contains "Exception"
            | summarize ErrorCount = count()
            | where ErrorCount > 10
          '''
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 0
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    actions: {
      actionGroups: [actionGroup.id]
    }
  }
}

// Container CPU Alert - Warning at 80%
resource containerCpuAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'alert-container-cpu-${environmentName}'
  location: 'global'
  tags: tags
  properties: {
    description: 'Alert when Container App CPU usage exceeds 80%'
    severity: 2
    enabled: enableAlerts
    scopes: [containerAppId]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'CpuCheck'
          metricName: 'UsageNanoCores'
          operator: 'GreaterThan'
          threshold: 800000000 // 80% of 1 core in nanocores
          timeAggregation: 'Average'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

// Container Memory Alert - Warning at 85%
resource containerMemoryAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'alert-container-memory-${environmentName}'
  location: 'global'
  tags: tags
  properties: {
    description: 'Alert when Container App memory usage exceeds 85%'
    severity: 2
    enabled: enableAlerts
    scopes: [containerAppId]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'MemoryCheck'
          metricName: 'WorkingSetBytes'
          operator: 'GreaterThan'
          threshold: 1717986918 // 85% of 2GB in bytes
          timeAggregation: 'Average'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

// Database Connection Alert
resource dbConnectionAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'alert-db-connections-${environmentName}'
  location: 'global'
  tags: tags
  properties: {
    description: 'Alert when database connections exceed 80% of max'
    severity: 2
    enabled: enableAlerts
    scopes: [postgresServerId]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'ConnectionCheck'
          metricName: 'active_connections'
          operator: 'GreaterThan'
          threshold: 80 // Adjust based on max_connections setting
          timeAggregation: 'Average'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

// Database Storage Alert - Warning at 80%
resource dbStorageAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'alert-db-storage-${environmentName}'
  location: 'global'
  tags: tags
  properties: {
    description: 'Alert when database storage exceeds 80% capacity'
    severity: 2
    enabled: enableAlerts
    scopes: [postgresServerId]
    evaluationFrequency: 'PT1H'
    windowSize: 'PT1H'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'StorageCheck'
          metricName: 'storage_percent'
          operator: 'GreaterThan'
          threshold: 80
          timeAggregation: 'Average'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

// Scheduled Query Rule for Custom SLO Alert (Log-based)
resource sloAlert 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: 'alert-slo-breach-${environmentName}'
  location: location
  tags: tags
  properties: {
    displayName: 'SLO Breach Alert - High HTTP Errors'
    description: 'Alert when HTTP 5xx error rate is high over 24 hours'
    enabled: enableAlerts
    scopes: [logAnalyticsWorkspaceId]
    evaluationFrequency: 'PT1H'
    windowSize: 'PT24H'
    severity: 1
    criteria: {
      allOf: [
        {
          query: '''
            ContainerAppConsoleLogs_CL
            | where TimeGenerated > ago(24h)
            | extend StatusCode = extract("HTTP/\\d\\.\\d (\\d{3})", 1, Log_s)
            | where StatusCode startswith "5"
            | summarize ErrorCount = count()
            | where ErrorCount > 100
          '''
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 0
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    actions: {
      actionGroups: [actionGroup.id]
    }
  }
}

// Fraud Detection Alert (custom log-based)
resource fraudAlert 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: 'alert-fraud-detection-${environmentName}'
  location: location
  tags: tags
  properties: {
    displayName: 'High Fraud Score Votes'
    description: 'Alert when multiple high fraud score votes are detected'
    enabled: enableAlerts
    scopes: [logAnalyticsWorkspaceId]
    evaluationFrequency: 'PT15M'
    windowSize: 'PT1H'
    severity: 2
    criteria: {
      allOf: [
        {
          query: '''
            ContainerAppConsoleLogs_CL
            | where TimeGenerated > ago(1h)
            | where Log_s contains "fraud_score"
            | extend FraudScore = extract("fraud_score[=:]\\s*(\\d+\\.\\d+)", 1, Log_s)
            | where todouble(FraudScore) > 0.7
            | summarize HighFraudVotes = count()
            | where HighFraudVotes > 10
          '''
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 0
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    actions: {
      actionGroups: [actionGroup.id]
    }
  }
}

// Outputs
output actionGroupId string = actionGroup.id
output actionGroupName string = actionGroup.name
