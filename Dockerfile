# ==============================================================================
# SENTINEL // OPS Enterprise V3.0 - Multi-Stage Production Dockerfile
# Etapa 1: Compilación de Frontend Vite React
# Etapa 2: Entorno Python FastAPI Uvicorn ASGI en Producción
# ==============================================================================

# --- Etapa 1: Construcción de Frontend ---
FROM node:20-alpine AS constructor_frontend
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# --- Etapa 2: Imagen Final de Producción Backend ---
FROM python:3.12-slim AS ejecucion_produccion

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=America/Bogota

# Instalar dependencias del sistema mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código del backend
COPY backend/app/ ./app

# Copiar bundle compilado del frontend
COPY --from=constructor_frontend /app/frontend/dist ./frontend_dist

EXPOSE 8000

CMD ["uvicorn", "app.main:aplicacion", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
