<div align="center">

# Paccioli CFO

### Tu CFO en tu computadora.

Le das tu estado de cuenta. Te dice cuánto ganaste, cuánto te toca pagar al SAT,<br>
cuántos días te alcanza el dinero y qué tienes que arreglar. **En vivo y gratis.**

[![pruebas](https://github.com/pachio2509/paccioli-cfo/actions/workflows/pruebas.yml/badge.svg)](https://github.com/pachio2509/paccioli-cfo/actions/workflows/pruebas.yml)
![Python](https://img.shields.io/badge/python-3.9%2B-0F1B2D)
![Licencia MIT](https://img.shields.io/badge/licencia-MIT-0F1B2D)
![Hecho en México](https://img.shields.io/badge/hecho%20en-M%C3%A9xico-2A7AD6)

<img src="docs/img/tablero.png" alt="Tablero de Paccioli CFO con semáforo, indicadores, alertas y preguntas" width="100%">

</div>

---

## ¿Para quién es?

Para el dueño de un negocio o el emprendedor que **cierra el mes sin saber si ganó dinero**.
Que vende, paga, cobra y paga tarjetas, y al final no sabe cuánto le quedó de verdad.

No necesitas saber contabilidad. Si sabes descargar tu estado de cuenta, ya puedes.

## Instálalo en 3 pasos

**1. Descárgalo**

```bash
git clone https://github.com/pachio2509/paccioli-cfo.git
cd paccioli-cfo
```

¿No usas git? Botón verde **Code → Download ZIP** y descomprímelo.

**2. Instálalo** (una sola vez, necesitas [Python 3.9+](https://www.python.org/downloads/))

| Mac / Linux | Windows |
|---|---|
| `./instalar.sh` | doble clic en `instalar.bat` |

**3. Ábrelo**

| Mac / Linux | Windows |
|---|---|
| `./iniciar.sh` | doble clic en `iniciar.bat` |

Se abre tu navegador. **Arrastra tu estado de cuenta** y listo.

> ¿Quieres verlo antes de usar tus datos? Corre `./iniciar.sh --demo` (o `iniciar.bat --demo`) y juega con **Café La Ceiba**, un negocio de ejemplo.

## Qué te dice

| | |
|---|---|
| **Semáforo** | En una frase: cómo te fue y qué es lo más importante. |
| **Ingresos, gastos y utilidad** | Sin IVA, como los ve un CFO. Lo que es del SAT no es tuyo. |
| **Punto de equilibrio** | Lo mínimo que tienes que vender al mes para no perder. |
| **Colchón de caja** | Cuántos días de pagos cubre lo que tienes en el banco. |
| **Aparta para el SAT** | ISR + IVA estimados según tu régimen (RESICO, actividad empresarial o persona moral) y cuándo vence. |
| **¿Quién te paga?** | Tus clientes y canales. Te avisa si dependes demasiado de uno. |
| **¿En qué se va tu dinero?** | Todo lo que salió, por concepto. |
| **Estado de resultados** | Completo, con lo que va "debajo de la línea" (tarjetas, créditos, retiros). |

<img src="docs/img/cascada.png" alt="Gráfica de cascada: de ingresos a utilidad" width="100%">

## Te pregunta lo que no entiende

Un banco dice `SPEI RECIBIDO EVENTOS PENINSULA SA DE CV`. ¿Es una venta? ¿Un préstamo? ¿Dinero tuyo de otra cuenta?
Paccioli **no adivina en silencio**: te pregunta.

- ¿En qué régimen fiscal estás?
- ¿Tus precios ya incluyen IVA?
- ¿Cobras por otro lado que no sea esta cuenta? ¿Cuánto al mes?
- Pagaste $43,658 de tarjetas. ¿Lo que compras con tarjeta es del negocio?
- Pagaste $203,349 a «Granos del Soconusco». ¿Qué es?

Contestas con un clic **y se aplica sola** a los movimientos parecidos, hoy y los próximos meses. Lo que todavía no sabe qué es, lo cuenta como gasto (mejor sorprenderte para bien).

## Y te avisa

- 🔴 **Este mes perdiste $2,402.** Revisa tus 3 gastos más grandes.
- 🟠 **Tu dinero en el banco cubre 23 días de pagos.** Lo sano es tener 30 o más.
- 🟠 **62% de tus ventas viene de un solo cliente.** Si se va, tu negocio se cae.
- 🟠 **No veo pago al SAT este mes.** Tu declaración vence el 19 de octubre.
- 🟠 **Vas a $3.6 millones al año: cerca del tope de RESICO.**
- 🟠 **Sacaste $30,000 para gastos personales.** Ponte un sueldo fijo.

<img src="docs/img/tendencia.png" alt="Ingresos, gastos y utilidad mes con mes" width="100%">

## En vivo

Deja abierto el tablero. Cada vez que sueltas un archivo nuevo en la carpeta `mis-estados-de-cuenta/` (o lo arrastras al navegador) **se recalcula solo**. Sin botones, sin "actualizar".

## Tus datos no salen de tu computadora

- Todo corre en tu compu (`127.0.0.1`). No hay nube, no hay cuenta, no hay login.
- Tus estados de cuenta y respuestas viven en `mis-estados-de-cuenta/` y `mi-negocio/`, que **nunca se suben a GitHub** (están en `.gitignore`).
- El código es abierto: puedes revisar línea por línea qué hace.

## Bancos que lee

| Archivo | Estado |
|---|---|
| **PDF de BBVA** (cuenta empresarial y Libretón) | ✅ Validado al centavo contra el resumen del banco |
| **Excel / CSV de cualquier banco o app** (Santander, Banorte, Banamex, HSBC, Nu, Mercado Pago, Clip...) | ✅ Si trae saldo, revisa que cada renglón cuadre |
| PDF de otros bancos | 🔜 Mientras, descarga el Excel o CSV desde tu banca en línea |

¿Tu banco no funciona? [Abre un issue](https://github.com/pachio2509/paccioli-cfo/issues) con el nombre del banco (**nunca subas tu estado de cuenta real**).

## Cómo piensa (los principios de un CFO)

1. **El banco es la verdad.** Si no cuadra con el banco, no se reporta.
2. **Resultados sin IVA, flujo con IVA.** El IVA cobrado no es tuyo.
3. **El fondo sobre la forma.** Pagar la tarjeta no es un gasto; lo que compraste con ella, sí.
4. **Un mes incompleto se marca como incompleto.** Nada de números a medias disfrazados.
5. **Cada criterio que decides se vuelve regla.** Contestas una vez.

Más detalle en [docs/como-funciona.md](docs/como-funciona.md).

## Para desarrolladores

```bash
python -m paccioli_cfo                  # tablero (carpeta actual)
python -m paccioli_cfo --demo           # negocio de ejemplo
python -m paccioli_cfo resumen          # tus números en la terminal
python -m paccioli_cfo --carpeta ~/mi-negocio --puerto 9000
python -m pytest                        # pruebas (solo datos inventados)
```

Sin frameworks: Python estándar + `pdfplumber` + `openpyxl`. El tablero es HTML/JS/SVG puro. Ver [CONTRIBUTING.md](CONTRIBUTING.md).

---

<div align="center">

**Paccioli CFO** es un proyecto de [Kaptal](https://kaptal.com.mx) · Mérida, México.<br>
¿Quieres que un CFO de verdad revise tus números? Escríbenos.

<sub>Los cálculos de impuestos son estimaciones informativas con la tarifa 2026 y no sustituyen a tu contador.</sub>

</div>
