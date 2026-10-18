#!/usr/bin/env bash
# Paccioli CFO · instala el skill de CFO en tu Claude Code (Mac y Linux), en un paso. Copia y pega en la Terminal:
#   curl -fsSL https://raw.githubusercontent.com/pachio2509/paccioli-cfo/main/instalar-skill.sh | bash
# Deja el skill en ~/.claude/skills/paccioli-cfo y prepara su Python. No toca nada más.
set -e
SKILLS="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
ZIP="${PACCIOLI_SKILL_ZIP:-https://github.com/pachio2509/paccioli-cfo/releases/latest/download/paccioli-cfo-skill.zip}"
echo "→ Descargando el skill de Paccioli CFO ..."
TMP="$(mktemp -d)"
curl -fsSL "$ZIP" -o "$TMP/skill.zip"
unzip -q "$TMP/skill.zip" -d "$TMP"
mkdir -p "$SKILLS"
# conserva el .venv si ya lo tenías: así la actualización es instantánea
[ -d "$SKILLS/paccioli-cfo/.venv" ] && mv "$SKILLS/paccioli-cfo/.venv" "$TMP/paccioli-cfo/.venv"
rm -rf "$SKILLS/paccioli-cfo"
mv "$TMP/paccioli-cfo" "$SKILLS/paccioli-cfo"
rm -rf "$TMP"
echo "→ Preparando Python (pdfplumber, openpyxl) ..."
PY=$(bash "$SKILLS/paccioli-cfo/preparar.sh")
VERSION=$(PYTHONPATH="$SKILLS/paccioli-cfo" "$PY" -c "import paccioli_cfo; print(paccioli_cfo.__version__)")
echo ""
echo "✓ Skill Paccioli CFO $VERSION instalado en $SKILLS/paccioli-cfo"
echo ""
echo "  Abre Claude Code (si ya estaba abierto, ciérralo y ábrelo de nuevo), adjunta tu estado de cuenta y escribe:"
echo "    «Aquí está mi estado de cuenta, hazme mi dashboard»"
