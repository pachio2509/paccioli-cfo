@echo off
REM Paccioli CFO - instalacion en Windows
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
%PY% --version >nul 2>nul || (echo Necesitas Python 3.9 o mas nuevo: https://www.python.org/downloads/ & pause & exit /b 1)
echo Creando entorno en .venv ...
%PY% -m venv .venv
.venv\Scripts\python -m pip install --quiet --upgrade pip
.venv\Scripts\python -m pip install --quiet -r requirements.txt
echo.
echo Listo. Para abrir tu tablero: doble clic en iniciar.bat
pause
