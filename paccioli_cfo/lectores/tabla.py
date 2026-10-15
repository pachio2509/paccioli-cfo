"""Lector universal de movimientos en CSV o Excel (casi cualquier banco o app los exporta).

Busca la fila de encabezados y reconoce columnas por su nombre:
  fecha        : fecha, fecha operacion, date, dia
  descripcion  : descripcion, concepto, detalle, movimiento, referencia, beneficiario
  cargo        : cargo, retiro, debito, egreso, salida, cargos, retiros
  abono        : abono, deposito, credito, ingreso, entrada, abonos, depositos
  importe      : importe, monto, cantidad, amount (con signo: negativo = cargo)
  saldo        : saldo, balance
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import re
import unicodedata
from pathlib import Path

from ..modelo import Movimiento

COLUMNAS = {
    "fecha": ("fecha", "fecha operacion", "fecha de operacion", "date", "dia", "fecha movimiento"),
    "descripcion": ("descripcion", "concepto", "detalle", "movimiento", "beneficiario", "description", "descripcion del movimiento"),
    "cargo": ("cargo", "cargos", "retiro", "retiros", "debito", "debitos", "egreso", "egresos", "salida", "salidas", "withdrawal", "debit"),
    "abono": ("abono", "abonos", "deposito", "depositos", "credito", "creditos", "ingreso", "ingresos", "entrada", "entradas", "deposit", "credit"),
    "importe": ("importe", "monto", "cantidad", "amount", "valor"),
    "saldo": ("saldo", "balance", "saldo final"),
    "referencia": ("referencia", "folio", "factura", "uuid", "reference"),
}
MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8, "sep": 9, "set": 9,
         "oct": 10, "nov": 11, "dic": 12, "jan": 1, "apr": 4, "aug": 8, "dec": 12}


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


def _num(v) -> float:
    if v is None or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("$", "").replace(" ", "")
    neg = s.startswith("(") and s.endswith(")") or s.startswith("-") or s.endswith("-")
    s = s.strip("()-")
    if s.count(",") and s.count(".") and s.rfind(",") > s.rfind("."):   # 1.234,56
        s = s.replace(".", "").replace(",", ".")
    elif "." not in s and s.count(",") == 1 and re.search(r",\d{1,2}$", s):  # 100,50
        s = s.replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        x = float(s)
    except ValueError:
        return 0.0
    return -x if neg else x


def _fecha(v) -> str:
    if isinstance(v, (dt.datetime, dt.date)):
        return v.strftime("%Y-%m-%d")
    s = str(v or "").strip()
    for f in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y", "%d.%m.%Y", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(s[:10], f).strftime("%Y-%m-%d")
        except ValueError:
            pass
    m = re.match(r"(\d{1,2})[/\- ]([A-Za-z]{3})[a-z]*[/\- ](\d{2,4})", s)
    if m and m.group(2).lower() in MESES:
        a = int(m.group(3))
        a = a + 2000 if a < 100 else a
        return f"{a}-{MESES[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
    return s


def _filas(ruta: Path) -> list[list]:
    if ruta.suffix.lower() in (".xlsx", ".xlsm"):
        import openpyxl
        wb = openpyxl.load_workbook(str(ruta), data_only=True)
        filas = []
        for ws in wb.worksheets:
            filas += [list(r) for r in ws.iter_rows(values_only=True)]
            filas.append([])  # separador entre hojas
        return filas
    raw = ruta.read_bytes()
    for enc in ("utf-8-sig", "utf-16", "latin-1"):
        try:
            texto = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    muestra = texto[:4000]
    sep = max((",", ";", "\t", "|"), key=muestra.count)
    return [r for r in csv.reader(io.StringIO(texto), delimiter=sep)]


def _mapear(encabezado: list) -> dict[str, int] | None:
    cols: dict[str, int] = {}
    for i, c in enumerate(encabezado):
        n = _norm(c)
        if not n:
            continue
        for campo, nombres in COLUMNAS.items():
            if campo not in cols and (n in nombres or any(n.startswith(x + " ") for x in nombres)):
                cols[campo] = i
                break
    if "fecha" in cols and ("cargo" in cols or "abono" in cols or "importe" in cols):
        return cols
    return None


def leer(ruta: str | Path, fuente: str | None = None) -> tuple[list[Movimiento], dict]:
    ruta = Path(ruta)
    fuente = fuente or ruta.stem
    movs: list[Movimiento] = []
    saldos: list[float] = []
    cols = None
    for fila in _filas(ruta):
        if not fila or all(c in (None, "") for c in fila):
            cols = None if fila == [] else cols
            continue
        if cols is None:
            cols = _mapear(fila)
            continue
        g = lambda k: fila[cols[k]] if k in cols and cols[k] < len(fila) else None
        fecha = _fecha(g("fecha"))
        if not re.match(r"\d{4}-\d{2}-\d{2}", fecha):
            continue
        cargo, abono = abs(_num(g("cargo"))), abs(_num(g("abono")))
        if "importe" in cols and not cargo and not abono:
            x = _num(g("importe"))
            cargo, abono = (-x, 0.0) if x < 0 else (0.0, x)
        if not cargo and not abono:
            continue
        movs.append(Movimiento(fuente=fuente, fecha=fecha, descripcion=str(g("descripcion") or "").strip(),
                               cargo=round(cargo, 2), abono=round(abono, 2), referencia=str(g("referencia") or "").strip(),
                               extra={"n": len(movs)}))
        if "saldo" in cols and g("saldo") not in (None, ""):
            saldos.append((len(movs) - 1, _num(g("saldo"))))
    if not movs:
        raise ValueError(f"No encontré movimientos en {ruta.name}: necesito columnas de fecha y cargo/abono (o importe).")
    fechas = sorted(m.fecha for m in movs)
    resumen = {"periodo": f"DEL {fechas[0]} AL {fechas[-1]}", "sin_saldos": not saldos}
    if saldos and len(saldos) == len(movs):
        resumen.update(_cuadre(movs, [x for _, x in saldos]))
    elif saldos:  # saldo solo en algunos renglones (fin de dia): se valida en esos puntos
        from .pdf_generico import _cuadre as cuadre_parcial
        resumen.update(cuadre_parcial(movs, saldos, None))
    return movs, resumen


def _cuadre(movs: list[Movimiento], saldos: list[float]) -> dict:
    """Revisa que cada saldo = saldo anterior + abono - cargo (en orden ascendente o descendente)."""
    neto = [m.abono - m.cargo for m in movs]
    asc = all(abs(saldos[i - 1] + neto[i] - saldos[i]) < .005 for i in range(1, len(movs)))
    desc = all(abs(saldos[i + 1] + neto[i] - saldos[i]) < .005 for i in range(len(movs) - 1))
    if desc and not asc:
        inicial, final = saldos[-1] - neto[-1], saldos[0]
    else:
        inicial, final = saldos[0] - neto[0], saldos[-1]
    return {"saldo_inicial": round(inicial, 2), "saldo_final": round(final, 2), "cuadre_saldos": asc or desc}
