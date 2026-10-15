"""El CFO: lee tus estados de cuenta, clasifica, valida contra el banco y calcula tus numeros.

Reglas que no se rompen (framework Paccioli):
- El banco es la verdad: cada estado de cuenta se valida al centavo contra su resumen.
- Resultados SIN IVA, flujo CON IVA.
- Traspasos entre tus cuentas no son ingreso ni gasto.
- Tarjetas, creditos, impuestos y gastos personales van debajo de la linea: no cambian tu utilidad operativa.
"""
from __future__ import annotations

import datetime as dt
from collections import defaultdict
from pathlib import Path

from . import alertas as mod_alertas
from . import fiscal, lectores, preguntas
from .categorias import CATEGORIAS
from .clasificador import clasificar, seccion
from .espacio import Espacio

IVA = fiscal.IVA
OPERACION = ("ventas", "otros_ingresos", "costo", "gasto_venta", "gasto_admin")
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

_cache: dict[str, tuple] = {}


def _leer(p: Path):
    st = p.stat()
    k = f"{p}:{st.st_size}:{st.st_mtime_ns}"
    if k not in _cache:
        _cache[k] = lectores.leer(p)
    movs, res = _cache[k]
    return [type(m)(**{**m.__dict__, "extra": dict(m.extra)}) for m in movs], dict(res)


def _validar(movs, res, nombre) -> dict:
    if "cuadre_saldos" in res:
        ok = res["cuadre_saldos"]
        return {"ok": ok, "texto": f"Cada saldo cuadra con sus movimientos ({len(movs)} renglones)." if ok else
                "Los saldos del archivo no cuadran con los movimientos: puede faltar algún renglón."}
    if res.get("sin_saldos") or "n_cargos" not in res:
        return {"ok": None, "texto": "Sin resumen del banco para validar (archivo exportado)."}
    nc, na = sum(1 for m in movs if m.cargo), sum(1 for m in movs if m.abono)
    c, a = sum(m.cargo for m in movs), sum(m.abono for m in movs)
    ok = nc == res["n_cargos"] and na == res["n_abonos"] and abs(c - res["cargos"]) < .005 and abs(a - res["abonos"]) < .005
    if "saldo_inicial" in res and "saldo_final" in res:
        ok = ok and abs(res["saldo_inicial"] + a - c - res["saldo_final"]) < .005
    texto = (f"Cuadra al centavo con tu banco: {nc} cargos y {na} abonos." if ok else
             f"No cuadra: leí {nc} cargos por {c:,.2f} y {na} abonos por {a:,.2f}; el banco dice {res['n_cargos']} por {res['cargos']:,.2f} y {res['n_abonos']} por {res['abonos']:,.2f}.")
    return {"ok": ok, "texto": texto}


def nombre_mes(mes: str) -> str:
    try:
        a, m = mes.split("-")
        return f"{MESES[int(m) - 1]} {a}"
    except (ValueError, IndexError):
        return mes


