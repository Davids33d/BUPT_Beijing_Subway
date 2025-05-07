# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['flask', 'werkzeug.middleware.proxy_fix', 'networkx', 'geojson', 'python_dotenv']
hiddenimports += collect_submodules('flask')


a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=[],
    datas=[('static', 'static'), ('templates', 'templates'), ('geo_data', 'geo_data'), ('distance_data', 'distance_data'), ('time_data', 'time_data'), ('config.py', '.'), ('.env', '.')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'PyQt5', 'tkinter', 'PIL', 'opencv', 'sphinx', 'alabaster'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='BeijingSubway',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['D:\\pythonProject\\交付版本\\static\\favicon.ico'],
)
