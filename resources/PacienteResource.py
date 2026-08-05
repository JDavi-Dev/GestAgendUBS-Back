# pode se cadastrar = CRUD

from flask import request, abort
from flask_restful import Resource, marshal

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from helpers.database import db
from helpers.logging import logger, log_exception
from helpers.auth import token_required, paciente_required, admin_required, get_current_referencia_id, get_jwt

from models.Credencial import Credencial
from models.Paciente import paciente_fields, Paciente
from models.Agendamento import Agendamento
from models.Horario import Horario


def _validar_cadastro(dados, senha):
    email = str(dados.get('email', '')).strip()
    if '@' not in email:
        return {"mensagem": "Informe um e-mail válido contendo '@'."}, 400
    if not senha or len(senha) < 8:
        return {"mensagem": "A senha deve ter no mínimo 8 caracteres."}, 400
    return None


def _booleano(valor):
    if isinstance(valor, bool):
        return valor
    return str(valor).strip().lower() in {'true', '1', 'sim'}


def _mensagem_integridade(error):
    texto = str(getattr(error, 'orig', error)).lower()
    if 'tb_paciente_cpf_key' in texto or ('cpf' in texto and 'unique' in texto):
        return "Já existe um paciente cadastrado com este CPF."
    if 'tb_paciente_telefone_key' in texto or ('telefone' in texto and 'unique' in texto):
        return "Já existe um paciente cadastrado com este telefone."
    if 'tb_paciente_email_key' in texto or ('email' in texto and 'unique' in texto):
        return "Já existe um paciente cadastrado com este e-mail."
    return "Não foi possível concluir o cadastro porque um dado informado já está em uso."


class PacientesResouce(Resource):
    @token_required
    def get(self):
        logger.info("Get - Todos os Pacientes")

        tipo = get_jwt().get("tipo")
        referencia_id = get_current_referencia_id()

        try:
            query = db.select(Paciente)

            if tipo == 'paciente':
                query = query.filter_by(id=referencia_id)
            elif tipo == 'profissional':
                query = (
                    query.join(Agendamento, Agendamento.paciente_id == Paciente.id)
                    .join(Horario, Horario.id == Agendamento.horario_id)
                    .where(Horario.profissional_id == referencia_id)
                    .distinct()
                )

            pacientes = db.session.execute(query).scalars().all()
            logger.info("Pacientes retornados com sucesso")
            return marshal(pacientes, paciente_fields), 200

        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao buscar Pacientes.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao buscar Pacientes")
            abort(500, description="Ocorreu um erro inesperado.")

    def post(self):
        logger.info("Post - Paciente")
        paciente_data = (request.get_json() or {}).copy()
        senha = paciente_data.pop('senha', None)

        erro = _validar_cadastro(paciente_data, senha)
        if erro:
            return erro

        paciente_data['email'] = paciente_data['email'].strip().lower()
        paciente_data['gestante'] = _booleano(paciente_data.get('gestante', False))
        paciente_data['possui_deficiencia'] = _booleano(paciente_data.get('possui_deficiencia', False))

        try:
            duplicado = db.session.execute(
                db.select(Paciente).where(
                    (Paciente.cpf == paciente_data.get('cpf'))
                    | (Paciente.telefone == paciente_data.get('telefone'))
                    | (Paciente.email == paciente_data.get('email'))
                )
            ).scalars().first()
            if duplicado:
                if duplicado.cpf == paciente_data.get('cpf'):
                    return {"mensagem": "Já existe um paciente cadastrado com este CPF."}, 409
                if duplicado.telefone == paciente_data.get('telefone'):
                    return {"mensagem": "Já existe um paciente cadastrado com este telefone."}, 409
                return {"mensagem": "Já existe um paciente cadastrado com este e-mail."}, 409

            novo_paciente = Paciente(**paciente_data)
            db.session.add(novo_paciente)
            db.session.flush()

            nova_credencial = Credencial(
                login=paciente_data['cpf'],
                senha=senha,
                tipo='paciente',
                referencia_id=novo_paciente.id
            )

            db.session.add(nova_credencial)
            db.session.commit()

            logger.info(f"Novo Paciente com id {novo_paciente.id} cadastrado com sucesso")
            return marshal(novo_paciente, paciente_fields), 201

        except IntegrityError as error:
            log_exception("Violação de unicidade ao inserir novo Paciente.")
            db.session.rollback()
            return {"mensagem": _mensagem_integridade(error)}, 409
        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao inserir novo Paciente.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except (KeyError, TypeError, ValueError):
            db.session.rollback()
            return {"mensagem": "Dados do paciente inválidos ou incompletos."}, 400
        except Exception:
            log_exception("Erro inesperado ao inserir novo Paciente")
            db.session.rollback()
            abort(500, description="Ocorreu um erro inesperado.")


