"""Lo que el CFO te pregunta para entender tu negocio. Cada respuesta se guarda y
se aplica sola a todos los movimientos parecidos, hoy y en los meses que vengan."""
from __future__ import annotations

from collections import defaultdict

from .categorias import OPCIONES_ABONO, OPCIONES_CARGO
from .clasificador import clave

MAX_MOVS = 12


def _peso(x: float) -> str:
    return f"${x:,.0f}"


def perfil(p: dict, estado: dict) -> list[dict]:
    q = []
    if not p.get("regimen"):
        q.append({"id": "perfil:regimen", "tipo": "perfil", "campo": "regimen", "prioridad": 1,
                  "titulo": "¿En qué régimen fiscal estás?",
                  "detalle": "Con esto calculo cuánto te toca pagar de impuestos cada mes.",
                  "opciones": [{"valor": "resico", "label": "RESICO (persona física)"},
                               {"valor": "actividad", "label": "Actividad empresarial (persona física)"},
                               {"valor": "moral", "label": "Empresa (persona moral)"},
                               {"valor": "no_se", "label": "No sé"}]})
    if not p.get("precios_iva"):
        q.append({"id": "perfil:precios_iva", "tipo": "perfil", "campo": "precios_iva", "prioridad": 2,
                  "titulo": "Cuando cobras, ¿tus precios ya incluyen IVA?",
                  "detalle": "Así separo lo que es tuyo de lo que es del SAT.",
                  "opciones": [{"valor": "incluyen", "label": "Sí, el precio ya trae IVA"},
                               {"valor": "mas_iva", "label": "Cobro precio + IVA aparte"},
                               {"valor": "no_cobro", "label": "No cobro IVA"}]})
    if not p.get("cuenta"):
        q.append({"id": "perfil:cuenta", "tipo": "perfil", "campo": "cuenta", "prioridad": 3,
                  "titulo": "¿Esta cuenta es solo del negocio?",
                  "detalle": "Si también la usas para cosas personales, te ayudo a separarlas.",
                  "opciones": [{"valor": "solo_negocio", "label": "Solo del negocio"},
                               {"valor": "mixta", "label": "La uso para las dos cosas"}]})
    if not p.get("otros_ingresos"):
        q.append({"id": "perfil:otros_ingresos", "tipo": "perfil", "campo": "otros_ingresos", "prioridad": 4,
                  "titulo": "¿Cobras por otro lado que no sea esta cuenta?",
                  "detalle": "Efectivo, otra cuenta, terminal, Mercado Pago, Stripe… Si no lo veo, no lo cuento.",
                  "opciones": [{"valor": "no", "label": "No, todo entra aquí"},
                               {"valor": "si", "label": "Sí, cobro por otros lados"}]})
    elif p.get("otros_ingresos") == "si" and not p.get("otros_ingresos_mensual"):
        q.append({"id": "perfil:otros_ingresos_mensual", "tipo": "perfil", "campo": "otros_ingresos_mensual", "prioridad": 4,
                  "titulo": "¿Cuánto cobras al mes por fuera de esta cuenta, más o menos?",
                  "detalle": "Escribe un estimado. Mejor aún: suelta aquí el estado de esa otra cuenta.",
                  "entrada": "numero", "opciones": []})
    if not p.get("nombre_negocio"):
        q.append({"id": "perfil:nombre_negocio", "tipo": "perfil", "campo": "nombre_negocio", "prioridad": 9,
                  "titulo": "¿Cómo se llama tu negocio?", "detalle": "Para ponerlo en tu tablero.",
                  "entrada": "texto", "opciones": []})
    return q


