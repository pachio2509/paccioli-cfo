"""Lector de estados de cuenta en PDF de cualquier banco (Santander, Banorte, Banamex, HSBC, Scotiabank, Nu, Hey...).

Cómo funciona, sin plantillas por banco:
1. Agrupa las palabras de cada página en renglones.
2. Un movimiento es un renglón que empieza con fecha (07/09/2026, 07/09/26, 07-SEP-26, 07 SEP, 07/SEP) y trae importes.
   Los renglones de abajo sin fecha ni importes se pegan a la descripción.
3. Cargo o abono, en este orden de confianza:
   a) por la columna del importe, si encuentra el encabezado (CARGOS/RETIROS/DÉBITOS y ABONOS/DEPÓSITOS/CRÉDITOS);
   b) por cómo cambia el saldo (saldo anterior + abono - cargo = saldo);
   c) por palabras del concepto (DEPÓSITO, RECIBIDO, ABONO...).
4. Valida al centavo: cada saldo impreso debe cuadrar con la suma de los movimientos.
   Si no cuadra, el tablero lo dice en rojo en vez de enseñarte números malos.
"""
from __future__ import annotations

import datetime as dt
import re
import unicodedata
from pathlib import Path

from ..modelo import Movimiento

IMPORTE = re.compile(r"^\(?-?\$?\s?\d{1,3}(?:,\d{3})*\.\d{2}\)?-?$")
MESES = {"ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6, "JUL": 7, "AGO": 8, "SEP": 9, "SET": 9,
         "OCT": 10, "NOV": 11, "DIC": 12, "JAN": 1, "APR": 4, "AUG": 8, "DEC": 12}
COL_CARGO = ("CARGO", "CARGOS", "RETIRO", "RETIROS", "DEBITO", "DEBITOS", "DEBE", "SALIDAS", "EGRESOS", "WITHDRAWALS")
COL_ABONO = ("ABONO", "ABONOS", "DEPOSITO", "DEPOSITOS", "CREDITO", "CREDITOS", "HABER", "ENTRADAS", "INGRESOS", "DEPOSITS")
COL_SALDO = ("SALDO", "SALDOS", "BALANCE")
PALABRAS_ABONO = ("DEPOSITO", "RECIBIDO", "ABONO", "ABONO DE", "SPEI RECIBIDO", "TRANSFERENCIA RECIBIDA", "INTERESES", "DEVOLUCION",
                  "REEMBOLSO", "NOMINA RECIBIDA", "CREDITO A CUENTA")
SALTAR = ("SALDO ANTERIOR", "SALDO INICIAL", "SALDO AL CORTE", "SALDO FINAL", "TOTAL DE", "TOTALES", "SALDO PROMEDIO")
BANCOS = ("SANTANDER", "BANORTE", "BANAMEX", "CITIBANAMEX", "HSBC", "SCOTIABANK", "INBURSA", "BANREGIO", "BANBAJIO", "BAJIO",
          "AFIRME", "BANCO AZTECA", "BANCOPPEL", "HEY BANCO", "NU MEXICO", "NU ", "MIFEL", "MONEX", "BX+", "INVEX", "BBVA",
          "MERCADO PAGO", "KLAR", "STORI", "SPIN", "UALA", "ALBO", "REVOLUT", "BANCO BASE", "VE POR MAS")


def _n(s: str) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().upper()


def _num(s: str) -> float:
    neg = s.startswith(("(", "-")) or s.endswith("-")
    x = float(re.sub(r"[^\d.]", "", s))
    return -x if neg else x


def _renglones(page, tol: float = 2.5) -> list[list[dict]]:
    out, actual, top = [], [], None
    for w in sorted(page.extract_words(keep_blank_chars=False, use_text_flow=False), key=lambda w: (round(w["top"]), w["x0"])):
        if top is None or w["top"] - top > tol:
            if actual:
                out.append(sorted(actual, key=lambda w: w["x0"]))
            actual, top = [], w["top"]
        actual.append(w)
    if actual:
        out.append(sorted(actual, key=lambda w: w["x0"]))
    return out


def _anio_base(texto: str) -> int:
    anios = [int(a) for a in re.findall(r"\b(20\d{2})\b", texto)]
    return max(set(anios), key=anios.count) if anios else dt.date.today().year


