# pode se cadastrar = CRUD

from flask import request, abort
from flask_restful import Resource, marshal

from sqlalchemy.exc import SQLAlchemyError

from helpers.database import db
from helpers.logging import logger, log_exception 

from models.Paciente import paciente_fields, Paciente

class PacientesResouce(Resource):
    def get(self):
        logger.info(f"Get - Todos os Pacientes")

        try:
            paciente = db.session.execute(db.select(Paciente)).scalars().all()

            logger.info(f"Pacientes retornados com sucesso")
            return marshal(paciente, paciente_fields), 200

        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao buscar Pacientes.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao buscar Pacientes")
            abort(500, description="Ocorreu um erro inesperado.")

    def post(self):
        logger.info("Post - Paciente")
        paciente_data = request.get_json()

        try:
            novo_paciente = Paciente(**paciente_data)

            db.session.add(novo_paciente)
            db.session.commit()

            logger.info(f"Novo Paciente com id {novo_paciente.id} cadastrado com sucesso")
            return marshal(novo_paciente, paciente_fields), 201
        
        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao inserir novo Paciente.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao inserir novo Paciente")
            abort(500, description="Ocorreu um erro inesperado.")

class PacienteResource(Resource):
    def get(self, id):
        logger.info(f"Get - Paciente por id: {id}")

        try:
            paciente = db.session.execute(
                db.select(Paciente)
                .filter_by(id=id)
            ).scalar_one_or_none()

            if paciente is None:
                logger.warning(f"Paciente com id {id} não encontrado.")
                return {"mensagem": "Paciente não encontrado."}, 404

            logger.info(f"Paciente com id {id} retornado com sucesso")            
            return marshal(paciente, paciente_fields), 200

        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao buscar paciente por id.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao buscar paciente")
            abort(500, description="Ocorreu um erro inesperado.")

    def put(self, id):
        logger.info(f"Put - Tentativa de atualizar Paciente com id: {id}")
        paciente_data = request.get_json()

        try:
            paciente = db.session.execute(
                db.select(Paciente)
                .filter_by(id=id)
            ).scalar_one_or_none()

            if paciente is None:
                logger.warning(f"Paciente com id {id} não encontrado para atualizar.")
                return {"mensagem": "Paciente não encontrado."}, 404

            for key, value in paciente_data.items():
                setattr(paciente, key, value)

            db.session.commit()

            logger.info(f"Paciente com id {id} atualizado com sucesso.")
            return {"mensagem": "Paciente atualizado com sucesso."}, 200
        
        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao atualizar Paciente.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception(f"Erro inesperado ao atualizar Paciente")
            abort(500, description="Ocorreu um erro inesperado.")

    def delete(self, id):
        logger.info(f"Delete - Tentativa de deleção Paciente com id: {id}")

        try:
            paciente = db.session.execute(
                db.select(Paciente)
                .filter_by(id=id)
            ).scalar_one_or_none()

            if paciente is None:
                logger.warning(f"Paciente com id {id} não encontrado para deleção.")
                return {"mensagem": "Paciente não encontrado."}, 404
            
            db.session.delete(paciente)
            db.session.commit()

            logger.info(f"Paciente com id {id} removido com sucesso.")
            return {"mensagem": "Paciente removido com sucesso."}, 200
        
        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao deletar Paciente.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao deletar Paciente")
            abort(500, description="Ocorreu um erro inesperado.")