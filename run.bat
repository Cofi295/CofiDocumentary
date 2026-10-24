@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
if not defined COFI_DOCUMENTARY_PORT set COFI_DOCUMENTARY_PORT=8878
if not defined COFI_REMOTION_DIR set COFI_REMOTION_DIR=B:\ALL_TOOLS\CofiRemotion
for /f "delims=" %%L in ('python runtime_logs.py backend') do set "COFI_RUNTIME_LOG=%%L"
if not defined COFI_RUNTIME_LOG exit /b 1
start "" "http://127.0.0.1:%COFI_DOCUMENTARY_PORT%"
start "" /B pythonw app.py 1>>"%COFI_RUNTIME_LOG%" 2>&1
exit /b 0
