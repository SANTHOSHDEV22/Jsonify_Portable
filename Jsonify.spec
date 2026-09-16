# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


# ============================================================
# Jsonify - PyInstaller Build Configuration
# ============================================================

project_root = Path(SPECPATH)
src_dir = project_root / "src"


# ------------------------------------------------------------
# PySide6 WebEngine
# ------------------------------------------------------------

hiddenimports = collect_submodules("PySide6.QtWebEngineWidgets")

datas = collect_data_files(
    "PySide6",
    include_py_files=False,
)


# ------------------------------------------------------------
# Jsonify static resources
#
# Include:
#   src/jsonify/resources/d3.min.js
#
# Inside the packaged application it will remain available as:
#   jsonify/resources/d3.min.js
# ------------------------------------------------------------

datas += [
    (
        str(src_dir / "jsonify" / "resources" / "d3.min.js"),
        "jsonify/resources",
    ),
]


# ------------------------------------------------------------
# Analysis
# ------------------------------------------------------------

a = Analysis(
    [str(src_dir / "jsonify" / "__main__.py")],
    pathex=[str(src_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)


# ------------------------------------------------------------
# Python module archive
# ------------------------------------------------------------

pyz = PYZ(a.pure)


# ------------------------------------------------------------
# Executable
# ------------------------------------------------------------

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Jsonify",
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


# ------------------------------------------------------------
# Application distribution folder
# ------------------------------------------------------------

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Jsonify",
)