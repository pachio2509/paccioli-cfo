# Cómo funciona Paccioli CFO

```
mis-estados-de-cuenta/  ──►  lectores/  ──►  clasificador  ──►  motor  ──►  tablero (navegador)
   PDF / Excel / CSV        BBVA PDF,        reglas auto +      estado de       alertas y
                            tabla univ.      tus respuestas     resultados      preguntas
```

## 1. Leer
- **BBVA PDF** (`lectores/bbva_pdf.py`): ubica las columnas CARGOS/ABONOS por su posición en la página, junta cada movimiento con sus líneas de detalle y **compara contra el resumen del banco** (número de cargos y abonos, totales y saldo). Si no cuadra al centavo, te lo dice.
- **Excel/CSV** (`lectores/tabla.py`): busca la fila de encabezados por nombre (fecha, concepto, cargo, abono, importe, saldo). Acepta `1,234.56`, `1.234,56`, `(500)`, `-500`, fechas `dd/mm/aaaa`, `aaaa-mm-dd` o `07/SEP/2026`. Si trae saldo, revisa que cada renglón cuadre (en orden ascendente o descendente).

## 2. Clasificar
En este orden, gana la primera que aplique:
1. **Tus respuestas** (`mi-negocio/reglas.json`), por contraparte o por movimiento.
2. **Cuenta propia**: si la contraparte se llama como el titular, es un traspaso y no cuenta.
3. **Reglas automáticas** para México (`categorias.py`): comisiones, terminales (Clip, Getnet...), plataformas (Rappi, Mercado Pago, Stripe...), nómina, IMSS, SAT, tarjetas, créditos, servicios, publicidad, software, paquetería, gasolina, honorarios, renta, seguros, efectivo y consumos.
4. Si no sabe: un **depósito** se supone venta y un **cargo** queda "por identificar" y se cuenta como gasto. Los que pesan más se vuelven preguntas.

## 3. Calcular (`motor.py`)
- **Estado de resultados** por mes: ventas, otros ingresos, costo directo, gastos de venta y de administración. Sin IVA si cobras IVA.
- **Debajo de la línea**: pagos de tarjetas y créditos, impuestos, retiros personales, préstamos y aportaciones. Mueven el dinero pero no son utilidad.
- **Punto de equilibrio** = gastos fijos ÷ margen de contribución.
- **Colchón** = saldo final ÷ salidas diarias promedio (sin traspasos).
- **Mes incompleto**: si los estados de cuenta no cubren el mes entero, se marca y no se usa como mes principal.

## 4. Impuestos (`fiscal.py`) · estimaciones 2026
- **RESICO persona física**: 1% a 2.5% de lo cobrado (art. 113-E LISR), tope $3.5 millones al año.
- **Actividad empresarial**: tarifa mensual 2026 (Anexo 8 RMF) sobre la utilidad del mes.
- **Persona moral**: 30% de la utilidad como referencia (tu pago provisional real usa coeficiente de utilidad).
- **IVA**: 16% cobrado menos 16% acreditable de gastos con IVA.
- **Vencimiento**: día 17 del mes siguiente (si cae en fin de semana, el lunes).

No sustituye a tu contador: es para que llegues a la plática sabiendo de qué tamaño es el número.

## 5. En vivo (`servidor.py`)
Servidor HTTP de la librería estándar, solo en `127.0.0.1`. Un hilo revisa la carpeta cada 2 segundos (tamaño y fecha de cada archivo + tus respuestas). El navegador pregunta `/api/version` cada 2 segundos y, si cambió, vuelve a dibujar.

| Ruta | Qué hace |
|---|---|
| `GET /api/estado` | Todo el análisis en JSON |
| `POST /api/subir?nombre=` | Guarda un archivo en `mis-estados-de-cuenta/` |
| `POST /api/responder` | `{id, valor}` contesta una pregunta |
| `POST /api/reclasificar` | `{id, categoria}` cambia un movimiento |
| `POST /api/quitar_archivo` | Mueve el archivo a `mi-negocio/archivos-quitados/` |
