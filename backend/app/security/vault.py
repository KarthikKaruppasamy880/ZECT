"""Secure vault for encryption key management using AWS Secrets Manager."""

import os
import boto3
from typing import Optional

class VaultManager:
    """
    Manages encryption keys securely.

    In production: Fetches from AWS Secrets Manager
    In development: Reads from ENCRYPTION_KEY environment variable
    """

    def __init__(self):
        """Initialize vault manager."""
        self.env = os.getenv("ENV", "development")
        self.key = self._load_key()

    def _load_key(self) -> bytes:
        """Load encryption key from vault or environment."""
        if self.env == "production":
            return self._get_key_from_aws_secrets_manager()
        else:
            return self._get_key_from_env()

    def _get_key_from_aws_secrets_manager(self) -> bytes:
        """
        Fetch encryption key from AWS Secrets Manager.

        Requires AWS credentials configured in environment.
        Secret name: zect/encryption-key
        """
        try:
            client = boto3.client("secretsmanager", region_name="us-east-1")
            response = client.get_secret_value(SecretId="zect/encryption-key")

            # Secret can be stored as string or binary
            if "SecretString" in response:
                key_str = response["SecretString"]
                # If it's a base64-encoded string, decode it
                if key_str.startswith("b'") or key_str.startswith('b"'):
                    # Python repr format: b'...' → strip the b' prefix and ' suffix
                    key_str = key_str[2:-1]
                return key_str.encode() if isinstance(key_str, str) else key_str
            else:
                # SecretBinary
                return response["SecretBinary"]
        except Exception as e:
            raise RuntimeError(
                f"Failed to fetch encryption key from AWS Secrets Manager: {e}. "
                f"Make sure the secret 'zect/encryption-key' exists and AWS credentials are configured."
            )

    def _get_key_from_env(self) -> bytes:
        """Fetch encryption key from environment variable."""
        key_str = os.getenv("ENCRYPTION_KEY")
        if not key_str:
            raise ValueError(
                "ENCRYPTION_KEY not set in environment. "
                "Set it in your .env file for development, or configure AWS Secrets Manager for production."
            )

        # Handle both string and bytes formats
        if isinstance(key_str, str):
            if key_str.startswith("b'") or key_str.startswith('b"'):
                # Python repr format: b'...' → strip the b' prefix and ' suffix
                key_str = key_str[2:-1]
            return key_str.encode()
        return key_str

    def get_key(self) -> bytes:
        """Get the current encryption key."""
        return self.key


# Global vault instance
try:
    vault = VaultManager()
except Exception as e:
    raise RuntimeError(f"Failed to initialize vault: {e}")