def analizar(espacio: Espacio, hoy: dt.date | None = None) -> dict:
    hoy = hoy or dt.date.today()
    perfil = espacio.perfil()
    archivos, movs, errores, titular, saldos = [], [], [], perfil.get("titular") or None, []
    vistos = set()
    for p in espacio.archivos():
        try:
            ms, res = _leer(p)
        except Exception as ex:  # noqa: BLE001 - se le muestra al usuario
            errores.append({"archivo": p.name, "error": str(ex)})
            continue
        val = _validar(ms, res, p.name)
        titular = titular or res.get("titular")
        nuevos = 0
        for m in ms:
            k = (m.fuente, m.fecha, m.cargo, m.abono, m.descripcion[:60])
            if k in vistos:
                continue
            vistos.add(k)
            movs.append(m)
            nuevos += 1
        if "saldo_final" in res:
            fin = max((m.fecha for m in ms), default="")
            saldos.append((fin, res["saldo_final"], res.get("banco", "")))
        archivos.append({"nombre": p.name, "banco": res.get("banco", "Archivo"), "periodo": res.get("periodo", ""),
                         "titular": res.get("titular"), "movimientos": nuevos, "validacion": val,
                         "saldo_final": res.get("saldo_final")})
    if titular and not perfil.get("titular"):
        perfil = espacio.guardar_perfil({"titular": titular})

    clasificar(movs, espacio.reglas(), titular)
    _aplicar_decisiones(movs, perfil)

    meses = sorted({m.mes for m in movs if m.mes != "sin-fecha"})
    cobertura = _cobertura(archivos, movs)
    por_mes = {mes: _mes([m for m in movs if m.mes == mes], perfil) for mes in meses}
    for mes in meses:
        por_mes[mes]["dias"] = cobertura.get(mes, 0)
        por_mes[mes]["parcial"] = cobertura.get(mes, 0) < _dias_mes(mes) - 1
    saldo = sorted(saldos)[-1][1] if saldos else None
    completos = [m for m in meses if not por_mes[m]["parcial"]]
    candidatos = completos or sorted(meses, key=lambda m: por_mes[m]["dias"])[-1:]
    ultimo = candidatos[-1] if candidatos else None
    dias_tot = sum(cobertura.values()) or 1
    salidas_tot = sum(m.cargo for m in movs if seccion(m) != "traspaso")
    estado = {
        "negocio": perfil.get("nombre_negocio") or (titular or "Tu negocio").title(),
        "perfil": perfil,
        "carpeta": str(espacio.estados),
        "actualizado": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "archivos": archivos, "errores": errores,
        "meses": [{"mes": m, "nombre": nombre_mes(m)} for m in meses],
        "por_mes": por_mes,
        "tendencia": [{"mes": m, "nombre": nombre_mes(m), "ingresos": por_mes[m]["ingresos"],
                       "gastos": por_mes[m]["gastos"], "utilidad": por_mes[m]["utilidad"]} for m in meses],
        "saldo": saldo,
        "mes_actual": ultimo,
        "gasto_diario": round(salidas_tot / dias_tot, 2),
        "proximo_vencimiento": fiscal.proximo_vencimiento(hoy).isoformat(),
        "movimientos": [dict(m.to_dict(), etiqueta=CATEGORIAS[m.categoria]["label"], seccion=seccion(m)) for m in movs],
        "categorias": {k: v["label"] for k, v in CATEGORIAS.items()},
    }
    estado["preguntas"] = preguntas.generar(movs, perfil, estado)
    estado["alertas"] = mod_alertas.generar(estado, ultimo, hoy)
    estado["supuestos"] = _supuestos(perfil)
    return estado


def _dias_mes(mes: str) -> int:
    a, m = map(int, mes.split("-"))
    sig = dt.date(a + (m == 12), 1 if m == 12 else m + 1, 1)
    return (sig - dt.date(a, m, 1)).days


def _cobertura(archivos, movs) -> dict[str, int]:
    """Cuantos dias de cada mes cubren tus estados de cuenta (para no comparar meses incompletos)."""
    import re as _re
    dias: dict[str, set] = {}
    for f in archivos:
        fechas = _re.findall(r"(\d{2})/(\d{2})/(\d{4})|(\d{4})-(\d{2})-(\d{2})", f.get("periodo") or "")
        pts = []
        for g in fechas:
            if g[0]:
                pts.append(dt.date(int(g[2]), int(g[1]), int(g[0])))
            else:
                pts.append(dt.date(int(g[3]), int(g[4]), int(g[5])))
        if len(pts) >= 2:
            d = pts[0]
            while d <= pts[-1]:
                dias.setdefault(d.strftime("%Y-%m"), set()).add(d)
                d += dt.timedelta(days=1)
    if not dias:  # sin periodo: se usa el rango de fechas de los movimientos por mes
        for mm in {m.mes for m in movs}:
            fs = sorted(m.fecha for m in movs if m.mes == mm)
            if fs and mm != "sin-fecha":
                dias[mm] = set(range(int(fs[0][8:10]), int(fs[-1][8:10]) + 1))
    return {k: len(v) for k, v in dias.items()}


