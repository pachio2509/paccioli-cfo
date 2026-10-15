@echo off
REM Paccioli CFO - abre tu tablero en el navegador
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe call instalar.bat
chcp 65001 >nul
.venv\Scripts\python -m paccioli_cfo %*
pause
