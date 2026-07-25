from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.credential import Credential, RevokedToken

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    credential_id: int
    role: str
    reference_id: int
    jti: str


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de autenticação obrigatório.")

    payload = decode_token(credentials.credentials, expected_type="access")
    jti = payload.get("jti")
    revoked = db.scalar(select(RevokedToken).where(RevokedToken.jti == jti))
    if revoked:
        expires_at = revoked.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at > datetime.now(UTC):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revogado.")

    try:
        credential_id = int(payload["sub"])
        reference_id = int(payload["reference_id"])
        role = str(payload["role"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.") from exc

    credential = db.get(Credential, credential_id)
    if not credential or not credential.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credencial inativa ou inexistente.")

    if credential.role != role or credential.reference_id != reference_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token não corresponde à credencial atual.")

    return CurrentUser(
        credential_id=credential.id,
        role=credential.role,
        reference_id=credential.reference_id,
        jti=jti,
    )


def require_roles(*allowed_roles: str):
    def dependency(current: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if current.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não possui permissão para executar esta operação.",
            )
        return current

    return dependency


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
AdminDep = Annotated[CurrentUser, Depends(require_roles("admin"))]
PatientDep = Annotated[CurrentUser, Depends(require_roles("patient"))]
ProfessionalDep = Annotated[CurrentUser, Depends(require_roles("professional"))]