def _aplicar_decisiones(movs, perfil):
    """Respuestas generales (tarjetas, consumos, efectivo) recategorizan en bloque."""
    destino = {"negocio": "otros_gastos", "personal": "personal"}
    for m in movs:
        if m.regla == "tuya":
            continue
        for campo, cat in (("tarjetas", "tarjetas"), ("consumos", "consumos"), ("efectivo", "efectivo")):
            if m.categoria == cat and perfil.get(campo) in destino:
                if campo == "consumos" and perfil[campo] == "negocio":
                    continue  # se queda como "Comidas y consumos" del negocio
                m.categoria, m.regla = destino[perfil[campo]], f"tu respuesta: {campo}"


def _separa_iva(perfil) -> bool:
    return perfil.get("precios_iva") != "no_cobro"


def _mes(movs, perfil) -> dict:
    sep = _separa_iva(perfil)
    lineas: dict[str, float] = defaultdict(float)
    for m in movs:
        c = CATEGORIAS[m.categoria]
        if c["seccion"] not in OPERACION + ("sin_identificar",):
            continue  # lo que no sé qué es cuenta como gasto (criterio conservador) hasta que me contestes
        monto = m.abono - m.cargo if c["seccion"] in ("ventas", "otros_ingresos") else m.cargo - m.abono
        if sep and c.get("iva"):
            monto /= (1 + IVA)
        lineas[m.categoria] += monto
    externo = float(perfil.get("otros_ingresos_mensual") or 0) if perfil.get("otros_ingresos") == "si" else 0.0
    sec = lambda s: sum(v for k, v in lineas.items() if CATEGORIAS[k]["seccion"] == s)
    ventas = sec("ventas") + (externo / (1 + IVA) if sep else externo)
    otros = sec("otros_ingresos")
    ingresos = ventas + otros
    costo, gv, ga = sec("costo"), sec("gasto_venta"), sec("gasto_admin") + sec("sin_identificar")
    gastos = costo + gv + ga
    utilidad = ingresos - gastos
    variables = sum(v for k, v in lineas.items() if CATEGORIAS[k].get("variable"))
    fijos = gastos - variables
    mc = 1 - variables / ingresos if ingresos else 0
    pe = fijos / mc if mc > 0 else None

    entradas = sum(m.abono for m in movs if seccion(m) != "traspaso")
    salidas = sum(m.cargo for m in movs if seccion(m) != "traspaso")
    abajo = defaultdict(float)
    for m in movs:
        if seccion(m) in ("financiero", "personal", "aportacion"):
            abajo[m.categoria] += m.importe
    clientes = defaultdict(float)
    canal = {}
    for m in movs:
        if m.abono and seccion(m) == "ventas":
            clientes[m.contraparte] += m.abono
            canal[m.contraparte] = m.categoria != "ventas"
    gastos_cat = defaultdict(float)
    for m in movs:
        if m.cargo and seccion(m) not in ("traspaso",):
            gastos_cat[CATEGORIAS[m.categoria]["label"]] += m.cargo
    iva_cobrado = sum(m.abono * IVA / (1 + IVA) for m in movs if seccion(m) == "ventas") if sep else 0
    iva_pagado = (sum(m.cargo * IVA / (1 + IVA) for m in movs if seccion(m) in OPERACION and CATEGORIAS[m.categoria].get("iva"))
                  + sum(m.cargo for m in movs if seccion(m) == "iva")) if sep else 0
    impuestos_pagados = sum(m.cargo for m in movs if m.categoria == "impuestos")
    filas = [{"categoria": k, "label": CATEGORIAS[k]["label"], "seccion": CATEGORIAS[k]["seccion"], "monto": round(v, 2)}
             for k, v in sorted(lineas.items(), key=lambda kv: -abs(kv[1]))]
    if externo:
        filas.insert(0, {"categoria": "externo", "label": "Ingresos fuera de esta cuenta (tu estimado)", "seccion": "ventas",
                         "monto": round(externo / (1 + IVA) if sep else externo, 2)})
    return {
        "ingresos": round(ingresos, 2), "ventas": round(ventas, 2), "otros_ingresos": round(otros, 2),
        "costo": round(costo, 2), "gasto_venta": round(gv, 2), "gasto_admin": round(ga, 2),
        "gastos": round(gastos, 2), "utilidad": round(utilidad, 2), "margen": round(utilidad / ingresos, 4) if ingresos else None,
        "margen_bruto": round((ingresos - costo) / ingresos, 4) if ingresos else None,
        "equilibrio": round(pe, 2) if pe else None, "margen_contribucion": round(mc, 4),
        "entradas": round(entradas, 2), "salidas": round(salidas, 2), "flujo": round(entradas - salidas, 2),
        "lineas": filas,
        "debajo": [{"categoria": k, "label": CATEGORIAS[k]["label"], "monto": round(v, 2)} for k, v in sorted(abajo.items(), key=lambda kv: kv[1])],
        "clientes": [{"nombre": k, "monto": round(v, 2), "canal": canal.get(k, False)} for k, v in sorted(clientes.items(), key=lambda kv: -kv[1])],
        "gastos_categoria": [{"nombre": k, "monto": round(v, 2)} for k, v in sorted(gastos_cat.items(), key=lambda kv: -kv[1])],
        "iva": {"cobrado": round(iva_cobrado, 2), "pagado": round(iva_pagado, 2), "neto": round(iva_cobrado - iva_pagado, 2)},
        "impuestos_pagados": round(impuestos_pagados, 2),
        "impuestos": _impuestos(ventas, ingresos, gastos, utilidad, iva_cobrado - iva_pagado, perfil),
        "n_movimientos": len(movs),
        "personal": round(-sum(v for k, v in abajo.items() if CATEGORIAS[k]["seccion"] == "personal"), 2),
        "tarjetas": round(-abajo.get("tarjetas", 0), 2),
    }


