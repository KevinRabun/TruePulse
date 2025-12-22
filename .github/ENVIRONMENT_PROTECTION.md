# GitHub Environment Protection Configuration

This document outlines the required GitHub environment protection settings for TruePulse production deployments.

## Environment Setup

### 1. Create Environments in GitHub

Navigate to: Repository → Settings → Environments

Create these environments:
- `dev` - Development environment
- `staging` - Staging/pre-production environment  
- `prod` - Production environment

### 2. Production Environment Protection Rules

For the `prod` environment, configure the following protection rules:

#### Required Reviewers
- Enable "Required reviewers"
- Add at least one reviewer (e.g., @KevinRabun)
- This ensures human approval before any production deployment

#### Deployment Branches
- Select "Selected branches and tags"
- Add rule: `main` (only allow production deployments from main branch)
- Add rule: `release/*` (allow deployments from release branches)

#### Wait Timer (Optional)
- Enable "Wait timer" 
- Set to 5-15 minutes
- Provides a window to cancel deployment if issues are discovered

#### Environment Secrets
Ensure these secrets are configured for the `prod` environment:
- `AZURE_CLIENT_ID` - Azure AD app client ID
- `AZURE_TENANT_ID` - Azure AD tenant ID
- `AZURE_SUBSCRIPTION_ID` - Azure subscription ID
- `POSTGRES_PASSWORD` - Production database password
- `JWT_SECRET_KEY` - Production JWT signing key
- `VOTE_HASH_SECRET` - Production vote hash secret
- `NEWSDATA_API_KEY` - NewsData.io API key
- `NEWSAPI_ORG_KEY` - NewsAPI.org API key
- `COMMUNICATION_SENDER_NUMBER` - Azure Communication Services sender number
- `TURNSTILE_SECRET_KEY` - Cloudflare Turnstile secret for CAPTCHA
- `FIELD_ENCRYPTION_KEY` - Base64-encoded 256-bit AES key for PII field encryption

### 3. Staging Environment Protection Rules

For the `staging` environment:

#### Deployment Branches
- Select "Selected branches and tags"
- Add rule: `main`
- Add rule: `develop`
- Add rule: `release/*`

#### Environment Secrets
Same as production but with staging-specific values.

### 4. Development Environment

For the `dev` environment:
- No required reviewers (allow automated deployments)
- Deployment branches: `main`, `develop`, `feature/*`
- Environment secrets with development-specific values

## Branch Protection Rules

Navigate to: Repository → Settings → Branches → Add rule

### Main Branch Protection

Branch name pattern: `main`

Enable:
- ✅ Require a pull request before merging
  - ✅ Require approvals: 1
  - ✅ Dismiss stale pull request approvals when new commits are pushed
  - ✅ Require review from Code Owners
- ✅ Require status checks to pass before merging
  - Required checks:
    - `CI Complete`
    - `backend-lint`
    - `backend-test`
    - `frontend-lint`
    - `frontend-test`
    - `security-scan`
- ✅ Require branches to be up to date before merging
- ✅ Require conversation resolution before merging
- ✅ Do not allow bypassing the above settings

### Develop Branch Protection (if using GitFlow)

Branch name pattern: `develop`

Enable:
- ✅ Require a pull request before merging
  - ✅ Require approvals: 1
- ✅ Require status checks to pass before merging

## Deployment Flow

### Automated Deployments

1. **Development** (`dev`):
   - Triggered: Push to `main` branch after CI passes
   - No approval required
   - Fast deployment for testing

2. **Staging** (`staging`):
   - Triggered: Manual dispatch or release candidate tags
   - Optional approval (recommended)
   - Pre-production validation environment

3. **Production** (`prod`):
   - Triggered: Release published
   - Required approval from designated reviewers
   - Includes smoke tests post-deployment

### Manual Deployment

Use the "Deploy" workflow dispatch to manually deploy to any environment:

1. Go to Actions → Deploy workflow
2. Click "Run workflow"
3. Select the target environment
4. Click "Run workflow"

## Verification Checklist

After configuration, verify:

- [ ] Production deployments require approval
- [ ] Only main branch can deploy to production
- [ ] CI checks must pass before merge
- [ ] Code owners are required for sensitive files
- [ ] All environment secrets are configured
- [ ] Branch protection prevents force pushes
- [ ] Staging environment is configured for pre-production testing
- [ ] Budget alerts are set up for each environment
