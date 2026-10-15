"""Servidor local del tablero. Solo escucha en tu compu (127.0.0.1): nada sale a internet.

- Vigila la carpeta mis-estados-de-cuenta: si sueltas un archivo nuevo, el tablero se recalcula solo.
- El navegador pregunta cada 2 segundos si hubo cambios (/api/version) y se actualiza en vivo.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import __version__, motor, preguntas
from .espacio import Espacio
from .lectores import SOPORTADOS

WEB = Path(__file__).parent / "web"
TIPOS = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


class Estado:
    """Cachea el analisis y lo recalcula solo cuando cambian tus archivos o respuestas."""

    def __init__(self, espacio: Espacio):
        self.espacio = espacio
        self.lock = threading.Lock()
        self.firma = None
        self.datos = None
        self.version = "0"

    def obtener(self) -> dict:
        with self.lock:
            f = self.espacio.firma()
            if f != self.firma or self.datos is None:
                try:
                    self.datos = motor.analizar(self.espacio)
                except Exception as ex:  # noqa: BLE001
                    traceback.print_exc()
                    self.datos = {"error": str(ex)}
                self.firma = f
                self.version = hashlib.sha1(f.encode()).hexdigest()[:10]
            return self.datos

    def vigilar(self, cada: float = 2.0) -> None:
        def ciclo():
            while True:
                time.sleep(cada)
                try:
                    if self.espacio.firma() != self.firma:
                        self.obtener()
                        print(f"  ↻ Cambios detectados: tablero actualizado ({time.strftime('%H:%M:%S')})")
                except Exception:  # noqa: BLE001
                    traceback.print_exc()
        threading.Thread(target=ciclo, daemon=True).start()


def crear_handler(estado: Estado):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):  # silencio en consola
            pass

        def _json(self, obj, code=200):
            b = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def _cuerpo(self) -> bytes:
            n = int(self.headers.get("Content-Length") or 0)
            if n > 60 * 1024 * 1024:
                raise ValueError("Archivo demasiado grande (máximo 60 MB).")
            return self.rfile.read(n)

        def do_GET(self):
            u = urlparse(self.path)
            if u.path == "/api/estado":
                d = estado.obtener()
                return self._json({**d, "version": estado.version, "app": __version__})
            if u.path == "/api/version":
                estado.obtener()
                return self._json({"version": estado.version})
            nombre = "index.html" if u.path in ("/", "") else u.path.lstrip("/")
            ruta = (WEB / nombre).resolve()
            if u.path == "/marca/logo":  # el logo de tu marca (marca.json)
                from . import marca
                ruta = marca.ruta_logo(marca.cargar())
                permitido = ruta is not None
            else:
                permitido = WEB.resolve() in ruta.parents and ruta.is_file()
            if not permitido:
                self.send_error(404)
                return
            b = ruta.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", TIPOS.get(ruta.suffix, "application/octet-stream"))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_POST(self):
            u = urlparse(self.path)
            esp = estado.espacio
            try:
                if u.path == "/api/subir":
                    nombre = unquote(parse_qs(u.query).get("nombre", ["estado.pdf"])[0])
                    nombre = re.sub(r"[^\w.\- ]", "_", Path(nombre).name)[:120]
                    if esp.es_demo:
                        return self._json({"ok": False, "error": "Estás en el demo de Café La Ceiba. Para usar tus datos, cierra esta ventana y abre Paccioli CFO sin --demo: ./iniciar.sh"}, 400)
                    if Path(nombre).suffix.lower() not in SOPORTADOS:
                        return self._json({"ok": False, "error": "Sube el PDF, Excel o CSV de tu estado de cuenta."}, 400)
                    destino = esp.estados / nombre
                    destino.write_bytes(self._cuerpo())
                    return self._json({"ok": True, "archivo": nombre})
                datos = json.loads(self._cuerpo() or b"{}")
                if u.path == "/api/responder":
                    preguntas.responder(esp, datos["id"], datos["valor"])
                elif u.path == "/api/reclasificar":
                    preguntas.responder(esp, "id:" + datos["id"], datos["categoria"])
                elif u.path == "/api/quitar_archivo":
                    origen = (esp.estados / Path(datos["nombre"]).name)
                    papelera = esp.datos / "archivos-quitados"
                    papelera.mkdir(exist_ok=True)
                    if origen.exists():
                        shutil.move(str(origen), str(papelera / origen.name))
                elif u.path == "/api/reiniciar":
                    esp.borrar_respuestas()
                else:
                    return self._json({"ok": False, "error": "Ruta desconocida"}, 404)
                return self._json({"ok": True})
            except Exception as ex:  # noqa: BLE001
                return self._json({"ok": False, "error": str(ex)}, 400)
    return H


def iniciar(carpeta: str | Path, puerto: int = 8765, abrir: bool = True) -> None:
    esp = Espacio(carpeta)
    estado = Estado(esp)
    estado.obtener()
    estado.vigilar()
    srv = None
    for p in range(puerto, puerto + 20):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", p), crear_handler(estado))
            puerto = p
            break
        except OSError:
            continue
    if srv is None:
        raise SystemExit("No encontré un puerto libre entre 8765 y 8785.")
    url = f"http://127.0.0.1:{puerto}"
    print(f"""
  ┌──────────────────────────────────────────────────────────┐
  │  PACCIOLI CFO · tu tablero financiero está en vivo       │
  └──────────────────────────────────────────────────────────┘
   Abre:      {url}
   Suelta tus estados de cuenta en:
              {esp.estados}
   Tus datos se quedan en tu compu. Para salir: Ctrl + C
""")
    if abrir:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  Hasta luego. Tus respuestas quedaron guardadas en", esp.datos)
