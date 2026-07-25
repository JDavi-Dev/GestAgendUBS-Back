#!/bin/sh
set -e

echo "==> Aplicando migrações do banco..."
alembic upgrade head

echo "==> Verificando administrador inicial..."
python -m app.scripts.bootstrap_admin

if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  echo "==> Inserindo dados de demonstração..."
  python -m app.scripts.seed_demo
fi

echo "==> Iniciando SGA UBS API..."
exec "$@"
