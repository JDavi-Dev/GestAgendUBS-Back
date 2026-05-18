# resources/HorarioResource.py

from flask import request, abort
from flask_restful import Resource, marshal
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_

from helpers.database import db
from helpers.logging import logger, log_exception 

from models.Horario import horario_fields, Horario
from models.Profissional import Profissional

class HorariosResource(Resource):
    def get(self):
        """Listar horários com filtros opcionais"""
        logger.info("Get - Todos os Horários")
        
        profissional_id = request.args.get('profissional_id', type=int)
        data = request.args.get('data')
        apenas_disponiveis = request.args.get('apenas_disponiveis', 'false').lower() == 'true'

        try:
            query = db.select(Horario)
            
            if profissional_id:
                query = query.filter_by(profissional_id=profissional_id)
            if data:
                query = query.filter_by(data=data)
            if apenas_disponiveis:
                query = query.filter_by(disponivel=True)
            
            horarios = db.session.execute(query).scalars().all()
            
            logger.info(f"Horários retornados com sucesso")
            return marshal(horarios, horario_fields), 200

        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao buscar Horários.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao buscar Horários")
            abort(500, description="Ocorreu um erro inesperado.")

    def post(self):
        """Criar horário disponível (apenas admin)"""
        logger.info("Post - Horário")
        horario_data = request.get_json()

        try:
            # Verificar se profissional existe
            profissional = db.session.execute(
                db.select(Profissional).filter_by(id=horario_data['profissional_id'])
            ).scalar_one_or_none()
            
            if not profissional:
                return {"mensagem": "Profissional não encontrado."}, 404
            
            # Verificar conflito de horário
            conflito = db.session.execute(
                db.select(Horario).where(
                    and_(
                        Horario.profissional_id == horario_data['profissional_id'],
                        Horario.data == horario_data['data'],
                        Horario.hora_inicio < horario_data['hora_fim'],
                        Horario.hora_fim > horario_data['hora_inicio']
                    )
                )
            ).scalar_one_or_none()
            
            if conflito:
                return {"mensagem": "Já existe horário conflitante para este profissional nesta data/horário."}, 409

            novo_horario = Horario(**horario_data)
            db.session.add(novo_horario)
            db.session.commit()

            logger.info(f"Novo Horário com id {novo_horario.id} cadastrado com sucesso")
            return marshal(novo_horario, horario_fields), 201
        
        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao inserir novo Horário.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao inserir novo Horário")
            abort(500, description="Ocorreu um erro inesperado.")

class HorarioResource(Resource):
    def get(self, id):
        logger.info(f"Get - Horário por id: {id}")

        try:
            horario = db.session.execute(
                db.select(Horario).filter_by(id=id)
            ).scalar_one_or_none()

            if horario is None:
                logger.warning(f"Horário com id {id} não encontrado.")
                return {"mensagem": "Horário não encontrado."}, 404

            return marshal(horario, horario_fields), 200

        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao buscar Horário por id.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao buscar Horário")
            abort(500, description="Ocorreu um erro inesperado.")

    def put(self, id):
        logger.info(f"Put - Atualizar Horário com id: {id}")
        horario_data = request.get_json()

        try:
            horario = db.session.execute(
                db.select(Horario).filter_by(id=id)
            ).scalar_one_or_none()

            if horario is None:
                logger.warning(f"Horário com id {id} não encontrado.")
                return {"mensagem": "Horário não encontrado."}, 404

            # Se estiver marcando como indisponível, verificar se não tem agendamento
            if not horario_data.get('disponivel', True) and horario.disponivel:
                from models.Agendamento import Agendamento
                tem_agendamento = db.session.execute(
                    db.select(Agendamento).filter_by(horario_id=id, status='agendado')
                ).scalar_one_or_none()
                
                if tem_agendamento:
                    return {"mensagem": "Não é possível indisponibilizar horário com agendamento ativo."}, 409

            for key, value in horario_data.items():
                setattr(horario, key, value)

            db.session.commit()
            logger.info(f"Horário com id {id} atualizado com sucesso.")
            return marshal(horario, horario_fields), 200
        
        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao atualizar Horário.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao atualizar Horário")
            abort(500, description="Ocorreu um erro inesperado.")

    def delete(self, id):
        logger.info(f"Delete - Remover Horário com id: {id}")

        try:
            horario = db.session.execute(
                db.select(Horario).filter_by(id=id)
            ).scalar_one_or_none()

            if horario is None:
                logger.warning(f"Horário com id {id} não encontrado.")
                return {"mensagem": "Horário não encontrado."}, 404
            
            # Verificar se tem agendamento ativo
            from models.Agendamento import Agendamento
            tem_agendamento = db.session.execute(
                db.select(Agendamento).filter_by(horario_id=id)
            ).scalar_one_or_none()
            
            if tem_agendamento:
                return {"mensagem": "Não é possível deletar horário com agendamentos associados."}, 409
            
            db.session.delete(horario)
            db.session.commit()

            logger.info(f"Horário com id {id} removido com sucesso.")
            return {"mensagem": "Horário removido com sucesso."}, 200
        
        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao deletar Horário.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao deletar Horário")
            abort(500, description="Ocorreu um erro inesperado.")