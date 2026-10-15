"""Clasifica cada movimiento: primero tus reglas (lo que ya contestaste), luego
las reglas automaticas, luego deteccion de cuentas propias. Lo que no se
reconoce queda 'sin identificar' y se convierte en pregunta.
"""
from __future__ import annotations

import re
import unicodedata

from .categorias import CATEGORIAS, FINTECH, REGLAS_AUTO
from .modelo import Movimiento

RAZON = re.compile(r"\b(SA DE CV|S DE RL|SAPI|S\.A\.|SC|SAS|S A DE C V)\b")
RUIDO = {"DE", "DEL", "LA", "LAS", "LOS", "Y", "SA", "CV", "SAPI", "RL", "SC"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().upper()
    return re.sub(r"\s+", " ", s).strip()


def _tiene(texto: str, palabra: str) -> bool:
    prefijo = palabra.endswith("*")
    k = norm(palabra.rstrip("*")).strip()
    # solo letras como frontera: BBVA pega numeros de referencia al concepto ("1108260HONORARIOS")
    return re.search(r"(?<![A-Z])" + re.escape(k) + ("" if prefijo else r"(?![A-Z])"), texto) is not None


TRANSFERENCIA = ("SPEI ENVIADO", "PAGO CUENTA DE TERCERO", "TRANSFERENCIA A", "TRASPASO A TERCERO")


def _auto(texto: str, tipo: str, solo_fuertes: bool = False) -> str | None:
    for regla in REGLAS_AUTO:
        t, palabras, cat = regla[:3]
        if solo_fuertes and "fuerte" not in regla[3:]:
            continue
        if t not in (tipo, "ambos") or not any(_tiene(texto, p) for p in palabras):
            continue
        # "comision" en una transferencia a una persona es una comision que tu pagas, no una comision del banco
        if cat == "comisiones_banco" and any(x in texto for x in TRANSFERENCIA):
            return "comisiones_pagadas"
        return cat
    return None


def contraparte(m: Movimiento) -> str:
    """Nombre legible de quien paga o cobra, a partir de la descripcion del banco."""
    d = m.descripcion
    bnet = re.search(r"BNET \d+ (.+?)(?: Referencia| Ref\.|$)", d)
    if bnet:
        return bnet.group(1).strip().title()
    partes = [p.strip() for p in d.split("|") if p.strip()]
    if len(partes) >= 2:
        ultimo = partes[-1]
        if not any(ch.isdigit() for ch in ultimo) and len(re.sub(r"[^A-Za-z]", "", ultimo)) >= 3 and "REFERENCIA" not in ultimo.upper():
            return re.sub(r"[,/]", " ", ultimo).title()
    for p in reversed(partes[1:]):
        if RAZON.search(p.upper()) or (p.isupper() and len(p.split()) >= 2 and not any(ch.isdigit() for ch in p)):
            return p.title()
    if len(partes) <= 1:
        return _contraparte_simple(d)
    if partes and partes[0].upper().startswith("SPEI RECIBIDO"):
        concepto = re.sub(r"^\d{6,7}", "", partes[1].split(" Referencia")[0]).strip() if len(partes) > 1 else ""
        if not concepto or concepto.isdigit():
            return "Depósito SPEI sin nombre (" + partes[0].upper().replace("SPEI RECIBIDO", "").strip().title() + ")"
    if len(partes) >= 2 and partes[0].upper().startswith("SPEI"):
        concepto = re.sub(r"^\d{6,7}", "", partes[1].split(" Referencia")[0]).strip()
        if concepto:
            return concepto.title()[:48]
    base = partes[0] if partes else d
    base = re.sub(r"\b(REF|AUT|RFC)[:.].*$", "", base, flags=re.I).strip()
    base = re.sub(r"\s+Ref\.?\s*\d+.*$", "", base).strip()
    return (base or "Sin descripción").title()[:48]


MARCAS = ("CLIP", "GETNET", "BILLPOCKET", "SUMUP", "ZETTLE", "NETPAY", "STRIPE", "PAYPAL", "SHOPIFY", "MERCADO PAGO",
          "MERCADO LIBRE", "AMAZON", "RAPPI", "UBER EATS", "DIDI FOOD", "CONEKTA", "OPENPAY", "AMERICAN EXPRESS", "CFE",
          "TELMEX", "TOTALPLAY", "IZZI", "TELCEL", "GOOGLE", "META ADS", "FACEBK", "SIPARE", "SAT")
PREFIJOS = r"^(SPEI|TRANSFERENCIA|TRANSF|DEPOSITO|DEP|PAGO|ABONO|CARGO|COMPRA|RECIBIDO|ENVIADO|INTERBANCARIA|EN|DE|A|POR)\b\s*"


def _contraparte_simple(d: str) -> str:
    """Descripcion de una sola pieza (tipico de CSV/Excel): quita prefijos, folios y referencias."""
    u = norm(d)
    for marca in MARCAS:
        if re.search(r"(?<![A-Z])" + re.escape(marca) + r"(?![A-Z])", u):
            return {"FACEBK": "Meta Ads", "SAT": "SAT", "CFE": "CFE", "SIPARE": "IMSS (SIPARE)"}.get(marca, marca.title())
    t = d.upper()
    t = re.sub(r"\b(REF|REFERENCIA|AUT|RFC|FOLIO|CONCEPTO)\b[:.]?.*$", "", t).strip()
    for _ in range(4):
        t = re.sub(PREFIJOS, "", t).strip()
    m = RAZON.search(t)
    if m:
        t = t[:m.end()]
    t = re.sub(r"\s*\b\d[\d/\-]*\b", "", t).strip(" -,.")
    return (t or d or "Sin descripción").title()[:48]


def clave(m: Movimiento) -> str:
    """Llave estable para agrupar movimientos 'parecidos' (misma contraparte)."""
    return norm(m.contraparte)[:40]


def _tokens(nombre: str) -> list[str]:
    return [t for t in norm(nombre).split() if len(t) >= 3 and t not in RUIDO]


def es_cuenta_propia(m: Movimiento, titular: str | None) -> bool:
    if not titular:
        return False
    tit = _tokens(titular)
    if not tit:
        return False
    cp = set(_tokens(m.contraparte))
    if len(set(tit) & cp) >= min(2, len(tit)):
        return True
    texto = norm(m.descripcion)
    return any(f in texto for f in FINTECH) and tit[0] in cp


def clasificar(movs: list[Movimiento], reglas_usuario: list[dict], titular: str | None = None) -> list[Movimiento]:
    for m in movs:
        m.contraparte = m.contraparte or contraparte(m)
        texto = norm(m.descripcion + " " + m.referencia)
        tipo = "abono" if m.abono else "cargo"
        k = clave(m)
        hecho = False
        for r in reglas_usuario:  # tus respuestas mandan
            if r.get("tipo") not in (None, tipo, "ambos"):
                continue
            if (r.get("clave") and r["clave"] == k) or (r.get("texto") and _tiene(texto, r["texto"])) or r.get("id") == m.id:
                m.categoria, m.regla = r["categoria"], "tuya"
                hecho = True
                break
        if hecho:
            continue
        cat = _auto(texto, tipo, solo_fuertes=True)
        if not cat and es_cuenta_propia(m, titular):
            m.categoria, m.regla = "traspaso_propio", "auto: cuenta propia"
            continue
        cat = cat or _auto(texto, tipo)
        if cat:
            m.categoria, m.regla = cat, "auto"
        else:
            if m.abono and _anonimo(m):  # un deposito grande sin nombre suele ser dinero tuyo: no lo cuento como venta
                m.categoria, m.regla = "entrada_por_identificar", "supuesto"
            elif m.abono:  # casi todo lo que entra a un negocio es venta: se supone y se pregunta si es grande
                m.categoria, m.regla = "ventas", "supuesto"
            else:
                m.categoria, m.regla = "sin_identificar", "sin regla"
    return movs


def _anonimo(m: Movimiento) -> bool:
    return "sin nombre" in (m.contraparte or "").lower()


def seccion(m: Movimiento) -> str:
    return CATEGORIAS[m.categoria]["seccion"]
