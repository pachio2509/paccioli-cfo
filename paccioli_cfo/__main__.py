"""Uso:
  python -m paccioli_cfo                 abre tu tablero (usa la carpeta actual)
  python -m paccioli_cfo --demo          abre el tablero con un negocio de ejemplo
  python -m paccioli_cfo resumen         imprime tus números en la terminal
  python -m paccioli_cfo exportar        guarda tu tablero en un solo archivo HTML (se abre sin servidor)
  python -m paccioli_cfo preguntas       lo que el CFO necesita que le contestes (JSON)
  python -m paccioli_cfo responder ID VALOR   contesta una pregunta (la usa Claude por ti)
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _demo() -> Path:
    destino = RAIZ / "demo" / ".espacio"
    estados = destino / "mis-estados-de-cuenta"
    estados.mkdir(parents=True, exist_ok=True)
    for f in (RAIZ / "demo" / "estados").glob("*.csv"):
        if not (estados / f.name).exists():
            shutil.copy(f, estados / f.name)
    (destino / "mi-negocio").mkdir(parents=True, exist_ok=True)
    (destino / "mi-negocio" / ".demo").touch()
    perfil = destino / "mi-negocio" / "perfil.json"
    if not perfil.exists():
        perfil.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(RAIZ / "demo" / "perfil.json", perfil)
    return destino


def main(argv=None) -> int:
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(prog="paccioli", description="Paccioli CFO: tu estado financiero desde tu estado de cuenta")
    ap.add_argument("accion", nargs="?", default="tablero", choices=["tablero", "resumen", "exportar", "preguntas", "responder"])
    ap.add_argument("args", nargs="*", help="Para 'responder': ID y VALOR")
    ap.add_argument("--salida", default=None, help="Archivo HTML para 'exportar' (default: tablero-<negocio>.html)")
    ap.add_argument("--carpeta", default=None, help="Carpeta de trabajo (default: la del proyecto)")
    ap.add_argument("--demo", action="store_true", help="Usar el negocio de ejemplo")
    ap.add_argument("--puerto", type=int, default=8765)
    ap.add_argument("--no-abrir", action="store_true", help="No abrir el navegador")
    a = ap.parse_args(argv)
    carpeta = _demo() if a.demo else Path(a.carpeta or RAIZ)

    if a.accion == "preguntas":
        import json
        from . import motor
        from .espacio import Espacio
        e = motor.analizar(Espacio(carpeta))
        qs = [{k: q[k] for k in ("id", "titulo", "detalle", "opciones") if k in q} | ({"entrada": q["entrada"]} if q.get("entrada") else {})
              for q in e["preguntas"] if q["tipo"] != "info"]
        print(json.dumps(qs, ensure_ascii=False, indent=1))
        return 0

    if a.accion == "responder":
        from . import preguntas
        from .espacio import Espacio
        if len(a.args) != 2:
            print("Uso: python -m paccioli_cfo responder ID VALOR")
            return 2
        preguntas.responder(Espacio(carpeta), a.args[0], a.args[1])
        print("Anotado:", a.args[0], "=", a.args[1])
        return 0

    if a.accion == "exportar":
        from . import exportar, motor
        from .espacio import Espacio
        e = motor.analizar(Espacio(carpeta))
        if not e.get("mes_actual"):
            print("No encontré estados de cuenta en", Espacio(carpeta).estados)
            return 1
        ruta = exportar.guardar(e, a.salida or Path(carpeta) / exportar._nombre(e))
        print(f"Tu tablero quedó en: {ruta}")
        return 0

    if a.accion == "resumen":
        from . import motor
        from .espacio import Espacio
        e = motor.analizar(Espacio(carpeta))
        mes = e.get("mes_actual")
        if not mes:
            print("No encontré estados de cuenta en", Espacio(carpeta).estados)
            return 1
        d = e["por_mes"][mes]
        print(f"\n{e['negocio']} · {[m['nombre'] for m in e['meses'] if m['mes'] == mes][0]}")
        for f in e["archivos"]:
            ok = {True: "✓", False: "✗", None: "·"}[f["validacion"]["ok"]]
            print(f"  {ok} {f['nombre']}: {f['validacion']['texto']}")
        print(f"  Ingresos   {d['ingresos']:>14,.2f}\n  Gastos     {d['gastos']:>14,.2f}\n  Utilidad   {d['utilidad']:>14,.2f}")
        print("\nTu CFO te avisa:")
        for x in e["alertas"]:
            print(f"  [{x['nivel'].upper():5}] {x['titulo']}")
        n = sum(1 for q in e['preguntas'] if q['tipo'] != 'info')
        if n:
            print(f"\nTe quiero preguntar {n} cosa{'s' if n != 1 else ''}: abre el tablero para contestarla{'s' if n != 1 else ''}.")
        return 0

    from .servidor import iniciar
    # en el demo, si sueltas un estado de cuenta tuyo, el tablero se pasa solo a tu carpeta real
    iniciar(carpeta, a.puerto, abrir=not a.no_abrir, carpeta_real=Path(a.carpeta or RAIZ) if a.demo else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
