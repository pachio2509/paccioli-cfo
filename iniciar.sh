#!/usr/bin/env bash
# Paccioli CFO · abre tu tablero en el navegador
cd "$(dirname "$0")"
[ -x .venv/bin/python ] || ./instalar.sh
exec ./.venv/bin/python -m paccioli_cfo "$@"
