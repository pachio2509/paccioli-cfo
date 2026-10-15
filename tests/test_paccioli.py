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


# ---------- casos de la vida real (con datos inventados)

def _mov(desc, cargo=0.0, abono=0.0, fecha="2026-09-10"):
    return Movimiento(fuente="t", fecha=fecha, descripcion=desc, cargo=cargo, abono=abono)


def test_pagar_tu_tarjeta_o_tu_credito_no_es_traspaso():
    tit = "ANA SOFIA PEREZ LUNA"
    tdc = _mov("SPEI ENVIADO INVEX | 0509260PAGO T Referencia 1 | ANA SOFIA PEREZ", cargo=7000)
    cred = _mov("SPEI ENVIADO BANORTE | 2309260pgo creditl Referencia 2 | ANA SOFIA PEREZ LUNA", cargo=20000)
    propia = _mov("SPEI ENVIADO STP | transf | REVOLUT ANA SOFIA PEREZ", cargo=5000)
    clasificar([tdc, cred, propia], [], tit)
    assert (tdc.categoria, cred.categoria, propia.categoria) == ("tarjetas", "creditos", "traspaso_propio")


def test_comision_a_una_persona_no_es_comision_bancaria():
    a = _mov("SPEI ENVIADO BANORTE | 0509260comision Referencia 3 | JUAN LOPEZ", cargo=5000)
    b = _mov("COMISION MANEJO DE CUENTA", cargo=150)
    clasificar([a, b], [])
    assert a.categoria == "comisiones_pagadas" and b.categoria == "comisiones_banco"


def test_deposito_sin_nombre_no_se_cuenta_como_venta():
    m = _mov("SPEI RECIBIDOSTP | 0200926 Referencia 0188492256 646", abono=100000)
    clasificar([m], [])
    assert m.categoria == "entrada_por_identificar"


def _csv(tmp_path, filas, nombre="banco.csv"):
    esp = Espacio(tmp_path)
    (esp.estados / nombre).write_text("Fecha,Concepto,Cargo,Abono,Saldo\n" + "\n".join(filas) + "\n", encoding="utf-8")
    return esp


def test_comisiones_netas_no_pierden_iva_ni_inventan_impuestos(tmp_path):
    esp = _csv(tmp_path, ["01/09/2026,SALDO,,,1000", "05/09/2026,SPEI RECIBIDO COMIS A 04 SEPTIEMBRE ALLIANZ MEXICO,,50000,51000",
                          "30/09/2026,PAGO RENTA BODEGA,11600,,39400"])
    preguntas.responder(esp, "perfil:regimen", "resico")
    e = motor.analizar(esp, HOY)
    d = e["por_mes"]["2026-09"]
    assert d["ingresos"] == pytest.approx(50000)  # llegan netas: no se les quita un IVA que nunca se cobro
    assert d["impuestos"]["definido"] is False and "estado de comisiones" in d["impuestos"]["texto"]
    assert any("comisiones que llegan netas" in a["titulo"] for a in e["alertas"])


def test_tarjetas_por_desglosar_quedan_aparte_y_mitad_y_mitad(tmp_path):
    esp = _csv(tmp_path, ["01/09/2026,SALDO,,,100000", "05/09/2026,VENTA CLIENTE SA DE CV,,11600,111600",
                          "20/09/2026,PAGO TARJETA DE CREDITO,23200,,88400"])
    preguntas.responder(esp, "perfil:tarjetas", "por_desglosar")
    d = motor.analizar(esp, HOY)["por_mes"]["2026-09"]
    assert d["gastos"] == 0 and d["tarjetas"] == pytest.approx(23200)
    preguntas.responder(esp, "perfil:tarjetas", "mixto")
    d = motor.analizar(esp, HOY)["por_mes"]["2026-09"]
    assert d["gastos"] == pytest.approx(10000) and d["tarjetas"] == pytest.approx(11600)


def test_estado_que_no_corta_en_mes_calendario(tmp_path):
    esp = _csv(tmp_path, ["07/09/2026,VENTA CLIENTE SA DE CV,,1160,1160", "20/09/2026,VENTA CLIENTE SA DE CV,,1160,2320",
                          "06/10/2026,VENTA CLIENTE SA DE CV,,1160,3480"])
    e = motor.analizar(esp, HOY)
    periodos = [m for m in e["meses"] if m.get("periodo")]
    assert len(periodos) == 1 and e["mes_actual"] == periodos[0]["mes"]
    assert e["por_mes"][e["mes_actual"]]["ingresos"] == pytest.approx(3000)
    assert any("mes calendario" in a["titulo"] for a in e["alertas"])


def test_avisa_si_mezclas_dos_titulares(demo):
    from paccioli_cfo import alertas
    e = motor.analizar(demo, HOY)
    e["archivos"][0]["rfc"], e["archivos"][1]["rfc"] = "AAAA800101AA1", "BBBB900202BB2"
    e["archivos"][0]["titular"], e["archivos"][1]["titular"] = "ANA PEREZ", "LUIS GOMEZ"
    assert any("distintas" in a["titulo"] for a in alertas.generar(e, e["mes_actual"], HOY))


def test_el_demo_no_acepta_estados_reales(demo):
    (demo.datos / ".demo").touch()
    (demo.estados / "mi-banco.csv").write_text("Fecha,Concepto,Cargo,Abono,Saldo\n01/09/2026,VENTA,,100,100\n", encoding="utf-8")
    e = motor.analizar(demo, HOY)
    assert e["es_demo"] and any("mezclado con el demo" in a["titulo"] for a in e["alertas"])


# ---------- PDF de cualquier banco (estados inventados en tests/fixtures)

def test_pdf_otro_banco_con_columnas_retiros_depositos():
    from paccioli_cfo import lectores
    movs, res = lectores.leer(RAIZ / "tests" / "fixtures" / "banco-columnas.pdf")
    assert len(movs) == 5 and res["cuadre_saldos"] is True
    assert sum(m.abono for m in movs) == pytest.approx(58000) and sum(m.cargo for m in movs) == pytest.approx(31920)
    assert res["periodo"] == "DEL 01/09/2026 AL 30/09/2026" and res["rfc"] == "TML180305AB1"
    assert movs[0].descripcion.startswith("DEPOSITO CLIENTE AUTOPARTES")


def test_pdf_otro_banco_importe_con_signo_y_fechas_con_mes():
    from paccioli_cfo import lectores
    movs, res = lectores.leer(RAIZ / "tests" / "fixtures" / "banco-importe-con-signo.pdf")
    assert [(m.fecha, m.cargo, m.abono) for m in movs] == [
        ("2026-09-16", 0.0, 4500.5), ("2026-09-20", 1250.25, 0.0), ("2026-10-01", 6000.0, 0.0), ("2026-10-10", 0.0, 7749.75)]
    assert res["cuadre_saldos"] is True and res["periodo"] == "DEL 15/09/2026 AL 14/10/2026"
