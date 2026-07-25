# Relatório de ajustes — Backend SGA UBS

## Escopo

O backend recebido em Flask foi reestruturado como uma aplicação FastAPI para alinhar a implementação às tecnologias e aos requisitos definidos no TCC. A mudança foi tratada como migração arquitetural, e não apenas como correção pontual, pois o framework original era incompatível com o documento.

## Correções principais

### Tecnologia e arquitetura

- Substituição de Flask/Flask-RESTful por FastAPI.
- Validação de entrada e saída com Pydantic.
- Separação em routers, services, schemas, models e core.
- Swagger/OpenAPI automático em `/docs`, `/redoc` e `/openapi.json`.
- SQLAlchemy 2 e Alembic mantidos.
- PostgreSQL como banco de produção.

### Segurança

- Cadastro público restrito a pacientes.
- Cadastro de profissional e administrador restrito a administradores.
- Verificação de propriedade em usuários e agendamentos.
- Paciente não consegue agendar para outro paciente.
- JWT access/refresh, rotação de refresh e revogação persistente.
- Hash de senha com bcrypt.
- Remoção de atribuição em massa; somente campos previstos nos schemas são aceitos.
- CORS configurável, sem liberação global fixa.
- Segredos removidos da imagem e do repositório.

### Integridade e concorrência

- Bloqueio de linha com `SELECT FOR UPDATE` para horário e paciente.
- Índice único parcial para impedir dois agendamentos ativos no mesmo horário.
- Verificação de sobreposição de consultas do paciente.
- Verificação de sobreposição na criação e atualização de horários.
- Transações com rollback e resposta HTTP 409 para conflitos.

### Requisitos funcionais

- CRUD completo de paciente, profissional e administrador.
- CRUD completo de horários.
- Consulta por especialidade, data, profissional e status.
- Agendamento, cancelamento com 24 horas e histórico.
- Agenda do profissional por intervalo.
- Registro de atendimento e falta.
- Dashboard gerencial.
- Fila de espera com prioridade alta, média e baixa, posição e alocação.

### Infraestrutura

- Substituição de uWSGI por Uvicorn.
- Dockerfile funcional para FastAPI.
- Docker Compose com PostgreSQL e healthchecks válidos.
- Migração Alembic compatível com a revisão original.
- Scripts de bootstrap administrativo e dados de demonstração.

## Validações executadas

- Compilação de todos os arquivos Python com `compileall`.
- Suíte Pytest: **12 testes aprovados**.
- Criação de banco SQLite vazio pelas duas revisões Alembic.
- Execução dos scripts de administrador inicial e dados de demonstração.
- Login dos três perfis.
- Criação de horário e agendamento sobre banco migrado.
- Cadastro de paciente sem telefone sobre banco migrado.

## Limitação da validação

O fluxo Alembic foi testado em SQLite para validar a sequência e a estrutura. O código de produção e a migração possuem caminho específico para PostgreSQL, mas não foi executado contra uma instância PostgreSQL real neste ambiente. Antes de atualizar um banco com dados importantes, faça backup e execute a migração em uma cópia de homologação.
