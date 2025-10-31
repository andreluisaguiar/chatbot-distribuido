#
# DOCKERFILE - chatbot-distribuido/backend/Dockerfile
#

# 1. Base Image
# Usamos uma imagem Python leve com Alpine Linux para reduzir o tamanho do container
FROM python:3.11-alpine

# 2. Configurações de Ambiente
# Define o diretório de trabalho dentro do container
WORKDIR /app

# 3. Dependências do Sistema
# Instala pacotes do sistema necessários para compilar algumas bibliotecas Python (e.g., asyncpg)
RUN apk add --no-cache gcc musl-dev postgresql-dev

# 4. Instalação de Dependências Python
# Copia o arquivo requirements.txt primeiro para otimizar o cache do Docker
COPY requirements.txt .

# Instala todas as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# 5. Código da Aplicação
# Copia todo o código da aplicação para o container
COPY ./app /app/app

# 6. Comando de Execução (Será revisado na próxima etapa)
# Define o comando padrão. Usaremos um script ou uvicorn para iniciar a API.
# Este é um PLACEHOLDER para o comando final que iniciará a API e os Consumers
CMD ["/bin/sh", "-c", "echo 'Backend pronto, aguardando comando de execução...' && sleep 3600"]