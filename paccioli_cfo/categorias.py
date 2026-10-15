"""Catalogo de categorias y reglas automaticas para negocios en Mexico.

Seccion = donde cae en el estado de resultados:
  ventas, otros_ingresos      -> ingresos de la operacion
  costo                       -> costo directo (lo que cuesta vender/producir)
  gasto_venta, gasto_admin    -> gastos de operacion
  financiero                  -> pagos de tarjetas y creditos, impuestos (debajo de la linea)
  personal                    -> retiros y gastos personales del dueno (debajo de la linea)
  aportacion                  -> prestamos y aportaciones recibidas (no son venta)
  traspaso                    -> entre cuentas propias (no cuenta)
  sin_identificar             -> genera una pregunta
iva: el monto trae IVA 16% (se separa en el estado de resultados si cobras IVA).
variable: cambia con las ventas (para el punto de equilibrio).
"""

CATEGORIAS = {
    # ---------- entradas
    "ventas":            {"label": "Ventas a clientes", "seccion": "ventas", "iva": True},
    "ventas_tarjeta":    {"label": "Ventas con tarjeta (terminal)", "seccion": "ventas", "iva": True},
    "ventas_plataforma": {"label": "Ventas en plataformas y tienda en línea", "seccion": "ventas", "iva": True},
    "otros_ingresos":    {"label": "Otros ingresos (rentas, intereses)", "seccion": "otros_ingresos", "iva": False},
    "prestamo":          {"label": "Préstamos recibidos", "seccion": "aportacion"},
    "aportacion":        {"label": "Aportaciones del dueño o socios", "seccion": "aportacion"},
    "devolucion":        {"label": "Reembolsos y devoluciones", "seccion": "aportacion"},
    "traspaso_propio":   {"label": "Traspasos entre mis cuentas", "seccion": "traspaso"},
    # ---------- costo directo
    "proveedores":       {"label": "Proveedores y mercancía", "seccion": "costo", "iva": True, "variable": True},
    "paqueteria":        {"label": "Envíos y paquetería", "seccion": "costo", "iva": True, "variable": True},
    "comisiones_venta":  {"label": "Comisiones de terminal y plataformas", "seccion": "gasto_venta", "iva": True, "variable": True},
    # ---------- gastos de operacion
    "nomina":            {"label": "Nómina y colaboradores", "seccion": "gasto_admin"},
    "imss":              {"label": "IMSS e Infonavit", "seccion": "gasto_admin"},
    "renta":             {"label": "Renta", "seccion": "gasto_admin", "iva": True},
    "servicios":         {"label": "Luz, agua, internet y teléfono", "seccion": "gasto_admin", "iva": True},
    "software":          {"label": "Software y suscripciones", "seccion": "gasto_admin", "iva": True},
    "publicidad":        {"label": "Publicidad y marketing", "seccion": "gasto_venta", "iva": True},
    "honorarios":        {"label": "Contador, abogado y asesores", "seccion": "gasto_admin", "iva": True},
    "combustible":       {"label": "Gasolina y transporte", "seccion": "gasto_admin", "iva": True},
    "comisiones_banco":  {"label": "Comisiones bancarias", "seccion": "gasto_admin"},
    "seguros":           {"label": "Seguros", "seccion": "gasto_admin", "iva": True},
    "consumos":          {"label": "Comidas y consumos", "seccion": "gasto_admin", "iva": True, "preguntar": True},
    "arrendamiento":     {"label": "Arrendamiento de auto o equipo", "seccion": "gasto_admin", "iva": True},
    "otros_gastos":      {"label": "Otros gastos del negocio", "seccion": "gasto_admin", "iva": True},
    # ---------- debajo de la linea
    "tarjetas":          {"label": "Pagos de tarjetas de crédito", "seccion": "financiero", "preguntar": True},
    "creditos":          {"label": "Pagos de créditos y préstamos", "seccion": "financiero"},
    "impuestos":         {"label": "Pagos al SAT y otros impuestos", "seccion": "financiero"},
    "iva_comision":      {"label": "IVA de comisiones bancarias", "seccion": "iva"},
    "efectivo":          {"label": "Retiros en efectivo", "seccion": "personal", "preguntar": True},
    "personal":          {"label": "Gastos personales del dueño", "seccion": "personal"},
    "sin_identificar":   {"label": "Sin identificar (contesta las preguntas)", "seccion": "sin_identificar"},
}

