"""
Shared encryption key helper for pgcrypto-based encryption at rest.

Used by api_keys.py and oauth_tokens.py for pgp_sym_encrypt/decrypt.
"""

import os


_KNOWN_DEFAULT_KEY = "langalpha-local-dev-encryption-key"


def get_encryption_key() -> str:
    """Return the symmetric encryption key for data stored at rest."""
    key = os.getenv("BYOK_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError(
            "BYOK_ENCRYPTION_KEY environment variable is not set. "
            "Required for encrypting sensitive data at rest."
        )
    if key == _KNOWN_DEFAULT_KEY and os.getenv("HOST_MODE", "oss") == "platform":
        raise RuntimeError(
            "BYOK_ENCRYPTION_KEY is the publicly known default. "
            "Refusing to encrypt with a compromised key in platform mode."
        )
    return key
