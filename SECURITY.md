# Security Policy

## Our Commitment

TruePulse is committed to maintaining the highest standards of security and privacy. We understand the sensitive nature of polling data and demographic information, and we take every measure to protect user privacy.

## Security Principles

### 1. Vote Privacy

- **Cryptographic Separation**: Individual votes cannot be traced back to users
- **One-Way Hashing**: Vote records use SHA-256 hashes that cannot be reversed
- **No Direct Links**: User IDs are never stored alongside vote choices

### 2. Data Protection

- **Encryption at Rest**: AES-256 encryption for all stored data
- **Encryption in Transit**: TLS 1.3 for all network communications
- **Key Management**: Azure Key Vault with HSM-backed keys

### 3. Access Control

- **Least Privilege**: All services run with minimum required permissions
- **Managed Identities**: No secrets in code or configuration
- **RBAC**: Role-based access control for all administrative functions

### 4. Infrastructure Security

- **DDoS Protection**: Azure DDoS Protection Standard
- **Web Application Firewall**: Azure WAF with OWASP ruleset
- **Network Isolation**: Private endpoints for all backend services
- **Regular Audits**: Automated security scanning and penetration testing

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### How to Report

1. **Email**: security@truepulse.io
2. **PGP Key**: Available at [/security/pgp-key.txt]

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact assessment
- Any suggested mitigations

### Our Response

- **Acknowledgment**: Within 24 hours
- **Initial Assessment**: Within 72 hours
- **Regular Updates**: Every 5 business days until resolution

### Safe Harbor

We consider security research conducted in accordance with this policy to be:

- Authorized under the Computer Fraud and Abuse Act (CFAA)
- Exempt from DMCA claims for circumventing technology controls
- Lawful, helpful, and conducted in good faith

We will not pursue legal action against researchers who:

- Make a good faith effort to avoid privacy violations
- Only access data necessary to demonstrate the vulnerability
- Do not modify or destroy data
- Report findings promptly and do not disclose publicly until resolved

## Security Features

### For Users

- **Multi-Factor Authentication**: TOTP and WebAuthn support
- **Session Management**: Secure, encrypted session tokens
- **Activity Monitoring**: View and revoke active sessions
- **Data Export**: GDPR-compliant data export functionality
- **Account Deletion**: Complete data removal on request

### For Enterprise Subscribers

- **IP Allowlisting**: Restrict API access to known IPs
- **Rate Limiting**: Configurable rate limits
- **Audit Logs**: Complete API access audit trail
- **Data Residency**: Choose data storage region
- **SLA**: 99.9% uptime guarantee with security SLAs

## Compliance

TruePulse is designed to comply with:

- **GDPR**: General Data Protection Regulation
- **CCPA**: California Consumer Privacy Act
- **SOC 2 Type II**: In progress
- **ISO 27001**: Planned

## Data Retention

| Data Type | Retention Period | Notes |
|-----------|------------------|-------|
| Vote Records | Indefinite | Anonymized, cannot be linked to users |
| User Profiles | Until deletion | Users can request full deletion |
| Session Data | 30 days | Automatically purged |
| Audit Logs | 7 years | Required for compliance |
| API Logs | 90 days | Aggregated after 30 days |

## Contact

- **Security Team**: security@truepulse.io
- **Privacy Officer**: privacy@truepulse.io
- **General Inquiries**: hello@truepulse.io

## Version

This security policy was last updated: December 2025
