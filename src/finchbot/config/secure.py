import base64
import json
import os
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from loguru import logger


class SecureConfig:
    """
    Secure configuration storage with encryption for sensitive data.

    Features:
    - Fernet symmetric encryption for API keys
    - Key derivation from master password
    - Secure storage file with restricted permissions
    """

    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path.home() / ".finchbot"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.secrets_file = self.config_dir / "secrets.enc"
        self.key_file = self.config_dir / ".key"
        self._cipher: Fernet | None = None
        self._secrets: dict = {}

    def _get_or_create_key(self, master_password: str = None) -> bytes:
        """Get or create encryption key."""
        if self.key_file.exists():
            with open(self.key_file, "rb") as f:
                return f.read()

        if master_password:
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=480000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))

            with open(self.key_file, "wb") as f:
                f.write(salt + key)

            os.chmod(self.key_file, 0o600)

            return key
        else:
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(key)

            os.chmod(self.key_file, 0o600)

            return key

    def initialize(self, master_password: str = None) -> None:
        """Initialize the secure config with optional master password."""
        key = self._get_or_create_key(master_password)
        self._cipher = Fernet(key)

        if self.secrets_file.exists():
            self._load_secrets()

    def _load_secrets(self) -> None:
        """Load encrypted secrets from file."""
        if not self._cipher:
            raise RuntimeError("SecureConfig not initialized")

        try:
            with open(self.secrets_file, "rb") as f:
                encrypted_data = f.read()

            decrypted_data = self._cipher.decrypt(encrypted_data)
            self._secrets = json.loads(decrypted_data.decode())
        except Exception as e:
            logger.warning(f"Failed to load secrets: {e}")
            self._secrets = {}

    def _save_secrets(self) -> None:
        """Save encrypted secrets to file."""
        if not self._cipher:
            raise RuntimeError("SecureConfig not initialized")

        data = json.dumps(self._secrets).encode()
        encrypted_data = self._cipher.encrypt(data)

        with open(self.secrets_file, "wb") as f:
            f.write(encrypted_data)

        os.chmod(self.secrets_file, 0o600)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a secret value."""
        return self._secrets.get(key, default)

    def set(self, key: str, value: str) -> None:
        """Set a secret value."""
        self._secrets[key] = value
        self._save_secrets()

    def delete(self, key: str) -> None:
        """Delete a secret."""
        if key in self._secrets:
            del self._secrets[key]
            self._save_secrets()

    def get_api_key(self, provider: str) -> str | None:
        """Get API key for a provider."""
        return self._secrets.get(f"api_key_{provider}")

    def set_api_key(self, provider: str, api_key: str) -> None:
        """Set API key for a provider."""
        self._secrets[f"api_key_{provider}"] = api_key
        self._save_secrets()
        logger.info(f"API key for {provider} stored securely")

    def delete_api_key(self, provider: str) -> None:
        """Delete API key for a provider."""
        key = f"api_key_{provider}"
        if key in self._secrets:
            del self._secrets[key]
            self._save_secrets()
            logger.info(f"API key for {provider} deleted")

    def list_providers(self) -> list:
        """List all providers with stored API keys."""
        providers = []
        for key in self._secrets:
            if key.startswith("api_key_"):
                providers.append(key[8:])
        return providers

    def export_encrypted(self) -> str:
        """Export all secrets as encrypted base64 string."""
        if not self._cipher:
            raise RuntimeError("SecureConfig not initialized")

        data = json.dumps(self._secrets).encode()
        encrypted_data = self._cipher.encrypt(data)
        return base64.urlsafe_b64encode(encrypted_data).decode()

    def import_encrypted(self, encrypted_string: str) -> None:
        """Import secrets from encrypted base64 string."""
        if not self._cipher:
            raise RuntimeError("SecureConfig not initialized")

        encrypted_data = base64.urlsafe_b64decode(encrypted_string.encode())
        decrypted_data = self._cipher.decrypt(encrypted_data)
        self._secrets = json.loads(decrypted_data.decode())
        self._save_secrets()


secure_config = SecureConfig()


def encrypt_value(value: str) -> str:
    """Encrypt a single value using the global secure config."""
    if not secure_config._cipher:
        secure_config.initialize()

    encrypted = secure_config._cipher.encrypt(value.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_value(encrypted_value: str) -> str:
    """Decrypt a single value using the global secure config."""
    if not secure_config._cipher:
        secure_config.initialize()

    encrypted = base64.urlsafe_b64decode(encrypted_value.encode())
    decrypted = secure_config._cipher.decrypt(encrypted)
    return decrypted.decode()
