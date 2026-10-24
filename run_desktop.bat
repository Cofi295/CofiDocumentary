@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
if not defined COFI_DOCUMENTARY_PORT set COFI_DOCUMENTARY_PORT=8878
for /f "delims=" %%L in ('python runtime_logs.py desktop') do set "COFI_RUNTIME_LOG=%%L"
if not defined COFI_RUNTIME_LOG exit /b 1
start "" /B pythonw desktop_app.py 1>>"%COFI_RUNTIME_LOG%" 2>&1
