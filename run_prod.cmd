@echo off
rem ============================================================
rem  Jsonify - production launcher (Windows)
rem
rem  Starts the packaged application from dist\Jsonify\ (the same
rem  build that ships to users). If no build exists yet it is
rem  created first with build_prod.cmd.
rem
rem    run_prod.cmd             start the packaged app
rem    run_prod.cmd file.json   start it and open a file
rem ============================================================
setlocal
cd /d "%~dp0"

set "EXE=dist\Jsonify\Jsonify.exe"

if not exist "%EXE%" (
    echo No production build found - building one first...
    call "%~dp0build_prod.cmd"
    if errorlevel 1 exit /b 1
)

start "" "%EXE%" %*
