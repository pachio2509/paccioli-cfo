"""Lee cualquier archivo soportado y devuelve (movimientos, resumen)."""
from __future__ import annotations

from pathlib import Path

from . import bbva_pdf, tabla

SOPORTADOS = (".pdf", ".csv", ".xlsx", ".xlsm", ".txt")


def leer(ruta: str | Path):
    ruta = Path(ruta)
    ext = ruta.suffix.lower()
    if ext == ".pdf":
        import pdfplumber
        with pdfplumber.open(str(ruta)) as pdf:
            inicio = "\n".join((p.extract_text() or "") for p in pdf.pages[:2])
        if "BBVA" in inicio.upper():
            movs, res = bbva_pdf.leer(ruta, "BBVA " + ("Libretón" if "LIBRET" in inicio.upper() else "Empresas"))
            res["banco"] = "BBVA"
            return movs, res
        raise ValueError(f"{ruta.name}: por ahora leo PDF de BBVA. De otros bancos descarga tus movimientos en Excel o CSV "
                         f"desde tu banca en línea y suéltalos aquí.")
    if ext in (".csv", ".xlsx", ".xlsm", ".txt"):
        return tabla.leer(ruta)
    raise ValueError(f"{ruta.name}: formato no soportado. Usa PDF de BBVA, Excel o CSV.")
