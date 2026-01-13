"""Encryption utilities for securing sensitive data like Plaid access tokens."""

from cryptography.fernet import Fernet

from .config import settings


class TokenEncryption:
    """Handles encryption and decryption of sensitive tokens."""

    def __init__(self):
        """Initialize the encryption cipher."""
        if not settings.encryption_key:
            raise ValueError(
                "Encryption key not configured. Set FINANCE_TRACKER_ENCRYPTION_KEY in .env\n"
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        self._cipher = Fernet(settings.encryption_key.encode())

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.

        Args:
            plaintext: The string to encrypt (e.g., Plaid access token)

        Returns:
            Encrypted string (base64 encoded)
        """
        encrypted_bytes = self._cipher.encrypt(plaintext.encode())
        return encrypted_bytes.decode()

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string.

        Args:
            ciphertext: The encrypted string to decrypt

        Returns:
            Decrypted plaintext string
        """
        decrypted_bytes = self._cipher.decrypt(ciphertext.encode())
        return decrypted_bytes.decode()


# Singleton instance
_encryptor: TokenEncryption | None = None


def get_encryptor() -> TokenEncryption:
    """Get the singleton encryption instance."""
    global _encryptor
    if _encryptor is None:
        _encryptor = TokenEncryption()
    return _encryptor


def encrypt_token(token: str) -> str:
    """Convenience function to encrypt a token."""
    return get_encryptor().encrypt(token)


def decrypt_token(encrypted_token: str) -> str:
    """Convenience function to decrypt a token."""
    return get_encryptor().decrypt(encrypted_token)
