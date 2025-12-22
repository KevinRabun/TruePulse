# PII Field Encryption Migration Guide

This document describes how to migrate existing PII data to encrypted storage.

## Overview

TruePulse now supports field-level encryption for PII (Personally Identifiable Information) fields:
- Email addresses
- Phone numbers

The encryption uses AES-256-GCM with keys stored in Azure Key Vault.

## Prerequisites

1. Generate an encryption key:
   ```bash
   cd src/backend
   python -c "from core.encryption import generate_encryption_key; print(generate_encryption_key())"
   ```

2. Store the key securely:
   - **Production**: Add to Azure Key Vault as `FIELD-ENCRYPTION-KEY`
   - **Development**: Add to `.env` as `FIELD_ENCRYPTION_KEY=<base64-key>`

## Database Schema Changes

### New Columns

The following columns are added to the `users` table:
- `email_encrypted` - Encrypted email address
- `email_hash` - Searchable hash of email (for lookups)
- `phone_encrypted` - Encrypted phone number
- `phone_hash` - Searchable hash of phone (for lookups)

### Migration Steps

1. **Add new columns** (without removing old ones):
   ```sql
   ALTER TABLE users 
   ADD COLUMN email_encrypted VARCHAR(600),
   ADD COLUMN email_hash VARCHAR(64),
   ADD COLUMN phone_encrypted VARCHAR(600),
   ADD COLUMN phone_hash VARCHAR(64);
   ```

2. **Create indexes on hash columns**:
   ```sql
   CREATE UNIQUE INDEX ix_users_email_hash ON users(email_hash);
   CREATE UNIQUE INDEX ix_users_phone_hash ON users(phone_hash) WHERE phone_hash IS NOT NULL;
   ```

3. **Run data migration script**:
   ```bash
   cd src/backend
   python -m scripts.migrate_pii_encryption
   ```

4. **Verify migration**:
   ```bash
   python -m scripts.verify_pii_migration
   ```

5. **Remove old columns** (after verification):
   ```sql
   -- Only run after confirming all data is migrated
   ALTER TABLE users 
   DROP COLUMN email,
   DROP COLUMN phone_number;
   ```

6. **Rename new columns**:
   ```sql
   ALTER TABLE users 
   RENAME COLUMN email_encrypted TO email,
   RENAME COLUMN phone_encrypted TO phone_number;
   ```

## Application Code Changes

### Searching by Email

Before (plaintext):
```python
user = await session.scalar(
    select(User).where(User.email == email)
)
```

After (using hash):
```python
from db.types import compute_email_hash

email_hash = compute_email_hash(email)
user = await session.scalar(
    select(User).where(User.email_hash == email_hash)
)
```

### Creating Users

```python
from db.types import compute_email_hash, compute_phone_hash

user = User(
    email=email,  # Will be encrypted automatically
    email_hash=compute_email_hash(email),
    phone_number=phone,  # Will be encrypted automatically
    phone_hash=compute_phone_hash(phone) if phone else None,
    ...
)
```

## Key Rotation

To rotate encryption keys:

1. Generate new key
2. Run key rotation script with both old and new keys
3. Update Key Vault with new key
4. Invalidate old key

See `scripts/rotate_encryption_key.py` for details.

## Rollback Plan

If migration fails:

1. Data remains in original unencrypted columns
2. Application can fall back to unencrypted access
3. Re-run migration after fixing issues

## Security Considerations

- Encryption key must be 256 bits (32 bytes)
- Key is stored in Azure Key Vault (not in code or config files)
- Hashes use PBKDF2-SHA256 with 10,000 iterations
- Each encrypted value uses a unique random nonce
- Decryption requires the same key used for encryption

## Testing

Run encryption tests:
```bash
cd src/backend
pytest tests/core/test_encryption.py -v
```
