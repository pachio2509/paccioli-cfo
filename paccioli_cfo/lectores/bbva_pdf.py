"""Lector de estados de cuenta BBVA en PDF (agrega fechas completas y titular): Maestra Pyme (empresas) y Libretón (personas).

Reglas aprendidas con estados de cuenta reales de empresa y de persona fisica (2026):
- Cargo vs abono se decide por la COLUMNA del importe, nunca por el codigo:
  N06 "PAGO CUENTA DE TERCERO" sirve para cobros y para pagos.
- Las columnas se ubican con el encabezado CARGOS / ABONOS / OPERACION /
  LIQUIDACION (los importes van alineados a la derecha: se compara el borde
  derecho x1). Maestra Pyme repite el encabezado en cada pagina; Libreton solo
  lo trae en la primera.
- En cada pagina el detalle empieza despues de "OPER LIQ"; si la pagina no lo
  tiene (Libreton), despues del bloque "No. de Cliente". Termina en
  "Total de Movimientos". No se filtra por altura fija.
- Un movimiento puede partirse entre paginas; su importe puede venir en la
  linea de continuacion.
"""
from __future__ import annotations

import re
from pathlib import Path

from ..modelo import Movimiento

AMT = re.compile(r"^\d{1,3}(,\d{3})*\.\d{2}$")
FECHA = re.compile(r"^\d{2}/[A-Z]{3}$")
PIE = ("BBVA MEXICO", "Estimado Cliente", "La GAT Real", "Av. Paseo de la Reforma")
COLS = {"CARGOS": "cargo", "ABONOS": "abono", "OPERACION": "saldo_op", "OPERACIÓN": "saldo_op",
        "LIQUIDACION": "saldo_liq", "LIQUIDACIÓN": "saldo_liq"}


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def _columnas(pdf) -> dict[str, float]:
    """Borde derecho de cada columna, tomado del primer encabezado del documento."""
    for page in pdf.pages:
        lineas: dict[int, list] = {}
        for w in page.extract_words():
            if w["text"] in COLS:
                lineas.setdefault(round(w["top"]), []).append(w)
        for ws in lineas.values():
            cols = {COLS[w["text"]]: w["x1"] for w in ws}
            if "cargo" in cols and "abono" in cols:
                return cols
    raise ValueError("No encontre el encabezado CARGOS/ABONOS: ¿es un estado de cuenta BBVA?")


def _lineas(page, tol: float = 2.5) -> dict[float, list]:
    """Agrupa palabras en renglones tolerando diferencias de 1-2 pt en 'top' (Libreton)."""
    lineas: dict[float, list] = {}
    actual = None
    for w in sorted(page.extract_words(), key=lambda w: w["top"]):
        if actual is None or w["top"] - actual > tol:
            actual = w["top"]
            lineas[actual] = []
        lineas[actual].append(w)
    return lineas


def _columna(x1: float, cols: dict[str, float]) -> str:
    return min(cols, key=lambda k: abs(cols[k] - x1))


def leer(ruta: str | Path, fuente: str = "BBVA") -> tuple[list[Movimiento], dict]:
    import pdfplumber

    movs: list[Movimiento] = []
    with pdfplumber.open(str(ruta)) as pdf:
        cols = _columnas(pdf)
        texto_ini = "\n".join((p.extract_text() or "") for p in pdf.pages[:2])
        resumen = _resumen(texto_ini)
        resumen["titular"] = titular(texto_ini)
        terminado = False
        for page in pdf.pages:
            if terminado:
                break
            lineas = _lineas(page)
            textos = {top: " ".join(w["text"] for w in sorted(ws, key=lambda w: w["x0"])) for top, ws in lineas.items()}
            tiene_oper = any(t.startswith("OPER LIQ") for t in textos.values())
            empezo = False
            for top in sorted(lineas):
                ws = sorted(lineas[top], key=lambda w: w["x0"])
                t = [w["text"] for w in ws]
                s = textos[top]
                if not empezo:
                    if (tiene_oper and s.startswith("OPER LIQ")) or (not tiene_oper and "No. de Cliente" in s):
                        empezo = True
                    continue
                if s.startswith("Total de Movimientos"):
                    terminado = True
                    break
                if s.startswith(PIE):
                    break
                if len(t) >= 3 and FECHA.match(t[0]) and FECHA.match(t[1]):
                    m = Movimiento(fuente=fuente, fecha=t[0], descripcion="")
                    m.codigo = t[2] if re.fullmatch(r"[A-Z]\d{2}", t[2]) else ""
                    partes = []
                    for w in ws[2 if not m.codigo else 3:]:
                        if AMT.match(w["text"]):
                            col = _columna(w["x1"], cols)
                            if col == "cargo":
                                m.cargo = _num(w["text"])
                            elif col == "abono":
                                m.abono = _num(w["text"])
                        else:
                            partes.append(w["text"])
                    m.extra["lineas"] = [" ".join(partes)]
                    movs.append(m)
                elif movs:
                    m = movs[-1]
                    for w in ws:
                        if AMT.match(w["text"]):
                            col = _columna(w["x1"], cols)
                            if col == "cargo" and not m.cargo:
                                m.cargo = _num(w["text"])
                            elif col == "abono" and not m.abono:
                                m.abono = _num(w["text"])
                    m.extra["lineas"].append(" ".join(x for x in t if not AMT.match(x)))
    fechas_iso(movs, resumen.get("periodo"))
    for m in movs:
        m.descripcion = " | ".join(x for x in m.extra.pop("lineas") if x)
        usd = re.search(r"USD\s*([\d.,]+)\s*TC0?([\d.]+)", m.descripcion)
        if usd:
            m.extra["usd"] = _num(usd.group(1))
            m.extra["tc"] = float(usd.group(2))
    return movs, resumen


