@echo off
REM Paccioli CFO - instala el skill de CFO en tu Claude Code (Windows), en un paso: doble clic.
REM Lo deja en %USERPROFILE%\.claude\skills\paccioli-cfo. No toca nada mas.
setlocal
set "SKILLS=%USERPROFILE%\.claude\skills"
set "ZIP=https://github.com/pachio2509/paccioli-cfo/releases/latest/download/paccioli-cfo-skill.zip"
set "TMP_DIR=%TEMP%\paccioli-skill-%RANDOM%"
echo Descargando el skill de Paccioli CFO ...
mkdir "%TMP_DIR%"
powershell -NoProfile -Command "Invoke-WebRequest -Uri '%ZIP%' -OutFile '%TMP_DIR%\skill.zip'; Expand-Archive -Path '%TMP_DIR%\skill.zip' -DestinationPath '%TMP_DIR%' -Force" || (echo No pude descargar el skill. Revisa tu internet. & pause & exit /b 1)
if not exist "%SKILLS%" mkdir "%SKILLS%"
if exist "%SKILLS%\paccioli-cfo" rmdir /s /q "%SKILLS%\paccioli-cfo"
move "%TMP_DIR%\paccioli-cfo" "%SKILLS%\paccioli-cfo" >nul
rmdir /s /q "%TMP_DIR%"
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
%PY% --version >nul 2>nul || (echo Necesitas Python 3.9 o mas nuevo: https://www.python.org/downloads/ ^(marca "Add Python to PATH"^) & pause & exit /b 1)
echo Preparando Python (pdfplumber, openpyxl) ...
%PY% -m venv "%SKILLS%\paccioli-cfo\.venv"
"%SKILLS%\paccioli-cfo\.venv\Scripts\python" -m pip install --quiet --disable-pip-version-check pdfplumber openpyxl
echo.
echo Listo. Skill Paccioli CFO instalado en %SKILLS%\paccioli-cfo
echo.
echo   Abre Claude Code (si ya estaba abierto, cierralo y abrelo de nuevo), adjunta tu estado de cuenta y escribe:
echo     "Aqui esta mi estado de cuenta, hazme mi dashboard"
pause
