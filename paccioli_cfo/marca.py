"""Tu marca en el tablero: nombre, asesor de contacto, logo y colores.

Por defecto es Paccioli CFO con el contacto de Kaptal. Un contador, despacho o consultor puede poner el suyo
creando `marca.json` junto al programa (copia `marca.ejemplo.json`) o con la variable PACCIOLI_MARCA=/ruta/marca.json.
Ponle "mostrar_asesor": false para no mostrar ningún contacto.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

DEFECTO = {
    "producto": "Paccioli CFO",
    "mostrar_asesor": True,
    "asesor": {
        "nombre": "Jorge Ayala",
        "puesto": "CFO",
        "empresa": "Kaptal",
        "whatsapp": "529991750122",
        "whatsapp_visible": "999 175 0122",
        "correo": "jorge@kaptal.com.mx",
        "web": "https://kaptal.com.mx",
        "hecho_en": "Mérida",
    },
    "mascota": True,
    "logo": None,
    "colores": {},
}


def cargar() -> dict:
    marca = json.loads(json.dumps(DEFECTO))
    ruta = Path(os.environ.get("PACCIOLI_MARCA") or RAIZ / "marca.json")
    if ruta.exists():
        propia = json.loads(ruta.read_text(encoding="utf-8"))
        asesor = marca["asesor"]
        if propia.get("asesor"):  # un asesor nuevo no hereda los datos de contacto del de Kaptal
            asesor = {k: propia["asesor"].get(k, "") for k in marca["asesor"]}
        marca.update({k: v for k, v in propia.items() if k != "asesor"})
        marca["asesor"] = asesor
        if marca.get("logo"):
            p = Path(marca["logo"])
            marca["logo"] = str(p if p.is_absolute() else ruta.parent / p)
    return marca


def ruta_logo(marca: dict) -> Path | None:
    p = marca.get("logo")
    return Path(p) if p and Path(p).is_file() else None


def publica(marca: dict) -> dict:
    """Lo que ve el navegador (sin rutas del disco)."""
    m = {k: v for k, v in marca.items() if k != "logo"}
    m["logo_url"] = "/marca/logo" if ruta_logo(marca) else None
    return m
