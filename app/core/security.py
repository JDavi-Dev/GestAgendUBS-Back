from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from fastapi import HTTPException, status

try:
    import bcrypt as _bcrypt
except ImportError:  # fallback útil apenas para ambientes de teste sem a dependência opcional
    _bcrypt = None
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError
    _argon2 = PasswordHasher()

from app.core.config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    if _bcrypt is not None:
        return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")
    return _argon2.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if password_hash.startswith("$2"):
        if _bcrypt is None:
            return False
        try:
            return _bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
        except ValueError:
            return False
    try:
        return _argon2.verify(password_hash, password)
    except (VerifyMismatchError, ValueError):
        return False


def create_token(
    *,
    credential_id: int,
    role: str,
    reference_id: int,
    token_type: str,
) -> str:
    now = datetime.now(UTC)
    if token_type == "access":
        expires = now + timedelta(minutes=settings.access_token_expire_minutes)
    elif token_type == "refresh":
        expires = now + timedelta(days=settings.refresh_token_expire_days)
    else:
        raise ValueError("Tipo de token inválido.")

    payload = {
        "sub": str(credential_id),
        "role": role,
        "reference_id": reference_id,
        "type": token_type,
        "jti": str(uuid4()),
        "iat": now,
        "exp": expires,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: str | None = None) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado.") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.") from exc

    if expected_type and payload.get("type") != expected_type:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tipo de token inválido.")
    return payload
