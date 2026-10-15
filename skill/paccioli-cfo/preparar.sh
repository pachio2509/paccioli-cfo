#!/usr/bin/env bash
# Deja listo un Python con lo que Paccioli necesita (pdfplumber, openpyxl) e imprime su ruta.
# No toca el Python del sistema: si falta algo, crea un .venv (dentro del skill o, si no se puede escribir, en /tmp).
set -e
SKILL="$(cd "$(dirname "$0")" && pwd)"
PY=$(command -v python3 || command -v python || true)
if [ -z "$PY" ]; then
  echo "Necesitas Python 3.9 o más nuevo: https://www.python.org/downloads/" >&2; exit 1
fi
if "$PY" -c "import pdfplumber, openpyxl" 2>/dev/null; then
  echo "$PY"; exit 0
fi
VENV="$SKILL/.venv"
[ -w "$SKILL" ] || VENV="${TMPDIR:-/tmp}/paccioli-cfo-venv"
if [ ! -x "$VENV/bin/python" ]; then
  "$PY" -m venv "$VENV" >&2
fi
"$VENV/bin/python" -c "import pdfplumber, openpyxl" 2>/dev/null || \
  "$VENV/bin/python" -m pip install --quiet --disable-pip-version-check pdfplumber openpyxl >&2
echo "$VENV/bin/python"
