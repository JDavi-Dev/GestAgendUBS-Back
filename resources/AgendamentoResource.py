# resources/AgendamentoResource.py

from flask import request, abort
from flask_restful import Resource, marshal

from sqlalchemy.exc import SQLAlchemyError

from helpers.database import db
from helpers.logging import logger, log_exception 
from helpers.auth import token_required, paciente_required, get_jwt, admin_required, get_current_referencia_id
from helpers.regras_negocio import cancelamento_permitido, paciente_tem_conflito

from models.Agendamento import agendamento_fields, Agendamento
from models.Horario import Horario
from models.Paciente import Paciente

class AgendamentosResource(Resource):

    @token_required
    def get(self):
        """Listar agendamentos com filtro baseados no tipo de usuário"""
        logger.info("Get - Todos os Agendamentos")
        
        paciente_id = request.args.get('paciente_id', type=int)
        profissional_id = request.args.get('profissional_id', type=int)
        status = request.args.get('status')

        try:
            tipo = get_jwt().get("tipo")
            referencia_id = get_current_referencia_id()

            query = db.select(Agendamento)

            if tipo == 'paciente':
                query = query.filter_by(paciente_id=referencia_id)
            elif tipo == 'profissional':
                query = query.join(Horario).filter(Horario.profissional_id == referencia_id)
            
            if paciente_id:
                query = query.filter_by(paciente_id=paciente_id)
            if profissional_id:
                query = query.join(Horario).filter(Horario.profissional_id == profissional_id)
            if status:
                query = query.filter_by(status=status)
            
            agendamentos = db.session.execute(query).scalars().all()
            
            logger.info(f"Agendamentos retornados com sucesso")
            return marshal(agendamentos, agendamento_fields), 200

        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao buscar Agendamentos.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao buscar Agendamentos")
            abort(500, description="Ocorreu um erro inesperado.")

    @paciente_required # Apenas paciente pode criar agendamentos
    def post(self):
        """Criar novo agendamento"""
        logger.info("Post - Agendamento")
        agendamento_data = request.get_json() or {}
        paciente_id = get_current_referencia_id()

        if agendamento_data.get('paciente_id') not in (None, paciente_id):
            return {"mensagem": "Você só pode criar agendamentos para o próprio cadastro."}, 403

        try:
            # Verificar se horário existe e está disponível
            horario = db.session.execute(
                db.select(Horario).filter_by(id=agendamento_data['horario_id']).with_for_update()
            ).scalar_one_or_none()
            
            if not horario:
                return {"mensagem": "Horário não encontrado."}, 404
            
            if not horario.disponivel:
                return {"mensagem": "Horário já está ocupado."}, 409
            
            # Verificar se paciente existe
            paciente = db.session.execute(
                db.select(Paciente).filter_by(id=paciente_id)
            ).scalar_one_or_none()
            
            if not paciente:
                return {"mensagem": "Paciente não encontrado."}, 404
            
            # Verificar se paciente já tem agendamento no mesmo horário
            if paciente_tem_conflito(db.session, paciente_id, horario):
                return {"mensagem": "Paciente já possui agendamento neste horário."}, 409
            
            # Criar agendamento
            novo_agendamento = Agendamento(
                paciente_id=paciente_id,
                horario_id=agendamento_data['horario_id'],
                status="agendado",
                motivo_cancelamento=None
            )
            
            # Marcar horário como indisponível
            horario.disponivel = False
            
            db.session.add(novo_agendamento)
            db.session.commit()

            logger.info(f"Novo Agendamento com id {novo_agendamento.id} criado com sucesso")
            return marshal(novo_agendamento, agendamento_fields), 201
        
        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao inserir novo Agendamento.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao inserir novo Agendamento")
            abort(500, description="Ocorreu um erro inesperado.")

class AgendamentoResource(Resource):
    @token_required
    def get(self, id):
        logger.info(f"Get - Agendamento por id: {id}")

        try:
            agendamento = db.session.execute(
                db.select(Agendamento).filter_by(id=id)
            ).scalar_one_or_none()

            if agendamento is None:
                logger.warning(f"Agendamento com id {id} não encontrado.")
                return {"mensagem": "Agendamento não encontrado."}, 404

            return marshal(agendamento, agendamento_fields), 200

        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao buscar Agendamento por id.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao buscar Agendamento")
            abort(500, description="Ocorreu um erro inesperado.")

    @token_required
    def put(self, id):
        logger.info(f"Put - Atualizar Agendamento com id: {id}")
        agendamento_data = request.get_json()

        tipo = get_jwt().get("tipo")
        referencia_id = get_current_referencia_id()

        try:
            agendamento = db.session.execute(
                db.select(Agendamento).filter_by(id=id)
            ).scalar_one_or_none()

            if agendamento is None:
                logger.warning(f"Agendamento com id {id} não encontrado.")
                return {"mensagem": "Agendamento não encontrado."}, 404

            # Verificar permissão
            if tipo == 'paciente':
                # Paciente só pode cancelar seus próprios agendamentos
                if agendamento.paciente_id != referencia_id:
                    return {"mensagem": "Você só pode cancelar seus próprios agendamentos."}, 403
            elif tipo == 'profissional':
                # Profissional só pode modificar agendamentos dos seus horários
                horario = db.session.get(Horario, agendamento.horario_id)
                if horario.profissional_id != referencia_id:
                    return {"mensagem": "Permissão negada."}, 403

            # Regra de cancelamento com antecedência mínima
            if 'status' in agendamento_data and agendamento_data['status'] == 'cancelado':
                horario = db.session.execute(
                    db.select(Horario).filter_by(id=agendamento.horario_id)
                ).scalar_one()
                
                if not cancelamento_permitido(horario.data, horario.hora_inicio):
                    return {"mensagem": "Cancelamento só permitido com 24 horas de antecedência."}, 409
                
                # Liberar horário novamente
                horario.disponivel = True
            
            for key, value in agendamento_data.items():
                setattr(agendamento, key, value)

            db.session.commit()
            logger.info(f"Agendamento com id {id} atualizado com sucesso.")
            return marshal(agendamento, agendamento_fields), 200
        
        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao atualizar Agendamento.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao atualizar Agendamento")
            abort(500, description="Ocorreu um erro inesperado.")

    @token_required
    @admin_required
    def delete(self, id):
        logger.info(f"Delete - Remover Agendamento com id: {id}")

        try:
            agendamento = db.session.execute(
                db.select(Agendamento).filter_by(id=id)
            ).scalar_one_or_none()

            if agendamento is None:
                logger.warning(f"Agendamento com id {id} não encontrado.")
                return {"mensagem": "Agendamento não encontrado."}, 404
            
            # Verificar se pode deletar (apenas se status for cancelado ou realizado)
            if agendamento.status in ['agendado', 'confirmado']:
                return {"mensagem": "Não é possível deletar agendamento ativo. Utilize cancelamento."}, 409
            
            db.session.delete(agendamento)
            db.session.commit()

            logger.info(f"Agendamento com id {id} removido com sucesso.")
            return {"mensagem": "Agendamento removido com sucesso."}, 200
        
        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao deletar Agendamento.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao deletar Agendamento")
            abort(500, description="Ocorreu um erro inesperado.")