# Migração da versão Flask para FastAPI

## Antes de começar

Faça backup do PostgreSQL:

```powershell
docker exec sga-banco pg_dump -U postgres -Fc nome_do_banco > backup_sga.dump
```

O nome do contêiner, usuário e banco devem ser ajustados ao ambiente existente.

## Caminho de migração

O backend anterior possuía a revisão Alembic:

```text
30ce74a5c507
```

Esta versão mantém essa revisão e adiciona:

```text
20260724_fastapi
```

Assim, um banco já marcado com a revisão antiga pode ser atualizado com:

```powershell
alembic current
alembic upgrade head
```

## Alterações realizadas pela migração

- Converte os perfis `paciente`, `profissional` e `administrador` para `patient`, `professional` e `admin`.
- Adiciona e-mail, endereço e grupo prioritário ao paciente.
- Adiciona CPF ao profissional.
- Adiciona CPF, telefone e status ativo ao administrador.
- Substitui `disponivel` por `status` nos horários.
- Copia a especialidade do profissional para os horários existentes.
- Normaliza os status dos agendamentos para `scheduled`, `cancelled`, `done` e `missed`.
- Corrige duplicidades ativas antes de criar o índice de reserva única.
- Adiciona a prioridade completa e os vínculos de alocação à fila de espera.
- Cria a tabela persistente de tokens revogados.
- Cria índices para filtros e controle de concorrência.

## Atenção aos logins antigos

Pacientes continuam autenticando por CPF. Profissionais e administradores continuam autenticando por e-mail.

Pacientes legados não possuíam e-mail. A migração gera temporariamente:

```text
<cpf>@sga.local
```

O administrador deve atualizar esses e-mails pelo CRUD.

Profissionais sem e-mail recebem:

```text
professional-<id>@sga.local
```

## Validação após migração

```powershell
pytest
uvicorn app.main:app --reload
```

Acesse `http://localhost:8000/docs` e teste login, listagem de horários, agendamento e cancelamento.
