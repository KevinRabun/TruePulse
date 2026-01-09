# IP Address Handling & Data Retention Policy

## Overview

TruePulse collects IP addresses solely for fraud prevention purposes. This document describes how IP addresses are processed, stored, and retained in compliance with GDPR and privacy best practices.

## Purpose of IP Collection

IP addresses are collected for the following limited purposes:

1. **Fraud Detection**: Identify VPN/proxy/Tor usage that may indicate vote manipulation
2. **Rate Limiting**: Prevent automated voting attacks
3. **Geographic Verification**: Ensure votes align with claimed user demographics
4. **Abuse Prevention**: Block known malicious actors (via AbuseIPDB integration)

## Data Flow

```
User Vote Request
       │
       ▼
┌─────────────────────────────┐
│   Extract Client IP         │
│   (X-Forwarded-For header)  │
└─────────────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   IP Intelligence Check     │
│   - VPN/Proxy detection     │
│   - Datacenter IP check     │
│   - Tor exit node check     │
│   - Geographic lookup       │
└─────────────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Risk Assessment           │
│   - IP risk score (0-100)   │
│   - Combined with other     │
│     fraud signals           │
└─────────────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│   Vote Processing           │
│   - IP NOT stored in vote   │
│   - Only hash stored        │
└─────────────────────────────┘
```

## Storage Policy

### What IS Stored

| Data | Location | Duration | Purpose |
|------|----------|----------|---------|
| IP-based rate limit counters | Azure Table Storage | 1 hour sliding window | Prevent rapid-fire voting |
| IP hash (SHA-256) | Azure Table Storage | 24 hours | Duplicate vote detection |
| Geographic aggregates | Cosmos DB | Indefinitely | Anonymous regional statistics |

### What is NOT Stored

- **Raw IP addresses are NOT stored in:**
  - Vote records (Cosmos DB)
  - User profiles (Cosmos DB)
  - Application logs (production builds)
  - Any persistent database

### Hashing Implementation

When IP addresses are used for fraud detection, they are immediately hashed:

```python
# From services/fraud_detection.py
import hashlib

def hash_ip_for_storage(ip_address: str, salt: str) -> str:
    """
    Create a one-way hash of an IP address.
    
    The salt is environment-specific (from settings.VOTE_HASH_SECRET)
    to prevent rainbow table attacks.
    """
    combined = f"{ip_address}:{salt}"
    return hashlib.sha256(combined.encode()).hexdigest()
```

## Retention Schedule

| Data Type | Retention Period | Deletion Method |
|-----------|-----------------|-----------------|
| Rate limit counters | 1 hour (auto-expiry) | Azure Table Storage TTL |
| IP hashes | 24 hours | Azure Table Storage TTL |
| Error logs with partial IPs | 7 days | Log rotation |
| Aggregated geo stats | Permanent | N/A (anonymous) |

## Third-Party Services

TruePulse uses the following external IP intelligence services:

1. **IPInfo.io** (Primary)
   - Data shared: IP address (queried in real-time, not stored by us)
   - Their retention: See [IPInfo Privacy Policy](https://ipinfo.io/privacy-policy)

2. **AbuseIPDB** (Secondary)
   - Data shared: IP address (for abuse checking)
   - Their retention: See [AbuseIPDB Privacy Policy](https://www.abuseipdb.com/privacy)

### Production Considerations

For production deployments, consider:
- Configuring IP intelligence services via environment variables
- Using private IP intelligence databases (MaxMind GeoIP2) for reduced third-party exposure
- Implementing IP truncation (e.g., zeroing last octet for IPv4)

## GDPR Compliance

### Legal Basis

IP address processing is based on:
- **Legitimate Interest** (Article 6(1)(f) GDPR): Fraud prevention and platform integrity
- **Contract Performance** (Article 6(1)(b) GDPR): Ensuring fair voting as part of service delivery

### Data Subject Rights

Users can exercise the following rights:

1. **Right to Access**: Users can request information about IP processing via support
2. **Right to Erasure**: IP data is automatically deleted within 24 hours
3. **Right to Object**: Users may contact support to object to IP processing
4. **Data Portability**: IP addresses are not included in data exports (already deleted)

### Technical Measures

- IP addresses truncated in logs (only first 3 octets logged: `192.168.1.x`)
- No correlation between IPs and user identities after vote processing
- Automatic TTL-based deletion in Azure Table Storage

## Implementation Details

### Backend Configuration

```python
# core/config.py
class Settings:
    # IP retention settings
    IP_HASH_TTL_SECONDS: int = 86400  # 24 hours
    RATE_LIMIT_WINDOW_SECONDS: int = 3600  # 1 hour
    LOG_TRUNCATE_IP: bool = True  # Truncate IPs in logs
```

### Azure Table Storage Key Structure

```
# Rate limiting (auto-expires)
rate_limit:vote:{ip_hash} -> counter (TTL: 1 hour)

# Duplicate detection (auto-expires)
vote_check:{poll_id}:{ip_hash} -> 1 (TTL: 24 hours)
```

## Audit & Monitoring

- IP processing is logged with truncated addresses only
- Fraud detection events are logged without raw IPs
- Regular audits verify no IP leakage to persistent storage

## Contact

For questions about IP handling or to exercise your data rights:
- Email: privacy@truepulse.io
- Support: https://truepulse.io/support

---

*Last Updated: January 2026*
*Version: 1.0*
