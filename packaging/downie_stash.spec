# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("tkinter")

analysis = Analysis(
    ["src/downie_to_stash/gui_app.py"],
    pathex=["src"],
    binaries=[],
    datas=[("src/downie_to_stash", "downie_to_stash")],
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
    name="DownieToStash.app",
    icon=None,
    bundle_identifier="cc.otter.downie-to-stash-import",
)
