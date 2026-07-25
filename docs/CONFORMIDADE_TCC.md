# Matriz de conformidade com o TCC — SGA UBS

| Requisito | Implementação |
|---|---|
| RF001 — Cadastrar Paciente | `POST /patients/register` e `POST /users` |
| RF002 — Consultar Paciente | `GET /users?role=patient` e `GET /users/{id}` |
| RF003 — Atualizar Paciente | `PUT /users/{id}` com propriedade/perfil |
| RF004 — Excluir Paciente | `DELETE /users/{id}` com validação de vínculos |
| RF005 — Autenticar Usuário | JWT access/refresh em `/auth/*` |
| RF006 — Cadastrar Profissional | `POST /users`, somente administrador |
| RF007 — Consultar Profissional | `GET /users?role=professional` |
| RF008 — Atualizar Profissional | `PUT /users/{id}`, somente próprio usuário/admin |
| RF009 — Excluir Profissional | `DELETE /users/{id}`, somente administrador |
| RF010 — Cadastrar Administrador | `POST /users`, somente administrador |
| RF011 — Consultar Administrador | `GET /users?role=admin`, somente administrador |
| RF012 — Atualizar Administrador | `PUT /users/{id}` |
| RF013 — Excluir Administrador | `DELETE /users/{id}`, preservando ao menos um admin |
| RF014 — Gerenciar Horários | CRUD completo em `/schedules` |
| RF015 — Consultar Horários | Filtros por especialidade, data, profissional e status |
| RF016 — Agendar Consulta | `POST /appointments` com transação e locks |
| RF017 — Cancelar Agendamento | `PATCH /appointments/{id}/cancel`, regra de 24h |
| RF018 — Consultar Histórico | `GET /appointments`; paciente limitado ao próprio histórico |
| RF019 — Consultar Agenda do Profissional | `GET /appointments` por profissional e intervalo |
| RF020 — Indicadores Gerenciais | `GET /dashboard/metrics` |
| RF021 — Gerenciar Fila de Espera | Entrada, consulta, cancelamento, posição e alocação |
| RNF001 — Concorrência | `FOR UPDATE` + índice único parcial |
| RNF002 — Padrão/OpenAPI | Camadas, schemas Pydantic e `/docs` |
| RNF003 — UX | Erros claros e contrato compatível com frontend React |
| RNF004 — Testes | Suíte Pytest em `tests/` |
| RNF005 — Segurança | bcrypt, JWT, revogação e autorização por perfil/propriedade |