class PacienteResource(Resource):
    @token_required
    def get(self, id):
        logger.info(f"Get - Paciente por id: {id}")

        tipo = get_jwt().get("tipo")
        referencia_id = get_current_referencia_id()

        try:
            if tipo == 'paciente' and id != referencia_id:
                return {"mensagem": "Você só pode visualizar seus próprios dados."}, 403

            if tipo == 'profissional':
                vinculo = db.session.execute(
                    db.select(Agendamento.id)
                    .join(Horario, Horario.id == Agendamento.horario_id)
                    .where(
                        Agendamento.paciente_id == id,
                        Horario.profissional_id == referencia_id,
                    )
                    .limit(1)
                ).scalar_one_or_none()
                if vinculo is None:
                    return {"mensagem": "Paciente não possui agendamento com este profissional."}, 403

            paciente = db.session.execute(db.select(Paciente).filter_by(id=id)).scalar_one_or_none()
            if paciente is None:
                logger.warning(f"Paciente com id {id} não encontrado.")
                return {"mensagem": "Paciente não encontrado."}, 404

            return marshal(paciente, paciente_fields), 200

        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao buscar paciente por id.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao buscar paciente")
            abort(500, description="Ocorreu um erro inesperado.")

    @paciente_required
    def put(self, id):
        logger.info(f"Put - Tentativa de atualizar Paciente com id: {id}")
        paciente_data = request.get_json() or {}

        referencia_id = get_current_referencia_id()
        if int(id) != referencia_id:
            return {"mensagem": "Você só pode alterar seus próprios dados."}, 403

        if 'email' in paciente_data and '@' not in str(paciente_data['email']):
            return {"mensagem": "Informe um e-mail válido contendo '@'."}, 400

        for campo in ('gestante', 'possui_deficiencia'):
            if campo in paciente_data:
                paciente_data[campo] = _booleano(paciente_data[campo])

        try:
            paciente = db.session.execute(db.select(Paciente).filter_by(id=id)).scalar_one_or_none()
            if paciente is None:
                return {"mensagem": "Paciente não encontrado."}, 404

            for key, value in paciente_data.items():
                setattr(paciente, key, value.strip().lower() if key == 'email' else value)

            db.session.commit()
            return {"mensagem": "Paciente atualizado com sucesso."}, 200

        except IntegrityError as error:
            db.session.rollback()
            return {"mensagem": _mensagem_integridade(error)}, 409
        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao atualizar Paciente.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao atualizar Paciente")
            abort(500, description="Ocorreu um erro inesperado.")

    @token_required
    @admin_required
    def delete(self, id):
        logger.info(f"Delete - Tentativa de deleção Paciente com id: {id}")

        try:
            paciente = db.session.execute(db.select(Paciente).filter_by(id=id)).scalar_one_or_none()
            if paciente is None:
                return {"mensagem": "Paciente não encontrado."}, 404

            credencial = db.session.execute(
                db.select(Credencial).filter_by(referencia_id=id, tipo='paciente')
            ).scalar_one_or_none()
            if credencial:
                db.session.delete(credencial)

            db.session.delete(paciente)
            db.session.commit()
            return {"mensagem": "Paciente removido com sucesso."}, 200

        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao deletar Paciente.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao deletar Paciente")
            abort(500, description="Ocorreu um erro inesperado.")
