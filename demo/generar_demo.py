"""Genera los estados de cuenta del negocio de ejemplo (inventado): Café La Ceiba, Mérida.

    python demo/generar_demo.py

Crea demo/estados/2026-07.csv, 2026-08.csv y 2026-09.csv con el formato que exporta
cualquier banca en línea (Fecha, Concepto, Cargo, Abono, Saldo). Siempre salen iguales (semilla fija).
"""
import calendar
import csv
import datetime as dt
import random
from pathlib import Path

AQUI = Path(__file__).parent
random.seed(2026)


def mes(anio, m, saldo, ventas_factor, con_sat):
    dias = calendar.monthrange(anio, m)[1]
    movs = []
    add = lambda d, concepto, cargo=0.0, abono=0.0: movs.append((dt.date(anio, m, d), concepto, round(cargo, 2), round(abono, 2)))
    for d in range(1, dias + 1):
        f = dt.date(anio, m, d)
        if f.weekday() != 6:  # la terminal deposita de lunes a sábado
            base = 9800 if f.weekday() >= 4 else 7600
            add(d, f"DEPOSITO CLIP LIQUIDACION {f:%d%m}", abono=base * ventas_factor * random.uniform(.8, 1.2))
        if f.weekday() == 1:
            add(d, "SPEI RECIBIDO RAPPI RESTAURANTES SA DE CV", abono=random.uniform(9000, 13500) * ventas_factor)
            add(d, "SPEI ENVIADO GRANOS DEL SOCONUSCO SA DE CV REF GRANO VERDE", cargo=random.uniform(14500, 17500) * ventas_factor)
        if f.weekday() == 3:
            add(d, "SPEI ENVIADO LACTEOS LA HOLANDESA PEDIDO SEMANAL", cargo=random.uniform(6200, 7800) * ventas_factor)
        if f.weekday() == 4:
            add(d, "SPEI RECIBIDO UBER EATS MEXICO", abono=random.uniform(4200, 6800) * ventas_factor)
    add(9, "SPEI RECIBIDO EVENTOS PENINSULA SA DE CV CATERING", abono=random.choice([28420, 34800, 41760]))
    add(21, "SPEI RECIBIDO HOTEL CASA DEL MAYAB SA DE CV CAFE PARA HOTEL", abono=random.choice([18560, 22040]))
    add(3, "RENTA LOCAL CALLE 47 CENTRO", cargo=38000)
    add(15, "PAGO DE NOMINA QUINCENA", cargo=46500)
    add(dias, "PAGO DE NOMINA QUINCENA", cargo=46500)
    add(17, "PAGO SIPARE IMSS INFONAVIT", cargo=14820)
    add(8, "CFE SUMINISTRADOR SERVICIOS BASICOS", cargo=random.uniform(6800, 8900))
    add(11, "TELMEX INFINITUM NEGOCIO", cargo=899)
    add(5, "FACEBK META ADS CAMPANA LOCAL", cargo=random.uniform(4500, 6500))
    add(12, "GOOGLE WORKSPACE", cargo=642)
    add(6, "SPEI ENVIADO DESPACHO CONTABLE HONORARIOS", cargo=6960)
    add(20, "PAGO TARJETA AMERICAN EXPRESS", cargo=random.uniform(11000, 19000))
    add(14, "RETIRO CAJERO AUTOMATICO", cargo=6000)
    add(27, "RETIRO CAJERO AUTOMATICO", cargo=4000)
    add(24, "SPEI ENVIADO MANTENIMIENTO REFRIGERACION DEL SURESTE", cargo=random.uniform(3200, 5400))
    add(25, "SPEI ENVIADO EMPAQUES BIODEGRADABLES YUC", cargo=random.uniform(5200, 7400) * ventas_factor)
    add(28, "COMISION MANEJO DE CUENTA", cargo=350)
    add(28, "IVA COMISION MANEJO DE CUENTA", cargo=56)
    if con_sat:
        add(16, "PAGO REFERENCIADO SAT DECLARACION MENSUAL", cargo=random.uniform(17000, 21000))
    movs.sort(key=lambda x: (x[0], -x[3]))
    filas = []
    for f, c, cargo, abono in movs:
        saldo = round(saldo + abono - cargo, 2)
        filas.append([f.strftime("%d/%m/%Y"), c, f"{cargo:.2f}" if cargo else "", f"{abono:.2f}" if abono else "", f"{saldo:.2f}"])
    return filas, saldo


def main():
    destino = AQUI / "estados"
    destino.mkdir(exist_ok=True)
    saldo = 142_300.00
    for m, factor, sat in ((7, 1.00, True), (8, 1.06, True), (9, 0.88, False)):
        filas, saldo = mes(2026, m, saldo, factor, sat)
        with open(destino / f"cafe-la-ceiba-2026-{m:02d}.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["Fecha", "Concepto", "Cargo", "Abono", "Saldo"])
            w.writerows(filas)
        print(f"2026-{m:02d}: {len(filas)} movimientos, saldo final {saldo:,.2f}")


if __name__ == "__main__":
    main()
