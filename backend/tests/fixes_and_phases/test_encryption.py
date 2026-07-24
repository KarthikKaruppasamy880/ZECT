"""Unit tests for Fernet encryption."""

import pytest
from cryptography.fernet import Fernet, InvalidToken
from app.security.vault import vault


class TestFernetEncryption:
    """Test Fernet encryption implementation."""

    @pytest.fixture
    def cipher(self):
        """Get cipher for testing."""
        key = vault.get_key()
        return Fernet(key)

    def test_round_trip_encryption(self, cipher):
        """Test encrypting and decrypting returns original value."""
        original = "openai_sk_secret123"

        # Encrypt
        encrypted = cipher.encrypt(original.encode()).decode()
        assert encrypted != original

        # Decrypt
        decrypted = cipher.decrypt(encrypted.encode()).decode()
        assert decrypted == original

    def test_encryption_is_non_deterministic(self, cipher):
        """Test that same value encrypts differently each time (non-deterministic)."""
        original = "openai_sk_secret123"

        # Encrypt same value twice
        encrypted1 = cipher.encrypt(original.encode()).decode()
        encrypted2 = cipher.encrypt(original.encode()).decode()

        # They should be DIFFERENT (non-deterministic)
        assert encrypted1 != encrypted2

        # But both should decrypt to the same plaintext
        assert cipher.decrypt(encrypted1.encode()).decode() == original
        assert cipher.decrypt(encrypted2.encode()).decode() == original

    def test_tampering_detection(self, cipher):
        """Test that tampering with ciphertext is detected."""
        original = "openai_sk_secret123"
        encrypted = cipher.encrypt(original.encode()).decode()

        # Tamper with the ciphertext
        tampered = encrypted[:-5] + "XXXXX"

        # Decryption should fail
        with pytest.raises(InvalidToken):
            cipher.decrypt(tampered.encode())

    def test_different_keys_cannot_decrypt(self):
        """Test that data encrypted with one key cannot be decrypted with another."""
        key1 = Fernet.generate_key()
        key2 = Fernet.generate_key()

        cipher1 = Fernet(key1)
        cipher2 = Fernet(key2)

        original = "openai_sk_secret123"
        encrypted = cipher1.encrypt(original.encode()).decode()

        # Different key should fail to decrypt
        with pytest.raises(InvalidToken):
            cipher2.decrypt(encrypted.encode())

    def test_empty_value_encryption(self, cipher):
        """Test encrypting empty string."""
        original = ""

        encrypted = cipher.encrypt(original.encode()).decode()
        decrypted = cipher.decrypt(encrypted.encode()).decode()

        assert decrypted == original

    def test_special_characters_encryption(self, cipher):
        """Test encrypting special characters and unicode."""
        original = "test!@#$%^&*()_+-=[]{}|;:',.<>?/`~\n\t\r"

        encrypted = cipher.encrypt(original.encode()).decode()
        decrypted = cipher.decrypt(encrypted.encode()).decode()

        assert decrypted == original

    def test_unicode_encryption(self, cipher):
        """Test encrypting unicode characters."""
        original = "こんにちは世界 🚀 مرحبا بالعالم"

        encrypted = cipher.encrypt(original.encode()).decode()
        decrypted = cipher.decrypt(encrypted.encode()).decode()

        assert decrypted == original

    def test_long_value_encryption(self, cipher):
        """Test encrypting a long value."""
        original = "x" * 10000  # 10KB value

        encrypted = cipher.encrypt(original.encode()).decode()
        decrypted = cipher.decrypt(encrypted.encode()).decode()

        assert decrypted == original


class TestVault:
    """Test vault initialization."""

    def test_vault_loads_key(self):
        """Test that vault successfully loads encryption key."""
        assert vault is not None
        key = vault.get_key()
        assert key is not None
        assert isinstance(key, bytes)
        assert len(key) > 0

    def test_vault_key_is_valid_fernet_key(self):
        """Test that vault key is a valid Fernet key."""
        key = vault.get_key()
        try:
            cipher = Fernet(key)
            assert cipher is not None
        except Exception as e:
            pytest.fail(f"Vault key is not a valid Fernet key: {e}")