# (tipo, palabras clave [cualquiera], categoria). Se evaluan en orden; la primera que coincide gana.
REGLAS_AUTO = [
    ("cargo", ["IVA COM", "IVA COMISION", "IVA POR COMISION"], "iva_comision"),
    ("cargo", ["COMISION", "SERV BANCA", "ANUALIDAD", "MEMBRESIA BANCO", "MANEJO DE CUENTA"], "comisiones_banco"),
    ("abono", ["INTERESES", "RENDIMIENTO", "10 FRACTIONAL", "RENTA "], "otros_ingresos"),
    ("ambos", ["TRASPASO", "TRANSF ENTRE CUENTAS", "TRANSF ENRE CUENTAS", "TRANSFERENCIA ENTRE CUENTAS", "TRASPASO PROPIO", "ENTRE CUENTAS PROPIAS"], "traspaso_propio"),
    ("abono", ["CLIP", "GETNET", "BILLPOCKET", "SUMUP", "ZETTLE", "VENTAS TPV", "DEPOSITO TPV", "LIQUIDACION TPV", "VTAS TDC", "VTAS TDD", "NETPAY", "TERMINAL"], "ventas_tarjeta"),
    ("abono", ["STRIPE", "PAYPAL", "SHOPIFY", "MERCADO PAGO", "MERCADOPAGO", "MERCADO LIBRE", "AMAZON", "RAPPI", "UBER EATS", "DIDI", "CONEKTA", "OPENPAY", "KUESKI", "ETSY"], "ventas_plataforma"),
    ("abono", ["REEMBOLSO", "DEVOLUCION", "BONIFICACION"], "devolucion"),
    ("abono", ["DISPOSICION DE CREDITO", "DISPOSICION CREDITO", "PRESTAMO", "CREDITO SIMPLE"], "prestamo"),
    ("abono", ["APORTACION", "ABONO DE CAPITAL", "CAPITAL SOCIO"], "aportacion"),
    ("cargo", ["NOMINA", "SUELDO", "DISPERSION", "AGUINALDO", "FINIQUITO", "SALARIO"], "nomina"),
    ("cargo", ["SIPARE", "IMSS", "INFONAVIT"], "imss"),
    ("cargo", ["SAT ", "SAT|", "IMPUESTO", "DECLARACION", "TESORERIA", "SECRETARIA DE FINANZAS", "ISN"], "impuestos"),
    ("cargo", ["AMERICAN EXPRESS", "AMEX", "PAGO TARJETA", "PAGO TDC", "PAGO TC ", "TARJETA DE CREDITO", "LIQUIDACION TARJETA", "INVEX", "BANAMEX TDC", "NU MEXICO TARJETA"], "tarjetas"),
    ("cargo", ["LEASING", "ARRENDAMIENTO PURO", "ARRENDADORA"], "arrendamiento"),
    ("cargo", ["PAGO CREDITO", "PGO CREDIT", "PAGO PRESTAMO", "AMORTIZACION", "HIPOTECA", "DOMICILIACION C", "KONFIO", "CREDITO PYME"], "creditos"),
    ("cargo", ["CFE", "TELMEX", "TOTALPLAY", "TOTAL PLAY", "IZZI", "MEGACABLE", "TELCEL", "AT&T", "ATT ", "MOVISTAR", "SIAPA", "JAPAY", "SACMEX", "AGUA ", "GAS NATURAL", "NATURGY", "STARLINK"], "servicios"),
    ("cargo", ["FACEBK", "FACEBOOK", "META ADS", "META PLATFORMS", "GOOGLE ADS", "TIKTOK", "LINKEDIN", "PINTEREST", "MAILCHIMP", "HUBSPOT"], "publicidad"),
    ("cargo", ["GOOGLE", "MICROSOFT", "ADOBE", "NOTION", "CANVA", "APPLE.COM", "APPLE COM", "OPENAI", "CHATGPT", "ANTHROPIC", "ZOOM", "SLACK", "DROPBOX", "TWILIO", "AWS", "AMAZON WEB", "GODADDY", "WIX", "SHOPIFY", "ALEGRA", "CONTPAQ", "ASPEL", "SPOTIFY", "NETFLIX"], "software"),
    ("cargo", ["DHL", "FEDEX", "ESTAFETA", "UPS", "PAQUETEXPRESS", "99MINUTOS", "SKYDROPX", "ENVIA.COM", "REDPACK", "CORREOS DE MEXICO"], "paqueteria"),
    ("cargo", ["GASOLINA", "GASOLINERA", "PEMEX", "OXXO GAS", "G500", "MOBIL", "SHELL", "BP ", "UBER", "CABIFY", "TAG ", "IAVE", "PASE ", "CASETA", "TELEVIA"], "combustible"),
    ("cargo", ["HONORARIOS", "CONTADOR", "CONTABILIDAD", "ASESORIA", "NOTARIA", "DESPACHO", "ABOGADO"], "honorarios"),
    ("cargo", ["RENTA", "ARRENDAMIENTO", "BODEGA", "ALQUILER"], "renta"),
    ("cargo", ["SEGURO", "SEGUROS", "GNP", "AXA", "QUALITAS", "MAPFRE", "CHUBB", "ALLIANZ", "METLIFE"], "seguros"),
    ("cargo", ["RETIRO CAJERO", "RETIRO EN EFECTIVO", "RETIRO EFECTIVO", "DISPOSICION EFECTIVO", "ATM", "CAJERO"], "efectivo"),
    ("cargo", ["OXXO", "7 ELEVEN", "STARBUCKS", "RESTAURANT", "REST ", "CAFE", "TAQUERIA", "BISTRO", "TAPROOM", "WALMART", "SORIANA", "CHEDRAUI", "COSTCO", "SAMS", "LIVERPOOL", "PALACIO DE HIERRO", "CINEPOLIS", "CINEMEX"], "consumos"),
    ("cargo", ["COMISION CLIP", "COMISION MERCADO PAGO", "COMISION STRIPE"], "comisiones_venta"),
]

