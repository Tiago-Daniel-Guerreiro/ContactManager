# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hidden_imports = collect_submodules('numpy')
hidden_imports.extend(collect_submodules('pandas'))

datas = collect_data_files('numpy')
datas.extend(collect_data_files('pandas'))

datas.extend([
    ('icon_light.png', '.'),
    ('icon_light.ico', '.'),
    ('icon_dark.png', '.'),
    ('icon_dark.ico', '.'),
    ('utils', 'utils'),
    ('config', 'config'),
    ('models', 'models'),
    ('controllers', 'controllers'),
    ('views', 'views'),
])

hidden_imports.extend([
    'customtkinter',
    'openpyxl',
    'psutil',
    'requests',
    'selenium',
    'selenium.webdriver',
    'selenium.webdriver.edge',
    'webdriver_manager',
    'PIL',
    'urllib3',
])

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy.testing', 'pytest', 'scipy'],
    noarchive=False,
    optimize=0
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ContactManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon_light.ico'
)