def _impuestos(ventas, ingresos, gastos, utilidad, iva_neto, perfil) -> dict:
    reg = perfil.get("regimen") or ""
    iva = max(iva_neto, 0) if _separa_iva(perfil) else 0
    if reg == "resico":
        isr = fiscal.isr_resico_pf(ingresos)
        texto = f"RESICO: {isr['tasa']:.2%} sobre lo que cobraste, sin deducciones."
        pago = isr["pago"]
    elif reg == "actividad":
        isr = fiscal.isr_pf_actividad_empresarial(ingresos, gastos)
        texto = "Actividad empresarial: tarifa 2026 sobre tu utilidad (aproximación de un mes)."
        pago = isr["pago"]
    elif reg == "moral":
        pago = round(max(utilidad, 0) * 0.30, 2)
        texto = "Persona moral: 30% de la utilidad como referencia. Tu pago provisional real usa tu coeficiente de utilidad."
    else:
        return {"definido": False, "texto": "Dime tu régimen fiscal para estimar tus impuestos."}
    return {"definido": True, "isr": round(pago, 2), "iva": round(iva, 2), "total": round(pago + iva, 2), "texto": texto}


def _supuestos(perfil) -> list[str]:
    s = []
    if not perfil.get("precios_iva"):
        s.append("Supuse que tus precios incluyen IVA: separé el 16% de tus ventas y gastos.")
    if perfil.get("precios_iva") == "no_cobro":
        s.append("No cobras IVA: todas las cifras van completas.")
    if not perfil.get("cuenta"):
        s.append("No sé si esta cuenta es solo del negocio: contesta para separar gastos personales.")
    return s