FINTECH = ("REVOLUT", "NVIO", "NU MEXICO", "NUBANK", "HEY BANCO", "KLAR", "STORI", "UALA", "SPIN BY OXXO", "MERCADO PAGO W", "CETES", "GBM", "BITSO")

# Opciones de respuesta para las preguntas (lo que el usuario ve)
OPCIONES_ABONO = [
    ("ventas", "Venta o cobro a un cliente"),
    ("traspaso_propio", "Dinero de otra cuenta mía"),
    ("prestamo", "Un préstamo o crédito"),
    ("aportacion", "Lo puse yo o un socio"),
    ("devolucion", "Reembolso o devolución"),
    ("otros_ingresos", "Otro ingreso (renta, intereses)"),
]
OPCIONES_CARGO = [
    ("proveedores", "Proveedor o mercancía"),
    ("nomina", "Nómina o pago a colaborador"),
    ("renta", "Renta"),
    ("servicios", "Servicio (luz, internet, teléfono)"),
    ("software", "Software o suscripción"),
    ("publicidad", "Publicidad"),
    ("honorarios", "Contador o asesor"),
    ("impuestos", "Impuestos"),
    ("tarjetas", "Pago de tarjeta"),
    ("creditos", "Pago de crédito"),
    ("traspaso_propio", "A otra cuenta mía"),
    ("personal", "Gasto personal mío"),
    ("otros_gastos", "Otro gasto del negocio"),
]
