# Contribuir a Paccioli CFO

¡Gracias! Lo más valioso que puedes aportar:

1. **Lectores de más bancos** (`paccioli_cfo/lectores/`). Un lector recibe la ruta del archivo y regresa `(movimientos, resumen)`. Si el banco trae totales, ponlos en el resumen (`n_cargos`, `cargos`, `n_abonos`, `abonos`, `saldo_inicial`, `saldo_final`) para validar al centavo.
2. **Reglas automáticas** (`paccioli_cfo/categorias.py`): proveedores, terminales y servicios comunes en México.
3. **Alertas** (`paccioli_cfo/alertas.py`): cosas que un buen CFO te diría.

## Reglas de oro
- **Nunca subas un estado de cuenta real**, ni en issues, ni en pruebas, ni en capturas. Usa datos inventados (mira `demo/generar_demo.py`).
- Sin dependencias pesadas: Python estándar + `pdfplumber` + `openpyxl`.
- Corre `python -m pytest` antes de abrir tu PR.
- Textos para el usuario en español claro, sin jerga contable.
