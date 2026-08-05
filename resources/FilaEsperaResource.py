# resources/FilaEsperaResource.py

from datetime import datetime

from flask import request, abort
from flask_restful import Resource, marshal
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, func, or_

from helpers.database import db
from helpers.logging import logger, log_exception
from helpers.auth import token_required, paciente_required, admin_required, get_current_referencia_id, get_jwt
from helpers.regras_negocio import paciente_tem_conflito

from models.FilaEspera import fila_espera_fields, FilaEspera
from models.Paciente import Paciente
from models.Profissional import Profissional
from models.Agendamento import Agendamento
from models.Horario import Horario


def _condicao_posicao(item):
    return or_(
        FilaEspera.prioridade < item.prioridade,
        and_(FilaEspera.prioridade == item.prioridade, FilaEspera.id < item.id),
    )


class FilaEsperaResource(Resource):
    @token_required
    def get(self):
        logger.info("GET - Fila de Espera")

        tipo = get_jwt().get("tipo")
        referencia_id = get_current_referencia_id()
        especialidade = request.args.get('especialidade')
        status = request.args.get('status')
        if status is None and tipo != 'paciente':
            status = 'aguardando'

        try:
            query = db.select(FilaEspera)

            if tipo == 'paciente':
                query = query.filter_by(paciente_id=referencia_id)
            elif tipo == 'profissional':
                profissional = db.session.get(Profissional, referencia_id)
                if not profissional or not profissional.especialidade:
                    return {"mensagem": "Profissional sem especialidade definida."}, 400
                query = query.filter_by(especialidade=profissional.especialidade)

            if especialidade:
                query = query.filter_by(especialidade=especialidade)
            if status:
                query = query.filter_by(status=status)

            query = query.order_by(FilaEspera.prioridade.asc(), FilaEspera.data_solicitacao.asc())
            fila = db.session.execute(query).scalars().all()

            resultado = []
            posicoes = {}
            for item in fila:
                paciente = db.session.get(Paciente, item.paciente_id)
                item_data = marshal(item, fila_espera_fields)
                item_data['paciente_nome'] = paciente.nome if paciente else 'Paciente não encontrado'
                if tipo != 'paciente' and item.status == 'aguardando':
                    posicoes[item.especialidade] = posicoes.get(item.especialidade, 0) + 1
                    item_data['posicao'] = posicoes[item.especialidade]
                else:
                    item_data['posicao'] = None
                item_data['prioridade_label'] = FilaEspera.get_prioridade_label(item.prioridade)
                resultado.append(item_data)

            return resultado, 200

        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao buscar Fila de Espera.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao buscar Fila de Espera")
            abort(500, description="Ocorreu um erro inesperado.")

    @paciente_required
    def post(self):
        logger.info("POST - Entrar na Fila de Espera")

        dados = request.get_json() or {}
        especialidade = str(dados.get('especialidade', '')).strip()
        paciente_id = get_current_referencia_id()
        if not especialidade:
            return {"mensagem": "Especialidade é obrigatória."}, 400

        try:
            paciente = db.session.get(Paciente, paciente_id)
            if not paciente:
                return {"mensagem": "Paciente não encontrado."}, 404

            existente = db.session.execute(
                db.select(FilaEspera).where(
                    FilaEspera.paciente_id == paciente_id,
                    FilaEspera.especialidade == especialidade,
                    FilaEspera.status == 'aguardando',
                )
            ).scalar_one_or_none()
            if existente:
                return {"mensagem": "Paciente já está na fila de espera para esta especialidade."}, 409

            agora = datetime.now()
            agendamento_ativo = db.session.execute(
                db.select(Agendamento.id)
                .join(Horario, Horario.id == Agendamento.horario_id)
                .join(Profissional, Profissional.id == Horario.profissional_id)
                .where(
                    Agendamento.paciente_id == paciente_id,
                    Agendamento.status.in_(['agendado', 'confirmado']),
                    Profissional.especialidade == especialidade,
                    or_(
                        Horario.data > agora.date(),
                        and_(Horario.data == agora.date(), Horario.hora_fim > agora.time()),
                    ),
                )
                .limit(1)
            ).scalar_one_or_none()
            if agendamento_ativo is not None:
                return {"mensagem": "Você já possui um agendamento ativo para esta especialidade."}, 409

            horario_livre = db.session.execute(
                db.select(Horario.id)
                .join(Profissional, Profissional.id == Horario.profissional_id)
                .where(
                    Horario.disponivel.is_(True),
                    Profissional.ativo.is_(True),
                    Profissional.especialidade == especialidade,
                    or_(
                        Horario.data > agora.date(),
                        and_(Horario.data == agora.date(), Horario.hora_inicio > agora.time()),
                    ),
                )
                .limit(1)
            ).scalar_one_or_none()
            if horario_livre is not None:
                return {"mensagem": "Há horário disponível para esta especialidade. Faça o agendamento antes de entrar na fila."}, 409

            prioridade = FilaEspera.calcular_prioridade(paciente)
            nova_fila = FilaEspera(
                paciente_id=paciente_id,
                especialidade=especialidade,
                prioridade=prioridade,
            )
            db.session.add(nova_fila)
            db.session.commit()

            posicao = db.session.execute(
                db.select(func.count(FilaEspera.id)).where(
                    FilaEspera.especialidade == especialidade,
                    FilaEspera.status == 'aguardando',
                    or_(FilaEspera.id == nova_fila.id, _condicao_posicao(nova_fila)),
                )
            ).scalar()

            return {
                "mensagem": "Paciente adicionado à fila de espera com sucesso.",
                "fila": {
                    "id": nova_fila.id,
                    "posicao": posicao,
                    "prioridade": prioridade,
                    "prioridade_label": FilaEspera.get_prioridade_label(prioridade),
                    "especialidade": especialidade,
                    "status": nova_fila.status,
                },
            }, 201

        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao inserir na Fila de Espera.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao inserir na Fila de Espera")
            db.session.rollback()
            abort(500, description="Ocorreu um erro inesperado.")


