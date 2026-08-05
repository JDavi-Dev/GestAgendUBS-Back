import os
import sys
from pathlib import Path

import pytest

# Garante que a raiz do backend esteja disponível para imports como
# "helpers" e "models", mesmo quando o pytest é iniciado fora da raiz.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
os.environ.setdefault('JWT_SECRET_KEY', 'teste-local')

from helpers.application import app
from helpers.database import db
import models  # noqa: F401 - registra os models no metadata


@pytest.fixture(autouse=True)
def banco_limpo():
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    with app.app_context():
        db.create_all()
        yield db.session
        db.session.remove()
        db.drop_all()
