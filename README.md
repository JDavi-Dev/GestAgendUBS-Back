# SGA UBS — Backend FastAPI

Backend do **Sistema de Gestão de Agendamentos para Unidades Básicas de Saúde (SGA UBS)**, reestruturado para ficar compatível com as tecnologias, requisitos funcionais e requisitos não funcionais descritos no TCC.

## Tecnologias

- Python 3.12
- FastAPI e Pydantic
- SQLAlchemy 2
- PostgreSQL
- Alembic
- JWT com access token e refresh token
- bcrypt para hash de senhas
- Pytest e HTTPX
- Docker e Docker Compose
- Swagger/OpenAPI automático

A documentação interativa fica disponível em:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Funcionalidades implementadas

- CRUD de pacientes, profissionais e administradores.
- Cadastro público somente para pacientes.
- Cadastro de profissional e administrador protegido por perfil administrativo.
- Login por CPF para paciente e por e-mail para profissional/administrador.
- Access token e refresh token JWT, rotação de refresh token e revogação persistida no banco.
- Controle de acesso por perfil e verificação de propriedade dos registros.
- CRUD de horários, filtro por especialidade, data, profissional e status.
- Validação de sobreposição de horários.
- Agendamento atômico com bloqueio de linha e índice único parcial para impedir reserva dupla.
- Bloqueio de agendamentos sobrepostos do mesmo paciente.
- Cancelamento com antecedência mínima de 24 horas.
- Histórico do paciente e agenda do profissional por intervalo de datas.
- Registro de atendimento realizado ou falta.
- Fila de espera priorizada: idosos, gestantes, PCD/cadeirantes e demais pacientes.
- Posição correta na fila por especialidade.
- Alocação administrativa de paciente da fila em horário disponível.
- Dashboard com ocupação, faltas, cancelamentos e totais do sistema.
- Migração de dados da estrutura Flask anterior.

## Execução com Docker — recomendada

### 1. Prepare o ambiente

No PowerShell, dentro da pasta do backend:

```powershell
Copy-Item .env.example .env
```

Edite o `.env` e troque, no mínimo:

```env
POSTGRES_PASSWORD=uma_senha_forte
JWT_SECRET_KEY=uma-chave-aleatoria-com-mais-de-32-caracteres
```

Para usar dados de demonstração:

```env
SEED_DEMO_DATA=true
```

### 2. Inicie os contêineres

```powershell
docker compose up --build
```

Verifique:

```text
http://localhost:8000/health
http://localhost:8000/docs
```

### 3. Encerrar

```powershell
docker compose down
```

Para também apagar o banco de desenvolvimento:

```powershell
docker compose down -v
```

## Execução local no Windows

O backend FastAPI não usa Nginx nem uWSGI para desenvolvimento.

### 1. Criar ambiente virtual

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Instalar dependências

```powershell
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

### 3. Configurar o ambiente

```powershell
Copy-Item .env.example .env
```

Ajuste `DATABASE_URL` para o PostgreSQL instalado ou executado por Docker.

### 4. Aplicar migrações

```powershell
alembic upgrade head
```

### 5. Criar o administrador inicial

Preencha as variáveis `BOOTSTRAP_ADMIN_*` no `.env` e execute:

```powershell
python -m app.scripts.bootstrap_admin
```

### 6. Executar a API

```powershell
uvicorn app.main:app --reload --port 8000
```

## Dados de demonstração

Execute depois das migrações:

```powershell
python -m app.scripts.seed_demo
```

Credenciais:

| Perfil | Identificador | Senha |
|---|---|---|
| Paciente | `12345678900` | `paciente123` |
| Profissional | `professional@sgaubs.com` | `prof123` |
| Administrador | valor de `BOOTSTRAP_ADMIN_EMAIL` | valor de `BOOTSTRAP_ADMIN_PASSWORD` |

O script é idempotente: pode ser executado novamente sem duplicar os usuários de demonstração.

## Integração com o frontend React

No `.env` do frontend Vite:

```env
VITE_USE_MOCKS=false
VITE_API_URL=http://localhost:8000
```

Depois gere novamente o frontend:

```powershell
npm run build
```

O contrato utilizado pelo frontend é:

```text
POST   /auth/login
POST   /auth/refresh
POST   /auth/logout
POST   /patients/register
GET    /users?role=patient|professional|admin
POST   /users
GET    /users/{id}
PUT    /users/{id}
DELETE /users/{id}
GET    /schedules
POST   /schedules
PUT    /schedules/{id}
DELETE /schedules/{id}
GET    /appointments
POST   /appointments
PATCH  /appointments/{id}/cancel
PATCH  /appointments/{id}/status
GET    /waitlist
POST   /waitlist
PATCH  /waitlist/{id}/cancel
POST   /waitlist/{id}/allocate
GET    /dashboard/metrics
```

## Testes automatizados

```powershell
pytest
```

Os testes cobrem:

- documentação OpenAPI e healthcheck;
- cadastro, autenticação e autorização por perfil;
- CRUD administrativo;
- conflito de horários;
- impedimento de reserva dupla;
- impedimento de agendamento em nome de outro paciente;
- regra de cancelamento de 24 horas;
- registro de atendimento/falta;
- prioridade e posição da fila de espera;
- proteção do dashboard.

## Controle de concorrência

A reserva de horário possui duas proteções complementares:

1. `SELECT ... FOR UPDATE` bloqueia o paciente e o horário durante a transação no PostgreSQL.
2. O índice único parcial `uq_active_appointment_schedule` impede mais de um agendamento com status `scheduled` para o mesmo horário, mesmo se duas requisições chegarem simultaneamente.

Isso evita o padrão inseguro de apenas consultar `disponível` e atualizar depois.

## Segurança

- Senhas nunca são retornadas pela API.
- Senhas são armazenadas com bcrypt.
- Rotas sensíveis validam perfil e propriedade do recurso.
- Paciente autenticado não consegue agendar para outro paciente, mesmo enviando outro `patientId`.
- Tokens revogados são persistidos em `tb_token_revogado`.
- CORS é limitado às origens configuradas.
- `.env` não é copiado para a imagem Docker e não deve ser versionado.
- Não mantenha as credenciais de demonstração em produção.

## Migração do backend Flask recebido

O histórico Alembic mantém a revisão original `30ce74a5c507` e adiciona a revisão `20260724_fastapi`.

Em um banco criado pelo backend anterior:

```powershell
alembic upgrade head
```

A migração converte os perfis antigos, adiciona os campos necessários, normaliza status, cria os índices de integridade e preserva os registros existentes. Faça backup antes de aplicar em um banco com dados importantes.

Mais detalhes: [`docs/MIGRATION_FROM_FLASK.md`](docs/MIGRATION_FROM_FLASK.md).

## Estrutura

```text
app/
  api/routers/        Endpoints FastAPI
  core/               Configuração, banco, JWT e dependências
  models/             Modelos SQLAlchemy
  schemas/            Validação Pydantic
  services/           Regras de negócio
  scripts/            Bootstrap e dados de demonstração
  utils/              Normalização de dados
alembic/               Migrações
 tests/                 Testes Pytest
```
