from helpers.application import app, api
from helpers.CORS import cors

from resources.PacienteResource import PacientesResouce, PacienteResource
from resources.ProfissionalResource import ProfissionaisResouce, ProfissionalResource
from resources.AdministradorResource import AdministradoresResouce, AdministradorResource
from resources.HorarioResource import HorariosResource, HorarioResource
from resources.AgendamentoResource import AgendamentosResource, AgendamentoResource

cors.init_app(app)

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