#!/usr/bin/env bash
# ==============================================================================
# SENTINEL // OPS - Script de Arranque Unificado para Git Bash
# ==============================================================================

RUTA_RAIZ="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$RUTA_RAIZ"

echo "=========================================================="
echo "   SENTINEL // OPS - Plataforma Táctica de Seguridad V2.0"
echo "=========================================================="

# 1. Iniciar Backend (FastAPI + Uvicorn)
echo "[1/2] Iniciando Backend en http://127.0.0.1:8000 ..."
cd "$RUTA_RAIZ/backend"
if [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
fi
python -m uvicorn app.main:aplicacion --host 127.0.0.1 --port 8000 &
PID_BACKEND=$!
echo "      Backend activo (PID: $PID_BACKEND)"

# 2. Iniciar Frontend (Vite + React)
echo "[2/2] Iniciando Frontend en http://localhost:5173 ..."
cd "$RUTA_RAIZ/frontend"
npm run dev

# Al cerrar el frontend, terminar el backend en segundo plano
kill $PID_BACKEND 2>/dev/null || true

