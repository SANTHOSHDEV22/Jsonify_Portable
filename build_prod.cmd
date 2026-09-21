@echo off
rem ============================================================
rem  Jsonify - production build (Windows)
rem
rem    build_prod.cmd                 build dist\Jsonify\ (PyInstaller, one-folder)
rem    build_prod.cmd --clean         wipe previous build files first
rem    build_prod.cmd --portable      also create dist\Jsonify-<ver>-portable.zip
rem    build_prod.cmd --installer     also compile the Inno Setup installer
rem
rem  Options can be combined. See scripts\build.py.
rem ============================================================
setlocal
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment in .\venv ...
    py -3 -m venv venv 2>nul
    if not exist "venv\Scripts\python.exe" python -m venv venv
    if not exist "venv\Scripts\python.exe" (
        echo Could not create a virtual environment. Install Python 3.11+ first.
        exit /b 1
    )
)

set "PY=venv\Scripts\python.exe"

"%PY%" -m pip install --quiet --upgrade pip
"%PY%" -m pip install --quiet -e ".[build]"
if errorlevel 1 (
    echo Dependency installation failed.
    exit /b 1
)

"%PY%" scripts\build.py %*
exit /b %errorlevel%
