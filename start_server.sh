#!/usr/bin/env bash
cd "$(dirname "$0")"
echo "🚀 Iniciando LeadStream M2M Engine en http://localhost:8000"
echo "📖 Swagger Docs en http://localhost:8000/docs"
./.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
