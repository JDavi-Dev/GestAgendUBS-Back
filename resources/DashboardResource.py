# resources/DashboardResource.py

from flask import request, abort
from flask_restful import Resource, marshal
from datetime import datetime, timedelta, date
from sqlalchemy import func, and_, extract, case
from sqlalchemy.exc import SQLAlchemyError

from helpers.database import db
from helpers.logging import logger, log_exception
from helpers.auth import token_required, admin_required, get_jwt

from models.Agendamento import Agendamento
from models.Horario import Horario
from models.Paciente import Paciente
from models.Profissional import Profissional
from models.FilaEspera import FilaEspera


class DashboardGeralResource(Resource):
    
    @token_required
    @admin_required
    def get(self):
        """Dashboard geral com métricas agregadas"""
        logger.info("GET - Dashboard Geral")
        
        # Parâmetros de período (opcionais)
        periodo_inicio = request.args.get('periodo_inicio')
        periodo_fim = request.args.get('periodo_fim')
        
        try:
            # Converter datas
            if periodo_inicio:
                data_inicio = datetime.strptime(periodo_inicio, '%Y-%m-%d').date()
            else:
                data_inicio = date.today() - timedelta(days=30)  # Últimos 30 dias
            
            if periodo_fim:
                data_fim = datetime.strptime(periodo_fim, '%Y-%m-%d').date()
            else:
                data_fim = date.today()
            
            # ============================================
            # 1. MÉTRICAS GERAIS
            # ============================================
            
            # Total de agendamentos no período
            total_agendamentos = db.session.execute(
                db.select(func.count(Agendamento.id)).where(
                    and_(
                        Agendamento.created_at >= data_inicio,
                        Agendamento.created_at <= data_fim + timedelta(days=1)
                    )
                )
            ).scalar() or 0
            
            # Agendamentos por status
            agendamentos_por_status = db.session.execute(
                db.select(
                    Agendamento.status,
                    func.count(Agendamento.id).label('total')
                ).where(
                    and_(
                        Agendamento.created_at >= data_inicio,
                        Agendamento.created_at <= data_fim + timedelta(days=1)
                    )
                ).group_by(Agendamento.status)
            ).all()
            
            status_dict = {status: total for status, total in agendamentos_por_status}
            
            # ============================================
            # 2. TAXA DE OCUPAÇÃO
            # ============================================
            
            # Total de horários disponíveis no período
            total_horarios = db.session.execute(
                db.select(func.count(Horario.id)).where(
                    and_(
                        Horario.data >= data_inicio,
                        Horario.data <= data_fim
                    )
                )
            ).scalar() or 1  # Evitar divisão por zero
            
            # Horários ocupados (com agendamento)
            horarios_ocupados = db.session.execute(
                db.select(func.count(Horario.id)).where(
                    and_(
                        Horario.data >= data_inicio,
                        Horario.data <= data_fim,
                        Horario.disponivel == False
                    )
                )
            ).scalar() or 0
            
            taxa_ocupacao = round((horarios_ocupados / total_horarios) * 100, 2)
            
            # ============================================
            # 3. TAXA DE FALTAS
            # ============================================
            
            total_realizados = status_dict.get('realizado', 0)
            total_faltas = status_dict.get('falta', 0)
            total_agendados = status_dict.get('agendado', 0) + status_dict.get('confirmado', 0)
            
            # Taxa de faltas = faltas / (realizados + faltas) * 100
            total_atendidos = total_realizados + total_faltas
            taxa_faltas = round((total_faltas / total_atendidos) * 100, 2) if total_atendidos > 0 else 0
            
            # ============================================
            # 4. AGENDAMENTOS POR PROFISSIONAL
            # ============================================
            
            agendamentos_por_profissional = db.session.execute(
                db.select(
                    Profissional.id,
                    Profissional.nome,
                    Profissional.especialidade,
                    func.count(Agendamento.id).label('total_agendamentos')
                ).join(
                    Horario, Horario.profissional_id == Profissional.id
                ).join(
                    Agendamento, Agendamento.horario_id == Horario.id
                ).where(
                    and_(
                        Agendamento.created_at >= data_inicio,
                        Agendamento.created_at <= data_fim + timedelta(days=1),
                        Agendamento.status.in_(['realizado', 'agendado', 'confirmado'])
                    )
                ).group_by(
                    Profissional.id, Profissional.nome, Profissional.especialidade
                ).order_by(
                    func.count(Agendamento.id).desc()
                )
            ).all()
            
            profissionais_top = [
                {
                    "id": p.id,
                    "nome": p.nome,
                    "especialidade": p.especialidade,
                    "total_agendamentos": p.total_agendamentos
                }
                for p in agendamentos_por_profissional[:5]  # Top 5
            ]
            
            # ============================================
            # 5. AGENDAMENTOS POR DIA (Últimos 7 dias)
            # ============================================
            
            data_inicio_semana = date.today() - timedelta(days=7)
            
            agendamentos_por_dia = db.session.execute(
                db.select(
                    func.date(Agendamento.created_at).label('data'),
                    func.count(Agendamento.id).label('total')
                ).where(
                    Agendamento.created_at >= data_inicio_semana
                ).group_by(
                    func.date(Agendamento.created_at)
                ).order_by(
                    func.date(Agendamento.created_at).asc()
                )
            ).all()
            
            tendencia_diaria = [
                {
                    "data": dia.data.isoformat(),
                    "total": dia.total
                }
                for dia in agendamentos_por_dia
            ]
            
            # ============================================
            # 6. TEMPO MÉDIO DE ESPERA (Simulado)
            # ============================================
            
            # Calcular diferença entre criação do agendamento e data da consulta
            tempos_espera = db.session.execute(
                db.select(
                    Agendamento.created_at,
                    Horario.data,
                    Horario.hora_inicio
                ).join(
                    Horario, Horario.id == Agendamento.horario_id
                ).where(
                    and_(
                        Agendamento.created_at >= data_inicio,
                        Agendamento.created_at <= data_fim + timedelta(days=1),
                        Agendamento.status.in_(['realizado', 'agendado', 'confirmado'])
                    )
                )
            ).all()
            
            if tempos_espera:
                total_dias = 0
                for item in tempos_espera:
                    data_consulta = datetime.combine(item.data, item.hora_inicio)
                    diff = (data_consulta - item.created_at).days
                    total_dias += max(diff, 0)  # Evitar valores negativos
                tempo_medio_espera = round(total_dias / len(tempos_espera), 1)
            else:
                tempo_medio_espera = 0
            
            # ============================================
            # 7. PACIENTES CADASTRADOS
            # ============================================
            
            total_pacientes = db.session.execute(
                db.select(func.count(Paciente.id))
            ).scalar() or 0
            
            # ============================================
            # 8. FILA DE ESPERA
            # ============================================
            
            total_fila_espera = db.session.execute(
                db.select(func.count(FilaEspera.id)).where(
                    FilaEspera.status == 'aguardando'
                )
            ).scalar() or 0
            
            # ============================================
            # 9. MONTAR RESPOSTA
            # ============================================
            
            resultado = {
                "periodo": {
                    "inicio": data_inicio.isoformat(),
                    "fim": data_fim.isoformat()
                },
                "resumo_geral": {
                    "total_agendamentos": total_agendamentos,
                    "total_pacientes": total_pacientes,
                    "total_profissionais": db.session.execute(
                        db.select(func.count(Profissional.id)).where(
                            Profissional.ativo == True
                        )
                    ).scalar() or 0,
                    "total_fila_espera": total_fila_espera,
                    "total_horarios_disponiveis": db.session.execute(
                        db.select(func.count(Horario.id)).where(
                            and_(
                                Horario.data >= date.today(),
                                Horario.disponivel == True
                            )
                        )
                    ).scalar() or 0
                },
                "metricas_agendamentos": {
                    "por_status": {
                        "agendado": status_dict.get('agendado', 0),
                        "confirmado": status_dict.get('confirmado', 0),
                        "realizado": status_dict.get('realizado', 0),
                        "cancelado": status_dict.get('cancelado', 0),
                        "falta": status_dict.get('falta', 0)
                    },
                    "taxa_ocupacao": taxa_ocupacao,
                    "taxa_faltas": taxa_faltas,
                    "tempo_medio_espera_dias": tempo_medio_espera
                },
                "tendencias": {
                    "agendamentos_por_dia": tendencia_diaria,
                    "profissionais_mais_ocupados": profissionais_top
                }
            }
            
            logger.info("Dashboard retornado com sucesso")
            return resultado, 200
            
        except ValueError:
            return {"mensagem": "Formato de data inválido. Use AAAA-MM-DD."}, 400
        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao buscar dados do Dashboard.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao buscar dados do Dashboard")
            abort(500, description="Ocorreu um erro inesperado.")


