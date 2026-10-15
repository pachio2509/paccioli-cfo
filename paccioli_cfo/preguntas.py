"""Lo que el CFO te pregunta para entender tu negocio. Cada respuesta se guarda y
se aplica sola a todos los movimientos parecidos, hoy y en los meses que vengan."""
from __future__ import annotations

from collections import defaultdict

from .categorias import OPCIONES_ABONO, OPCIONES_ABONO_PERSONAL, OPCIONES_CARGO, OPCIONES_CARGO_PERSONAL
from .clasificador import clave
from .paises import OPCIONES_PAIS, contexto

MAX_MOVS = 12


_CTX: dict = {}


def _peso(x: float) -> str:
    from .paises import dinero
    return dinero(x, _CTX)


def perfil(p: dict, estado: dict) -> list[dict]:
    q = []
    ctx = contexto(p)
    personal = ctx["uso"] == "personal"
    if not p.get("uso"):
        q.append({"id": "perfil:uso", "tipo": "perfil", "campo": "uso", "prioridad": 0,
                  "titulo": "¿Para qué usas esta cuenta?",
                  "detalle": "Así te hablo en tus palabras y hago las cuentas que te sirven.",
                  "opciones": [{"valor": "negocio", "label": "Mi negocio o empresa"},
                               {"valor": "independiente", "label": "Trabajo por mi cuenta (freelance, profesionista)"},
                               {"valor": "personal", "label": "Mis finanzas personales"}]})
    if not p.get("pais"):
        q.append({"id": "perfil:pais", "tipo": "perfil", "campo": "pais", "prioridad": 0.5,
                  "titulo": "¿En qué país estás?", "detalle": "Para tu moneda y tus impuestos.",
                  "opciones": [{"valor": v, "label": l} for v, l in OPCIONES_PAIS]})
    elif ctx["pais"] == "otro" and not p.get("moneda"):
        q.append({"id": "perfil:moneda", "tipo": "perfil", "campo": "moneda", "prioridad": 0.6,
                  "titulo": "¿En qué moneda está tu cuenta?", "detalle": "Escribe el código de 3 letras: USD, EUR, BRL…",
                  "entrada": "texto", "opciones": []})
    elif ctx["pais"] == "otro" and str(p.get("tasa_impuesto") or "") == "" and not personal:
        q.append({"id": "perfil:tasa_impuesto", "tipo": "perfil", "campo": "tasa_impuesto", "prioridad": 0.7,
                  "titulo": "¿De cuánto es el impuesto a las ventas en tu país (IVA, VAT)?",
                  "detalle": "Escribe el porcentaje, por ejemplo 16. Si no cobras ese impuesto, escribe 0.",
                  "entrada": "numero", "opciones": []})
    if personal:
        return q
    if not p.get("regimen") and ctx["es_mx"]:
        q.append({"id": "perfil:regimen", "tipo": "perfil", "campo": "regimen", "prioridad": 1,
                  "titulo": "¿En qué régimen fiscal estás?",
                  "detalle": "Con esto calculo cuánto te toca pagar de impuestos cada mes.",
                  "opciones": [{"valor": "resico", "label": "RESICO (persona física)"},
                               {"valor": "actividad", "label": "Actividad empresarial (persona física)"},
                               {"valor": "moral", "label": "Empresa (persona moral)"},
                               {"valor": "no_se", "label": "No sé"}]})
    imp = ctx["impuesto"]
    if not p.get("precios_iva") and ctx["tasa"] > 0:
        q.append({"id": "perfil:precios_iva", "tipo": "perfil", "campo": "precios_iva", "prioridad": 2,
                  "titulo": f"Cuando cobras, ¿tus precios ya incluyen {imp}?",
                  "detalle": f"Así separo lo que es tuyo de lo que es de {ctx['autoridad']}.",
                  "opciones": [{"valor": "incluyen", "label": f"Sí, el precio ya trae {imp}"},
                               {"valor": "mas_iva", "label": f"Cobro precio + {imp} aparte"},
                               {"valor": "no_cobro", "label": f"No cobro {imp}"}]})
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
                  "titulo": "¿Cómo se llama tu negocio?" if ctx["uso"] == "negocio" else "¿Con qué nombre quieres ver tu tablero?",
                  "detalle": "Para ponerlo en tu tablero.",
                  "entrada": "texto", "opciones": []})
    return q


def generar(movs, p: dict, estado: dict) -> list[dict]:
    _CTX.clear(); _CTX.update(contexto(p))
    q = perfil(p, estado)
    entradas = sum(m.abono for m in movs) or 1
    salidas = sum(m.cargo for m in movs) or 1

    # decisiones en bloque
    bloques = [("tarjetas", "tarjetas", "Pagaste {t} de tarjetas de crédito. Lo que compras con tarjeta, ¿es del negocio?",
                "Si no estás seguro, déjalas aparte: no cambian tu utilidad hasta que sueltes aquí el estado de cuenta de la tarjeta."),
               ("consumos", "consumos", "Hay {t} en comidas, súper y consumos. ¿Son del negocio?", "Si son personales, no cuentan como gasto."),
               ("efectivo", "efectivo", "Sacaste {t} en efectivo. ¿Para qué es?", "El efectivo sin comprobante no es deducible.")]
    if p.get("uso") == "personal":
        bloques = bloques[:1]  # en finanzas personales los consumos y el efectivo ya son tus gastos
    for campo, cat, titulo, det in bloques:
        tot = sum(m.cargo for m in movs if m.categoria == cat)
        if tot and not p.get(campo):
            ops = [{"valor": "negocio", "label": "Del negocio"}, {"valor": "personal", "label": "Personal"}]
            if campo == "tarjetas" and p.get("uso") == "personal":
                titulo = "Pagaste {t} de tarjetas de crédito. ¿Lo cuento como gasto?"
                ops = [{"valor": "negocio", "label": "Sí, son mis compras"}, {"valor": "por_desglosar", "label": "Déjalo aparte"}]
            elif campo == "tarjetas":
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
            ops = OPCIONES_ABONO_PERSONAL if p.get("uso") == "personal" else OPCIONES_ABONO
        else:
            titulo = f"Pagaste {_peso(tot)} a «{m0.contraparte}»" + (f" en {n} pagos" if n > 1 else "") + ". ¿Qué es?"
            ops = OPCIONES_CARGO_PERSONAL if p.get("uso") == "personal" else OPCIONES_CARGO
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
