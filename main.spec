# -*- mode: python ; coding: utf-8 -*-


import sys
import platform
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import importlib.util
import os

# Detecta a plataforma
is_windows = platform.system().lower() == "windows"
is_linux = platform.system().lower() == "linux"

hidden_imports = collect_submodules('numpy')
hidden_imports.extend(collect_submodules('pandas'))

datas = collect_data_files('numpy')
datas.extend(collect_data_files('pandas'))

# Adiciona ícones baseado na plataforma
icon_files = [
    ('icon.png', '.'),
]
if is_windows:
    icon_files.append(('icon.ico', '.'))
datas.extend(icon_files)
datas.extend([
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
    'selenium.webdriver.chrome',
    'selenium.webdriver.firefox',
    'webdriver_manager',
    'PIL',
    'urllib3',
    'tkinter',
    'tkinter.messagebox',
    'tkinter.filedialog',
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

if is_windows:
    icon_path = 'icon.ico'
else:
    icon_path = 'icon.png'

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
    console=not is_windows,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path
)
