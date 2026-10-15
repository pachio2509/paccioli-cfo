"""País, moneda e impuesto al consumo. México trae además el cálculo de ISR (RESICO, actividad empresarial, persona moral).

Para otro país: tu moneda, tu tasa de IVA/IGV/VAT y el nombre de tu autoridad. El impuesto sobre la renta no se
estima fuera de México (cada país es distinto): se separa el impuesto al consumo y se te dice que lo confirmes con tu contador.
"""
from __future__ import annotations

# codigo: (nombre, moneda, locale, tasa impuesto al consumo, nombre del impuesto, autoridad)
PAISES = {
    "MX": ("México", "MXN", "es-MX", 0.16, "IVA", "el SAT"),
    "CO": ("Colombia", "COP", "es-CO", 0.19, "IVA", "la DIAN"),
    "PE": ("Perú", "PEN", "es-PE", 0.18, "IGV", "la SUNAT"),
    "CL": ("Chile", "CLP", "es-CL", 0.19, "IVA", "el SII"),
    "AR": ("Argentina", "ARS", "es-AR", 0.21, "IVA", "ARCA"),
    "EC": ("Ecuador", "USD", "es-EC", 0.15, "IVA", "el SRI"),
    "GT": ("Guatemala", "GTQ", "es-GT", 0.12, "IVA", "la SAT"),
    "CR": ("Costa Rica", "CRC", "es-CR", 0.13, "IVA", "Hacienda"),
    "DO": ("República Dominicana", "DOP", "es-DO", 0.18, "ITBIS", "la DGII"),
    "PA": ("Panamá", "USD", "es-PA", 0.07, "ITBMS", "la DGI"),
    "UY": ("Uruguay", "UYU", "es-UY", 0.22, "IVA", "la DGI"),
    "BO": ("Bolivia", "BOB", "es-BO", 0.13, "IVA", "el SIN"),
    "PY": ("Paraguay", "PYG", "es-PY", 0.10, "IVA", "la DNIT"),
    "SV": ("El Salvador", "USD", "es-SV", 0.13, "IVA", "Hacienda"),
    "HN": ("Honduras", "HNL", "es-HN", 0.15, "ISV", "el SAR"),
    "ES": ("España", "EUR", "es-ES", 0.21, "IVA", "Hacienda"),
    "US": ("Estados Unidos", "USD", "en-US", 0.0, "sales tax", "el IRS"),
}
SIMBOLOS = {"MXN": "$", "COP": "$", "CLP": "$", "ARS": "$", "USD": "$", "PEN": "S/", "GTQ": "Q", "CRC": "₡", "DOP": "RD$",
            "UYU": "$U", "BOB": "Bs", "PYG": "₲", "HNL": "L", "EUR": "€", "GBP": "£", "BRL": "R$"}
OPCIONES_PAIS = [("MX", "México"), ("CO", "Colombia"), ("PE", "Perú"), ("CL", "Chile"), ("AR", "Argentina"),
                 ("ES", "España"), ("US", "Estados Unidos"), ("otro", "Otro país")]


def contexto(perfil: dict) -> dict:
    """Todo lo que cambia por país y por tipo de usuario, en un solo lugar (el tablero lo usa para sus textos)."""
    codigo = (perfil.get("pais") or "MX").upper()
    nombre, moneda, locale, tasa, impuesto, autoridad = PAISES.get(codigo, ("Tu país", "MXN", "es-MX", 0.16, "IVA", "tu autoridad fiscal"))
    if perfil.get("moneda"):
        moneda = str(perfil["moneda"]).upper()[:3]
    if str(perfil.get("tasa_impuesto") or "") != "":
        try:
            v = float(str(perfil["tasa_impuesto"]).replace("%", "").replace(",", "."))
            tasa = v / 100 if v > 1 else v  # acepta 16 o 0.16
        except ValueError:
            pass
    uso = perfil.get("uso") or "negocio"
    return {"pais": codigo if codigo in PAISES else "otro", "pais_nombre": nombre, "moneda": moneda, "locale": locale,
            "simbolo": SIMBOLOS.get(moneda, moneda + " "),
            "tasa": tasa, "impuesto": impuesto, "autoridad": autoridad, "es_mx": codigo == "MX", "uso": uso}


def dinero(x: float, ctx: dict | None = None) -> str:
    """Monto redondeado con el simbolo de tu moneda: $12,500 · S/12,500 · €12,500."""
    sim = (ctx or {}).get("simbolo", "$")
    return f"{'−' if x < 0 else ''}{sim}{abs(x):,.0f}"
