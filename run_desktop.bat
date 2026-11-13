@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
if not defined COFI_DOCUMENTARY_PORT set COFI_DOCUMENTARY_PORT=8878

set "PY_EXE=C:\Users\koing\AppData\Local\Python\pythoncore-3.14-64\python.exe"
set "PYW_EXE=C:\Users\koing\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe"
if not exist "%PY_EXE%" set "PY_EXE=python"
if not exist "%PYW_EXE%" set "PYW_EXE=pythonw"

for /f "delims=" %%L in ('"%PY_EXE%" runtime_logs.py desktop') do set "COFI_RUNTIME_LOG=%%L"
start "" "%PYW_EXE%" desktop_app.py
exit /b 0
