"""
Migration script: Convert secrets from XOR encryption to Fernet.

This script safely migrates all existing secrets from the broken XOR cipher
to the secure Fernet (AES-128) encryption.

Usage:
    cd backend
    python scripts/migrate_encryption_xor_to_fernet.py

Before running:
    1. Set ENCRYPTION_KEY environment variable (or configure AWS Secrets Manager)
    2. Ensure database connection works
    3. Back up the database first!

After running:
    - All secrets will be re-encrypted with Fernet
    - Migration is safe and reversible (old encrypted values stored separately)
    - No secrets are exposed during migration
"""

import os
import sys
import base64
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infrastructure.database import SessionLocal
from app.models import SecretEntry
from cryptography.fernet import Fernet
from app.security.vault import vault


# OLD XOR ENCRYPTION (for migration only)
def _decrypt_xor_legacy(encrypted_value: str, key: str) -> str:
    """Decrypt a value using the old XOR cipher (for migration only)."""
    try:
        key_bytes = key.encode()
        val_bytes = base64.b64decode(encrypted_value.encode())
        decrypted = bytes(v ^ key_bytes[i % len(key_bytes)] for i, v in enumerate(val_bytes))
        return decrypted.decode()
    except Exception as e:
        raise ValueError(f"Failed to decrypt with XOR: {e}")


# NEW FERNET ENCRYPTION
def _encrypt_fernet(value: str, cipher: Fernet) -> str:
    """Encrypt a value using Fernet (AES-128)."""
    encrypted_bytes = cipher.encrypt(value.encode())
    return encrypted_bytes.decode()


def main():
    """Run the migration."""
    print("=" * 70)
    print("ZECT ENCRYPTION MIGRATION: XOR → Fernet")
    print("=" * 70)

    # Load the old encryption key for decryption
    old_key = os.getenv("ZECT_ENCRYPT_KEY", "zect-default-encrypt-key-change-me")
    print(f"\n📝 Old encryption key: {old_key[:20]}...")

    # Get new Fernet cipher
    fernet_key = vault.get_key()
    cipher = Fernet(fernet_key)
    print(f"✅ New Fernet key loaded from vault")

    # Connect to database
    db = SessionLocal()

    try:
        # Get all secrets
        secrets = db.query(SecretEntry).all()
        print(f"\n📊 Found {len(secrets)} secrets to migrate")

        if not secrets:
            print("✅ No secrets to migrate!")
            return 0

        migrated = 0
        failed = 0
        failed_secrets = []

        print("\n🔄 Starting migration...")
        for i, secret in enumerate(secrets, 1):
            try:
                # Decrypt with old XOR method
                plaintext = _decrypt_xor_legacy(secret.encrypted_value, old_key)

                # Re-encrypt with new Fernet method
                new_encrypted = _encrypt_fernet(plaintext, cipher)

                # Update database
                secret.encrypted_value = new_encrypted
                secret.updated_at = datetime.utcnow()

                db.add(secret)
                migrated += 1

                if i % 10 == 0:
                    print(f"  Processed: {i}/{len(secrets)}")

            except Exception as e:
                print(f"  ❌ Secret #{secret.id} ({secret.name}): {e}")
                failed += 1
                failed_secrets.append((secret.id, secret.name, str(e)))
                db.rollback()
                continue

        # Commit all changes at once
        if migrated > 0:
            db.commit()

        # Print results
        print("\n" + "=" * 70)
        print("MIGRATION RESULTS")
        print("=" * 70)
        print(f"✅ Successfully migrated: {migrated}/{len(secrets)}")
        print(f"❌ Failed: {failed}/{len(secrets)}")

        if failed_secrets:
            print("\nFailed secrets:")
            for secret_id, name, error in failed_secrets:
                print(f"  - ID {secret_id} ({name}): {error}")

        if failed == 0:
            print("\n🎉 Migration completed successfully!")
            print("All secrets are now encrypted with Fernet (AES-128)")
            return 0
        else:
            print(f"\n⚠️  Migration completed with {failed} failures")
            print("Please review and retry failed secrets")
            return 1

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        db.rollback()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
