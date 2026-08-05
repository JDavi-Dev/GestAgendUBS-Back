from helpers.application import app, api
from helpers.CORS import cors
from helpers.jwt import jwt
from flask import send_from_directory
import os

from resources.PacienteResource import PacientesResouce, PacienteResource
from resources.ProfissionalResource import ProfissionaisResouce, ProfissionalResource
from resources.AdministradorResource import AdministradoresResouce, AdministradorResource
from resources.HorarioResource import HorariosResource, HorarioResource
from resources.AgendamentoResource import AgendamentosResource, AgendamentoResource
from resources.LoginResource import LoginResource, RefreshTokenResource, LogoutResource
from resources.FilaEsperaResource import FilaEsperaResource, FilaEsperaItemResource, FilaEsperaPosicaoResource
from resources.DashboardResource import DashboardGeralResource, DashboardRelatorioFaltasResource, DashboardRelatorioAgendamentosResource

cors.init_app(app)

#adicionando manualmente 
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "docs")

@app.route("/docs/")
@app.route("/docs")
def swagger_docs():
    return send_from_directory(DOCS_DIR, "index.html")

@app.route("/docs/<path:filename>")
def swagger_static(filename):
    return send_from_directory(DOCS_DIR, filename)


# Rotas Paciente
api.add_resource(PacientesResouce, '/pacientes')
api.add_resource(PacienteResource, '/paciente/<int:id>')

# Rotas Profissional
api.add_resource(ProfissionaisResouce, '/profissionais')
api.add_resource(ProfissionalResource, '/profissional/<int:id>')

# Rotas Administrador
api.add_resource(AdministradoresResouce, '/administradores')
api.add_resource(AdministradorResource, '/administrador/<int:id>')

# Rotas Horario
api.add_resource(HorariosResource, '/horarios')
api.add_resource(HorarioResource, '/horario/<int:id>')

# Rotas Agendamento
api.add_resource(AgendamentosResource, '/agendamentos')
api.add_resource(AgendamentoResource, '/agendamento/<int:id>')

# Rotas de autenticação
api.add_resource(LoginResource, '/login')
api.add_resource(RefreshTokenResource, '/refresh')
api.add_resource(LogoutResource, '/logout')

# Rotas da fila de espera
api.add_resource(FilaEsperaResource, '/fila-espera')
api.add_resource(FilaEsperaItemResource, '/fila-espera/<int:id>')
api.add_resource(FilaEsperaPosicaoResource, '/fila-espera/posicao')

# Rotas Dashboard
api.add_resource(DashboardGeralResource, '/dashboard/geral')
api.add_resource(DashboardRelatorioFaltasResource, '/dashboard/relatorio/faltas')
api.add_resource(DashboardRelatorioAgendamentosResource, '/dashboard/relatorio/agendamentos')
