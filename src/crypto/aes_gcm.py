import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class AesGcmCipher:
    """Utility class for AES-GCM encryption and decryption."""

    @staticmethod
    def encrypt(plaintext: bytes, key: bytes) -> bytes:
        """
        Encrypts plaintext using AES-GCM.
        The key must be 32 bytes for AES-256.
        Returns: nonce (12 bytes) + ciphertext (includes auth tag).
        """
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        return nonce + ciphertext

    @staticmethod
    def decrypt(ciphertext_with_nonce: bytes, key: bytes) -> bytes:
        """
        Decrypts ciphertext that was prepended with a 12-byte nonce.
        """
        nonce = ciphertext_with_nonce[:12]
        ciphertext = ciphertext_with_nonce[12:]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None)
