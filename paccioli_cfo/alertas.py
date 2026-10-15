"""El CFO te avisa: alertas sobre caja, utilidad, impuestos y orden de tus cuentas.

Niveles: rojo (atiéndelo ya), ambar (revísalo esta semana), verde (vas bien), info.
"""
from __future__ import annotations

import datetime as dt

from . import fiscal


def _p(x) -> str:
    return f"${x:,.0f}"


def generar(e: dict, mes: str | None, hoy: dt.date) -> list[dict]:
    a: list[dict] = []
    add = lambda nivel, titulo, detalle, accion="": a.append({"nivel": nivel, "titulo": titulo, "detalle": detalle, "accion": accion})
    if not mes:
        add("info", "Suelta tu estado de cuenta para empezar", "Arrastra el PDF de BBVA o el Excel/CSV de tu banco al tablero, o ponlo en la carpeta mis-estados-de-cuenta.")
        return a
    d = e["por_mes"][mes]
    p = e["perfil"]
    meses = [x["mes"] for x in e["meses"]]
    ing, util, gastos = d["ingresos"], d["utilidad"], d["gastos"]

    for f in e["archivos"]:
        if f["validacion"]["ok"] is False:
            add("rojo", f"{f['nombre']} no cuadra con el banco", f["validacion"]["texto"], "Revisa que el archivo esté completo.")
    for err in e["errores"]:
        add("ambar", f"No pude leer {err['archivo']}", err["error"])

    # utilidad
    if ing and util < 0:
        add("rojo", f"Este mes perdiste {_p(-util)}", f"Ingresaste {_p(ing)} y gastaste {_p(gastos)} en la operación.",
            "Revisa tus 3 gastos más grandes y si puedes subir precios.")
    elif ing and d["margen"] is not None and d["margen"] < 0.10:
        add("ambar", f"Ganas poco: {d['margen']:.0%} de margen", f"De cada $100 que entran te quedan ${d['margen'] * 100:.0f}.",
            "Un negocio sano deja 15% o más.")
    elif ing and d["margen"] is not None:
        add("verde", f"Ganaste {_p(util)} ({d['margen']:.0%} de margen)", "Tu operación deja utilidad.")

    # caja
    salidas_mes = e.get("gasto_diario", 0) * 30
    if e.get("saldo") is not None and salidas_mes:
        dias = e["saldo"] / (salidas_mes / 30)
        if dias < 30:
            add("rojo" if dias < 15 else "ambar", f"Tu dinero en el banco cubre {dias:.0f} día{'' if round(dias) == 1 else 's'} de pagos",
                f"Tienes {_p(e['saldo'])} y pagas alrededor de {_p(salidas_mes)} al mes. Lo sano es tener al menos 30 días de colchón.", "Cobra lo pendiente y aplaza lo que no sea urgente.")
    if d["flujo"] < 0 and len(meses) > 1:
        add("ambar", f"Salió más dinero del que entró: {_p(-d['flujo'])}", "Sin contar traspasos entre tus cuentas.")

    # equilibrio
    if d["equilibrio"] and ing:
        colchon = (ing - d["equilibrio"]) / ing
        if colchon < 0.15:
            add("ambar", f"Necesitas vender {_p(d['equilibrio'])} al mes para no perder",
                f"Estás {'por debajo' if colchon < 0 else f'solo {colchon:.0%} arriba'} de tu punto de equilibrio.")

    # dependencia de un cliente
    clientes = [c for c in d["clientes"] if "sin nombre" not in c["nombre"].lower() and not c.get("canal")]
    if clientes and d["ventas"]:
        top = clientes[0]
        part = top["monto"] / sum(c["monto"] for c in d["clientes"])
        if part >= 0.4 and len(clientes) > 1:
            add("ambar", f"{part:.0%} de tus ventas viene de {top['nombre']}", "Si ese cliente se va, tu negocio se cae.",
                "Busca 2 o 3 clientes más de ese tamaño.")

    # tarjetas y mezcla personal
    if d["tarjetas"] and d["salidas"] and d["tarjetas"] / d["salidas"] > 0.2 and p.get("tarjetas") != "personal":
        add("ambar", f"{d['tarjetas'] / d['salidas']:.0%} de lo que sale va a tarjetas", f"Pagaste {_p(d['tarjetas'])} de tarjetas y no sé en qué se gastó.",
            "Suelta aquí el estado de cuenta de tu tarjeta.")
    if d["personal"] and ing and d["personal"] / ing > 0.1:
        add("ambar", f"Sacaste {_p(d['personal'])} para gastos personales", "Es dinero del negocio que no se queda en el negocio.",
            "Ponte un sueldo fijo y abre una cuenta solo para el negocio.")
    if p.get("cuenta") == "mixta":
        add("info", "Usas la misma cuenta para el negocio y para ti", "Así es difícil saber cuánto ganas de verdad.", "Abre una cuenta solo para el negocio.")

    # sin identificar
    sin = [m for m in e["movimientos"] if m["mes"] == mes and m["regla"] in ("sin regla", "supuesto")]
    monto_sin = sum(m["cargo"] + m["abono"] for m in sin)
    if monto_sin and (d["entradas"] + d["salidas"]) and monto_sin / (d["entradas"] + d["salidas"]) > 0.1:
        add("ambar", f"Hay {_p(monto_sin)} que no sé qué son", f"{len(sin)} movimientos sin identificar.", "Contesta las preguntas del tablero.")

    # impuestos
    imp = d["impuestos"]
    venc = dt.date.fromisoformat(e["proximo_vencimiento"])
    if imp.get("definido"):
        add("info", f"Aparta {_p(imp['total'])} para el SAT", f"{imp['texto']} Vence el {venc.day} de {_mes(venc.month)}. Es un estimado: confírmalo con tu contador.")
    elif p.get("regimen") != "no_se":
        add("info", "¿Cuánto vas a pagar de impuestos?", "Contesta tu régimen fiscal y te digo cuánto apartar.")
    if ing and not d["impuestos_pagados"] and p.get("regimen") not in (None, "", "no_se"):
        add("ambar", "No veo pago al SAT este mes", f"Si tuviste ingresos, tu declaración vence el {venc.day} de {_mes(venc.month)}.")
    if p.get("regimen") == "resico" and meses:
        anual = sum(e["por_mes"][m]["ingresos"] for m in meses) / len(meses) * 12
        if anual > fiscal.TOPE_RESICO_PF * 0.85:
            add("rojo" if anual > fiscal.TOPE_RESICO_PF else "ambar", f"Vas a {_p(anual)} al año: cerca del tope de RESICO",
                "El tope es $3.5 millones. Si lo pasas, cambias de régimen y pagas más.", "Habla con tu contador antes de que pase.")
    orden = {"rojo": 0, "ambar": 1, "info": 2, "verde": 3}
    return sorted(a, key=lambda x: orden[x["nivel"]])


def _mes(n: int) -> str:
    return ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"][n - 1]
