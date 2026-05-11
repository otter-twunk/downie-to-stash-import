# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT_DIR = Path(SPECPATH).parent
SRC_DIR = ROOT_DIR / "src"

datas = collect_data_files("downie_to_stash")
hiddenimports = collect_submodules("tkinter") + collect_submodules("downie_to_stash")

analysis = Analysis(
    [str(SRC_DIR / "downie_to_stash" / "gui_app.py")],
    pathex=[str(SRC_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="DownieToStash",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DownieToStash",
)
app = BUNDLE(
    coll,
    name="Downie to Stash Import Helper.app",
    icon=None,
    bundle_identifier="cc.otter.downie-to-stash-import",
)
