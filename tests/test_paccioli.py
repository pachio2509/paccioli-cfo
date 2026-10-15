"""Pruebas con datos inventados (nunca con estados de cuenta reales)."""
import datetime as dt
import shutil
from pathlib import Path

import pytest

from paccioli_cfo import fiscal, motor, preguntas
from paccioli_cfo.clasificador import _contraparte_simple, clasificar
from paccioli_cfo.espacio import Espacio
from paccioli_cfo.lectores import tabla
from paccioli_cfo.modelo import Movimiento

RAIZ = Path(__file__).resolve().parent.parent
HOY = dt.date(2026, 10, 15)


@pytest.fixture
def demo(tmp_path):
    esp = Espacio(tmp_path)
    for f in (RAIZ / "demo" / "estados").glob("*.csv"):
        shutil.copy(f, esp.estados / f.name)
    return esp


def test_lee_csv_y_cuadra_saldos(demo):
    e = motor.analizar(demo, HOY)
    assert len(e["archivos"]) == 3
    assert all(f["validacion"]["ok"] for f in e["archivos"])
    assert [m["mes"] for m in e["meses"]] == ["2026-07", "2026-08", "2026-09"]
    assert e["mes_actual"] == "2026-09"
    assert e["saldo"] == pytest.approx(241274.39, abs=0.01)


def test_csv_con_saldos_rotos(tmp_path):
    f = tmp_path / "x.csv"
    f.write_text("Fecha,Concepto,Cargo,Abono,Saldo\n01/09/2026,VENTA,,100,1100\n02/09/2026,PAGO,50,,999\n", encoding="utf-8")
    _, res = tabla.leer(f)
    assert res["cuadre_saldos"] is False


def test_csv_descendente_e_importe_con_signo(tmp_path):
    f = tmp_path / "y.csv"
    f.write_text("Fecha;Descripción;Importe;Saldo\n02/09/2026;PAGO;-50,00;1050,00\n01/09/2026;VENTA;100,00;1100,00\n", encoding="utf-8")
    movs, res = tabla.leer(f)
    assert {(m.cargo, m.abono) for m in movs} == {(50.0, 0.0), (0.0, 100.0)}
    assert res["cuadre_saldos"] and res["saldo_final"] == 1050.0


def test_preguntas_y_respuestas_se_vuelven_reglas(demo):
    e = motor.analizar(demo, HOY)
    ids = [q["id"] for q in e["preguntas"]]
    assert "perfil:regimen" in ids
    prov = next(i for i in ids if "GRANOS DEL SOCONUSCO" in i)
    preguntas.responder(demo, prov, "proveedores")
    e2 = motor.analizar(demo, HOY)
    granos = [m for m in e2["movimientos"] if "SOCONUSCO" in m["descripcion"]]
    assert granos and all(m["categoria"] == "proveedores" for m in granos)
    assert prov not in [q["id"] for q in e2["preguntas"]]


def test_estado_de_resultados_suma(demo):
    e = motor.analizar(demo, HOY)
    for d in e["por_mes"].values():
        assert d["utilidad"] == pytest.approx(d["ingresos"] - d["gastos"], abs=0.05)


def test_impuestos_resico(demo):
    preguntas.responder(demo, "perfil:regimen", "resico")
    e = motor.analizar(demo, HOY)
    imp = e["por_mes"][e["mes_actual"]]["impuestos"]
    assert imp["definido"] and imp["isr"] > 0


def test_alertas_presentes(demo):
    e = motor.analizar(demo, HOY)
    assert e["alertas"] and {a["nivel"] for a in e["alertas"]} <= {"rojo", "ambar", "info", "verde"}


def test_contraparte_legible():
    assert _contraparte_simple("SPEI RECIBIDO RAPPI RESTAURANTES SA DE CV") == "Rappi"
    assert _contraparte_simple("DEPOSITO CLIP LIQUIDACION 0109") == "Clip"
    assert _contraparte_simple("SPEI ENVIADO GRANOS DEL SOCONUSCO SA DE CV REF 123") == "Granos Del Soconusco Sa De Cv"


def test_cuenta_propia_es_traspaso():
    m = Movimiento(fuente="t", fecha="2026-09-01", descripcion="SPEI RECIBIDO|NU MEXICO|0001|MARIA FERNANDA LOPEZ", abono=5000)
    clasificar([m], [], "MARIA FERNANDA LOPEZ RUIZ")
    assert m.categoria == "traspaso_propio"


def test_fiscal():
    assert fiscal.isr_resico_pf(60000)["pago"] == pytest.approx(900)
    assert fiscal.proximo_vencimiento(dt.date(2026, 10, 15)) == dt.date(2026, 10, 19)
    assert fiscal.proximo_vencimiento(dt.date(2026, 10, 20)) == dt.date(2026, 11, 17)
