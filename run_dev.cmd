@echo off
rem ============================================================
rem  Jsonify - development launcher (Windows)
rem
rem    run_dev.cmd            create venv + install (first run), then start the app
rem    run_dev.cmd file.json  start the app and open a file
rem    run_dev.cmd test       run the test suite (extra pytest args allowed)
rem    run_dev.cmd check      ruff + format check + mypy + tests
rem    run_dev.cmd cli ...    run the command-line interface, e.g. run_dev.cmd cli format a.json
rem ============================================================
setlocal
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment in .\venv ...
    py -3 -m venv venv 2>nul
    if not exist "venv\Scripts\python.exe" python -m venv venv
    if not exist "venv\Scripts\python.exe" (
        echo.
        echo Could not create a virtual environment.
        echo Install Python 3.11 or newer from https://www.python.org/downloads/ and try again.
        exit /b 1
    )
)

set "PY=venv\Scripts\python.exe"

"%PY%" -m pip install --quiet --upgrade pip
"%PY%" -m pip install --quiet -e ".[dev]"
if errorlevel 1 (
    echo.
    echo Dependency installation failed. See the messages above.
    exit /b 1
)

if /i "%~1"=="test" goto :test
if /i "%~1"=="check" goto :check
if /i "%~1"=="cli" goto :cli

"%PY%" -m jsonify %*
exit /b %errorlevel%

:test
shift
"%PY%" -m pytest %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:check
"%PY%" -m ruff check . || exit /b 1
"%PY%" -m ruff format --check . || exit /b 1
"%PY%" -m mypy || exit /b 1
"%PY%" -m pytest -q
exit /b %errorlevel%

:cli
shift
"%PY%" -m jsonify %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%
