@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_BACKEND.ps1"
if errorlevel 1 (
  echo.
  echo Loi: can cai Python 3.12+ va chay INSTALL_DEPENDENCIES.bat truoc.
)
pause
