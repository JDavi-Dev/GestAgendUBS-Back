from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_token, decode_token, verify_password
from app.models import Credential, RevokedToken
from app.services.users import user_to_dict
from app.utils.normalization import only_digits


def _normalize_identifier(identifier: str) -> str:
    digits = only_digits(identifier) or ""
    if len(digits) == 11:
        return digits
    return identifier.strip().lower()


def _token_expiration(payload: dict) -> datetime:
    exp = payload.get("exp")
    if isinstance(exp, datetime):
        return exp.astimezone(UTC)
    if isinstance(exp, (int, float)):
        return datetime.fromtimestamp(exp, tz=UTC)
    raise HTTPException(status_code=401, detail="Token sem expiração válida.")


def is_revoked(db: Session, jti: str) -> bool:
    revoked = db.get(RevokedToken, jti)
    if not revoked:
        return False
    expires_at = revoked.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at > datetime.now(UTC)


def revoke_payload(db: Session, payload: dict) -> None:
    jti = payload.get("jti")
    if not jti or db.get(RevokedToken, jti):
        return
    db.add(RevokedToken(jti=jti, expires_at=_token_expiration(payload)))


def cleanup_expired_revocations(db: Session) -> None:
    db.execute(delete(RevokedToken).where(RevokedToken.expires_at <= datetime.now(UTC)))


def login(db: Session, identifier: str, password: str) -> dict:
    normalized = _normalize_identifier(identifier)
    credential = db.scalar(select(Credential).where(Credential.login == normalized))
    if not credential or not credential.active or not verify_password(password, credential.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas.")

    access_token = create_token(
        credential_id=credential.id,
        role=credential.role,
        reference_id=credential.reference_id,
        token_type="access",
    )
    refresh_token = create_token(
        credential_id=credential.id,
        role=credential.role,
        reference_id=credential.reference_id,
        token_type="refresh",
    )
    return {
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "tokenType": "bearer",
        "user": user_to_dict(db, credential, include_private=True),
    }


def refresh(db: Session, refresh_token: str) -> dict:
    payload = decode_token(refresh_token, expected_type="refresh")
    if is_revoked(db, payload["jti"]):
        raise HTTPException(status_code=401, detail="Refresh token revogado.")

    credential = db.get(Credential, int(payload["sub"]))
    if not credential or not credential.active:
        raise HTTPException(status_code=401, detail="Credencial inativa ou inexistente.")

    # Rotação: o refresh token anterior deixa de ser reutilizável.
    revoke_payload(db, payload)
    cleanup_expired_revocations(db)

    access_token = create_token(
        credential_id=credential.id,
        role=credential.role,
        reference_id=credential.reference_id,
        token_type="access",
    )
    new_refresh_token = create_token(
        credential_id=credential.id,
        role=credential.role,
        reference_id=credential.reference_id,
        token_type="refresh",
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()

    return {
        "accessToken": access_token,
        "refreshToken": new_refresh_token,
        "tokenType": "bearer",
        "user": user_to_dict(db, credential, include_private=True),
    }


def logout(db: Session, access_token: str, refresh_token: str | None = None) -> None:
    access_payload = decode_token(access_token, expected_type="access")
    revoke_payload(db, access_payload)
    if refresh_token:
        refresh_payload = decode_token(refresh_token, expected_type="refresh")
        if refresh_payload.get("sub") != access_payload.get("sub"):
            raise HTTPException(status_code=400, detail="Os tokens pertencem a usuários diferentes.")
        revoke_payload(db, refresh_payload)
    cleanup_expired_revocations(db)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
