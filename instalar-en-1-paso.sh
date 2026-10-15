#!/usr/bin/env bash
# Paccioli CFO · instalación en un paso para Mac y Linux. Copia y pega en la Terminal:
#   curl -fsSL https://raw.githubusercontent.com/pachio2509/paccioli-cfo/main/instalar-en-1-paso.sh | bash
set -e
DESTINO="${PACCIOLI_DIR:-$HOME/Paccioli-CFO}"
echo "→ Descargando Paccioli CFO en $DESTINO ..."
TMP="$(mktemp -d)"
curl -fsSL "${PACCIOLI_ZIP:-https://github.com/pachio2509/paccioli-cfo/archive/refs/heads/main.zip}" -o "$TMP/p.zip"
unzip -q "$TMP/p.zip" -d "$TMP"
mkdir -p "$DESTINO"
# conserva tus estados de cuenta y respuestas si ya lo tenias instalado
rsync -a --exclude 'mis-estados-de-cuenta' --exclude 'mi-negocio' "$TMP/paccioli-cfo-main/" "$DESTINO/"
rm -rf "$TMP"
cd "$DESTINO"
chmod +x instalar.sh iniciar.sh "Abrir Paccioli CFO.command"
./instalar.sh
if [ -d "$HOME/Desktop" ] && [ -z "$PACCIOLI_SIN_ABRIR" ]; then
  ln -sf "$DESTINO/Abrir Paccioli CFO.command" "$HOME/Desktop/Paccioli CFO.command"
  echo "✓ Te dejé un acceso directo en tu Escritorio: «Paccioli CFO»"
fi
[ -n "$PACCIOLI_SIN_ABRIR" ] && exit 0
echo "→ Abriendo tu tablero ..."
./iniciar.sh
