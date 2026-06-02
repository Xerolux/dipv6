#!/usr/bin/env python3
"""
Secrets Manager for Encrypted Credential Storage
Encrypts sensitive data (passwords, tokens) using Fernet (AES-128)
"""

import os
import json
import logging
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64

logger = logging.getLogger(__name__)

SECRETS_DIR = Path("/etc/dynipv6/secrets")
KEY_FILE = SECRETS_DIR / ".key"
SALT_FILE = SECRETS_DIR / ".salt"


class SecretsManager:
    """
    Manages encrypted storage of sensitive credentials
    Uses Fernet (AES-128) symmetric encryption
    """

    def __init__(self):
        """Initialize secrets manager"""
        SECRETS_DIR.mkdir(parents=True, exist_ok=True)
        os.chmod(SECRETS_DIR, 0o700)  # Only owner can read

        self.cipher = self._get_cipher()

    @staticmethod
    def _get_cipher():
        """Get or create encryption cipher"""
        try:
            # Load existing key
            if KEY_FILE.exists():
                with open(KEY_FILE, 'rb') as f:
                    key = f.read()
                logger.info("Loaded existing encryption key")
            else:
                # Generate new key
                key = Fernet.generate_key()
                with open(KEY_FILE, 'wb') as f:
                    f.write(key)
                os.chmod(KEY_FILE, 0o600)  # Only owner can read
                logger.info("Generated new encryption key")

            return Fernet(key)
        except Exception as e:
            logger.error(f"Failed to initialize cipher: {e}")
            raise

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext password/token

        Args:
            plaintext: Plain password or token

        Returns:
            Encrypted string (base64)
        """
        try:
            if isinstance(plaintext, str):
                plaintext = plaintext.encode('utf-8')

            encrypted = self.cipher.encrypt(plaintext)
            return encrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise

    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt encrypted password/token

        Args:
            encrypted: Encrypted string (base64)

        Returns:
            Decrypted plaintext
        """
        try:
            if isinstance(encrypted, str):
                encrypted = encrypted.encode('utf-8')

            decrypted = self.cipher.decrypt(encrypted)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise

    def encrypt_config(self, config: dict) -> dict:
        """
        Encrypt sensitive fields in config

        Args:
            config: Configuration dictionary

        Returns:
            Config with encrypted sensitive fields
        """
        config_copy = config.copy()

        # Encrypt ISPConfig password
        if 'ispconfig_password' in config_copy:
            config_copy['ispconfig_password'] = self.encrypt(
                config_copy['ispconfig_password']
            )

        # Encrypt admin password (if stored in config, not recommended)
        if 'admin_password' in config_copy:
            config_copy['admin_password'] = self.encrypt(
                config_copy['admin_password']
            )

        return config_copy

    def decrypt_config(self, config: dict) -> dict:
        """
        Decrypt sensitive fields in config

        Args:
            config: Configuration dictionary with encrypted fields

        Returns:
            Config with decrypted fields
        """
        config_copy = config.copy()

        # Decrypt ISPConfig password
        if 'ispconfig_password' in config_copy and config_copy['ispconfig_password'].startswith('gAAAAAA'):
            try:
                config_copy['ispconfig_password'] = self.decrypt(
                    config_copy['ispconfig_password']
                )
            except Exception as e:
                logger.error(f"Failed to decrypt ISPConfig password: {e}")
                # Return as-is if decryption fails
                pass

        # Decrypt admin password
        if 'admin_password' in config_copy and isinstance(config_copy['admin_password'], str) and config_copy['admin_password'].startswith('gAAAAAA'):
            try:
                config_copy['admin_password'] = self.decrypt(
                    config_copy['admin_password']
                )
            except Exception as e:
                logger.error(f"Failed to decrypt admin password: {e}")
                pass

        return config_copy


class ConfigWithSecrets:
    """Configuration manager with encrypted secrets"""

    def __init__(self, config_file: Path):
        """Initialize config manager"""
        self.config_file = config_file
        self.secrets_manager = SecretsManager()
        self.config = self.load()

    def load(self) -> dict:
        """Load and decrypt configuration"""
        try:
            with open(self.config_file, 'r') as f:
                encrypted_config = json.load(f)

            # Decrypt sensitive fields
            decrypted_config = self.secrets_manager.decrypt_config(encrypted_config)
            logger.info("Configuration loaded and decrypted successfully")
            return decrypted_config
        except FileNotFoundError:
            logger.error(f"Config file not found: {self.config_file}")
            raise
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in config file: {self.config_file}")
            raise
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            raise

    def save(self, config: dict = None):
        """Save and encrypt configuration"""
        try:
            if config is None:
                config = self.config

            # Encrypt sensitive fields
            encrypted_config = self.secrets_manager.encrypt_config(config)

            # Save to file
            with open(self.config_file, 'w') as f:
                json.dump(encrypted_config, f, indent=2)

            # Restrict file permissions
            os.chmod(self.config_file, 0o600)
            logger.info("Configuration saved and encrypted successfully")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            raise

    def get(self, key: str, default=None):
        """Get config value"""
        return self.config.get(key, default)

    def set(self, key: str, value):
        """Set config value"""
        self.config[key] = value

    def update(self, updates: dict):
        """Update multiple config values"""
        self.config.update(updates)


def test_encryption():
    """Test encryption/decryption"""
    try:
        sm = SecretsManager()

        # Test password
        password = "MySecurePassword123!"
        encrypted = sm.encrypt(password)
        decrypted = sm.decrypt(encrypted)

        assert decrypted == password, "Encryption/Decryption mismatch!"
        print(f"✓ Encryption test passed")
        print(f"  Original:  {password}")
        print(f"  Encrypted: {encrypted[:50]}...")
        print(f"  Decrypted: {decrypted}")
    except Exception as e:
        print(f"✗ Encryption test failed: {e}")


if __name__ == '__main__':
    test_encryption()
