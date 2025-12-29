"""
Two-Factor Authentication (2FA) with TOTP
Time-based One-Time Password implementation (RFC 6238)

Phase 2 Day 5: 2FA Implementation
"""

import hashlib
import json
import secrets
from io import BytesIO
from typing import List, Optional, Tuple

import pyotp
import qrcode
from cryptography.fernet import Fernet

from utils.logger import ModuleLogger


class TOTPManager:
    """Manage TOTP 2FA operations

    Features:
    - TOTP secret generation and storage (encrypted)
    - QR code generation for authenticator apps
    - Token verification with time window
    - Backup code generation and verification
    """

    def __init__(self, encryption_key: bytes):
        """Initialize TOTP manager with encryption key

        Args:
            encryption_key: Fernet encryption key for secret storage
        """
        self.logger = ModuleLogger("TOTPManager")
        self.cipher = Fernet(encryption_key)
        self.logger.info("TOTP manager initialized")

    def generate_secret(self) -> str:
        """Generate new TOTP secret (base32)

        Returns:
            Base32-encoded secret (e.g., "JBSWY3DPEHPK3PXP")
        """
        secret = pyotp.random_base32()
        self.logger.debug(f"Generated new TOTP secret (length: {len(secret)})")
        return secret

    def encrypt_secret(self, secret: str) -> str:
        """Encrypt TOTP secret for database storage

        Args:
            secret: Plain TOTP secret

        Returns:
            Encrypted secret (base64-encoded)
        """
        try:
            encrypted = self.cipher.encrypt(secret.encode()).decode()
            self.logger.debug("Secret encrypted successfully")
            return encrypted
        except Exception as e:
            self.logger.error(f"Failed to encrypt secret: {e}")
            raise

    def decrypt_secret(self, encrypted: str) -> str:
        """Decrypt TOTP secret from database

        Args:
            encrypted: Encrypted secret from storage

        Returns:
            Plain TOTP secret
        """
        try:
            decrypted = self.cipher.decrypt(encrypted.encode()).decode()
            self.logger.debug("Secret decrypted successfully")
            return decrypted
        except Exception as e:
            self.logger.error(f"Failed to decrypt secret: {e}")
            raise

    def get_provisioning_uri(self, secret: str, username: str, issuer: str = "Arvis") -> str:
        """Generate provisioning URI for QR code

        Args:
            secret: TOTP secret
            username: User's username
            issuer: Application name (default: "Arvis")

        Returns:
            otpauth:// URI for authenticator apps
        """
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=username, issuer_name=issuer)
        self.logger.debug(f"Generated provisioning URI for user: {username}")
        return uri

    def generate_qr_code(self, uri: str) -> bytes:
        """Generate QR code image (PNG bytes)

        Args:
            uri: Provisioning URI

        Returns:
            PNG image bytes
        """
        try:
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=5)
            qr.add_data(uri)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            # Convert to PNG bytes
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            qr_bytes = buffer.getvalue()

            self.logger.debug(f"Generated QR code ({len(qr_bytes)} bytes)")
            return qr_bytes
        except Exception as e:
            self.logger.error(f"Failed to generate QR code: {e}")
            raise

    def verify_token(self, secret: str, token: str, window: int = 1) -> bool:
        """Verify TOTP token (30-second time-based)

        Args:
            secret: TOTP secret (decrypted)
            token: 6-digit token from authenticator app
            window: Time window tolerance (±1 = 90 seconds total)

        Returns:
            True if token is valid
        """
        try:
            # Remove spaces and validate format
            token = token.replace(" ", "").replace("-", "")

            if not token.isdigit() or len(token) != 6:
                self.logger.warning(f"Invalid token format: {len(token)} chars")
                return False

            totp = pyotp.TOTP(secret)
            valid = totp.verify(token, valid_window=window)

            if valid:
                self.logger.info("TOTP token verified successfully")
            else:
                self.logger.warning("TOTP token verification failed")

            return valid
        except Exception as e:
            self.logger.error(f"Token verification error: {e}")
            return False

    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """Generate backup recovery codes

        Args:
            count: Number of codes to generate (default: 10)

        Returns:
            List of backup codes (format: "XXXX-XXXX-XXXX")
        """
        codes = []
        for _ in range(count):
            # Format: XXXX-XXXX-XXXX (12 hex chars)
            code = "-".join([secrets.token_hex(2).upper() for _ in range(3)])
            codes.append(code)

        self.logger.info(f"Generated {count} backup codes")
        return codes

    def hash_backup_code(self, code: str) -> str:
        """Hash backup code for secure storage (SHA-256)

        Args:
            code: Plain backup code

        Returns:
            SHA-256 hash (hex string)
        """
        return hashlib.sha256(code.encode()).hexdigest()

    def hash_backup_codes(self, codes: List[str]) -> List[str]:
        """Hash multiple backup codes

        Args:
            codes: List of plain backup codes

        Returns:
            List of hashed codes
        """
        return [self.hash_backup_code(code) for code in codes]

    def verify_backup_code(self, code: str, hashed_codes: List[str]) -> Tuple[bool, List[str]]:
        """Verify backup code and return updated list (one-time use)

        Args:
            code: Plain backup code to verify
            hashed_codes: List of hashed codes from storage

        Returns:
            (valid, remaining_hashed_codes)
        """
        try:
            code_hash = self.hash_backup_code(code)

            if code_hash in hashed_codes:
                # Remove used code
                remaining = [h for h in hashed_codes if h != code_hash]
                self.logger.info(f"Backup code used ({len(remaining)} remaining)")
                return True, remaining
            else:
                self.logger.warning("Invalid backup code")
                return False, hashed_codes
        except Exception as e:
            self.logger.error(f"Backup code verification error: {e}")
            return False, hashed_codes

    def serialize_backup_codes(self, hashed_codes: List[str]) -> str:
        """Serialize hashed backup codes to JSON string for storage

        Args:
            hashed_codes: List of hashed backup codes

        Returns:
            JSON string
        """
        return json.dumps(hashed_codes)

    def deserialize_backup_codes(self, json_str: str) -> List[str]:
        """Deserialize backup codes from JSON string

        Args:
            json_str: JSON string from storage

        Returns:
            List of hashed backup codes
        """
        try:
            return json.loads(json_str) if json_str else []
        except Exception as e:
            self.logger.error(f"Failed to deserialize backup codes: {e}")
            return []


# Singleton instance
_totp_manager: Optional[TOTPManager] = None


def get_totp_manager(encryption_key: Optional[bytes] = None) -> TOTPManager:
    """Get or create TOTP manager singleton

    Args:
        encryption_key: Fernet encryption key (auto-generated if None)

    Returns:
        TOTPManager instance
    """
    global _totp_manager

    if _totp_manager is None:
        if encryption_key is None:
            # Generate or load from environment
            import os

            key_str = os.getenv("TOTP_ENCRYPTION_KEY")

            if not key_str:
                # Generate new key
                key_str = Fernet.generate_key().decode()
                # Note: Should be saved to .env in production
                logger = ModuleLogger("TOTPManager")
                logger.warning("Generated temporary TOTP encryption key (not persisted)")

            encryption_key = key_str.encode()

        _totp_manager = TOTPManager(encryption_key)

    return _totp_manager


def reset_totp_manager():
    """Reset singleton (for testing)"""
    global _totp_manager
    _totp_manager = None
