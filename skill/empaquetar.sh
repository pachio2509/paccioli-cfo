#!/usr/bin/env bash
# Arma el skill de Claude en dist/paccioli-cfo-skill.zip (SKILL.md + el programa adentro).
set -e
cd "$(dirname "$0")/.."
rm -rf dist/skill && mkdir -p dist/skill/paccioli-cfo
cp skill/paccioli-cfo/SKILL.md dist/skill/paccioli-cfo/
rsync -a --exclude '__pycache__' --exclude '*.pyc' paccioli_cfo dist/skill/paccioli-cfo/
cp LICENSE dist/skill/paccioli-cfo/
(cd dist/skill && rm -f ../paccioli-cfo-skill.zip && zip -qr ../paccioli-cfo-skill.zip paccioli-cfo)
rm -rf dist/skill
echo "✓ Skill listo: dist/paccioli-cfo-skill.zip"
