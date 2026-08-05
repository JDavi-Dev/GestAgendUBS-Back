# resources/ProfissionalResource
from flask import request, abort
from flask_restful import Resource, marshal

from sqlalchemy.exc import SQLAlchemyError

from helpers.database import db
from helpers.logging import logger, log_exception 
from helpers.auth import token_required, admin_required, get_jwt

from models.Credencial import Credencial
from models.Profissional import profissional_fields, Profissional

class ProfissionaisResouce(Resource):
    @token_required
    def get(self):
        logger.info(f"Get - Todos os Profissionais")

        try:
            tipo = get_jwt().get("tipo")
            if tipo not in ['paciente', 'administrador']:
                return {"mensagem": "Acesso negado."}, 403

            profissional = db.session.execute(db.select(Profissional)).scalars().all()

            logger.info(f"Profissionais retornados com sucesso")
            return marshal(profissional, profissional_fields), 200

        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao buscar Profissionais.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao buscar Profissionais")
            abort(500, description="Ocorreu um erro inesperado.")

    def post(self):
        logger.info("Post - Profissional")
        profissional_data = request.get_json()

        senha = profissional_data.pop('senha', None)
    
        if not senha or len(senha) < 8:
            return {"mensagem": "A senha deve ter no mínimo 8 caracteres."}, 400

        if '@' not in str(profissional_data.get('email', '')):
            return {"mensagem": "Informe um e-mail válido contendo '@'."}, 400

        try:
            novo_profissional = Profissional(**profissional_data)

            db.session.add(novo_profissional)
            db.session.flush()

            nova_credencial = Credencial(
                login=profissional_data['email'],
                senha=senha,
                tipo='profissional',
                referencia_id=novo_profissional.id
            )

            db.session.add(nova_credencial)
            db.session.commit()

            logger.info(f"Novo Profissional com id {novo_profissional.id} cadastrado com sucesso")
            return marshal(novo_profissional, profissional_fields), 201
        
        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao inserir novo profissional.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao inserir novo profissional")
            abort(500, description="Ocorreu um erro inesperado.")

class ProfissionalResource(Resource):
    @token_required
    def get(self, id):
        logger.info(f"Get - Profissional por id: {id}")

        try:
            profissional = db.session.execute(
                db.select(Profissional)
                .filter_by(id=id)
            ).scalar_one_or_none()

            if profissional is None:
                logger.warning(f"Profissional com id {id} não encontrado.")
                return {"mensagem": "Profissional não encontrado."}, 404

            logger.info(f"Profissional com id {id} retornado com sucesso")            
            return marshal(profissional, profissional_fields), 200

        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao buscar Profissional por id.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao buscar Profissional")
            abort(500, description="Ocorreu um erro inesperado.")

    @token_required
    @admin_required
    def put(self, id):
        logger.info(f"Put - Tentativa de atualizar Profissional com id: {id}")
        profissional_data = request.get_json()

        if 'email' in profissional_data and '@' not in str(profissional_data['email']):
            return {"mensagem": "Informe um e-mail válido contendo '@'."}, 400

        try:
            profissional = db.session.execute(
                db.select(Profissional)
                .filter_by(id=id)
            ).scalar_one_or_none()

            if profissional is None:
                logger.warning(f"Profissional com id {id} não encontrado para atualizar.")
                return {"mensagem": "Profissional não encontrado."}, 404

            for key, value in profissional_data.items():
                setattr(profissional, key, value)

            db.session.commit()

            logger.info(f"Profissional com id {id} atualizado com sucesso.")
            return {"mensagem": "Profissional atualizado com sucesso."}, 200
        
        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao atualizar Profissional.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception(f"Erro inesperado ao atualizar Profissional")
            abort(500, description="Ocorreu um erro inesperado.")

    @token_required
    @admin_required
    def delete(self, id):
        logger.info(f"Delete - Tentativa de deleção Profissional com id: {id}")

        try:
            profissional = db.session.execute(
                db.select(Profissional)
                .filter_by(id=id)
            ).scalar_one_or_none()

            if profissional is None:
                logger.warning(f"Profissional com id {id} não encontrado para deleção.")
                return {"mensagem": "Profissional não encontrado."}, 404
            
            # Deletar credencial associada
            credencial = db.session.execute(
                db.select(Credencial).filter_by(referencia_id=id, tipo='profissional')
            ).scalar_one_or_none()

            if credencial:
                db.session.delete(credencial)

            db.session.delete(profissional)
            db.session.commit()

            logger.info(f"Profissional com id {id} removido com sucesso.")
            return {"mensagem": "Profissional removido com sucesso."}, 200
        
        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao deletar Profissional.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao deletar Profissional")
            abort(500, description="Ocorreu um erro inesperado.")