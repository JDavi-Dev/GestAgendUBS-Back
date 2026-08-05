from os import getenv
from dotenv import load_dotenv

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

from helpers.application import app

from flask_migrate import Migrate
from flask_bcrypt import Bcrypt

load_dotenv()

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app.config["SQLALCHEMY_DATABASE_URI"] = getenv("SQLALCHEMY_DATABASE_URI")
db.init_app(app)

bcrypt = Bcrypt()
migrate = Migrate(app, db)