# -*- mode: python ; coding: utf-8 -*-

import os
import pathlib

project_root = pathlib.Path(os.environ.get("RAMENER_PROJECT_ROOT", pathlib.Path.cwd())).resolve()
src_dir = project_root / "src"
main_script = src_dir / "ramener" / "__main__.py"

block_cipher = None


a = Analysis(
    [str(main_script)],
    pathex=[str(src_dir)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ramener',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ramener',
)

app = BUNDLE(
    coll,
    name='Ramener.app',
    icon=str(project_root / "packaging" / "ramener.icns"),
    bundle_identifier='com.ramener.cli',
    argv_emulation=True,
    info_plist={
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "PDF Document",
                "CFBundleTypeRole": "Viewer",
                "CFBundleTypeExtensions": ["pdf", "PDF"],
                "LSItemContentTypes": ["com.adobe.pdf"],
            }
        ],
        "LSApplicationCategoryType": "public.app-category.productivity",
    },
)
