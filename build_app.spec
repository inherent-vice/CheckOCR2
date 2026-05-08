# -*- mode: python ; coding: utf-8 -*-
"""
Check Capture OCR V6.1 - PyInstaller 빌드 설정
OneDIR Windowed 배포용 완전한 의존성 포함
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
from PyInstaller.building.api import PYZ, EXE, COLLECT
from PyInstaller.building.build_main import Analysis
from checkocr2.build_metadata import write_build_metadata

# 현재 디렉토리
block_cipher = None
app_name = "CheckCaptureOCR_V6.1"
main_script = "check_capture_ocr.py"
build_metadata_path = os.path.join("build", "generated", "build_metadata.json")
write_build_metadata(build_metadata_path)

# EasyOCR 모델 및 데이터 파일 수집
easyocr_datas = collect_data_files('easyocr')

# 추가 데이터 파일들
added_files = [
    ('eye_ocr_02_scanline.ico', '.'),  # 메인 아이콘 파일
    ('eye_ocr_02_scanline.png', '.'),  # PNG 아이콘 (작업표시줄용)
    ('app_icon.ico', '.'),  # 백업 아이콘 파일 (있는 경우)
    ('app_icon.png', '.'),  # 백업 PNG 아이콘 (있는 경우)
    (build_metadata_path, 'checkocr2'),
]

# 실제로 존재하는 파일만 포함
added_files = [(src, dst) for src, dst in added_files if os.path.exists(src)]

# tkinter 관련 바이너리 파일들 (Windows 전용)
tkinter_binaries = []
if sys.platform.startswith('win'):
    import tkinter
    tkinter_dir = os.path.dirname(tkinter.__file__)
    # tkinter DLL 파일들을 명시적으로 포함
    tkinter_binaries = [
        (os.path.join(tkinter_dir, '..', '..', 'DLLs', 'tcl86t.dll'), '.'),
        (os.path.join(tkinter_dir, '..', '..', 'DLLs', 'tk86t.dll'), '.'),
        (os.path.join(tkinter_dir, '..', '..', 'DLLs', '_tkinter.pyd'), '.'),
    ]
    # 존재하는 파일만 추가
    tkinter_binaries = [(src, dst) for src, dst in tkinter_binaries if os.path.exists(src)]

# 숨겨진 imports - 의존성 누락 방지
hidden_imports = [
    # tkinter 관련 모든 모듈 명시적 포함
    'tkinter',
    'tkinter.ttk',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'tkinter.simpledialog',
    'tkinter.scrolledtext',
    'tkinter.font',
    'tkinter.constants',
    'tkinter.commondialog',
    'tkinter.dialog',
    '_tkinter',  # C 확장 모듈
    
    # 데이터 처리
    'pandas',
    'numpy',
    'openpyxl',
    'openpyxl.workbook',
    'openpyxl.worksheet',
    'openpyxl.utils',
    
    # 이미지 처리
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'PIL.ImageDraw',
    'PIL.ImageFilter',
    'PIL.ImageOps',
    'cv2',
    
    # OCR
    'easyocr',
    'easyocr.easyocr',
    'easyocr.recognition',
    'easyocr.detection',
    'easyocr.utils',
    
    # 자동화
    'pyautogui',
    'pyperclip',
    
    # 시스템
    'platform',
    'subprocess',
    'threading',
    'queue',
    'logging',
    'json',
    'datetime',
    're',
    'os',
    'time',
    'typing',
    
    # 디버깅 및 시스템 (torch 의존성)
    'pdb',
    'cmd',
    'bdb',
    'code',
    'linecache',
    'traceback',
    'inspect',
    
    # PyTorch (EasyOCR 의존성)
    'torch',
    'torchvision',
    'torch.nn',
    'torch.nn.functional',
    'torch.utils',
    'torch.utils.data',
    
    # 기타 EasyOCR 의존성
    'scipy',
    'scipy.ndimage',
    'skimage',
    'sklearn',
    'matplotlib',
    'yaml',
    'requests',
    'urllib3',
    'certifi',
]

# EasyOCR 하위 모듈들 자동 수집
easyocr_modules = collect_submodules('easyocr')
hidden_imports.extend(easyocr_modules)

# PyTorch 하위 모듈들 수집
torch_modules = collect_submodules('torch')
hidden_imports.extend(torch_modules)

# tkinter 하위 모듈들 수집
tkinter_modules = collect_submodules('tkinter')
hidden_imports.extend(tkinter_modules)

# 분석 단계
a = Analysis(
    [main_script],
    pathex=[],
    binaries=tkinter_binaries,  # tkinter 바이너리 추가
    datas=added_files + easyocr_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 표준 라이브러리는 제외하지 않음 (torch 등에서 사용)
        # 'test', 'unittest', 'doctest', 'difflib' 등은 제외하지 않음
        
        # 개발 도구만 제외
        'IPython',
        'jupyter',
        'notebook',
        'spyder',
        
        # 불필요한 GUI 라이브러리만 제외
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'wx',
        
        # 개발/테스트 프레임워크만 제외
        'pytest',
        'nose',
        'coverage',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# PYZ 아카이브
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# EXE 실행 파일
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # UPX 압축 활성화
    console=False,  # Windowed 모드 (콘솔 창 숨김)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='eye_ocr_02_scanline.ico',  # 아이콘 설정
)

# OneDIR 배포용 COLLECT
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=app_name,
)

print(f"""
🚀 PyInstaller 빌드 설정 완료!

📋 빌드 정보:
- 애플리케이션: {app_name}
- 메인 스크립트: {main_script}
- 배포 형태: OneDIR Windowed
- 아이콘: eye_ocr_02_scanline.ico
- UPX 압축: 활성화
- 콘솔: 숨김 (GUI 전용)

📦 포함된 의존성:
- EasyOCR + 모든 하위 모듈
- PyTorch + Torchvision
- Pandas + NumPy + OpenPyXL
- PIL/Pillow + OpenCV
- PyAutoGUI + PyPerclip
- Tkinter + TTK

🔧 빌드 명령어:
pyinstaller build_app.spec

📂 출력 디렉토리:
./dist/{app_name}/
""") 
