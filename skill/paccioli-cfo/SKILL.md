---
name: paccioli-cfo
description: Skill de CFO que crea un dashboard financiero a partir del estado de cuenta de cualquier banco y cualquier país (PDF, Excel, CSV o foto). Sirve para negocios, independientes y finanzas personales — cuánto entró, cuánto se gastó, cuánto quedó, cuánto apartar para impuestos y qué arreglar primero. Úsalo cuando alguien suba o mencione su estado de cuenta, pida un dashboard o tablero de sus finanzas, quiera saber cómo va su negocio o sus finanzas, su estado de resultados, su utilidad, su ahorro, su punto de equilibrio o cuánto pagar de impuestos, o diga "Paccioli", "mi CFO", "mis números".
---

# Paccioli CFO · skill de CFO que crea tu dashboard

Le das tu estado de cuenta y te entrega su dashboard financiero, en lenguaje sencillo. Sirve para un negocio, para alguien que trabaja por su cuenta o para las finanzas personales, en cualquier país.

La persona que te habla probablemente **no sabe contabilidad ni usa la terminal**. Tú haces todo el trabajo técnico. Ella solo te da su archivo y contesta preguntas sencillas.

## Reglas que no se rompen

1. **El banco es la verdad.** Cada estado de cuenta se valida al centavo contra sus saldos. Si no cuadra, no reportes números: arréglalo o dilo.
2. **Nunca inventes un movimiento.** Si transcribes un PDF o una foto, cada renglón sale del documento.
3. **Lo que no sabes, lo preguntas.** No adivines si un depósito es venta o si una tarjeta es del negocio.
4. **Los datos no salen de aquí.** No los subas a ningún sitio ni los pongas en una URL.
5. **Habla como a un dueño de negocio**, no como a un contador. Cifras redondeadas, frases cortas.

## Paso 1 · Prepara el programa

El programa viene dentro de este skill, en `paccioli_cfo/`. Ubica la carpeta del skill (donde está este archivo). `preparar.sh` deja listo un Python con lo necesario sin tocar el del sistema (en Mac moderno `pip install` directo falla) e imprime su ruta:

```bash
SKILL="<carpeta de este skill>"
PY=$(bash "$SKILL/preparar.sh")
export PYTHONPATH="$SKILL"
"$PY" -m paccioli_cfo --help
```

Usa siempre `"$PY" -m paccioli_cfo ...` en los pasos que siguen. Si la persona ya tiene Paccioli CFO instalado en su computadora (carpeta `paccioli-cfo` con `.venv`), puedes usar ese: `./.venv/bin/python -m paccioli_cfo`.

## Paso 2 · Crea su espacio y pon sus archivos

```bash
NEG="$HOME/Paccioli/<nombre-del-negocio>"      # en claude.ai usa una carpeta de trabajo, p. ej. /tmp/paccioli/<negocio>
mkdir -p "$NEG/mis-estados-de-cuenta"
cp <archivos que te dio> "$NEG/mis-estados-de-cuenta/"
"$PY" -m paccioli_cfo resumen --carpeta "$NEG"
```

Una carpeta por negocio. Si te dan estados de **dos personas o empresas distintas**, sepáralos en dos carpetas.

## Paso 3 · Revisa que cada archivo cuadre

En la salida de `resumen`, cada archivo dice `✓` (cuadra con el banco), `✗` (no cuadra) o `·` (no trae saldos para validar).

- **✓** → sigue al paso 4.
- **✗, `No pude leer`, o es una foto/escaneo** → transcríbelo tú (ver abajo) y vuelve a correr `resumen`.
- **·** → sigue, pero avísale que no se pudo validar contra el banco.

### Cómo transcribir un estado de cuenta que el programa no lee

Lee el documento completo (todas las páginas) y escribe un CSV con exactamente estas columnas:

```csv
Fecha,Concepto,Cargo,Abono,Saldo
07/09/2026,SPEI RECIBIDO CLIENTE XYZ SA DE CV,,23200.00,40516.18
08/09/2026,PAGO TARJETA DE CREDITO,10800.00,,29716.18
```

