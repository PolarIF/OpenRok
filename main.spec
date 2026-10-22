# -*- mode: python ; coding: utf-8 -*-
# One folder (OpenRok/OpenRok.exe + _internal/), shipped as a ZIP: starts
# faster than a single self-extracting .exe and antivirus flags it less.
import sys

from importlib.util import find_spec

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules

if sys.platform == 'win32':
    # keyring finds its backend through entry points, invisible to the import analysis
    escondidos = ['keyring.backends.Windows']
    # The desktop portal capture only exists on Linux
    fora = ['pytest', 'Xlib', 'PySide6.QtMultimedia']
else:
    escondidos = ['Xlib', 'Xlib.display', 'Xlib.X', 'keyring.backends.SecretService']
    fora = ['pytest']

# Imported from inside the compiled tesserocr module (Linux wheels), where the analysis can't see it
if find_spec('cysignals'):
    escondidos += collect_submodules('cysignals', filter=lambda nome: '.tests' not in nome)

a = Analysis(
    ['main.py'],
    pathex=[],
    # tesseract54.dll, leptonica and the image libraries live inside the tesserocr package
    binaries=collect_dynamic_libs('tesserocr'),
    datas=[('data', 'data'), ('openrok/tessdata', 'openrok/tessdata'), ('openrok/ui/logo.svg', 'openrok/ui')],
    hiddenimports=escondidos,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=fora,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='OpenRok',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='OpenRok',
)
