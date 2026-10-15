#!/usr/bin/env bash
# Paccioli CFO · doble clic en Mac para abrir tu tablero (la primera vez se instala solo)
cd "$(dirname "$0")"
chmod +x instalar.sh iniciar.sh 2>/dev/null
./iniciar.sh "$@"
