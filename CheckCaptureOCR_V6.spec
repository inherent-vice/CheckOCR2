# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['check_capture_ocr.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('eye_ocr_02_scanline.ico', '.'),
        ('eye_ocr_02_scanline.png', '.'),
        ('app_icon.ico', '.'),
        ('requirements.txt', '.'),
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.simpledialog',
        'pdb',
        'difflib',
        'bdb',
        'cmd',
        'code',
        'codeop',
        'pprint',
        'reprlib',
        'traceback',
        'linecache',
        'PIL._tkinter_finder',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CheckCaptureOCR_V6.1',
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
    icon='eye_ocr_02_scanline.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CheckCaptureOCR_V6.1',
)