def _fecha(palabras: list[str], anio: int) -> tuple[str | None, int]:
    """Fecha al inicio del renglón. Devuelve (ISO, cuántas palabras ocupó)."""
    if not palabras:
        return None, 0
    p0 = _n(palabras[0])
    m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})$", p0)
    if m:
        a = int(m.group(3)); a = a + 2000 if a < 100 else a
        return _iso(a, int(m.group(2)), int(m.group(1))), 1
    m = re.match(r"^(\d{1,2})[/\-.]?([A-Z]{3})[A-Z]*[/\-.]?(\d{2,4})?$", p0)
    if m and m.group(2) in MESES:
        a = int(m.group(3)) if m.group(3) else anio
        a = a + 2000 if a < 100 else a
        return _iso(a, MESES[m.group(2)], int(m.group(1))), 1
    if re.match(r"^\d{1,2}$", p0) and len(palabras) > 1 and _n(palabras[1])[:3] in MESES:
        usa = 2
        a = anio
        if len(palabras) > 2 and re.match(r"^(20)?\d{2}$", palabras[2]):
            a = int(palabras[2]); a = a + 2000 if a < 100 else a
            usa = 3
        return _iso(a, MESES[_n(palabras[1])[:3]], int(p0)), usa
    return None, 0


def _iso(a: int, m: int, d: int) -> str | None:
    try:
        return dt.date(a, m, d).isoformat()
    except ValueError:
        return None


def _columnas(paginas) -> dict[str, float]:
    """Borde derecho de las columnas de importes, si el PDF trae encabezado."""
    for ren in (r for pag in paginas for r in pag):
        cols = {}
        for w in ren:
            t = re.sub(r"[^A-Z]", "", _n(w["text"]))
            if t in COL_CARGO and "cargo" not in cols:
                cols["cargo"] = w["x1"]
            elif t in COL_ABONO and "abono" not in cols:
                cols["abono"] = w["x1"]
            elif t in COL_SALDO and "saldo" not in cols:
                cols["saldo"] = w["x1"]
        if "cargo" in cols and "abono" in cols:
            return cols
    return {}


def _periodo(tx: str, anio: int) -> str | None:
    """'Periodo del 07/09/2026 al 06/10/2026' o 'Periodo 15-SEP-26 al 14-OCT-26' -> 'DEL 07/09/2026 AL 06/10/2026'."""
    f = r"(\d{1,2}[/\-. ](?:\d{1,2}|[A-Z]{3})[A-Z]*[/\-. ]\d{2,4})"
    m = re.search(r"(?:PERIODO|DEL|CORTE)\D{0,20}?" + f + r"\s+(?:AL|A|-)\s+" + f, tx)
    if not m:
        return None
    a, _ = _fecha([re.sub(r"[ .]", "/", m.group(1))], anio)
    b, _ = _fecha([re.sub(r"[ .]", "/", m.group(2))], anio)
    if not a or not b:
        return None
    dmy = lambda x: f"{x[8:10]}/{x[5:7]}/{x[:4]}"
    return f"DEL {dmy(a)} AL {dmy(b)}"


def _saldo_anterior(texto: str) -> float | None:
    m = re.search(r"SALDO (?:ANTERIOR|INICIAL)[^\d\n]{0,40}\$?\s?(\d{1,3}(?:,\d{3})*\.\d{2})", _n(texto))
    return _num(m.group(1)) if m else None


