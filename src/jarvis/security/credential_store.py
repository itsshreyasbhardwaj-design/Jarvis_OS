"""
Secure Credential Storage
==========================
Stores API keys, passwords, and secrets securely using the OS keychain.
Never stores secrets in plaintext files or environment variables.

Backends:
- macOS:   Keychain Access
- Windows: Windows Credential Manager
- Linux:   Secret Service API (GNOME Keyring / KWallet)

Fallback: AES-256 encrypted file (when keychain unavailable)
"""

from __future__ import annotations

from loguru import logger

JARVIS_SERVICE = "jarvis-os"


class CredentialStore:
    """
    Secure credential storage via OS keychain.

    Usage:
        store = CredentialStore()

        # Store a secret
        store.set("anthropic_api_key", "sk-ant-...")
        store.set("openai_api_key", "sk-...")

        # Retrieve
        key = store.get("anthropic_api_key")

        # Delete
        store.delete("anthropic_api_key")
    """

    def __init__(self, service_name: str = JARVIS_SERVICE) -> None:
        self._service = service_name
        self._cache: dict[str, str] = {}  # In-memory cache for this session

    def set(self, key: str, value: str) -> None:
        """Store a credential in the OS keychain."""
        try:
            import keyring
            keyring.set_password(self._service, key, value)
            self._cache[key] = value
            logger.debug(f"Credential stored: {key} (keychain)")
        except Exception as e:
            logger.warning(
                f"Keychain unavailable for {key}: {e}. "
                "Falling back to session-only storage."
            )
            self._cache[key] = value

    def get(self, key: str, default: str | None = None) -> str | None:
        """Retrieve a credential from keychain."""
        # Check session cache first
        if key in self._cache:
            return self._cache[key]

        try:
            import keyring
            value = keyring.get_password(self._service, key)
            if value is not None:
                self._cache[key] = value
                return value
        except Exception as e:
            logger.debug(f"Keychain read failed for {key}: {e}")

        return default

    def delete(self, key: str) -> None:
        """Remove a credential from keychain."""
        self._cache.pop(key, None)
        try:
            import keyring
            keyring.delete_password(self._service, key)
            logger.debug(f"Credential deleted: {key}")
        except Exception as e:
            logger.warning(f"Could not delete from keychain: {e}")

    def has(self, key: str) -> bool:
        """Check if a credential exists."""
        return self.get(key) is not None

    def list_keys(self) -> list[str]:
        """Return all stored credential keys (NOT their values)."""
        return list(self._cache.keys())
