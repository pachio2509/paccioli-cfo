"""Tu tablero en un solo archivo HTML: se abre con doble clic, sin servidor y sin internet.

Lo usa Claude cuando lee tu estado de cuenta desde claude.ai, y sirve para mandarle tu tablero a tu socio o a tu contador.
Lleva tus números adentro: compártelo solo con quien tú quieras.
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path

WEB = Path(__file__).parent / "web"


def _data_uri(ruta: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(ruta.read_bytes()).decode()


def html(estado: dict) -> str:
    pagina = (WEB / "index.html").read_text(encoding="utf-8")
    css = (WEB / "estilos.css").read_text(encoding="utf-8")
    js = (WEB / "app.js").read_text(encoding="utf-8")
    imagenes = {"/" + p.relative_to(WEB).as_posix(): _data_uri(p) for p in list(WEB.glob("*.png")) + list(WEB.glob("lucca/*.png"))}

    def incrustar(texto: str) -> str:
        for ruta, uri in imagenes.items():
            texto = texto.replace(f'"{ruta}"', f'"{uri}"').replace(f"'{ruta}'", f"'{uri}'")
        return texto

    # las poses de Lucca se arman en JS ("/lucca/lucca-" + pose + ".png"): se pasan como mapa
    poses = {Path(r).stem.replace("lucca-", ""): u for r, u in imagenes.items() if "/lucca/" in r}
    from . import marca as mod_marca
    logo = mod_marca.ruta_logo(mod_marca.cargar())
    if logo and estado.get("marca"):
        tipo = {".jpg": "jpeg", ".jpeg": "jpeg", ".webp": "webp", ".svg": "svg+xml"}.get(logo.suffix.lower(), "png")
        estado = {**estado, "marca": {**estado["marca"], "logo_url": f"data:image/{tipo};base64," + base64.b64encode(logo.read_bytes()).decode()}}
    from . import __version__
    estado = {**estado, "app": __version__}
    datos = json.dumps(estado, ensure_ascii=False).replace("</", "<\\/")
    pagina = pagina.replace('<link rel="stylesheet" href="/estilos.css">', f"<style>{css}</style>")
    pagina = pagina.replace('<script src="/app.js"></script>',
                            f"<script>window.__ESTADO__ = {datos};\nwindow.__LUCCA__ = {json.dumps(poses)};</script>\n<script>{js}</script>")
    return incrustar(pagina)


def guardar(estado: dict, salida: str | Path) -> Path:
    salida = Path(salida)
    salida.write_text(html(estado), encoding="utf-8")
    return salida


def _nombre(estado: dict) -> str:
    import unicodedata
    nombre = unicodedata.normalize("NFKD", estado.get("negocio") or "mi-negocio").encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", nombre.lower()).strip("-") or "mi-negocio"
    return f"tablero-{base}.html"
