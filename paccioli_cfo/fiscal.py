"""Calculos fiscales Mexico.

Tarifa mensual ISR 2026: Anexo 8 RMF 2026, DOF 28-12-2025 (art. 96 LISR).
Actualizar TARIFAS cada anio y dejar la fuente en docs/fiscal-mx.md.
"""
from __future__ import annotations

IVA = 0.16

# (limite inferior, cuota fija, % sobre excedente)
TARIFAS = {
    2026: [
        (0.01, 0.00, 0.0192), (844.60, 16.22, 0.0640), (7168.52, 420.95, 0.1088),
        (12598.03, 1011.68, 0.1600), (14644.65, 1339.14, 0.1792), (17533.65, 1856.84, 0.2136),
        (35362.84, 5665.16, 0.2352), (55736.69, 10457.09, 0.3000), (106410.51, 25659.23, 0.3200),
        (141880.67, 37009.69, 0.3400), (425642.00, 133488.54, 0.3500),
    ],
}


def isr_tarifa_mensual(base: float, anio: int = 2026, meses: int = 1) -> float:
    """ISR con la tarifa mensual (meses=1) o la acumulada a `meses` (limites x meses)."""
    if base <= 0:
        return 0.0
    tabla = TARIFAS[anio]
    for li, cuota, tasa in reversed(tabla):
        if base >= li * meses:
            return round(cuota * meses + (base - li * meses) * tasa, 2)
    return 0.0


def isr_pf_actividad_empresarial(ingresos_cobrados: float, deducciones_pagadas: float,
                                 anio: int = 2026, meses: int = 1,
                                 pagos_previos: float = 0.0, retenciones: float = 0.0) -> dict:
    """Pago provisional PF actividad empresarial (art. 106 LISR).
    Con meses=1 es la aproximacion de un mes tipico; para el pago exacto pasar los
    acumulados de enero al mes y los pagos provisionales previos."""
    utilidad = ingresos_cobrados - deducciones_pagadas
    isr = isr_tarifa_mensual(utilidad, anio, meses)
    pago = max(0.0, isr - pagos_previos - retenciones)
    return {"utilidad_fiscal": round(utilidad, 2), "isr_causado": isr,
            "tasa_efectiva": round(isr / utilidad, 4) if utilidad > 0 else 0.0,
            "pago": round(pago, 2)}


def isr_pm_provisional(ingresos_acumulados: float, coeficiente_utilidad: float,
                       pagos_previos: float = 0.0, retenciones: float = 0.0) -> dict:
    """Pago provisional PM regimen general (art. 14 LISR)."""
    base = ingresos_acumulados * coeficiente_utilidad
    isr = base * 0.30
    return {"utilidad_estimada": round(base, 2), "isr_causado": round(isr, 2),
            "pago": round(max(0.0, isr - pagos_previos - retenciones), 2)}


def iva_de_total(total_con_iva: float) -> tuple[float, float]:
    """Separa base e IVA de un monto que ya incluye 16%."""
    base = total_con_iva / (1 + IVA)
    return round(base, 2), round(total_con_iva - base, 2)


def iva_mensual(trasladado: float, acreditable: float, retenido_a_favor: float = 0.0) -> dict:
    neto = trasladado - acreditable - retenido_a_favor
    return {"trasladado": round(trasladado, 2), "acreditable": round(acreditable, 2),
            "retenciones": round(retenido_a_favor, 2), "a_cargo": round(max(neto, 0), 2),
            "a_favor": round(max(-neto, 0), 2)}


# Retenciones a personas fisicas por honorarios que hace una persona moral
RETENCION_HONORARIOS = {
    "actividades_profesionales": {"isr": 0.10, "iva": IVA * 2 / 3},
    "resico": {"isr": 0.0125, "iva": IVA * 2 / 3},
}

TOPE_RESICO_PF = 3_500_000


# RESICO personas fisicas (art. 113-E LISR): tasa sobre ingresos cobrados del mes, sin deducciones
RESICO_PF = [(25_000.00, 0.0100), (50_000.00, 0.0110), (83_333.33, 0.0150), (208_333.33, 0.0200), (3_500_000.00, 0.0250)]


def isr_resico_pf(ingresos_mes: float) -> dict:
    tasa = next((t for tope, t in RESICO_PF if ingresos_mes <= tope), RESICO_PF[-1][1])
    return {"base": round(ingresos_mes, 2), "tasa": tasa, "pago": round(max(ingresos_mes, 0) * tasa, 2)}


def proximo_vencimiento(hoy) -> "datetime.date":
    """Dia 17 del mes siguiente al que se declara; si cae en fin de semana se recorre al lunes."""
    import datetime as dt
    d = dt.date(hoy.year, hoy.month, 17)
    if hoy.day > 17:
        d = dt.date(hoy.year + (hoy.month == 12), 1 if hoy.month == 12 else hoy.month + 1, 17)
    while d.weekday() >= 5:
        d += dt.timedelta(days=1)
    return d
