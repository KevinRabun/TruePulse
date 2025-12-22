# TruePulse Service Level Objectives (SLOs) and Monitoring

This document defines the Service Level Objectives for TruePulse and the monitoring infrastructure to track them.

## Table of Contents

1. [Service Level Objectives](#service-level-objectives)
2. [Service Level Indicators](#service-level-indicators)
3. [Azure Monitor Configuration](#azure-monitor-configuration)
4. [Alerting Rules](#alerting-rules)
5. [Dashboards](#dashboards)
6. [Error Budget Policy](#error-budget-policy)

---

## Service Level Objectives

### Availability SLO

| Service | Target | Measurement Window |
|---------|--------|-------------------|
| **API Availability** | 99.9% | 30 days rolling |
| **Frontend Availability** | 99.9% | 30 days rolling |
| **Database Availability** | 99.95% | 30 days rolling |
| **Overall System** | 99.9% | 30 days rolling |

**99.9% availability = ~43.8 minutes downtime/month**

### Latency SLO

| Endpoint Category | P50 Target | P95 Target | P99 Target |
|-------------------|------------|------------|------------|
| **Health checks** | < 50ms | < 100ms | < 200ms |
| **Poll listing** | < 200ms | < 500ms | < 1s |
| **Vote submission** | < 300ms | < 800ms | < 2s |
| **User authentication** | < 200ms | < 500ms | < 1s |
| **Poll creation** | < 500ms | < 1s | < 2s |

### Throughput SLO

| Metric | Target |
|--------|--------|
| **Concurrent users** | 1,000+ |
| **Votes per minute** | 10,000+ |
| **API requests per second** | 500+ |

### Data Integrity SLO

| Metric | Target |
|--------|--------|
| **Vote accuracy** | 100% (no vote loss) |
| **Data durability** | 99.999% |
| **Backup success rate** | 100% |

---

## Service Level Indicators

### Availability SLI

```
Availability = (Successful Requests / Total Requests) × 100

Where:
- Successful = HTTP 2xx, 3xx responses
- Failed = HTTP 5xx responses (not 4xx, which are client errors)
```

### Latency SLI

```
Latency Percentile = Time for N% of requests to complete

Measured at:
- API Gateway/Container App ingress
- Application Insights request telemetry
```

### Error Rate SLI

```
Error Rate = (5xx Responses / Total Responses) × 100
```

---

## Azure Monitor Configuration

### Application Insights Setup

The backend application uses Application Insights for telemetry. Configuration is in `core/config.py`:

```python
# Application Insights is configured via APPLICATIONINSIGHTS_CONNECTION_STRING
# Set automatically by Azure Container Apps when deployed
```

### Custom Metrics

Add these custom metrics to track SLOs:

```python
# In backend/core/metrics.py
from opencensus.ext.azure import metrics_exporter
from opencensus.stats import aggregation, measure, stats, view

# Vote submission latency
vote_latency_measure = measure.MeasureFloat(
    "vote_submission_latency",
    "Time to process vote submission",
    "ms"
)

# Active polls gauge
active_polls_measure = measure.MeasureInt(
    "active_polls_count",
    "Number of currently active polls",
    "1"
)

# Error count
error_count_measure = measure.MeasureInt(
    "error_count",
    "Number of errors by type",
    "1"
)
```

### Log Analytics Queries

#### Availability Query

```kusto
// Calculate availability over 30 days
requests
| where timestamp > ago(30d)
| summarize 
    TotalRequests = count(),
    SuccessfulRequests = countif(success == true or resultCode startswith "4"),
    FailedRequests = countif(success == false and resultCode startswith "5")
| extend Availability = round(SuccessfulRequests * 100.0 / TotalRequests, 3)
```

#### Latency Percentiles Query

```kusto
// Calculate latency percentiles by endpoint
requests
| where timestamp > ago(1h)
| summarize 
    P50 = percentile(duration, 50),
    P95 = percentile(duration, 95),
    P99 = percentile(duration, 99)
    by name
| order by P95 desc
```

#### Error Rate Query

```kusto
// Error rate over time
requests
| where timestamp > ago(24h)
| summarize 
    Total = count(),
    Errors = countif(resultCode startswith "5")
    by bin(timestamp, 1h)
| extend ErrorRate = round(Errors * 100.0 / Total, 2)
| project timestamp, ErrorRate
| render timechart
```

#### Vote Processing Query

```kusto
// Vote submission performance
requests
| where timestamp > ago(1h)
| where name contains "vote"
| summarize 
    Count = count(),
    AvgDuration = avg(duration),
    P95Duration = percentile(duration, 95),
    Errors = countif(success == false)
    by bin(timestamp, 5m)
| render timechart
```

---

## Alerting Rules

### Bicep Configuration for Alerts

Add to `infra/modules/monitoring.bicep`:

```bicep
// Availability Alert - Less than 99.9%
resource availabilityAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'truepulse-availability-alert'
  location: 'global'
  properties: {
    description: 'Alert when availability drops below 99.9%'
    severity: 1
    enabled: true
    scopes: [applicationInsightsId]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT1H'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'AvailabilityCheck'
          metricName: 'availabilityResults/availabilityPercentage'
          operator: 'LessThan'
          threshold: 99.9
          timeAggregation: 'Average'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroupId
      }
    ]
  }
}

// High Latency Alert - P95 > 2s
resource latencyAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'truepulse-latency-alert'
  location: 'global'
  properties: {
    description: 'Alert when P95 latency exceeds 2 seconds'
    severity: 2
    enabled: true
    scopes: [applicationInsightsId]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'LatencyCheck'
          metricName: 'requests/duration'
          operator: 'GreaterThan'
          threshold: 2000
          timeAggregation: 'Average'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroupId
      }
    ]
  }
}

// High Error Rate Alert - > 5%
resource errorRateAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'truepulse-error-rate-alert'
  location: 'global'
  properties: {
    description: 'Alert when error rate exceeds 5%'
    severity: 1
    enabled: true
    scopes: [applicationInsightsId]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'ErrorRateCheck'
          metricName: 'requests/failed'
          operator: 'GreaterThan'
          threshold: 5
          timeAggregation: 'Average'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroupId
      }
    ]
  }
}
```

### Alert Severity Mapping

| Severity | Azure Level | Response Time | Examples |
|----------|-------------|---------------|----------|
| **Critical** | Sev 0 | 15 min | Complete outage, security breach |
| **Error** | Sev 1 | 1 hour | High error rate, availability below SLO |
| **Warning** | Sev 2 | 4 hours | Elevated latency, approaching limits |
| **Information** | Sev 3 | 24 hours | Performance degradation trends |

### Action Groups Configuration

```bicep
// Action group for alerts
resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: 'truepulse-alerts'
  location: 'global'
  properties: {
    groupShortName: 'TruePulse'
    enabled: true
    emailReceivers: [
      {
        name: 'OpsTeam'
        emailAddress: 'ops@truepulse.io'
        useCommonAlertSchema: true
      }
    ]
    // Add webhook for PagerDuty/Slack integration
    webhookReceivers: [
      {
        name: 'SlackWebhook'
        serviceUri: 'https://hooks.slack.com/services/XXX'
        useCommonAlertSchema: true
      }
    ]
  }
}
```

---

## Dashboards

### Azure Dashboard Configuration

Create a dashboard JSON for the Azure Portal:

```json
{
  "properties": {
    "lenses": [
      {
        "order": 0,
        "parts": [
          {
            "position": {"x": 0, "y": 0, "colSpan": 6, "rowSpan": 4},
            "metadata": {
              "type": "Extension/Microsoft_Azure_Monitoring/PartType/MetricsChartPart",
              "settings": {
                "title": "Availability",
                "metrics": [
                  {
                    "resourceId": "{appInsightsId}",
                    "name": "availabilityResults/availabilityPercentage"
                  }
                ]
              }
            }
          },
          {
            "position": {"x": 6, "y": 0, "colSpan": 6, "rowSpan": 4},
            "metadata": {
              "type": "Extension/Microsoft_Azure_Monitoring/PartType/MetricsChartPart",
              "settings": {
                "title": "Response Time (P95)",
                "metrics": [
                  {
                    "resourceId": "{appInsightsId}",
                    "name": "requests/duration",
                    "aggregation": "P95"
                  }
                ]
              }
            }
          }
        ]
      }
    ]
  }
}
```

### Key Dashboard Widgets

1. **Availability Gauge** - Current availability percentage
2. **Latency Chart** - P50, P95, P99 over time
3. **Error Rate** - 5xx errors over time
4. **Request Volume** - Requests per minute
5. **Active Users** - Concurrent sessions
6. **Vote Activity** - Votes per minute
7. **Database Connections** - Connection pool usage
8. **Container Health** - CPU/Memory utilization

### Workbook Queries

Create an Azure Workbook for detailed SLO tracking:

```kusto
// SLO Summary Table
let availability = requests
| where timestamp > ago(30d)
| summarize 
    Availability = round(countif(success == true or resultCode startswith "4") * 100.0 / count(), 3);

let latency = requests
| where timestamp > ago(30d)
| summarize P95Latency = round(percentile(duration, 95), 0);

let errorRate = requests
| where timestamp > ago(30d)
| summarize ErrorRate = round(countif(resultCode startswith "5") * 100.0 / count(), 2);

print 
    Availability = toscalar(availability),
    P95Latency = toscalar(latency),
    ErrorRate = toscalar(errorRate)
```

---

## Error Budget Policy

### Error Budget Calculation

```
Monthly Error Budget = (1 - SLO Target) × Total Minutes in Month

For 99.9% SLO:
Error Budget = (1 - 0.999) × 43,200 minutes = 43.2 minutes/month
```

### Error Budget Tracking

```kusto
// Calculate remaining error budget
let slo_target = 0.999;
let month_minutes = 43200;
let error_budget_minutes = (1 - slo_target) * month_minutes;

requests
| where timestamp > startofmonth(now())
| summarize 
    TotalRequests = count(),
    FailedRequests = countif(resultCode startswith "5")
| extend 
    CurrentAvailability = 1.0 - (FailedRequests * 1.0 / TotalRequests),
    ErrorBudgetUsed = (1 - (1.0 - (FailedRequests * 1.0 / TotalRequests))) / (1 - slo_target) * 100
| project 
    CurrentAvailability = round(CurrentAvailability * 100, 3),
    ErrorBudgetUsedPercent = round(ErrorBudgetUsed, 1),
    ErrorBudgetRemainingMinutes = round(error_budget_minutes * (1 - ErrorBudgetUsed / 100), 1)
```

### Error Budget Policies

| Budget Remaining | Actions |
|------------------|---------|
| **> 50%** | Normal operations, feature development prioritized |
| **25-50%** | Caution: reduce risky deployments, increase testing |
| **10-25%** | Warning: freeze non-critical changes, focus on stability |
| **< 10%** | Critical: emergency mode, only critical fixes |
| **0%** | SLO breached: all hands on reliability |

### Monthly Review Process

1. **Week 1**: Review previous month's SLO performance
2. **Week 2**: Identify top reliability issues
3. **Week 3**: Implement reliability improvements
4. **Week 4**: Validate improvements, plan next month

---

## Implementation Checklist

### Initial Setup

- [ ] Enable Application Insights on Container App
- [ ] Configure Log Analytics workspace
- [ ] Deploy alerting rules via Bicep
- [ ] Create Action Group with contacts
- [ ] Create Azure Dashboard
- [ ] Create Azure Workbook for SLO tracking

### Ongoing Operations

- [ ] Weekly SLO review meeting
- [ ] Monthly error budget review
- [ ] Quarterly SLO target review
- [ ] Annual reliability roadmap planning

### Integration Points

- [ ] Connect alerts to PagerDuty/Opsgenie
- [ ] Connect alerts to Slack/Teams
- [ ] Export metrics to Grafana (optional)
- [ ] Set up status page (e.g., Statuspage.io)

---

## Quick Reference

### Key Metrics Lookup

| Metric | Application Insights Name | Target |
|--------|---------------------------|--------|
| Availability | `availabilityResults/availabilityPercentage` | > 99.9% |
| Response Time | `requests/duration` | P95 < 2s |
| Error Rate | `requests/failed` | < 1% |
| Request Rate | `requests/count` | Baseline |
| Dependencies | `dependencies/duration` | P95 < 500ms |

### Azure CLI Quick Commands

```bash
# View current alerts
az monitor metrics alert list --resource-group rg-truepulse-prod --output table

# Test alert (trigger manually)
az monitor metrics alert update --name truepulse-availability-alert --resource-group rg-truepulse-prod --enabled false
az monitor metrics alert update --name truepulse-availability-alert --resource-group rg-truepulse-prod --enabled true

# View Application Insights metrics
az monitor app-insights metrics show --app truepulse-insights-prod --resource-group rg-truepulse-prod --metric requests/count
```

---

**Document Version:** 1.0  
**Last Updated:** January 2025  
**Next Review:** April 2025
