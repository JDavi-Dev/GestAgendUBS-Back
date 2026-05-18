# resources/AdministradorResource

from flask import request, abort
from flask_restful import Resource, marshal

from sqlalchemy.exc import SQLAlchemyError

from helpers.database import db
from helpers.logging import logger, log_exception 

from models.Administrador import administrador_fields, Administrador

class AdministradoresResouce(Resource):
    def get(self):
        logger.info(f"Get - Todos os Administradores")

        try:
            administrador = db.session.execute(db.select(Administrador)).scalars().all()

            logger.info(f"Administradores retornados com sucesso")
            return marshal(administrador, administrador_fields), 200

        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao buscar Administradores.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao buscar Administradores")
            abort(500, description="Ocorreu um erro inesperado.")

    def post(self):
        logger.info("Post - Administrador")
        administrador_data = request.get_json()

        try:
            novo_administrador = Administrador(**administrador_data)

            db.session.add(novo_administrador)
            db.session.commit()

            logger.info(f"Novo Administrador com id {novo_administrador.id} cadastrado com sucesso")
            return marshal(novo_administrador, administrador_fields), 201
        
        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao inserir novo Administrador.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao inserir novo Administrador")
            abort(500, description="Ocorreu um erro inesperado.")

class AdministradorResource(Resource):
    def get(self, id):
        logger.info(f"Get - Administrador por id: {id}")

        try:
            administrador = db.session.execute(
                db.select(Administrador)
                .filter_by(id=id)
            ).scalar_one_or_none()

            if administrador is None:
                logger.warning(f"Administrador com id {id} não encontrado.")
                return {"mensagem": "Administrador não encontrado."}, 404

            logger.info(f"Administrador com id {id} retornado com sucesso")            
            return marshal(administrador, administrador_fields), 200

        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao buscar Administrador por id.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao buscar Administrador")
            abort(500, description="Ocorreu um erro inesperado.")

    def put(self, id):
        logger.info(f"Put - Tentativa de atualizar Administrador com id: {id}")
        administrador_data = request.get_json()

        try:
            administrador = db.session.execute(
                db.select(Administrador)
                .filter_by(id=id)
            ).scalar_one_or_none()

            if administrador is None:
                logger.warning(f"Administrador com id {id} não encontrado para atualizar.")
                return {"mensagem": "Administrador não encontrado."}, 404

            for key, value in administrador_data.items():
                setattr(administrador, key, value)

            db.session.commit()

            logger.info(f"Administrador com id {id} atualizado com sucesso.")
            return {"mensagem": "Administrador atualizado com sucesso."}, 200
        
        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao atualizar Administrador.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception(f"Erro inesperado ao atualizar Administrador")
            abort(500, description="Ocorreu um erro inesperado.")