# 🏥 GestAgendUBS - Sistema de Gestão de Agendamentos para Unidades de Saúde (UBS)

## 📖 Sobre o Projeto

Este é o backend do Sistema de Agendamento para Unidades Básicas de Saúde (UBS), desenvolvido como **Projeto Integrador em Sistema para Internet**. O sistema visa substituir cadernos e senhas físicas por uma **plataforma digital** eficiente, reduzindo filas e otimizando o fluxo de **atendimento**.

## 👥 Equipe
- [José Davi](https://github.com/JDavi-Dev)
- [Igor Gabriel](https://github.com/igor721)
- [Maria José](souzagoncalves85)

## 🚀 Tecnologias Utilizadas

- Python + FastAPI
- PostgreSQL
- Redis
- Docker

## 📋 Funcionalidades Principais

- CRUD de profissionais, pacientes e agendamentos
- Gestão de horários por profissional/especialidade
- Fila de espera inteligente (priorização por idade/gestação)
- Dashboard com indicadores (tempo médio de espera, ocupação, faltas)
- Histórico do paciente por CPF
## Testes automatizados (RNF004)

Com as dependências instaladas, execute:

```bash
pytest -q
```

Os testes em `tests/test_regras_negocio.py` cobrem duplo agendamento, cancelamento com 24 horas de antecedência e conflito de horários.
