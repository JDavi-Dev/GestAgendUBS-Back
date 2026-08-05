#!/bin/sh

set -e

echo "==> Aplicando migrações (se houver)..."

flask db upgrade

# echo "==> Verificando necessidade de popular banco..."
# python init_db.py

echo "==> Iniciando uWSGI..."

exec "$@"