- `Fecha` en dd/mm/aaaa. `Cargo` = sale dinero, `Abono` = entra dinero, sin signos ni `$`.
- `Concepto`: copia la descripción del banco completa (incluye el nombre de quien paga o cobra: así se clasifica sola).
- `Saldo`: el saldo impreso en ese renglón. Si el banco solo lo imprime al final del día, ponlo en el último movimiento del día y deja vacíos los demás.
- Guárdalo como `<nombre-original>-transcrito.csv` en `mis-estados-de-cuenta/` y **mueve el original fuera de esa carpeta** (si no, se cuenta doble).
- Corre `resumen` otra vez. Debe salir `✓`. Si sale `✗`, busca el renglón que falta o el importe mal copiado; no entregues números hasta que cuadre.

## Paso 4 · Hazle las preguntas importantes

```bash
"$PY" -m paccioli_cfo preguntas --carpeta "$NEG"
```

Devuelve una lista con `id`, `titulo` y `opciones`. Pregúntale **máximo 3 a la vez**, en sus palabras. Siempre empieza por:
1. **Para qué usa la cuenta** (`perfil:uso`: `negocio`, `independiente` o `personal`). Si ya te lo dijo en la conversación, contéstalo tú.
2. **En qué país está** (`perfil:pais`: `MX`, `CO`, `PE`, `CL`, `AR`, `ES`, `US`… u `otro`; con `otro` pide moneda y tasa de impuesto). Si el estado de cuenta lo deja claro (banco, moneda), contéstalo tú y díselo.

Después, en negocios: régimen fiscal (solo México), si cobra con impuesto incluido y las tarjetas. Luego los depósitos y pagos grandes que no se reconocen.

Para cada respuesta:

```bash
"$PY" -m paccioli_cfo responder "<id>" "<valor de la opcion>" --carpeta "$NEG"
```

Guías para que no se equivoque:
- **Tarjetas:** si no tiene el estado de cuenta de la tarjeta, la respuesta honesta es `por_desglosar` (quedan aparte y no cambian su utilidad). Solo `negocio` si de verdad todo lo que paga con tarjeta es del negocio.
- **Comisionistas (agentes de seguros, promotorías):** sus comisiones llegan netas de ISR e IVA retenidos. Pídele su estado de comisiones; sin él no se estiman impuestos.
- **Depósitos sin nombre** (por ejemplo, "SPEI sin nombre" de STP): suelen ser dinero suyo de otra cuenta. Pregúntale antes de contarlos como venta.
- **Si su estado no corta en mes calendario** (del 7 de septiembre al 6 de octubre), el tablero muestra el periodo completo. Para un mes exacto, pídele el estado anterior.

## Paso 5 · Entrégale su tablero

**Si estás en su computadora (Claude Code):** abre el tablero en vivo. Córrelo en segundo plano (no termina solo: es un servidor local) y abre el navegador él mismo.

```bash
"$PY" -m paccioli_cfo --carpeta "$NEG"
```

Si sueltas un archivo en el tablero del demo (`--demo`), se pasa solo a la carpeta real: no hay que cerrar nada.

**Si estás en claude.ai o no puedes abrir un navegador:** genera el tablero en un solo archivo y entrégaselo para descargar.

```bash
"$PY" -m paccioli_cfo exportar --carpeta "$NEG" --salida "<carpeta de salida>/tablero-<negocio>.html"
```

El archivo se abre con doble clic, sin internet. Lleva sus números adentro: dile que lo comparta solo con quien quiera.

Después, explícale en **5 renglones o menos**:
1. Cuánto le quedó (utilidad, o ahorro en finanzas personales) y qué porcentaje es.
2. Su salud financiera y lo más importante que debe arreglar.
3. Cuánto apartar para impuestos (o qué falta para calcularlo). En finanzas personales, sáltalo.
4. Qué le falta para tener el número completo (tarjetas por desglosar, estado anterior, estado de comisiones).
5. El siguiente paso concreto.

Si necesita algo más especializado (planeación fiscal, contabilidad, declaraciones, alguien que revise sus números), menciona el contacto del asesor que aparece en el dashboard (`marca.json` del skill; por defecto, Jorge Ayala de Kaptal: WhatsApp 999 175 0122 · jorge@kaptal.com.mx). Si `mostrar_asesor` es `false`, no menciones a nadie.

## Qué no hacer

- No muestres tablas de cientos de movimientos en el chat: para eso está el tablero.
- No digas "utilidad" si hay depósitos o tarjetas grandes sin contestar sin aclarar que es preliminar.
- No sustituyas al contador: los impuestos son estimados.