class DashboardRelatorioFaltasResource(Resource):
    
    @token_required
    @admin_required
    def get(self):
        """Relatório detalhado de faltas"""
        logger.info("GET - Relatório de Faltas")
        
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        
        try:
            if data_inicio:
                dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            else:
                dt_inicio = date.today() - timedelta(days=30)
            
            if data_fim:
                dt_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
            else:
                dt_fim = date.today()
            
            # Buscar agendamentos com status 'falta'
            faltas = db.session.execute(
                db.select(
                    Agendamento.id,
                    Paciente.nome.label('paciente_nome'),
                    Paciente.cpf,
                    Paciente.telefone,
                    Profissional.nome.label('profissional_nome'),
                    Profissional.especialidade,
                    Horario.data.label('data_consulta'),
                    Horario.hora_inicio,
                    Agendamento.created_at.label('data_agendamento')
                ).join(
                    Paciente, Paciente.id == Agendamento.paciente_id
                ).join(
                    Horario, Horario.id == Agendamento.horario_id
                ).join(
                    Profissional, Profissional.id == Horario.profissional_id
                ).where(
                    and_(
                        Agendamento.status == 'falta',
                        Horario.data >= dt_inicio,
                        Horario.data <= dt_fim
                    )
                ).order_by(
                    Horario.data.desc()
                )
            ).all()
            
            resultado = {
                "periodo": {
                    "inicio": dt_inicio.isoformat(),
                    "fim": dt_fim.isoformat()
                },
                "total_faltas": len(faltas),
                "faltas": [
                    {
                        "id": f.id,
                        "paciente_nome": f.paciente_nome,
                        "paciente_cpf": f.cpf,
                        "paciente_telefone": f.telefone,
                        "profissional_nome": f.profissional_nome,
                        "especialidade": f.especialidade,
                        "data_consulta": f.data_consulta.isoformat(),
                        "hora_consulta": f.hora_inicio.strftime('%H:%M'),
                        "data_agendamento": f.data_agendamento.isoformat()
                    }
                    for f in faltas
                ]
            }
            
            logger.info(f"Relatório de faltas retornado: {len(faltas)} faltas")
            return resultado, 200
            
        except ValueError:
            return {"mensagem": "Formato de data inválido. Use AAAA-MM-DD."}, 400
        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao buscar relatório de faltas.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao buscar relatório de faltas")
            abort(500, description="Ocorreu um erro inesperado.")


