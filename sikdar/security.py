"""Password hashing and encryption of stored secrets.

* The owner password is hashed with scrypt (a 64 byte derivation: the first half
  is stored as the verifier, the second half is used as a key-wrapping key and
  is never stored).
* A random data key encrypts the clients' Income-Tax-portal passwords (Fernet).
  That data key is stored only in wrapped (encrypted) form, so the portal
  passwords can be read only after the owner has logged in.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken

_N, _R, _P = 2 ** 14, 8, 1


def _derive(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P,
        maxmem=128 * 1024 * 1024, dklen=64,
    )


def _fernet_from(raw32: bytes) -> Fernet:
    return Fernet(base64.urlsafe_b64encode(raw32))


@dataclass
class VaultRecord:
    salt: str          # hex
    verifier: str      # hex
    wrapped_key: str   # fernet token (str)


class Vault:
    """Holds the unlocked data key for the current session."""

    def __init__(self, data_key: bytes):
        self._fernet = Fernet(data_key)
        self._data_key = data_key

    @property
    def data_key(self) -> bytes:
        return self._data_key

    def encrypt(self, text: str) -> str:
        if not text:
            return ""
        return self._fernet.encrypt(text.encode("utf-8")).decode("ascii")

    def decrypt(self, token: str) -> str:
        if not token:
            return ""
        try:
            return self._fernet.decrypt(token.encode("ascii")).decode("utf-8")
        except InvalidToken:
            return ""


def create_record(password: str, data_key: bytes | None = None) -> tuple[VaultRecord, Vault]:
    data_key = data_key or Fernet.generate_key()
    salt = os.urandom(16)
    dk = _derive(password, salt)
    verifier, wrap_key = dk[:32], dk[32:]
    wrapped = _fernet_from(wrap_key).encrypt(data_key).decode("ascii")
    return VaultRecord(salt.hex(), verifier.hex(), wrapped), Vault(data_key)


def unlock(password: str, rec: VaultRecord) -> Vault | None:
    salt = bytes.fromhex(rec.salt)
    dk = _derive(password, salt)
    verifier, wrap_key = dk[:32], dk[32:]
    if not hmac.compare_digest(verifier.hex(), rec.verifier):
        return None
    try:
        data_key = _fernet_from(wrap_key).decrypt(rec.wrapped_key.encode("ascii"))
    except InvalidToken:
        return None
    return Vault(data_key)


def password_strength(password: str) -> tuple[int, str]:
    """Return (score 0-4, label)."""
    score = 0
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if any(c.islower() for c in password) and any(c.isupper() for c in password):
        score += 1
    if any(c.isdigit() for c in password) and any(not c.isalnum() for c in password):
        score += 1
    labels = ["Too weak", "Weak", "Fair", "Good", "Strong"]
    if not password:
        return 0, ""
    return score, labels[score]
