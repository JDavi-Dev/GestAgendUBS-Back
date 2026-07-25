from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import Credential
from app.schemas.user import UserCreate
from app.services.users import create_user


def main() -> None:
    settings = get_settings()
    if not (
        settings.bootstrap_admin_name
        and settings.bootstrap_admin_email
        and settings.bootstrap_admin_password
    ):
        print("Administrador inicial não configurado; etapa ignorada.")
        return

    with SessionLocal() as db:
        login = settings.bootstrap_admin_email.lower()
        if db.scalar(select(Credential).where(Credential.login == login)):
            print("Administrador inicial já existe.")
            return
        create_user(
            db,
            UserCreate(
                role="admin",
                name=settings.bootstrap_admin_name,
                email=login,
                password=settings.bootstrap_admin_password,
                cpf=settings.bootstrap_admin_cpf or None,
                phone=settings.bootstrap_admin_phone or None,
                position="Administrador da UBS",
            ),
        )
        print(f"Administrador inicial criado: {login}")


if __name__ == "__main__":
    main()