def generar(movs, p: dict, estado: dict) -> list[dict]:
    q = perfil(p, estado)
    entradas = sum(m.abono for m in movs) or 1
    salidas = sum(m.cargo for m in movs) or 1

    # decisiones en bloque
    bloques = [("tarjetas", "tarjetas", "Pagaste {t} de tarjetas de crédito. Lo que compras con tarjeta, ¿es del negocio?",
                "Si no estás seguro, déjalas aparte: no cambian tu utilidad hasta que sueltes aquí el estado de cuenta de la tarjeta."),
               ("consumos", "consumos", "Hay {t} en comidas, súper y consumos. ¿Son del negocio?", "Si son personales, no cuentan como gasto."),
               ("efectivo", "efectivo", "Sacaste {t} en efectivo. ¿Para qué es?", "El efectivo sin comprobante no es deducible.")]
    for campo, cat, titulo, det in bloques:
        tot = sum(m.cargo for m in movs if m.categoria == cat)
        if tot and not p.get(campo):
            ops = [{"valor": "negocio", "label": "Del negocio"}, {"valor": "personal", "label": "Personal"}]
            if campo == "tarjetas":
                # lo honesto cuando no tienes el estado de la tarjeta: dejarlas aparte, no adivinar
                ops = [{"valor": "por_desglosar", "label": "Todavía no sé: déjalas aparte"},
                       {"valor": "negocio", "label": "Todo es del negocio"},
                       {"valor": "personal", "label": "Todo es personal"},
                       {"valor": "mixto", "label": "Mitad y mitad"}]
            q.append({"id": f"perfil:{campo}", "tipo": "perfil", "campo": campo, "prioridad": 5,
                      "titulo": titulo.format(t=_peso(tot)), "detalle": det, "opciones": ops, "monto": round(tot, 2)})

    # movimientos que no reconozco (salidas) y depositos grandes que supuse ventas
    grupos = defaultdict(list)
    for m in movs:
        if m.regla == "sin regla" or (m.regla == "supuesto" and m.abono):
            grupos[("abono" if m.abono else "cargo", clave(m))].append(m)
    filas = []
    for (tipo, k), ms in grupos.items():
        tot = sum(x.abono or x.cargo for x in ms)
        base = entradas if tipo == "abono" else salidas
        umbral = max(2000.0, 0.03 * base) if tipo == "abono" else max(500.0, 0.01 * base)
        if tot < umbral:
            continue
        m0 = ms[0]
        n = len(ms)
        if tipo == "abono":
            titulo = f"Te depositaron {_peso(tot)} de «{m0.contraparte}»" + (f" en {n} pagos" if n > 1 else "") + ". ¿Qué es?"
            ops = OPCIONES_ABONO
        else:
            titulo = f"Pagaste {_peso(tot)} a «{m0.contraparte}»" + (f" en {n} pagos" if n > 1 else "") + ". ¿Qué es?"
            ops = OPCIONES_CARGO
        filas.append({"id": f"mov:{tipo}:{k}", "tipo": "movimiento", "mov_tipo": tipo, "clave": k, "monto": round(tot, 2),
                      "prioridad": 6, "titulo": titulo,
                      "detalle": f"{m0.fecha} · {m0.descripcion[:90]}",
                      "opciones": [{"valor": v, "label": l} for v, l in ops]})
    filas.sort(key=lambda x: -x["monto"])
    q += filas[:MAX_MOVS]
    if len(filas) > MAX_MOVS:
        resto = sum(f["monto"] for f in filas[MAX_MOVS:])
        q.append({"id": "info:mas", "tipo": "info", "prioridad": 99, "titulo": f"Y {len(filas) - MAX_MOVS} movimientos más por {_peso(resto)}",
                  "detalle": "Contesta los de arriba primero: muchas respuestas se aplican solas a los demás.", "opciones": []})
    return sorted(q, key=lambda x: x["prioridad"])


def responder(espacio, pregunta_id: str, valor) -> None:
    """Guarda tu respuesta. Perfil -> perfil.json; movimiento -> regla para esa contraparte."""
    from .categorias import CATEGORIAS
    from .espacio import PERFIL_VACIO
    tipo, _, resto = pregunta_id.partition(":")
    if tipo == "perfil":
        if resto not in PERFIL_VACIO:
            raise ValueError(f"Campo desconocido: {resto}")
        if resto == "otros_ingresos_mensual":
            valor = float(str(valor).replace(",", "").replace("$", "") or 0)
        espacio.guardar_perfil({resto: valor})
    elif tipo == "mov":
        mov_tipo, _, k = resto.partition(":")
        if valor not in CATEGORIAS:
            raise ValueError(f"Categoría desconocida: {valor}")
        espacio.agregar_regla({"tipo": mov_tipo, "clave": k, "categoria": valor, "origen": "pregunta"})
    elif tipo == "id":
        if valor not in CATEGORIAS:
            raise ValueError(f"Categoría desconocida: {valor}")
        espacio.agregar_regla({"id": resto, "categoria": valor, "origen": "corrección"})
    else:
        raise ValueError(f"Pregunta desconocida: {pregunta_id}")
