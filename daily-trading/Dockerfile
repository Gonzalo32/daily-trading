# Dockerfile para el Bot de Day Trading
FROM python:3.9-slim

# Metadatos
LABEL maintainer="Trading Bot Team"
LABEL description="Bot de Day Trading Automatizado"
LABEL version="1.0.0"

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TZ=UTC

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos de dependencias
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Crear directorios necesarios
RUN mkdir -p logs models data backups

# Crear usuario no-root
RUN useradd --create-home --shell /bin/bash tradingbot
RUN chown -R tradingbot:tradingbot /app
USER tradingbot

# Exponer puerto del dashboard
EXPOSE 8000

# Comando por defecto
CMD ["python", "main.py"]
