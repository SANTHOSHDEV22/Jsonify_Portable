# -*- mode: python ; coding: utf-8 -*-
#
# Jsonify - PyInstaller build configuration.
#
#   python scripts/build.py          (recommended - see that file for options)
#   pyinstaller Jsonify.spec         (direct)
#
# Produces dist/Jsonify/ containing:
#   Jsonify.exe       the desktop app (no console window)
#   jsonify-cli.exe   the command-line interface (console)

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

project_root = Path(SPECPATH)
icon_file = project_root / "assets" / "jsonify.ico"
src_dir = project_root / "src"


# ------------------------------------------------------------
# Hidden imports
#
# QtWebEngine powers the graph view; every jsonify submodule is
# listed explicitly so nothing imported lazily is missed.
# ------------------------------------------------------------

hiddenimports = collect_submodules("PySide6.QtWebEngineWidgets")
hiddenimports += collect_submodules("jsonify")


# ------------------------------------------------------------
# Data files
#
#   * PySide6 / Qt resources
#   * jsonify/resources: d3.min.js, jsonify.png, ...
# ------------------------------------------------------------

datas = collect_data_files("PySide6", include_py_files=False)

datas += collect_data_files("jsonify.resources", include_py_files=False)


a = Analysis(
    [str(src_dir / "jsonify" / "__main__.py")],
    pathex=[str(src_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pytest", "mypy", "ruff"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)


# ------------------------------------------------------------
# Executables (one shared analysis, two entry points)
# ------------------------------------------------------------

gui_exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Jsonify",
    icon=str(icon_file),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

cli_exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="jsonify-cli",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)


# ------------------------------------------------------------
# Application distribution folder
# ------------------------------------------------------------

coll = COLLECT(
    gui_exe,
    cli_exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Jsonify",
)
