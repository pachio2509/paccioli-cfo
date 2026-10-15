#!/usr/bin/env bash
# Paccioli CFO · instalación en Mac o Linux
set -e
cd "$(dirname "$0")"
PY=$(command -v python3 || command -v python || true)
if [ -z "$PY" ]; then
  echo "Necesitas Python 3.9 o más nuevo: https://www.python.org/downloads/"; exit 1
fi
echo "→ Creando entorno en .venv ..."
"$PY" -m venv .venv
./.venv/bin/python -m pip install --quiet --upgrade pip
./.venv/bin/python -m pip install --quiet -r requirements.txt
chmod +x iniciar.sh
echo ""
echo "✓ Listo. Para abrir tu tablero:   ./iniciar.sh"
echo "  Para ver el negocio de ejemplo:  ./iniciar.sh --demo"