def _resumen(texto: str) -> dict:
    """Saldo inicial/final, conteos y datos del titular del resumen del estado de cuenta."""
    r: dict = {}
    pats = {
        "saldo_inicial": r"(?:Saldo de Operaci[oó]n Inicial|Saldo Anterior)\s+([\d,]+\.\d{2})",
        "saldo_final": r"Saldo Final(?: \(\+\))?\s+([\d,]+\.\d{2})",
    }
    for k, p in pats.items():
        mm = re.search(p, texto)
        if mm:
            r[k] = _num(mm.group(1))
    for k, p in {"periodo": r"Periodo\s+(DEL .+? AL \S+)", "cuenta": r"No\. de Cuenta\s+(\d+)",
                 "rfc": r"R\.F\.C\s+([A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3})", "producto": r"(Maestra Pyme|MAESTRA PYME|Libret[oó]n[^\n]*)"}.items():
        mm = re.search(p, texto)
        if mm:
            r[k] = mm.group(1).strip()
    dep = re.search(r"Dep[oó]sitos / Abonos \(\+\)\s+(\d+)\s+([\d,]+\.\d{2})", texto)
    ret = re.search(r"Retiros / Cargos \(-\)\s+(\d+)\s+([\d,]+\.\d{2})", texto)
    if dep:
        r["n_abonos"], r["abonos"] = int(dep.group(1)), _num(dep.group(2))
    if ret:
        r["n_cargos"], r["cargos"] = int(ret.group(1)), _num(ret.group(2))
    return r


MESES = {"ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6, "JUL": 7, "AGO": 8,
         "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12}
NO_ES_NOMBRE = ("ESTADO DE CUENTA", "MAESTRA", "LIBRET", "PAGINA", "INFORMACI", "DOMICILIO", "MONEDA", "PERIODO",
                "FECHA DE CORTE", "NO. DE", "R.F.C", "SUCURSAL", "DIRECCION", "PLAZA", "TELEFONO", "BBVA")


def fechas_iso(movs: list[Movimiento], periodo: str | None) -> None:
    """Convierte '07/SEP' a '2026-09-07' usando el anio del periodo (maneja cortes dic-ene)."""
    anio_fin = None
    mes_fin = None
    if periodo:
        mm = re.findall(r"(\d{2})/(\d{2})/(\d{4})", periodo)
        if mm:
            anio_fin, mes_fin = int(mm[-1][2]), int(mm[-1][1])
    for i, m in enumerate(movs):
        m.extra["n"] = i
        d = re.match(r"(\d{2})/([A-Z]{3})", m.fecha)
        if not d or not anio_fin:
            continue
        mes = MESES.get(d.group(2))
        if not mes:
            continue
        anio = anio_fin - 1 if mes > mes_fin else anio_fin
        m.fecha = f"{anio}-{mes:02d}-{int(d.group(1)):02d}"


def titular(texto: str) -> str | None:
    """Nombre del titular: la primera linea en mayusculas que parece nombre de persona o empresa."""
    for linea in texto.splitlines()[:40]:
        s = re.split(r"\s{2,}|Periodo|Fecha de Corte|No\. de|R\.F\.C|SUCURSAL", linea.strip())[0].strip()
        if not s or any(k in s.upper() for k in NO_ES_NOMBRE) or any(ch.isdigit() for ch in s):
            continue
        if s.isupper() and len(s.split()) >= 2 and len(s) <= 70:
            return s
    return None