def leer(ruta: str | Path) -> tuple[list[Movimiento], dict]:
    import pdfplumber

    with pdfplumber.open(str(ruta)) as pdf:
        paginas = [_renglones(p) for p in pdf.pages]
        texto = "\n".join((p.extract_text() or "") for p in pdf.pages)
    tx = _n(texto)
    cabeza = "\n".join(l for l in _n(texto[:2500]).splitlines() if not re.search(r"SPEI|TRANSF|RECIBID|ENVIAD", l))
    hallados = [(cabeza.find(b), b.strip()) for b in BANCOS if b in cabeza]
    banco = min(hallados)[1] if hallados else "PDF"  # el banco que aparece primero en el encabezado
    anio = _anio_base(texto)
    cols = _columnas(paginas)
    inicial = _saldo_anterior(texto)

    crudos = []  # [fecha, descripcion, [(importe, x1)], top]
    pendiente = []  # texto sin fecha: puede ser del movimiento de arriba o del de abajo (celdas de 2 lineas)

    def pegar(i: int, t: str, antes: bool) -> None:
        if len(crudos[i][1]) < 220:
            crudos[i][1] = (t + " " + crudos[i][1] if antes else crudos[i][1] + " | " + t).strip()

    def soltar(top_nuevo: float | None) -> None:
        for tp, t in pendiente:
            if top_nuevo is None:
                if tp - crudos[-1][3] < 30:  # lo que sigue al ultimo movimiento, no el pie de pagina
                    pegar(-1, t, False)
            elif top_nuevo - tp < 20 and (len(crudos) < 2 or top_nuevo - tp < tp - crudos[-2][3]):
                pegar(-1, t, True)  # mas cerca del movimiento de abajo
            elif len(crudos) >= 2 and tp - crudos[-2][3] < 30:
                pegar(-2, t, False)
        pendiente.clear()

    for pag_i, pag in enumerate(paginas):
        for ren in pag:
            top = ren[0]["top"] + pag_i * 10000
            palabras = [w["text"] for w in ren]
            fecha, usa = _fecha(palabras, anio)
            importes = [(w["text"], w["x1"]) for w in ren if IMPORTE.match(w["text"].replace(" ", ""))]
            texto_ren = " ".join(w["text"] for w in ren[usa:] if not IMPORTE.match(w["text"].replace(" ", "")))
            if fecha:
                # bancos que repiten la fecha (operacion y liquidacion)
                f2, usa2 = _fecha(palabras[usa:], anio)
                if f2:
                    texto_ren = " ".join(w["text"] for w in ren[usa + usa2:] if not IMPORTE.match(w["text"].replace(" ", "")))
                if any(s in _n(texto_ren) for s in SALTAR):
                    pendiente.clear()
                    continue
                crudos.append([fecha, texto_ren.strip(), importes, top])
                soltar(top)
            elif crudos and importes and not crudos[-1][2]:
                crudos[-1][2] = importes
                crudos[-1][1] = (crudos[-1][1] + " " + texto_ren).strip()
            elif not importes and texto_ren and not any(s in _n(texto_ren) for s in SALTAR + ("PAGINA", "HOJA")):
                pendiente.append((top, texto_ren))
            elif importes:
                pendiente.clear()  # renglon con importes que no es movimiento (totales, resumen)
    if crudos:
        soltar(None)

    movs, saldos_imp, previo = [], [], inicial
    for fecha, desc, importes, _ in crudos:
        if not importes:
            continue
        cargo = abono = 0.0
        saldo = None
        if cols:
            borde = max(cols["cargo"], cols["abono"]) + 25
            for t, x1 in importes:
                v = _num(t)
                if abs(x1 - cols["cargo"]) <= 25 and not cargo:
                    cargo = abs(v)
                elif abs(x1 - cols["abono"]) <= 25 and not abono:
                    abono = abs(v)
                elif x1 > borde and saldo is None:
                    saldo = v  # la primera columna a la derecha de cargos/abonos es el saldo
        if not cols or (not cargo and not abono):
            vals = [_num(t) for t, _ in importes]
            if len(vals) >= 2:
                importe, saldo = abs(vals[-2]), vals[-1]
                if previo is not None and abs(previo - importe - saldo) < 0.01:
                    cargo = importe
                elif previo is not None and abs(previo + importe - saldo) < 0.01:
                    abono = importe
                else:
                    cargo, abono = (0.0, importe) if any(p in _n(desc) for p in PALABRAS_ABONO) else (importe, 0.0)
            else:
                v = vals[0]
                if v < 0:
                    cargo = -v
                else:
                    cargo, abono = (0.0, v) if any(p in _n(desc) for p in PALABRAS_ABONO) else (v, 0.0)
        if not cargo and not abono:
            continue
        movs.append(Movimiento(fuente=banco.title(), fecha=fecha, descripcion=desc or "Sin descripción",
                               cargo=round(cargo, 2), abono=round(abono, 2), extra={"n": len(movs)}))
        if saldo is not None:
            saldos_imp.append((len(movs) - 1, saldo))
            previo = saldo
        elif previo is not None:
            previo = round(previo + abono - cargo, 2)

    if not movs:
        raise ValueError(f"{Path(ruta).name}: no encontré movimientos en este PDF. Descarga tus movimientos en Excel o CSV "
                         "desde tu banca en línea, o pídele a Claude que lo convierta (ver README).")
    fechas = sorted(m.fecha for m in movs)
    if banco == "PDF":  # banco que no conozco: uso el nombre de su encabezado
        primera = next((l.strip() for l in texto.splitlines() if l.strip()), "")
        banco = re.split(r"[·|,]| - ", primera)[0].strip()[:40] or "PDF"
    res = {"banco": banco.title() if banco.isupper() else banco, "periodo": _periodo(tx, anio) or f"DEL {fechas[0]} AL {fechas[-1]}"}
    res["periodo_inferido"] = not _periodo(tx, anio)
    rfc = re.search(r"\b([A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3})\b", tx)
    if rfc:
        res["rfc"] = rfc.group(1)
    res.update(_cuadre(movs, saldos_imp, inicial))
    return movs, res


def _cuadre(movs, saldos_imp, inicial) -> dict:
    """Cada saldo impreso = saldo anterior + abonos - cargos. Sin saldos impresos no se puede validar."""
    if not saldos_imp:
        return {"sin_saldos": True}
    i0, s0 = saldos_imp[0]
    base = inicial if inicial is not None else s0 - (movs[i0].abono - movs[i0].cargo) - sum(m.abono - m.cargo for m in movs[:i0])
    corrido, ok, j = base, True, 0
    for i, m in enumerate(movs):
        corrido += m.abono - m.cargo
        while j < len(saldos_imp) and saldos_imp[j][0] == i:
            ok = ok and abs(corrido - saldos_imp[j][1]) < 0.01
            j += 1
    return {"saldo_inicial": round(base, 2), "saldo_final": round(corrido, 2), "cuadre_saldos": ok}
