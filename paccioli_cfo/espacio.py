"""Tu espacio de trabajo: donde viven tus estados de cuenta y lo que el CFO aprende de tu negocio.

  mis-estados-de-cuenta/   sueltas aqui tus PDF, Excel o CSV (nunca salen de tu compu)
  mi-negocio/perfil.json   tus respuestas sobre el negocio (regimen, IVA, otros ingresos...)
  mi-negocio/reglas.json   como clasificar cada contraparte (lo aprende de tus respuestas)
"""
from __future__ import annotations

import json
import time
from pathlib import Path

PERFIL_VACIO = {
    "nombre_negocio": "",
    "titular": "",
    "regimen": "",            # resico | actividad | moral | no_se
    "precios_iva": "",        # incluyen | mas_iva | no_cobro
    "cuenta": "",             # solo_negocio | mixta
    "otros_ingresos": "",     # no | si
    "otros_ingresos_mensual": 0,
    "tarjetas": "",           # por_desglosar | negocio | personal | mixto
    "consumos": "",           # negocio | personal
    "efectivo": "",           # negocio | personal
}


class Espacio:
    def __init__(self, raiz: str | Path):
        self.raiz = Path(raiz).resolve()
        self.estados = self.raiz / "mis-estados-de-cuenta"
        self.datos = self.raiz / "mi-negocio"
        self.estados.mkdir(parents=True, exist_ok=True)
        self.datos.mkdir(parents=True, exist_ok=True)

    @property
    def es_demo(self) -> bool:
        """El negocio de ejemplo: aqui no se suben estados de cuenta reales (se mezclarian con datos inventados)."""
        return (self.datos / ".demo").exists()

    # ---------- perfil
    @property
    def ruta_perfil(self) -> Path:
        return self.datos / "perfil.json"

    def perfil(self) -> dict:
        p = dict(PERFIL_VACIO)
        if self.ruta_perfil.exists():
            p.update(json.loads(self.ruta_perfil.read_text(encoding="utf-8")))
        return p

    def guardar_perfil(self, cambios: dict) -> dict:
        p = self.perfil()
        p.update({k: v for k, v in cambios.items() if k in PERFIL_VACIO})
        self.ruta_perfil.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
        return p

    # ---------- reglas aprendidas
    @property
    def ruta_reglas(self) -> Path:
        return self.datos / "reglas.json"

    def reglas(self) -> list[dict]:
        if self.ruta_reglas.exists():
            return json.loads(self.ruta_reglas.read_text(encoding="utf-8"))
        return []

    def agregar_regla(self, regla: dict) -> None:
        reglas = [r for r in self.reglas() if not (r.get("clave") and r.get("clave") == regla.get("clave")
                                                   and r.get("tipo") == regla.get("tipo"))
                  and not (r.get("id") and r.get("id") == regla.get("id"))]
        regla["cuando"] = time.strftime("%Y-%m-%d %H:%M")
        reglas.insert(0, regla)
        self.ruta_reglas.write_text(json.dumps(reglas, ensure_ascii=False, indent=2), encoding="utf-8")

    def borrar_respuestas(self) -> None:
        for f in (self.ruta_reglas, self.ruta_perfil):
            if f.exists():
                f.unlink()

    # ---------- archivos
    def archivos(self) -> list[Path]:
        from .lectores import SOPORTADOS
        return sorted(p for p in self.estados.iterdir()
                      if p.is_file() and p.suffix.lower() in SOPORTADOS and not p.name.startswith((".", "~$")))

    def firma(self) -> str:
        """Cambia cuando cambia cualquier archivo o respuesta: asi el tablero se actualiza solo."""
        partes = []
        for p in self.archivos() + [self.ruta_perfil, self.ruta_reglas]:
            if p.exists():
                st = p.stat()
                partes.append(f"{p.name}:{st.st_size}:{st.st_mtime_ns}")
        return "|".join(partes)