class FilaEsperaItemResource(Resource):
    @token_required
    @admin_required
    def put(self, id):
        dados = request.get_json() or {}

        try:
            fila_item = db.session.execute(
                db.select(FilaEspera).where(FilaEspera.id == id).with_for_update()
            ).scalar_one_or_none()
            if not fila_item:
                return {"mensagem": "Item da fila não encontrado."}, 404
            if fila_item.status != 'aguardando':
                return {"mensagem": f"Item da fila já está {fila_item.status}."}, 409

            if dados.get('status') == 'recusado':
                mensagem = str(dados.get('mensagem_status', '')).strip()
                fila_item.status = 'recusado'
                fila_item.mensagem_status = mensagem or None
                db.session.commit()
                return {"mensagem": "Solicitação recusada e paciente notificado."}, 200

            horario_id = dados.get('horario_id')
            if not horario_id:
                return {"mensagem": "Horário é obrigatório para alocação."}, 400

            horario = db.session.execute(
                db.select(Horario).where(Horario.id == horario_id).with_for_update()
            ).scalar_one_or_none()
            if not horario:
                return {"mensagem": "Horário não encontrado."}, 404
            if not horario.disponivel:
                return {"mensagem": "Horário não está disponível."}, 409

            profissional = db.session.get(Profissional, horario.profissional_id)
            if not profissional or profissional.especialidade != fila_item.especialidade:
                return {"mensagem": f"Horário não corresponde à especialidade {fila_item.especialidade}."}, 409

            if paciente_tem_conflito(db.session, fila_item.paciente_id, horario):
                return {"mensagem": "Paciente já possui agendamento neste horário."}, 409

            novo_agendamento = Agendamento(
                paciente_id=fila_item.paciente_id,
                horario_id=horario_id,
                status='agendado',
            )
            horario.disponivel = False
            fila_item.status = 'alocado'
            fila_item.mensagem_status = 'Sua solicitação foi alocada em um horário disponível.'

            db.session.add(novo_agendamento)
            db.session.commit()

            return {
                "mensagem": "Paciente alocado com sucesso.",
                "agendamento_id": novo_agendamento.id,
                "paciente_id": fila_item.paciente_id,
                "horario_id": horario_id,
            }, 200

        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao atualizar item da fila.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao atualizar item da fila")
            db.session.rollback()
            abort(500, description="Ocorreu um erro inesperado.")

    @token_required
    @admin_required
    def delete(self, id):
        """Mantido para compatibilidade: exclui apenas solicitações aguardando."""
        try:
            fila_item = db.session.get(FilaEspera, id)
            if not fila_item:
                return {"mensagem": "Item da fila não encontrado."}, 404
            if fila_item.status != 'aguardando':
                return {"mensagem": f"Não é possível remover item com status '{fila_item.status}'."}, 409

            db.session.delete(fila_item)
            db.session.commit()
            return {"mensagem": "Item removido da fila com sucesso."}, 200

        except SQLAlchemyError:
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            abort(500, description="Ocorreu um erro inesperado.")


class FilaEsperaPosicaoResource(Resource):
    @token_required
    def get(self):
        paciente_id = get_current_referencia_id()
        especialidade = request.args.get('especialidade')
        if not especialidade:
            return {"mensagem": "Especialidade é obrigatória."}, 400

        try:
            fila_item = db.session.execute(
                db.select(FilaEspera).where(
                    FilaEspera.paciente_id == paciente_id,
                    FilaEspera.especialidade == especialidade,
                    FilaEspera.status == 'aguardando',
                )
            ).scalar_one_or_none()

            if not fila_item:
                return {
                    "mensagem": "Paciente não está na fila de espera para esta especialidade.",
                    "na_fila": False,
                }, 200

            posicao = db.session.execute(
                db.select(func.count(FilaEspera.id)).where(
                    FilaEspera.especialidade == especialidade,
                    FilaEspera.status == 'aguardando',
                    _condicao_posicao(fila_item),
                )
            ).scalar() + 1

            total = db.session.execute(
                db.select(func.count(FilaEspera.id)).where(
                    FilaEspera.especialidade == especialidade,
                    FilaEspera.status == 'aguardando',
                )
            ).scalar()

            return {
                "na_fila": True,
                "posicao": posicao,
                "total": total,
                "prioridade": fila_item.prioridade,
                "prioridade_label": FilaEspera.get_prioridade_label(fila_item.prioridade),
                "especialidade": especialidade,
                "data_solicitacao": fila_item.data_solicitacao.isoformat(),
            }, 200

        except SQLAlchemyError:
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            abort(500, description="Ocorreu um erro inesperado.")
