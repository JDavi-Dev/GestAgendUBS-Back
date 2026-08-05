# resources/HorarioResource.py

from datetime import date, time

from flask import request, abort
from flask_restful import Resource, marshal
from sqlalchemy.exc import SQLAlchemyError

from helpers.database import db
from helpers.logging import logger, log_exception
from helpers.auth import token_required, admin_required, profissional_required, get_current_referencia_id
from helpers.regras_negocio import existe_conflito_horario

from models.Horario import horario_fields, Horario
from models.Profissional import Profissional


def _normalizar_horario(dados):
    normalizado = dados.copy()
    if isinstance(normalizado.get('data'), str):
        normalizado['data'] = date.fromisoformat(normalizado['data'])
    if isinstance(normalizado.get('hora_inicio'), str):
        normalizado['hora_inicio'] = time.fromisoformat(normalizado['hora_inicio'])
    if isinstance(normalizado.get('hora_fim'), str):
        normalizado['hora_fim'] = time.fromisoformat(normalizado['hora_fim'])
    return normalizado


class HorariosResource(Resource):
    @token_required
    def get(self):
        logger.info("Get - Todos os Horários")

        profissional_id = request.args.get('profissional_id', type=int)
        data_filtro = request.args.get('data')
        apenas_disponiveis = request.args.get('apenas_disponiveis', 'false').lower() == 'true'

        try:
            query = db.select(Horario)
            if profissional_id:
                query = query.filter_by(profissional_id=profissional_id)
            if data_filtro:
                query = query.filter_by(data=data_filtro)
            if apenas_disponiveis:
                query = query.filter_by(disponivel=True)

            horarios = db.session.execute(query).scalars().all()
            return marshal(horarios, horario_fields), 200

        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao buscar Horários.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao buscar Horários")
            abort(500, description="Ocorreu um erro inesperado.")

    @admin_required
    def post(self):
        logger.info("Post - Horário")

        try:
            horario_data = _normalizar_horario(request.get_json() or {})
            profissional = db.session.get(Profissional, horario_data['profissional_id'])
            if not profissional:
                return {"mensagem": "Profissional não encontrado."}, 404

            if horario_data['data'] < date.today():
                return {"mensagem": "Não é possível cadastrar horário em uma data anterior à atual."}, 400

            if horario_data['hora_fim'] <= horario_data['hora_inicio']:
                return {"mensagem": "O horário final deve ser posterior ao horário inicial."}, 400

            if existe_conflito_horario(
                db.session,
                horario_data['profissional_id'],
                horario_data['data'],
                horario_data['hora_inicio'],
                horario_data['hora_fim'],
            ):
                return {"mensagem": "Já existe horário conflitante para este profissional nesta data/horário."}, 409

            novo_horario = Horario(**horario_data)
            db.session.add(novo_horario)
            db.session.commit()
            return marshal(novo_horario, horario_fields), 201

        except (KeyError, TypeError, ValueError):
            db.session.rollback()
            return {"mensagem": "Dados do horário inválidos ou incompletos."}, 400
        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao inserir novo Horário.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao inserir novo Horário")
            db.session.rollback()
            abort(500, description="Ocorreu um erro inesperado.")


class HorarioResource(Resource):
    @token_required
    def get(self, id):
        try:
            horario = db.session.get(Horario, id)
            if horario is None:
                return {"mensagem": "Horário não encontrado."}, 404
            return marshal(horario, horario_fields), 200
        except SQLAlchemyError:
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            abort(500, description="Ocorreu um erro inesperado.")

    @profissional_required
    def put(self, id):
        logger.info(f"Put - Atualizar Horário com id: {id}")
        referencia_id = get_current_referencia_id()

        try:
            horario_data = _normalizar_horario(request.get_json() or {})
            horario = db.session.get(Horario, id)
            if horario is None:
                return {"mensagem": "Horário não encontrado."}, 404
            if horario.profissional_id != referencia_id:
                return {"mensagem": "Você só pode modificar seus próprios horários."}, 403

            from models.Agendamento import Agendamento
            if not horario_data.get('disponivel', True) and horario.disponivel:
                tem_agendamento = db.session.execute(
                    db.select(Agendamento).where(
                        Agendamento.horario_id == id,
                        Agendamento.status.in_(['agendado', 'confirmado'])
                    )
                ).scalar_one_or_none()
                if tem_agendamento:
                    return {"mensagem": "Não é possível indisponibilizar horário com agendamento ativo."}, 409

            data_final = horario_data.get('data', horario.data)
            inicio_final = horario_data.get('hora_inicio', horario.hora_inicio)
            fim_final = horario_data.get('hora_fim', horario.hora_fim)
            if fim_final <= inicio_final:
                return {"mensagem": "O horário final deve ser posterior ao horário inicial."}, 400

            if existe_conflito_horario(
                db.session,
                horario.profissional_id,
                data_final,
                inicio_final,
                fim_final,
                ignorar_id=id,
            ):
                return {"mensagem": "Já existe horário conflitante para este profissional nesta data/horário."}, 409

            for key, value in horario_data.items():
                setattr(horario, key, value)

            db.session.commit()
            return marshal(horario, horario_fields), 200

        except (TypeError, ValueError):
            db.session.rollback()
            return {"mensagem": "Dados do horário inválidos."}, 400
        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao atualizar Horário.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao atualizar Horário")
            db.session.rollback()
            abort(500, description="Ocorreu um erro inesperado.")

    @token_required
    @admin_required
    def delete(self, id):
        try:
            horario = db.session.get(Horario, id)
            if horario is None:
                return {"mensagem": "Horário não encontrado."}, 404

            from models.Agendamento import Agendamento
            tem_agendamento = db.session.execute(
                db.select(Agendamento).filter_by(horario_id=id)
            ).scalar_one_or_none()
            if tem_agendamento:
                return {"mensagem": "Não é possível deletar horário com agendamentos associados."}, 409

            db.session.delete(horario)
            db.session.commit()
            return {"mensagem": "Horário removido com sucesso."}, 200

        except SQLAlchemyError:
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            abort(500, description="Ocorreu um erro inesperado.")
