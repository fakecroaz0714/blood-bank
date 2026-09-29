"""
Authentication utilities and cross-platform password hashing compatibility.
Ensures robust password hashing (PBKDF2/SHA256 and scrypt) across all platforms,
including macOS systems where LibreSSL lacks native scrypt support.
"""
import hashlib
from werkzeug.security import generate_password_hash as _w_generate_password_hash
from werkzeug.security import check_password_hash as _w_check_password_hash

# Polyfill hashlib.scrypt if missing (macOS system Python linked with LibreSSL)
if not hasattr(hashlib, 'scrypt'):
    try:
        from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
        def _scrypt(password, *, salt=None, n=16384, r=8, p=1, maxmem=0, dklen=64):
            kdf = Scrypt(salt=salt, length=dklen, n=n, r=r, p=p)
            return kdf.derive(password)
        hashlib.scrypt = _scrypt
    except Exception:
        pass


def hash_password(password: str, method: str = 'pbkdf2:sha256') -> str:
    """
    Generate a secure, salted password hash.
    Defaults to pbkdf2:sha256 for universal compatibility and security.
    """
    try:
        return _w_generate_password_hash(password, method=method)
    except Exception:
        return _w_generate_password_hash(password)


def generate_password_hash(password: str, method: str = 'pbkdf2:sha256') -> str:
    """Drop-in replacement for werkzeug's generate_password_hash with safe default."""
    return hash_password(password, method=method)


def check_password_hash(pwhash: str, password: str) -> bool:
    """
    Securely check if stored password hash matches plaintext password.
    Supports pbkdf2:sha256, scrypt, and legacy formats.
    """
    if not pwhash or not password:
        return False
    try:
        return _w_check_password_hash(pwhash, password)
    except Exception:
        return False