class DashboardRelatorioAgendamentosResource(Resource):
    
    @token_required
    @admin_required
    def get(self):
        """Relatório detalhado de agendamentos por período"""
        logger.info("GET - Relatório de Agendamentos")
        
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        status = request.args.get('status')
        profissional_id = request.args.get('profissional_id', type=int)
        
        try:
            if data_inicio:
                dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            else:
                dt_inicio = date.today() - timedelta(days=30)
            
            if data_fim:
                dt_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
            else:
                dt_fim = date.today()
            
            # Construir query
            query = db.select(
                Agendamento.id,
                Paciente.nome.label('paciente_nome'),
                Paciente.cpf,
                Profissional.nome.label('profissional_nome'),
                Profissional.especialidade,
                Horario.data.label('data_consulta'),
                Horario.hora_inicio,
                Agendamento.status,
                Agendamento.motivo_cancelamento,
                Agendamento.created_at.label('data_agendamento')
            ).join(
                Paciente, Paciente.id == Agendamento.paciente_id
            ).join(
                Horario, Horario.id == Agendamento.horario_id
            ).join(
                Profissional, Profissional.id == Horario.profissional_id
            ).where(
                and_(
                    Horario.data >= dt_inicio,
                    Horario.data <= dt_fim
                )
            )
            
            if status:
                query = query.where(Agendamento.status == status)
            if profissional_id:
                query = query.where(Profissional.id == profissional_id)
            
            query = query.order_by(Horario.data.desc())
            
            agendamentos = db.session.execute(query).all()
            
            resultado = {
                "periodo": {
                    "inicio": dt_inicio.isoformat(),
                    "fim": dt_fim.isoformat()
                },
                "filtros": {
                    "status": status,
                    "profissional_id": profissional_id
                },
                "total": len(agendamentos),
                "agendamentos": [
                    {
                        "id": a.id,
                        "paciente_nome": a.paciente_nome,
                        "paciente_cpf": a.cpf,
                        "profissional_nome": a.profissional_nome,
                        "especialidade": a.especialidade,
                        "data_consulta": a.data_consulta.isoformat(),
                        "hora_consulta": a.hora_inicio.strftime('%H:%M'),
                        "status": a.status,
                        "motivo_cancelamento": a.motivo_cancelamento,
                        "data_agendamento": a.data_agendamento.isoformat()
                    }
                    for a in agendamentos
                ]
            }
            
            logger.info(f"Relatório de agendamentos retornado: {len(agendamentos)} registros")
            return resultado, 200
            
        except ValueError:
            return {"mensagem": "Formato de data inválido. Use AAAA-MM-DD."}, 400
        except SQLAlchemyError:
            log_exception("Exception SQLAlchemy ao buscar relatório de agendamentos.")
            db.session.rollback()
            abort(500, description="Problema com o banco de dados.")
        except Exception:
            log_exception("Erro inesperado ao buscar relatório de agendamentos")
            abort(500, description="Ocorreu um erro inesperado.")