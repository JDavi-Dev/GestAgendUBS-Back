# --- ESTÁGIO 1: Build ---
FROM python:3.11-slim AS builder

# Criar diretório do build
WORKDIR /build

# Instala ferramentas de compilação
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean

COPY requirements.txt .

# Instala as libs em uma pasta específica
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# --- ESTÁGIO 2: Runtime (Image final leve) ---
FROM python:3.11-slim

# Criar diretório da app
WORKDIR /app

# Copia as bibliotecas já instaladas/compiladas do estágio anterior
COPY --from=builder /install /usr/local

COPY . .

# Instala APENAS o necessário para o runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dar permissão de execução ao script de entrada
RUN chmod +x ./docker-entrypoint.sh

# Definir o script como o ponto de entrada
ENTRYPOINT ["./docker-entrypoint.sh"]

# Comando de inicialização
CMD ["uwsgi", "--ini", "uwsgi.ini"]