# Documentação Swagger — SGA UBS

Este pacote foi gerado com base no Backend Flask/Flask-RESTful enviado.

## Estrutura

- `index.html`: interface Swagger UI.
- `swagger.yaml`: especificação OpenAPI 3.0.3 completa e autossuficiente.
- `swagger.json`: mesma especificação em JSON.
- `openapi/paths`: rotas agrupadas por domínio.
- `openapi/schemas`: schemas individuais.
- `openapi/security`: esquemas JWT.
- `openapi/components`: respostas reutilizáveis e tags.

## Instalação no Backend

Copie a pasta `docs` para a raiz do Backend, no mesmo nível do `app.py`.

Adicione ao `app.py`, depois da criação/importação de `app`:

```python
from flask import send_from_directory

@app.route("/docs")
@app.route("/docs/")
def swagger_docs():
    return send_from_directory("docs", "index.html")

@app.route("/docs/<path:filename>")
def swagger_static(filename):
    return send_from_directory("docs", filename)
```

Reinicie o servidor e acesse:

`http://localhost:5000/docs`

## Docker

Garanta que a pasta seja copiada para a imagem. Se o Dockerfile já utiliza algo como:

```dockerfile
COPY . .
```

nenhuma alteração adicional será necessária.

## Autorização

1. Execute `POST /login`.
2. Copie o valor de `access_token`.
3. Clique em **Authorize**.
4. Informe somente o token. O Swagger UI adicionará `Bearer` automaticamente.

Para `POST /refresh`, use o `refresh_token` no esquema `refreshToken`.

## Observações de segurança encontradas no código

A documentação reflete a implementação atual:

- `POST /administradores` é público.
- `POST /profissionais` é público.
- `PUT /administrador/{id}` não possui proteção JWT.
- Algumas consultas individuais não validam a propriedade do recurso.
- `POST /agendamentos` aceita `paciente_id` no corpo apesar de exigir perfil paciente.

Recomenda-se corrigir essas permissões no Backend antes de publicar a API em produção.

## Dependência externa da interface

O `index.html` carrega os arquivos visuais do Swagger UI pelo CDN jsDelivr. A especificação da API permanece local. Em um ambiente sem internet, instale e hospede `swagger-ui-dist` localmente.
