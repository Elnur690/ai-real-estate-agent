import re
import hmac
import hashlib
import struct
import time
import base64
import secrets
from typing import List, Optional
from urllib.parse import quote
from fastapi import HTTPException, status

def validate_strong_password(password: str) -> None:
    """
    Enforces strong password policy:
    1. Minimum 8 characters
    2. At least one uppercase letter [A-Z]
    3. At least one lowercase letter [a-z]
    4. At least one number [0-9]
    5. At least one special character [!@#$%^&*...]
    """
    if not password or len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Şifrə minimum 8 simvoldan ibarət olmalıdır."
        )

    if len(password) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Şifrə maksimum 128 simvol ola bilər."
        )

    errors = []
    if not re.search(r'[A-Z]', password):
        errors.append("ən azı 1 böyük hərf (A-Z)")
    if not re.search(r'[a-z]', password):
        errors.append("ən azı 1 kiçik hərf (a-z)")
    if not re.search(r'[0-9]', password):
        errors.append("ən azı 1 rəqəm (0-9)")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>\-_=+\\/~`\[\]]', password):
        errors.append("ən azı 1 xüsusi simvol (!@#$%^&*...)")

    if errors:
        msg = "Güclü şifrə tələb olunur: " + ", ".join(errors) + " ehtiva etməlidir."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


# ----------------- RFC 6238 TOTP (2FA Authenticator) Engine -----------------

BASE32_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"

def generate_totp_secret(length: int = 32) -> str:
    """Generates a cryptographically secure Base32 secret for Google Authenticator."""
    return ''.join(secrets.choice(BASE32_CHARS) for _ in range(length))

def generate_totp_uri(secret: str, email: str, issuer: str = "RealEstate AI") -> str:
    """Generates standard otpauth:// URI for Authenticator apps."""
    clean_issuer = quote(issuer)
    clean_email = quote(email)
    return f"otpauth://totp/{clean_issuer}:{clean_email}?secret={secret}&issuer={clean_issuer}&algorithm=SHA1&digits=6&period=30"

def generate_backup_codes(count: int = 8) -> List[str]:
    """Generates single-use backup recovery codes formatted as XXXX-XXXX."""
    codes = []
    for _ in range(count):
        part1 = secrets.token_hex(2).upper()
        part2 = secrets.token_hex(2).upper()
        codes.append(f"{part1}-{part2}")
    return codes

def get_current_totp_token(secret: str, time_step: int = 30) -> str:
    """Calculates current 6-digit TOTP token according to RFC 6238."""
    # Normalize base32 secret padding
    cleaned_secret = secret.strip().upper().replace(" ", "")
    padding = (8 - (len(cleaned_secret) % 8)) % 8
    cleaned_secret += "=" * padding
    
    key = base64.b32decode(cleaned_secret)
    counter = int(time.time() // time_step)
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[19] & 0x0F
    code = (struct.unpack(">I", h[offset:offset+4])[0] & 0x7FFFFFFF) % 1000000
    return f"{code:06d}"

def verify_totp_code(secret: str, code: str, window: int = 1) -> bool:
    """
    Verifies 6-digit code with +/- 1 time-step (30s) drift tolerance.
    """
    if not secret or not code:
        return False
    
    clean_code = code.strip().replace(" ", "").replace("-", "")
    if len(clean_code) != 6 or not clean_code.isdigit():
        return False

    cleaned_secret = secret.strip().upper().replace(" ", "")
    padding = (8 - (len(cleaned_secret) % 8)) % 8
    cleaned_secret += "=" * padding

    try:
        key = base64.b32decode(cleaned_secret)
    except Exception:
        return False

    now_counter = int(time.time() // 30)
    for offset_step in range(now_counter - window, now_counter + window + 1):
        msg = struct.pack(">Q", offset_step)
        h = hmac.new(key, msg, hashlib.sha1).digest()
        offset = h[19] & 0x0F
        expected = (struct.unpack(">I", h[offset:offset+4])[0] & 0x7FFFFFFF) % 1000000
        if f"{expected:06d}" == clean_code:
            return True

    return False
