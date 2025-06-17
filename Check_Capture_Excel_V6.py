import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import pandas as pd
import pyperclip
import pyautogui
import time
import os
from PIL import Image, ImageTk
import numpy as np
import easyocr # PaddleOCR 대신 EasyOCR 사용
import json
import logging
from datetime import datetime
import threading
import queue
import re

############################################
# 로깅 설정
############################################
def setup_logging():
    # 로깅 기본 설정: 레벨, 포맷, 핸들러(파일, 스트림)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('ocr_app.log', encoding='utf-8'), # 로그 파일 핸들러
            logging.StreamHandler() # 콘솔 출력 핸들러
        ]
    )
    return logging.getLogger(__name__) # 로거 객체 반환

############################################
# 통합 설정 관리 시스템
############################################
class UnifiedSettingsManager:
    def __init__(self):
        self.settings_file = "settings.json" # 설정 파일명
        self.data = self.load_settings() # 설정 로드

        # 기본 구조 초기화 (파일에 해당 키가 없을 경우)
        if 'presets' not in self.data:
            self.data['presets'] = {}
        if 'current' not in self.data:
            self.data['current'] = {}
        if 'advanced' not in self.data:
            self.data['advanced'] = self._get_default_advanced_settings()

    def load_settings(self):
        """통합 설정 파일 로드"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f) # JSON 파일 로드
        except Exception as e:
            print(f"설정 로드 오류: {e}") # 오류 발생 시 메시지 출력
        return {} # 오류 또는 파일 부재 시 빈 딕셔너리 반환

    def save_settings(self):
        """통합 설정 파일 저장"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False) # JSON 파일 저장 (들여쓰기, UTF-8)
        except Exception as e:
            print(f"설정 저장 오류: {e}") # 오류 발생 시 메시지 출력

    # 프리셋 관련 메서드
    def save_preset(self, name, settings):
        """프리셋 저장"""
        self.data['presets'][name] = {
            'click_point': settings['click_point'],
            'all_area': settings['all_area'],
            'date_area': settings['date_area'],
            'rate_area': settings['rate_area'],
            'delays': settings['delays'],
            'advanced': settings.get('advanced', {}), # 고급 설정도 프리셋에 포함
            'created_at': datetime.now().isoformat() # 생성 시간 기록
        }
        self.save_settings() # 변경사항 저장

    def get_preset_names(self):
        """프리셋 이름 목록 반환"""
        return list(self.data['presets'].keys())

    def apply_preset(self, name):
        """프리셋 적용 (설정 데이터 반환)"""
        return self.data['presets'].get(name, None)

    def delete_preset(self, name):
        """프리셋 삭제"""
        if name in self.data['presets']:
            del self.data['presets'][name]
            self.save_settings() # 변경사항 저장

    # 현재 설정 관련 메서드
    def save_current_settings(self, settings):
        """현재 설정 저장"""
        self.data['current'] = settings
        self.save_settings() # 변경사항 저장

    def get_current_settings(self):
        """현재 설정 반환"""
        return self.data.get('current', {})

    def _get_default_advanced_settings(self):
        """기본 고급 설정 반환 (전처리 기능 제거, 영어 OCR 고정)"""
        return {
            # OCR 설정
            'ocr_gpu_enabled': False,
            'ocr_confidence_threshold': 0.2,
            'ocr_languages': ['en'], # 영어로 고정 (한국어 제거)
            'ocr_max_attempts': 1, # 원본만 사용으로 1회로 단순화
            'ocr_detail_level': 0, # EasyOCR detail 파라미터 (0: 텍스트만, 1: 상세 정보)

            # 자동화 설정
            'click_interval': 0.1,
            'thread_count': self._get_optimal_thread_count(),

            # 신뢰도 설정 (사용하지 않지만 호환성 유지)
            'min_date_confidence': 0.0,
            'min_rate_confidence': 0.0,
        }

    def _get_optimal_thread_count(self):
        """현재 PC에 최적화된 스레드 개수 계산 (참고용, 현재 코드에서 직접 사용되진 않음)"""
        cpu_count = os.cpu_count() or 4 # CPU 코어 개수 (없으면 기본 4)
        optimal_threads = min(max(cpu_count, 2), 8) # 최소 2개, 최대 8개
        return optimal_threads

    # 고급 설정 접근 메서드들
    def get_advanced(self, key, default=None):
        """고급 설정 값 반환"""
        return self.data['advanced'].get(key, default)

    def set_advanced(self, key, value):
        """고급 설정 값 설정"""
        self.data['advanced'][key] = value
        self.save_settings() # 변경사항 저장

    def reset_advanced_settings(self):
        """고급 설정 초기화"""
        self.data['advanced'] = self._get_default_advanced_settings()
        self.save_settings() # 변경사항 저장

############################################
# 진행 상황 추적기
############################################
class ProgressTracker:
    def __init__(self, parent):
        self.parent = parent
        self.progress_var = tk.DoubleVar() # 진행률 변수
        self.status_var = tk.StringVar() # 상태 메시지 변수
        self.current_item_var = tk.StringVar() # 현재 처리 항목 변수
        self.setup_ui()

    def setup_ui(self):
        """진행 상황 표시 UI 구성"""
        self.progress_frame = tk.Frame(self.parent) # 메인 프레임

        self.current_label = tk.Label(
            self.progress_frame,
            textvariable=self.current_item_var,
            font=('Arial', 9, 'bold'),
            fg='blue'
        )
        self.current_label.pack(pady=(0, 3))

        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            variable=self.progress_var,
            maximum=100
        )
        self.progress_bar.pack(fill='x', pady=(0, 5))

        self.status_label = tk.Label(
            self.progress_frame,
            textvariable=self.status_var,
            font=('Arial', 9)
        )
        self.status_label.pack()

        self.progress_frame.pack_forget() # 처음에는 숨김

    def show(self):
        """진행 상황 UI 표시"""
        try:
            if self.progress_frame.winfo_exists():
                self.progress_frame.pack(fill='x', padx=5, pady=5)
        except tk.TclError:
            pass # 창이 이미 파괴된 경우 무시

    def hide(self):
        """진행 상황 UI 숨김"""
        try:
            if self.progress_frame.winfo_exists():
                self.progress_frame.pack_forget()
        except tk.TclError:
            pass # 창이 이미 파괴된 경우 무시

    def update_progress(self, current, total, status_text, current_item=""):
        """진행 상황 업데이트"""
        if total > 0:
            progress = (current / total) * 100
            self.progress_var.set(progress)
            self.status_var.set(f"{status_text} ({current}/{total}) - {progress:.1f}%")
            self.current_item_var.set(current_item)

############################################
# 작업 제어 시스템
############################################
class WorkController:
    def __init__(self):
        self.is_stopped = False # 작업 중단 플래그
        self.is_running = False # 작업 실행 중 플래그
        self.skip_current = False # 현재 항목 건너뛰기 플래그
        self.current_item = "" # 현재 처리 중인 항목명

    def start_work(self):
        """작업 시작 시 상태 설정"""
        self.is_stopped = False
        self.is_running = True
        self.skip_current = False

    def stop_work(self):
        """작업 중단 시 상태 설정"""
        self.is_stopped = True
        self.is_running = False
        return "작업이 중단되었습니다"

    def skip_current_item(self):
        """현재 항목 건너뛰기 시 상태 설정"""
        self.skip_current = True
        return f"현재 항목 '{self.current_item}'을 건너뛰었습니다"

    def reset(self):
        """컨트롤러 상태 초기화"""
        self.is_stopped = False
        self.is_running = False
        self.skip_current = False
        self.current_item = ""

############################################
# 영역 시각화 오버레이 창
############################################
class AreaVisualizationOverlay(tk.Toplevel):
    def __init__(self, master, areas_info, auto_close=True):
        super().__init__(master)
        self.master = master
        self.areas_info = areas_info # 시각화할 영역 정보
        self.auto_close = auto_close # 자동 종료 여부

        self.attributes("-fullscreen", True) # 전체 화면
        self.attributes("-topmost", True) # 항상 위에 표시
        self.configure(bg="black")
        self.attributes("-alpha", 0.7) # 반투명도 설정

        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.draw_areas() # 영역 그리기

        if auto_close:
            self.after(3000, self.destroy) # 3초 후 자동 종료

        self.bind("<KeyPress>", self.on_key_press) # ESC 키로 종료 바인딩
        self.focus_set()

    def draw_areas(self):
        """설정된 영역들을 캔버스에 그리기"""
        colors = ["red", "blue", "green", "yellow", "orange"] # 영역별 색상
        labels = ["클릭 포인트", "전체 영역", "날짜 영역", "금리 영역"] # 영역별 레이블

        # 클릭 포인트 그리기
        if "click_point" in self.areas_info:
            x, y = self.areas_info["click_point"]
            r = 10 # 원의 반지름
            self.canvas.create_oval(x-r, y-r, x+r, y+r,
                                    fill=colors[0], outline="white", width=3)
            self.canvas.create_text(x, y-25, text=labels[0],
                                    fill="white", font=("Arial", 12, "bold"))

        # 사각형 영역들 그리기
        area_keys = ["all_area", "date_area", "rate_area"]
        for i, key in enumerate(area_keys):
            if key in self.areas_info and self.areas_info[key]: # 영역 정보 유효성 체크
                x1, y1, x2, y2 = self.areas_info[key]
                color = colors[i+1]
                self.canvas.create_rectangle(x1, y1, x2, y2,
                                             outline=color, width=4, fill="")
                center_x = (x1 + x2) // 2
                center_y = y1 - 20 if y1 > 30 else y2 + 20
                self.canvas.create_text(center_x, center_y, text=labels[i+1],
                                        fill=color, font=("Arial", 14, "bold"))
                width = x2 - x1
                height = y2 - y1
                size_text = f"{width}x{height}"
                self.canvas.create_text(center_x, center_y + 20, text=size_text,
                                        fill="white", font=("Arial", 10))

        # 안내 메시지
        screen_width = self.winfo_screenwidth()
        info_text = "설정된 영역들이 표시됩니다"
        if self.auto_close:
            info_text += " (3초 후 자동 종료)"
        info_text += " | ESC: 종료"
        self.canvas.create_text(screen_width//2, 50, text=info_text,
                                fill="white", font=("Arial", 16, "bold"))

    def on_key_press(self, event):
        """키 입력 처리 (ESC로 창 닫기)"""
        if event.keysym == "Escape":
            self.destroy()

############################################
# 드래그로 좌표를 지정하는 Overlay Window
############################################
class DragCaptureOverlay(tk.Toplevel):
    def __init__(self, master=None, color="red"):
        super().__init__(master)
        self.master = master
        self.color = color # 드래그 영역 테두리 색상

        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.configure(bg="black")
        self.attributes("-alpha", 0.3) # 반투명도

        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.start_x = None
        self.start_y = None
        self.rect_id = None # 드래그 중인 사각형 ID
        self.x1, self.y1, self.x2, self.y2 = None, None, None, None # 최종 좌표

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

    def on_button_press(self, event):
        """마우스 버튼 누를 때 (드래그 시작)"""
        self.start_x = event.x
        self.start_y = event.y
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline=self.color, width=2
        )

    def on_move_press(self, event):
        """마우스 드래그 중"""
        curX, curY = (event.x, event.y)
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, curX, curY)

    def on_button_release(self, event):
        """마우스 버튼 놓을 때 (드래그 종료)"""
        end_x, end_y = (event.x, event.y)
        # 좌상단, 우하단 좌표로 정규화
        self.x1 = min(self.start_x, end_x)
        self.y1 = min(self.start_y, end_y)
        self.x2 = max(self.start_x, end_x)
        self.y2 = max(self.start_y, end_y)
        self.destroy() # 오버레이 창 닫기

############################################
# 포인터 한 번 클릭으로 좌표를 지정하는 Overlay
############################################
class PointCaptureOverlay(tk.Toplevel):
    def __init__(self, master=None, color="red"):
        super().__init__(master)
        self.master = master
        self.color = color # 클릭 지점 표시 색상

        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.configure(bg="black")
        self.attributes("-alpha", 0.3)

        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.click_x = None
        self.click_y = None # 최종 클릭 좌표

        self.canvas.bind("<ButtonPress-1>", self.on_click)

    def on_click(self, event):
        """마우스 클릭 시"""
        self.click_x = event.x
        self.click_y = event.y
        r = 5 # 표시할 원의 반지름
        self.canvas.create_oval(
            self.click_x - r, self.click_y - r,
            self.click_x + r, self.click_y + r,
            fill=self.color, outline=self.color
        )
        self.destroy() # 오버레이 창 닫기

############################################
# 메인 GUI + OCR 로직이 결합된 코드
############################################
class CheckCaptureOCRApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("📊 Check Capture OCR V6") # 버전명 변경
        self.geometry("1150x600") # 창 크기 조정 (내용에 맞게 초기 높이 조정)
        self.resizable(True, True)
        self.minsize(950, 600) # 최소 높이 조정

        self.center_window() # 창 중앙 배치

        # 테마 시스템 초기화
        self.available_themes = {
            'modern_blue': {'name': '🔵 모던 블루', 'primary': '#1976D2', 'secondary': '#42A5F5', 'success': '#4CAF50', 'warning': '#FF9800', 'danger': '#F44336', 'light': '#F5F5F5', 'dark': '#212121', 'white': '#FFFFFF', 'accent': '#9C27B0', 'surface': '#FFFFFF', 'on_surface': '#212121', 'outline': '#79747E'},
            'dark_pro': {'name': '🌙 다크 프로', 'primary': '#BB86FC', 'secondary': '#03DAC6', 'success': '#4CAF50', 'warning': '#FFC107', 'danger': '#CF6679', 'light': '#121212', 'dark': '#000000', 'white': '#FFFFFF', 'accent': '#03DAC6', 'surface': '#1E1E1E', 'on_surface': '#E1E1E1', 'outline': '#938F99'},
            'elegant_purple': {'name': '💜 엘레간트 퍼플', 'primary': '#6750A4', 'secondary': '#958DA5', 'success': '#4CAF50', 'warning': '#F57C00', 'danger': '#BA1A1A', 'light': '#FEF7FF', 'dark': '#21005D', 'white': '#FFFFFF', 'accent': '#D0BCFF', 'surface': '#FFFBFE', 'on_surface': '#1D1B20', 'outline': '#79747E'},
            'green_nature': {'name': '🌿 그린 네이처', 'primary': '#006E26', 'secondary': '#52634F', 'success': '#4CAF50', 'warning': '#F57C00', 'danger': '#BA1A1A', 'light': '#F6FFF6', 'dark': '#00210A', 'white': '#FFFFFF', 'accent': '#006E26', 'surface': '#FEFFFE', 'on_surface': '#1A1C18', 'outline': '#72796F'},
            'orange_warm': {'name': '🧡 오렌지 웜', 'primary': '#8F4E00', 'secondary': '#77574B', 'success': '#4CAF50', 'warning': '#FF8F00', 'danger': '#BA1A1A', 'light': '#FFFBF8', 'dark': '#2F1500', 'white': '#FFFFFF', 'accent': '#FFB59D', 'surface': '#FFFBF8', 'on_surface': '#201A16', 'outline': '#837568'}
        }

        self.settings_manager = UnifiedSettingsManager() # 설정 관리자 초기화
        saved_theme = self.settings_manager.get_advanced('ui_theme', 'modern_blue')
        self.current_theme = saved_theme if saved_theme in self.available_themes else 'modern_blue'
        self.colors = self.available_themes[self.current_theme].copy()
        self.configure(bg=self.colors['surface'])

        self.logger = setup_logging() # 로거 설정
        self.progress_tracker = ProgressTracker(self) # 진행 추적기 초기화
        self.work_controller = WorkController() # 작업 컨트롤러 초기화

        self.message_queue = queue.Queue() # 스레드 통신 큐
        self.worker_thread = None # 워커 스레드 참조

        # ===== 기본값 설정 (tk.Variable) =====
        self.input_excel_path = tk.StringVar()
        self.output_folder_path = tk.StringVar()
        self.click_x = tk.IntVar(value=340); self.click_y = tk.IntVar(value=165)
        self.allarea_x1 = tk.IntVar(value=15); self.allarea_y1 = tk.IntVar(value=200)
        self.allarea_x2 = tk.IntVar(value=1845); self.allarea_y2 = tk.IntVar(value=870)
        self.datearea_x1 = tk.IntVar(value=826); self.datearea_y1 = tk.IntVar(value=88)
        self.datearea_x2 = tk.IntVar(value=1064); self.datearea_y2 = tk.IntVar(value=127)
        self.ratearea_x1 = tk.IntVar(value=1069); self.ratearea_y1 = tk.IntVar(value=89)
        self.ratearea_x2 = tk.IntVar(value=1326); self.ratearea_y2 = tk.IntVar(value=126)
        self.paste_delay = tk.DoubleVar(value=0.5)
        self.loading_delay = tk.DoubleVar(value=2.5)
        self.save_detail_images = tk.BooleanVar(value=True) # 상세 이미지 저장 옵션

        # Excel 그리드 관련 변수
        self.excel_data = []
        self.current_processing_index = -1
        self.grid_tree = None

        # 고급 설정 UI 연동 변수 (기존 변수명 유지, 값은 settings_manager에서 관리)
        self.lang_var = tk.StringVar(value='ko') # OCR 언어
        self.confidence_threshold = tk.DoubleVar(value=75.0) # OCR 신뢰도 (UI 표시용)
        self.use_gpu = tk.BooleanVar(value=False) # GPU 사용 여부 (UI 표시용)
        self.max_threads = tk.IntVar(value=4) # 최대 스레드 (UI 표시용, 실제 스레드는 1개)

        # 이미지 전처리 UI 연동 변수 (전처리 기능 제거로 삭제)
        # self.apply_sharpening = tk.BooleanVar(value=False)
        # self.apply_contrast = tk.BooleanVar(value=False)
        # self.apply_denoising = tk.BooleanVar(value=False)
        # self.apply_binarization = tk.BooleanVar(value=False)
        # 아래 변수들은 현재 UI에는 없지만, 고급 설정에 포함될 수 있음
        self.image_scale_factor = tk.DoubleVar(value=1.0)
        self.image_quality = tk.IntVar(value=95)

        # 테마 및 기타 UI 변수
        self.theme_var = tk.StringVar()
        self.log_level_var = tk.StringVar(value="INFO")

        self.ocr_reader = None # EasyOCR 리더 객체
        self.initialize_ocr() # OCR 초기화

        self._build_ui() # GUI 빌드
        self._setup_keyboard_shortcuts() # 단축키 설정

        self.check_queue() # 메시지 큐 확인 시작
        self.load_last_settings() # 마지막 설정 로드

    def center_window(self):
        """창을 화면 중앙에 배치"""
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = 1200 # 기본 창 너비
        window_height = 350 # 기본 창 높이 (조정)
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")

    def initialize_ocr(self):
        """EasyOCR 초기화 - 영어로 고정"""
        try:
            self.logger.info("EasyOCR 초기화 중... (영어 전용)")
            gpu_enabled = self.settings_manager.get_advanced('ocr_gpu_enabled', False)
            # 언어를 영어로 고정
            languages = ['en']
            self.ocr_reader = easyocr.Reader(languages, gpu=gpu_enabled)
            self.logger.info(f"EasyOCR 초기화 완료 - 언어: {languages}, GPU: {gpu_enabled}")
        except Exception as e:
            self.logger.error(f"EasyOCR 초기화 실패: {e}")
            try: # 폴백: 영어, GPU 비활성화로 재시도
                self.logger.info("기본 모드(영어, CPU)로 EasyOCR 재초기화 시도...")
                self.ocr_reader = easyocr.Reader(['en'], gpu=False)
                self.settings_manager.set_advanced('ocr_gpu_enabled', False) # 설정도 업데이트
                self.settings_manager.set_advanced('ocr_languages', ['en'])
                self.logger.info("EasyOCR 영어 모드(CPU)로 초기화 완료.")
            except Exception as e2:
                messagebox.showerror("치명적 오류", f"OCR 엔진 초기화에 완전히 실패했습니다: {e2}")
                self.logger.critical(f"OCR 엔진 초기화 완전 실패: {e2}")
                # 여기서 앱을 종료하거나, OCR 기능을 비활성화하는 등의 처리가 필요할 수 있음
                # raise # 필요시 에러를 다시 발생시켜 앱 종료 유도

    def _setup_keyboard_shortcuts(self):
        """키보드 단축키 설정"""
        self.focus_set()
        self.bind_all('<Control-s>', lambda e: self.quick_save_settings())
        self.bind_all('<Control-l>', lambda e: self.load_last_settings())
        self.bind_all('<F5>', lambda e: self.handle_f5_key())
        self.bind_all('<Escape>', lambda e: self.stop_processing())
        self.bind_all('<F1>', lambda e: self.show_shortcuts())

    def handle_f5_key(self):
        """F5 키 처리: 실행 중이면 중단, 아니면 실행"""
        if self.work_controller.is_running:
            self.stop_processing()
        else:
            self.run_ocr_process()

    def check_queue(self):
        """큐에서 메시지 확인하여 GUI 업데이트"""
        try:
            while True: # 큐에 있는 모든 메시지 처리
                msg_type, data = self.message_queue.get_nowait()
                if msg_type == "progress":
                    if len(data) == 4:
                        current, total, status, current_item_text = data
                        self.progress_tracker.update_progress(current, total, status, current_item_text)
                        self.work_controller.current_item = current_item_text
                    elif len(data) == 3: # current_item_text가 없는 경우
                        current, total, status = data
                        self.progress_tracker.update_progress(current, total, status, "")
                elif msg_type == "log":
                    self.update_log_display(data) # 로그 메시지 직접 로깅
                elif msg_type == "error":
                    self.update_log_display(f"오류: {data}", level="ERROR")
                elif msg_type == "status": # 더 이상 직접 사용하지 않고 로그로 통합 가능
                    self.update_log_display(f"상태: {data}")
                elif msg_type == "complete":
                    self._on_work_complete(data)
                elif msg_type == "stopped":
                    self._on_work_stopped()
                elif msg_type == "grid_update":
                    self._handle_grid_update(data)
        except queue.Empty:
            pass # 큐가 비어있으면 아무것도 안 함
        self.after(100, self.check_queue) # 100ms 마다 주기적으로 큐 확인

    def _build_ui(self):
        """메인 UI 빌드 시스템"""
        self._create_menu()
        self._create_simple_toolbar()

        # Grid 레이아웃을 위한 설정
        # row 0: 툴바, row 1: 메인 컨테이너
        self.grid_rowconfigure(0, weight=0) # 툴바는 세로 확장 안 함
        self.grid_rowconfigure(1, weight=1) # 메인 컨테이너가 세로 공간 모두 사용
        # column 0: 메인 컨테이너가 전체 너비 사용 (columnspan=3으로 설정)
        self.grid_columnconfigure(0, weight=1) # 메인 컨테이너가 가로 공간 모두 사용

        main_container = tk.Frame(self, bg=self.colors['surface'])
        # 창 테두리에 붙도록 padx, pady 모두 0으로 명시
        main_container.grid(row=1, column=0, sticky='nsew', padx=0, pady=0) 

        # 메인 컨테이너 내부 grid 설정 (3개의 패널)
        main_container.grid_rowconfigure(0, weight=1)  # 이 행이 세 패널의 높이를 결정하고 세로 확장
        main_container.grid_columnconfigure(0, weight=0)  # 좌측 패널 고정 너비 (조정 안 함)
        main_container.grid_columnconfigure(1, weight=1)  # 중앙 패널 확장
        main_container.grid_columnconfigure(2, weight=1)  # 우측 패널 확장

        left_panel = tk.Frame(main_container, bg=self.colors['surface'], width=280)
        # 좌측 패널은 row 0, column 0, sticky nsew, padx/pady 0
        left_panel.grid(row=0, column=0, sticky='nsew', padx=0, pady=0) 
        left_panel.pack_propagate(False) # 내부 위젯이 부모 크기 강제 안 함

        center_panel = tk.Frame(main_container, bg=self.colors['surface'])
        # 중앙 패널은 row 0, column 1, sticky nsew, padx/pady 0
        center_panel.grid(row=0, column=1, sticky='nsew', padx=0, pady=0)  

        right_panel = tk.Frame(main_container, bg=self.colors['surface'], width=200)
        # 우측 패널은 row 0, column 2, sticky nsew, padx/pady 0
        right_panel.grid(row=0, column=2, sticky='nsew', padx=0, pady=0) 
        right_panel.pack_propagate(False) # 내부 위젯이 부모 크기 강제 안 함

        self._create_stable_left_panel(left_panel)
        self._create_center_excel_grid(center_panel)
        self._create_stable_right_panel(right_panel)

    def _create_menu(self):
        """메뉴바 생성"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # 파일 메뉴
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="파일", menu=file_menu)
        file_menu.add_command(label="Excel 파일 로드 (Ctrl+O)", command=self.load_excel_to_grid, accelerator="Ctrl+O")
        file_menu.add_command(label="Excel 파일 선택", command=self.browse_input_excel)
        file_menu.add_command(label="출력 폴더 선택", command=self.browse_output_folder)
        file_menu.add_separator()
        file_menu.add_command(label="종료 (Alt+F4)", command=self.quit, accelerator="Alt+F4")

        # 설정 메뉴
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="설정", menu=settings_menu)
        settings_menu.add_command(label="현재 설정 저장 (Ctrl+S)", command=self.quick_save_settings, accelerator="Ctrl+S")
        settings_menu.add_command(label="마지막 설정 불러오기 (Ctrl+L)", command=self.load_last_settings, accelerator="Ctrl+L")
        settings_menu.add_separator()
        settings_menu.add_command(label="고급 설정 저장", command=self.save_advanced_ui_to_settings) # 고급 설정 기능은 제거되었지만 메뉴 항목은 유지
        settings_menu.add_command(label="고급 설정 초기화", command=self.reset_advanced_settings_and_ui) # 고급 설정 기능은 제거되었지만 메뉴 항목은 유지

        # 미리보기 메뉴
        preview_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="미리보기", menu=preview_menu)
        preview_menu.add_command(label="전체 영역 미리보기", command=self.show_area_preview)

        # 실행 메뉴
        run_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="실행", menu=run_menu)
        run_menu.add_command(label="OCR 시작/중단 (F5)", command=self.handle_f5_key, accelerator="F5")
        run_menu.add_command(label="처리 중단 (Esc)", command=self.stop_processing, accelerator="Esc")

        # 도움말 메뉴
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="도움말", menu=help_menu)
        help_menu.add_command(label="키보드 단축키 (F1)", command=self.show_shortcuts, accelerator="F1")
        help_menu.add_command(label="프로그램 정보", command=self.show_about)

        # 키보드 단축키 바인딩
        self.bind_all('<Control-o>', lambda e: self.load_excel_to_grid())

    def _create_center_excel_grid(self, parent):
        """중앙 Excel 데이터 그리드 생성"""
        grid_section = self._create_section_frame(parent, "📊 Excel 데이터 그리드")
        control_frame = tk.Frame(grid_section, bg=self.colors['white'])
        control_frame.pack(fill='x', pady=(0, 5))

        left_controls = tk.Frame(control_frame, bg=self.colors['white'])
        left_controls.pack(side='left', fill='x', expand=True, padx=(0, 5))
        tk.Button(left_controls, text="📁 Excel 로드", command=self.load_excel_to_grid, font=('Segoe UI', 9), bg=self.colors['primary'], fg='white', relief='flat', cursor='hand2').pack(side='left', padx=(0, 5))
        tk.Button(left_controls, text="➕ 행 추가", command=self.add_empty_row, font=('Segoe UI', 9), bg=self.colors['success'], fg='white', relief='flat', cursor='hand2').pack(side='left', padx=(0, 5))
        tk.Button(left_controls, text="📋 붙여넣기", command=self.paste_from_clipboard, font=('Segoe UI', 9), bg=self.colors['secondary'], fg='white', relief='flat', cursor='hand2').pack(side='left', padx=(0, 5))

        right_controls = tk.Frame(control_frame, bg=self.colors['white'])
        right_controls.pack(side='right')
        tk.Button(right_controls, text="🗑️ 삭제", command=self.delete_selected_rows, font=('Segoe UI', 9), bg=self.colors['danger'], fg='white', relief='flat', cursor='hand2').pack(side='right', padx=(5, 0))
        tk.Button(right_controls, text="🧹 전체삭제", command=self.clear_all_data, font=('Segoe UI', 9), bg=self.colors['warning'], fg='white', relief='flat', cursor='hand2').pack(side='right', padx=(5, 0))

        tree_frame = tk.Frame(grid_section, bg=self.colors['white'])
        tree_frame.pack(fill='both', expand=True)
        columns = ('종목코드', '종목명', '날짜', '금리', '상태')
        # 그리드 높이 제거: 부모 컨테이너 크기에 맞춰 자동 조정
        self.grid_tree = ttk.Treeview(tree_frame, columns=columns, show='headings') 
        for col_name in columns: self.grid_tree.heading(col_name, text=col_name)
        # 컬럼 너비 조정: 내용이 잘리지 않으면서도 컴팩트하게
        col_widths = {'종목코드': 95, '종목명': 180, '날짜': 120, '금리': 95, '상태': 100}
        for col_name, width in col_widths.items():
            self.grid_tree.column(col_name, width=width, anchor='center', minwidth=width-10, stretch=True)

        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.grid_tree.yview)
        # h_scrollbar 제거 - 좌우 스크롤바 없애기 요청 반영
        # h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.grid_tree.xview)

        self.grid_tree.configure(yscrollcommand=v_scrollbar.set)
        # self.grid_tree.configure(xscrollcommand=h_scrollbar.set) # 수평 스크롤 연동 제거

        self.grid_tree.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        # h_scrollbar.pack(side="bottom", fill="x") # 수평 스크롤바 패킹 제거

        self.grid_tree.bind('<Double-1>', self.on_cell_double_click)
        self.grid_tree.bind('<Button-3>', self.show_context_menu)
        self.grid_tree.bind('<Delete>', lambda e: self.delete_selected_rows())
        self.grid_tree.bind('<Control-c>', lambda e: self.copy_selected_rows())
        self.grid_tree.bind('<Control-v>', lambda e: self.paste_from_clipboard())

        status_frame = tk.Frame(grid_section, bg=self.colors['white'])
        status_frame.pack(fill='x', pady=(5, 0))
        self.grid_status_label = tk.Label(status_frame, text="총 0행 | 처리 완료: 0행 | 대기 중: 0행", font=('Segoe UI', 9), bg=self.colors['white'], fg=self.colors['on_surface'])
        self.grid_status_label.pack(side='left')
        self.grid_progress_label = tk.Label(status_frame, text="진행률: 0%", font=('Segoe UI', 9, 'bold'), bg=self.colors['white'], fg=self.colors['primary'])
        self.grid_progress_label.pack(side='right')

    def _create_simple_toolbar(self):
        """상단 툴바 생성 (실행/중단 버튼 포함)"""
        toolbar = tk.Frame(self, bg=self.colors['primary'], height=35)
        # 툴바는 row 0, column 0, sticky ew, 창 상단에 붙도록 pady 0
        toolbar.grid(row=0, column=0, sticky='ew', padx=0, pady=0) 
        toolbar.pack_propagate(False)
        
        # 제목 레이블
        tk.Label(toolbar, text="📊 Check OCR V6", font=('Segoe UI', 11, 'bold'), bg=self.colors['primary'], fg='white').pack(side='left', padx=8, pady=6)
        
        # 우측 컨트롤 영역
        controls_frame = tk.Frame(toolbar, bg=self.colors['primary'])
        controls_frame.pack(side='right', padx=8, pady=4)
        
        # 실행/중단 버튼
        self.run_btn = tk.Button(controls_frame, text="🚀 OCR 시작 (F5)", command=self.run_ocr_process, 
                                font=('Segoe UI', 9, 'bold'), bg=self.colors['success'], fg='white', 
                                relief='flat', cursor='hand2')
        self.run_btn.pack(side='left', padx=(0, 5))
        
        self.stop_btn = tk.Button(controls_frame, text="⏹️ 중단", command=self.stop_processing, 
                                 font=('Segoe UI', 9, 'bold'), bg=self.colors['danger'], fg='white', 
                                 relief='flat', cursor='hand2')
        self.stop_btn.pack(side='left', padx=(0, 15))
        
        # 테마 선택
        tk.Label(controls_frame, text="테마:", font=('Segoe UI', 9), bg=self.colors['primary'], fg='white').pack(side='left', padx=(0, 3))
        self.theme_combo = ttk.Combobox(controls_frame, textvariable=self.theme_var, width=10, state="readonly", font=('Segoe UI', 8))
        self.theme_combo['values'] = [theme['name'] for theme in self.available_themes.values()]
        self.theme_combo.set(self.available_themes[self.current_theme]['name'])
        self.theme_combo.pack(side='left')
        self.theme_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_theme())

    def _create_stable_left_panel(self, parent):
        """좌측 설정 패널 생성"""
        canvas = tk.Canvas(parent, bg=self.colors['surface'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['surface'])
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        def _on_mousewheel(event): canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel) # 모든 위젯에서 마우스휠 스크롤 가능하도록
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._create_file_section(scrollable_frame)
        self._create_coordinates_section(scrollable_frame)
        self._create_timing_section(scrollable_frame)
        self._create_options_section(scrollable_frame)

    def _create_stable_right_panel(self, parent):
        """우측 패널 생성 (로그만) - 중앙 그리드와 높이 동기화"""
        # 로그 섹션이 부모의 전체 공간을 차지하도록 설정
        log_frame = tk.Frame(parent, bg=self.colors['surface'])
        log_frame.pack(fill='both', expand=True)

        self._create_log_section(log_frame)

    def _create_stable_bottom_bar(self):
        """하단 실행 바 생성 (비활성화됨 - 버튼이 상단으로 이동)"""
        # 이 메서드는 더 이상 사용되지 않음 - 버튼이 상단 툴바로 이동
        pass

    def _create_file_section(self, parent):
        """파일 설정 섹션 UI"""
        section = self._create_section_frame(parent, "📁 파일 설정")
        excel_frame = tk.Frame(section, bg=self.colors['white'])
        excel_frame.pack(fill='x', pady=(0, 3))
        tk.Label(excel_frame, text="Excel 입력 파일:", font=('Segoe UI', 9, 'bold'), bg=self.colors['white']).pack(anchor='w')
        excel_input = tk.Frame(excel_frame, bg=self.colors['white'])
        excel_input.pack(fill='x', pady=(2, 0))
        self.excel_entry = tk.Entry(excel_input, textvariable=self.input_excel_path, font=('Segoe UI', 9), relief='solid', bd=1)
        self.excel_entry.pack(side='left', fill='x', expand=True, padx=(0, 3))
        tk.Button(excel_input, text="찾기", command=self.browse_input_excel, font=('Segoe UI', 8), bg=self.colors['secondary'], fg='white', relief='flat', cursor='hand2', width=6).pack(side='right')

        output_frame = tk.Frame(section, bg=self.colors['white'])
        output_frame.pack(fill='x')
        tk.Label(output_frame, text="출력 폴더:", font=('Segoe UI', 9, 'bold'), bg=self.colors['white']).pack(anchor='w')
        output_input = tk.Frame(output_frame, bg=self.colors['white'])
        output_input.pack(fill='x', pady=(2, 0))
        self.output_entry = tk.Entry(output_input, textvariable=self.output_folder_path, font=('Segoe UI', 9), relief='solid', bd=1)
        self.output_entry.pack(side='left', fill='x', expand=True, padx=(0, 3))
        tk.Button(output_input, text="찾기", command=self.browse_output_folder, font=('Segoe UI', 8), bg=self.colors['secondary'], fg='white', relief='flat', cursor='hand2', width=6).pack(side='right')

    def _create_coordinates_section(self, parent):
        """좌표 및 영역 설정 섹션 UI (좌표 숫자 제거)"""
        section = self._create_section_frame(parent, "🎯 좌표 및 영역 설정")
        click_frame = tk.Frame(section, bg=self.colors['white'])
        click_frame.pack(fill='x', pady=(0, 8))
        tk.Label(click_frame, text="클릭 포인트:", font=('Segoe UI', 10, 'bold'), bg=self.colors['white']).pack(side='left') # 라벨을 왼쪽에 배치
        tk.Button(click_frame, text="위치지정", command=self.relocate_clickpoint, font=('Segoe UI', 9), bg=self.colors['accent'], fg='white', relief='flat', cursor='hand2', width=10).pack(side='right') # 버튼을 오른쪽에 배치

        areas = [
            ("전체 영역", [self.allarea_x1, self.allarea_y1, self.allarea_x2, self.allarea_y2], self.relocate_allarea, self.colors['danger']),
            ("날짜 영역", [self.datearea_x1, self.datearea_y1, self.datearea_x2, self.datearea_y2], self.relocate_datearea, self.colors['primary']),
            ("금리 영역", [self.ratearea_x1, self.ratearea_y1, self.ratearea_x2, self.ratearea_y2], self.relocate_ratearea, self.colors['success'])
        ]
        for area_name, vars_list, func, color in areas:
            area_frame = tk.Frame(section, bg=self.colors['white'])
            area_frame.pack(fill='x', pady=(0, 6))
            tk.Label(area_frame, text=f"{area_name}:", font=('Segoe UI', 10, 'bold'), bg=self.colors['white']).pack(side='left') # 라벨을 왼쪽에 배치
            tk.Button(area_frame, text="영역지정", command=func, font=('Segoe UI', 9), bg=color, fg='white', relief='flat', cursor='hand2', width=10).pack(side='right') # 버튼을 오른쪽에 배치

        # '전체 영역 미리보기' 버튼 추가
        preview_frame = tk.Frame(section, bg=self.colors['white'])
        preview_frame.pack(fill='x', pady=(8, 0))
        tk.Button(preview_frame, text="🔍 전체 영역 미리보기", command=self.show_area_preview, font=('Segoe UI', 9, 'bold'), bg=self.colors['danger'], fg='white', relief='flat', cursor='hand2', width=28, pady=4).pack(fill='x')

    def _create_timing_section(self, parent):
        """타이밍 설정 섹션 UI"""
        section = self._create_section_frame(parent, "⏱️ 타이밍 설정")
        timing_grid = tk.Frame(section, bg=self.colors['white'])
        timing_grid.pack(fill='x')
        left_timing = tk.Frame(timing_grid, bg=self.colors['white'])
        left_timing.pack(side='left', fill='x', expand=True, padx=(0, 15))
        tk.Label(left_timing, text="붙여넣기 딜레이:", font=('Segoe UI', 10, 'bold'), bg=self.colors['white']).pack(anchor='w')
        paste_input = tk.Frame(left_timing, bg=self.colors['white'])
        paste_input.pack(fill='x', pady=(5, 0))
        tk.Entry(paste_input, textvariable=self.paste_delay, font=('Segoe UI', 10), width=8, relief='solid', bd=1).pack(side='left', padx=(0, 5))
        tk.Label(paste_input, text="초", font=('Segoe UI', 10), bg=self.colors['white']).pack(side='left')

        right_timing = tk.Frame(timing_grid, bg=self.colors['white'])
        right_timing.pack(side='left', fill='x', expand=True)
        tk.Label(right_timing, text="로딩 딜레이:", font=('Segoe UI', 10, 'bold'), bg=self.colors['white']).pack(anchor='w')
        loading_input = tk.Frame(right_timing, bg=self.colors['white'])
        loading_input.pack(fill='x', pady=(5, 0))
        tk.Entry(loading_input, textvariable=self.loading_delay, font=('Segoe UI', 10), width=8, relief='solid', bd=1).pack(side='left', padx=(0, 5))
        tk.Label(loading_input, text="초", font=('Segoe UI', 10), bg=self.colors['white']).pack(side='left')

    def _create_options_section(self, parent):
        """옵션 설정 섹션 UI (스레드 설정 추가)"""
        section = self._create_section_frame(parent, "⚙️ 옵션 설정")
        tk.Checkbutton(section, text="상세 이미지 저장 (영역별 개별 파일)", variable=self.save_detail_images, font=('Segoe UI', 10), bg=self.colors['white'], selectcolor=self.colors['light']).pack(anchor='w', pady=(0, 5))

        # 스레드 설정 추가
        thread_frame = tk.Frame(section, bg=self.colors['white'])
        thread_frame.pack(fill='x', pady=(0, 5))
        tk.Label(thread_frame, text="스레드:", font=('Segoe UI', 10), bg=self.colors['white']).pack(side='left')
        self.max_threads.set(self.settings_manager.get_advanced('thread_count', 4))
        tk.Entry(thread_frame, textvariable=self.max_threads, font=('Segoe UI', 10), width=6, relief='solid', bd=1).pack(side='left', padx=(3, 2))
        tk.Label(thread_frame, text="개", font=('Segoe UI', 10), bg=self.colors['white']).pack(side='left')

    def _create_preview_section(self, parent):
        """미리보기 섹션 UI"""
        section = self._create_section_frame(parent, "👁️ 영역 미리보기")
        tk.Button(section, text="🔍 전체 영역 미리보기", command=self.show_area_preview, font=('Segoe UI', 9, 'bold'), bg=self.colors['danger'], fg='white', relief='flat', cursor='hand2', width=28, pady=4).pack(fill='x', pady=(0, 6))
        individual_frame = tk.Frame(section, bg=self.colors['white'])
        individual_frame.pack(fill='x')
        preview_buttons = [
            ("🔴 전체", 'all', self.colors['danger']), ("🔵 날짜", 'date', self.colors['primary']), ("⚪ 금리", 'rate', self.colors['success'])
        ]
        for text, area_type, color in preview_buttons:
            tk.Button(individual_frame, text=text, command=lambda t=area_type: self.show_individual_area_preview(t), font=('Segoe UI', 9, 'bold'), bg=color, fg='white', relief='flat', cursor='hand2', width=8).pack(side='left', padx=1, fill='x', expand=True)

    def _create_log_section(self, parent):
        """로그 섹션 UI"""
        section = self._create_section_frame(parent, "📊 상태 및 로그")
        log_frame = tk.Frame(section, bg=self.colors['white'])
        log_frame.pack(fill='both', expand=True)
        self.log_text = tk.Text(log_frame, font=('Consolas', 7), bg=self.colors['white'], fg=self.colors['on_surface'], relief='solid', bd=1, wrap='word', state='disabled')
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")
        # 로그 태그 설정
        self.log_text.tag_configure("INFO", foreground=self.colors['primary'])
        self.log_text.tag_configure("WARNING", foreground=self.colors['warning'])
        self.log_text.tag_configure("ERROR", foreground=self.colors['danger'])
        self.log_text.tag_configure("SUCCESS", foreground=self.colors['success'])


        log_controls = tk.Frame(section, bg=self.colors['white'])
        log_controls.pack(fill='x', pady=(6, 0))
        tk.Button(log_controls, text="🗑️ 지우기", command=self.clear_log, font=('Segoe UI', 9), bg=self.colors['danger'], fg='white', relief='flat', cursor='hand2', width=8).pack(side='left', padx=(0, 5))
        tk.Button(log_controls, text="💾 저장", command=self.save_log, font=('Segoe UI', 9), bg=self.colors['success'], fg='white', relief='flat', cursor='hand2', width=8).pack(side='right')

    def _create_section_frame(self, parent, title):
        """UI 섹션 프레임 생성 헬퍼"""
        section_container = tk.Frame(parent, bg=self.colors['surface'])
        section_container.pack(fill='x', pady=(0, 4))
        title_frame = tk.Frame(section_container, bg=self.colors['primary'], height=22)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)
        tk.Label(title_frame, text=title, font=('Segoe UI', 9, 'bold'), bg=self.colors['primary'], fg='white').pack(side='left', padx=6, pady=3)
        content_frame = tk.Frame(section_container, bg=self.colors['white'], relief='solid', bd=1)
        content_frame.pack(fill='both', expand=True, padx=0, pady=0)
        inner_frame = tk.Frame(content_frame, bg=self.colors['white'])
        inner_frame.pack(fill='both', expand=True, padx=6, pady=0) # padx=6은 좌우 내부 패딩 유지
        return inner_frame

    def apply_theme(self):
        """테마 적용 및 UI 재구성"""
        try:
            selected_name = self.theme_var.get()
            selected_theme_key = next((key for key, theme in self.available_themes.items() if theme['name'] == selected_name), None)
            if selected_theme_key:
                self.current_theme = selected_theme_key
                self.colors = self.available_themes[selected_theme_key].copy()
                self.rebuild_ui_instantly() # UI 즉시 재구성
                self.settings_manager.set_advanced('ui_theme', selected_theme_key)
                self.logger.info(f"테마 적용됨: {selected_name}")
        except Exception as e:
            self.logger.error(f"테마 적용 중 오류: {e}")

    def rebuild_ui_instantly(self):
        """UI 즉시 재구성 (기존 값 유지)"""
        try:
            self.configure(bg=self.colors['surface'])
            # 기존 grid 설정 초기화
            for i in range(10):  # 충분한 범위로 grid 설정 해제
                try:
                    self.grid_rowconfigure(i, weight=0)
                    self.grid_columnconfigure(i, weight=0)
                except:
                    pass
            
            for child in self.winfo_children():
                if not isinstance(child, tk.Menu): # 메뉴바는 제외
                    child.destroy()
            self._build_ui() # UI 다시 빌드
            current_settings = self.get_current_settings() # 현재 설정값 가져오기
            self.apply_settings(current_settings) # 설정값 다시 적용
            self.update_advanced_ui_from_settings() # 고급설정 UI도 업데이트
            self.refresh_grid() # 그리드 데이터도 복원
        except Exception as e:
            self.logger.error(f"UI 재구성 중 오류: {e}")

    def update_preset_combo(self):
        """프리셋 콤보박스 업데이트"""
        if hasattr(self, 'preset_combo') and self.preset_combo:
            preset_names = self.settings_manager.get_preset_names()
            self.preset_combo['values'] = preset_names
            if preset_names:
                self.preset_combo.current(0)
            else:
                self.preset_combo.set('') # 비어있을 경우

    def apply_selected_preset(self):
        """선택된 프리셋 적용"""
        if not hasattr(self, 'preset_combo'): return
        selected = self.preset_combo.get()
        if selected:
            preset_settings = self.settings_manager.apply_preset(selected)
            if preset_settings:
                self.apply_settings(preset_settings)
                self.update_advanced_ui_from_settings() # 고급 설정 UI도 업데이트
                messagebox.showinfo("정보", f"프리셋 '{selected}'이 적용되었습니다.")

    def save_current_preset(self):
        """현재 설정을 프리셋으로 저장"""
        name_entry_widget = getattr(self, 'preset_name_entry', None)
        name = ""
        if name_entry_widget:
            name = name_entry_widget.get().strip()
            if name == "새 프리셋 이름" or not name:
                messagebox.showwarning("경고", "유효한 프리셋 이름을 입력해주세요.")
                return
        else: # Fallback if UI element is not ready (e.g. during init)
            name = simpledialog.askstring("프리셋 저장", "프리셋 이름을 입력하세요:")
            if not name: return

        current_settings = self.get_current_settings()
        self.settings_manager.save_preset(name, current_settings)
        self.update_preset_combo()
        if name_entry_widget:
            name_entry_widget.delete(0, tk.END)
            name_entry_widget.insert(0, "새 프리셋 이름")
        messagebox.showinfo("완료", f"'{name}' 프리셋이 저장되었습니다.")

    def get_current_settings(self):
        """현재 UI의 모든 설정 값을 딕셔너리로 반환"""
        settings = {
            'click_point': (self.click_x.get(), self.click_y.get()),
            'all_area': (self.allarea_x1.get(), self.allarea_y1.get(), self.allarea_x2.get(), self.allarea_y2.get()),
            'date_area': (self.datearea_x1.get(), self.datearea_y1.get(), self.datearea_x2.get(), self.datearea_y2.get()),
            'rate_area': (self.ratearea_x1.get(), self.ratearea_y1.get(), self.ratearea_x2.get(), self.ratearea_y2.get()),
            'delays': {'paste': self.paste_delay.get(), 'loading': self.loading_delay.get()},
            'save_detail_images': self.save_detail_images.get(),
            'advanced': self.settings_manager.data.get('advanced', self.settings_manager._get_default_advanced_settings()).copy() # 올바른 메서드 호출
        }
        return settings

    def apply_settings(self, settings_dict):
        """주어진 설정 딕셔너리를 UI에 적용"""
        if not settings_dict: return
        self.click_x.set(settings_dict.get('click_point', (0,0))[0])
        self.click_y.set(settings_dict.get('click_point', (0,0))[1])
        # 각 영역 좌표 설정 (존재 여부 및 길이 체크)
        for area_key, vars_prefix in [('all_area', 'allarea'), ('date_area', 'datearea'), ('rate_area', 'ratearea')]:
            coords = settings_dict.get(area_key)
            if coords and len(coords) == 4:
                getattr(self, f"{vars_prefix}_x1").set(coords[0])
                getattr(self, f"{vars_prefix}_y1").set(coords[1])
                getattr(self, f"{vars_prefix}_x2").set(coords[2])
                getattr(self, f"{vars_prefix}_y2").set(coords[3])

        delays = settings_dict.get('delays', {})
        self.paste_delay.set(delays.get('paste', 0.5))
        self.loading_delay.set(delays.get('loading', 2.5))
        self.save_detail_images.set(settings_dict.get('save_detail_images', True))

        if 'advanced' in settings_dict: # 프리셋이나 저장된 설정에서 고급설정 로드
            self.settings_manager.data['advanced'].update(settings_dict['advanced'])


    def quick_save_settings(self):
        """현재 UI 설정을 settings.json의 'current' 항목에 저장"""
        settings = self.get_current_settings()
        self.settings_manager.save_current_settings(settings)
        self.logger.info("현재 설정이 저장되었습니다.")

    def load_last_settings(self):
        """settings.json의 'current' 설정을 불러와 UI에 적용"""
        try:
            settings = self.settings_manager.get_current_settings()
            if settings:
                self.apply_settings(settings)
                self.update_advanced_ui_from_settings() # 고급 설정 UI도 업데이트
                self.logger.info("마지막 설정이 성공적으로 불러와졌습니다.")
            else:
                self.logger.info("저장된 현재 설정이 없습니다. 기본값을 사용합니다.")
                # 기본값으로 고급 설정 UI 업데이트
                self.settings_manager.data['advanced'] = self.settings_manager._get_default_advanced_settings()
                self.update_advanced_ui_from_settings()
        except Exception as e:
            self.logger.error(f"설정 불러오기 실패: {e}")


    def save_advanced_ui_to_settings(self):
        """고급 설정 UI의 현재 값들을 settings_manager에 저장 (영어 고정, 전처리 기능 제거)"""
        try:
            # OCR 설정
            self.settings_manager.set_advanced('ocr_gpu_enabled', self.use_gpu.get())
            # UI에서는 %로 받으므로 100으로 나눠서 저장
            self.settings_manager.set_advanced('ocr_confidence_threshold', round(self.confidence_threshold.get() / 100.0, 2))
            # 언어는 영어로 고정
            self.settings_manager.set_advanced('ocr_languages', ['en'])

            # 자동화 설정 (UI에 있는 것만)
            self.settings_manager.set_advanced('thread_count', self.max_threads.get())

            self.settings_manager.save_settings() # 파일에 최종 저장
            messagebox.showinfo("성공", "고급 설정이 저장되었습니다. (OCR 언어: 영어 고정)")
            self.logger.info("고급 설정 UI 값이 설정에 저장되었습니다. (영어 고정)")
            # OCR 엔진 재초기화 필요시 알림 또는 자동 재초기화
            self.initialize_ocr()

        except Exception as e:
            messagebox.showerror("오류", f"고급 설정 저장 중 오류: {e}")
            self.logger.error(f"고급 설정 저장 실패: {e}")


    def reset_advanced_settings_and_ui(self):
        """고급 설정을 기본값으로 초기화하고 UI도 업데이트"""
        if messagebox.askyesno("확인", "모든 고급 설정을 기본값으로 되돌리시겠습니까?"):
            self.settings_manager.reset_advanced_settings()
            self.update_advanced_ui_from_settings()
            messagebox.showinfo("완료", "고급 설정이 초기화되었습니다.")
            self.logger.info("고급 설정이 기본값으로 초기화되었습니다.")
            self.initialize_ocr() # OCR 엔진도 기본 설정으로 재초기화

    def update_advanced_ui_from_settings(self):
        """settings_manager의 고급 설정을 UI에 반영 (영어 고정, 전처리 기능 제거)"""
        try:
            # OCR 설정
            self.use_gpu.set(self.settings_manager.get_advanced('ocr_gpu_enabled', False))
            self.confidence_threshold.set(self.settings_manager.get_advanced('ocr_confidence_threshold', 0.2) * 100) # %로 표시
            # 언어는 영어로 고정되므로 UI 업데이트 불필요
            # languages = self.settings_manager.get_advanced('ocr_languages', ['en'])
            # self.lang_var.set('en')  # 항상 영어

            # 자동화 설정
            self.max_threads.set(self.settings_manager.get_advanced('thread_count', 4))

            self.logger.debug("고급 설정 UI가 현재 설정값으로 업데이트되었습니다. (영어 고정)")
        except Exception as e:
            self.logger.error(f"고급 설정 UI 업데이트 실패: {e}")


    def clear_log(self):
        """로그 텍스트 영역 지우기"""
        if hasattr(self, 'log_text') and self.log_text:
            self.log_text.config(state='normal')
            self.log_text.delete(1.0, tk.END)
            self.log_text.config(state='disabled')

    def save_log(self):
        """현재 로그 내용을 파일로 저장"""
        if hasattr(self, 'log_text') and self.log_text:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if filename:
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        content = self.log_text.get(1.0, tk.END)
                        f.write(content)
                    messagebox.showinfo("성공", f"로그가 저장되었습니다: {filename}")
                except Exception as e:
                    messagebox.showerror("오류", f"로그 저장 실패: {e}")

    def update_log_display(self, message, level="INFO"):
        """로그 텍스트 영역에 메시지 추가 (로그 레벨에 따라 색상 적용 가능)"""
        if hasattr(self, 'log_text') and self.log_text:
            self.log_text.config(state='normal')
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            # 로깅 모듈을 통해 실제 로그 파일에도 기록
            if level == "ERROR":
                self.logger.error(message)
                tag = "ERROR"
            elif level == "WARNING":
                self.logger.warning(message)
                tag = "WARNING"
            elif level == "SUCCESS": # SUCCESS는 logging에 기본 레벨이 없으므로 INFO로 기록
                self.logger.info(message)
                tag = "SUCCESS"
            else: # INFO 및 기타
                self.logger.info(message)
                tag = "INFO"

            self.log_text.insert(tk.END, f"{timestamp} - {message}\n", tag)
            self.log_text.see(tk.END) # 가장 최근 로그로 스크롤
            self.log_text.config(state='disabled')


    def show_area_preview(self):
        """설정된 모든 영역 미리보기"""
        areas_info = {
            "click_point": (self.click_x.get(), self.click_y.get()),
            "all_area": (self.allarea_x1.get(), self.allarea_y1.get(), self.allarea_x2.get(), self.allarea_y2.get()),
            "date_area": (self.datearea_x1.get(), self.datearea_y1.get(), self.datearea_x2.get(), self.datearea_y2.get()),
            "rate_area": (self.ratearea_x1.get(), self.ratearea_y1.get(), self.ratearea_x2.get(), self.ratearea_y2.get())
        }
        AreaVisualizationOverlay(self, areas_info, auto_close=True)

    def show_individual_area_preview(self, area_type):
        """개별 영역 미리보기 (캡처 후 새 창에 표시)"""
        coords_map = {
            'all': (self.allarea_x1.get(), self.allarea_y1.get(), self.allarea_x2.get(), self.allarea_y2.get()),
            'date': (self.datearea_x1.get(), self.datearea_y1.get(), self.datearea_x2.get(), self.datearea_y2.get()),
            'rate': (self.ratearea_x1.get(), self.ratearea_y1.get(), self.ratearea_x2.get(), self.ratearea_y2.get()),
        }
        title_map = {'all': "전체 영역", 'date': "날짜 영역", 'rate': "금리 영역"}

        if area_type not in coords_map: return
        coords = coords_map[area_type]
        if not all(isinstance(c, int) and c >= 0 for c in coords) or coords[2] <= coords[0] or coords[3] <= coords[1]:
            messagebox.showwarning("경고", f"{title_map[area_type]}의 좌표가 유효하지 않습니다.")
            return

        try:
            screenshot = pyautogui.screenshot(region=coords)
            preview_window = tk.Toplevel(self)
            preview_window.title(f"{title_map[area_type]} 미리보기")
            preview_window.geometry("400x300") # 창 크기 고정 또는 이미지 크기에 맞게 조정
            preview_window.configure(bg=self.colors['surface'])

            img_resized = screenshot.copy()
            img_resized.thumbnail((380, 280), Image.Resampling.LANCZOS) # 창 크기에 맞게 섬네일
            photo = ImageTk.PhotoImage(img_resized)

            label = tk.Label(preview_window, image=photo, bg=self.colors['surface'])
            label.image = photo # 참조 유지 중요!
            label.pack(padx=10, pady=10)
            info_text = f"좌표: ({coords[0]}, {coords[1]}) - ({coords[2]}, {coords[3]}) | 크기: {coords[2]-coords[0]}x{coords[3]-coords[1]}"
            tk.Label(preview_window, text=info_text, font=('Segoe UI', 9), bg=self.colors['surface'], fg=self.colors['on_surface']).pack(pady=(0,5))

        except Exception as e:
            messagebox.showerror("오류", f"미리보기 생성 실패: {e}")
            self.logger.error(f"개별 영역 미리보기 실패 ({area_type}): {e}")


    def browse_input_excel(self):
        """Input Excel 파일 선택 대화상자"""
        file_path = filedialog.askopenfilename(title="엑셀 파일 선택", filetypes=[("Excel files", "*.xlsx;*.xls")])
        if file_path:
            self.input_excel_path.set(file_path)
            base_path = os.path.dirname(file_path)
            if not self.output_folder_path.get(): # 출력 폴더가 비어있으면 자동으로 채움
                self.output_folder_path.set(base_path)

    def browse_output_folder(self):
        """Output 폴더 선택 대화상자"""
        folder_path = filedialog.askdirectory(title="출력 폴더 선택")
        if folder_path:
            self.output_folder_path.set(folder_path)

    def relocate_clickpoint(self):
        """클릭 포인트 재지정 (오버레이 사용)"""
        overlay = PointCaptureOverlay(self, color="red")
        self.wait_window(overlay) # 오버레이 창이 닫힐 때까지 대기
        if overlay.click_x is not None:
            self.click_x.set(overlay.click_x)
            self.click_y.set(overlay.click_y)

    def _relocate_area_generic(self, x1_var, y1_var, x2_var, y2_var, color):
        """영역 재지정 일반 로직 (오버레이 사용)"""
        overlay = DragCaptureOverlay(self, color=color)
        self.wait_window(overlay)
        if overlay.x1 is not None:
            x1_var.set(overlay.x1)
            y1_var.set(overlay.y1)
            x2_var.set(overlay.x2)
            y2_var.set(overlay.y2)

    def relocate_allarea(self): self._relocate_area_generic(self.allarea_x1, self.allarea_y1, self.allarea_x2, self.allarea_y2, "red")
    def relocate_datearea(self): self._relocate_area_generic(self.datearea_x1, self.datearea_y1, self.datearea_x2, self.datearea_y2, "blue")
    def relocate_ratearea(self): self._relocate_area_generic(self.ratearea_x1, self.ratearea_y1, self.ratearea_x2, self.ratearea_y2, "green") # 색상 변경

    def stop_processing(self):
        """OCR 처리 중단 요청"""
        if self.work_controller.is_running:
            message = self.work_controller.stop_work()
            self.message_queue.put(("log", message)) # 로그에도 중단 메시지 기록

    def _on_work_complete(self, summary_message):
        """작업 완료 시 UI 및 상태 업데이트"""
        self.work_controller.reset()
        self.progress_tracker.hide()
        if hasattr(self, 'run_btn'): self.run_btn.config(text="🚀 OCR 시작 (F5)", state='normal')
        self.current_processing_index = -1 # 현재 처리 인덱스 초기화
        self.refresh_grid() # 그리드 상태 최종 업데이트
        messagebox.showinfo("처리 완료", summary_message)
        self.quick_save_settings() # 작업 완료 후 자동 설정 저장

    def _on_work_stopped(self):
        """작업 중단 시 UI 및 상태 업데이트"""
        self.work_controller.reset()
        self.progress_tracker.hide()
        if hasattr(self, 'run_btn'): self.run_btn.config(text="🚀 OCR 시작 (F5)", state='normal')
        self.current_processing_index = -1
        self.refresh_grid()
        messagebox.showinfo("중단됨", "작업이 사용자에 의해 중단되었습니다.")

    def _handle_grid_update(self, data):
        """스레드로부터 그리드 업데이트 메시지 처리"""
        try:
            update_type, grid_index, *payload = data
            if 0 <= grid_index < len(self.excel_data):
                if update_type == "processing":
                    self.current_processing_index = grid_index
                    self.excel_data[grid_index]['상태'] = '처리 중...'
                    self.grid_tree.see(self.grid_tree.get_children()[grid_index]) # 현재 작업 중인 항목으로 스크롤
                elif update_type == "complete" and len(payload) >= 3:
                    date_res, rate_res, status_res = payload[0], payload[1], payload[2]
                    if date_res: self.excel_data[grid_index]['날짜'] = date_res
                    if rate_res: self.excel_data[grid_index]['금리'] = rate_res
                    self.excel_data[grid_index]['상태'] = status_res
                elif update_type == "error" and len(payload) >= 1:
                    self.excel_data[grid_index]['상태'] = payload[0] # 에러 메시지 또는 "오류"
                self.refresh_grid() # 변경사항 즉시 그리드에 반영
        except Exception as e:
            self.logger.error(f"그리드 업데이트 중 오류: {e}, 데이터: {data}")

    def show_shortcuts(self):
        """키보드 단축키 도움말 표시"""
        shortcuts = """
🎹 키보드 단축키:
• F5: OCR 처리 실행/중단
• Escape: 처리 중단
• F1: 단축키 도움말 (이 창)
• Ctrl+S: 모든 설정 저장
• Ctrl+L: 마지막 설정 불러오기
        """
        messagebox.showinfo("키보드 단축키", shortcuts)

    def show_about(self):
        """프로그램 정보 표시"""
        about_text = """
📋 Check Capture OCR - V6
OCR 자동화 애플리케이션 (EasyOCR 기반)
        """
        messagebox.showinfo("프로그램 정보", about_text)

    def run_ocr_process(self):
        """OCR 프로세스 시작 (스레드에서 실행)"""
        if self.work_controller.is_running:
            self.stop_processing()
            return
        if not self.validate_inputs():
            return

        self.work_controller.start_work()
        self.progress_tracker.show()
        if hasattr(self, 'run_btn'): self.run_btn.config(text="⏹️ 처리 중단 (F5)", state='normal')

        self.worker_thread = threading.Thread(target=self.execute_ocr_workflow, daemon=True)
        self.worker_thread.start()

    def validate_inputs(self):
        """입력값 유효성 검증"""
        input_file = self.input_excel_path.get().strip()
        output_dir = self.output_folder_path.get().strip()
        if not input_file or not os.path.exists(input_file):
            messagebox.showwarning("경고", "유효한 Input Excel 파일 경로를 지정하세요.")
            return False
        if not output_dir or not os.path.isdir(output_dir):
            messagebox.showwarning("경고", "유효한 Output 폴더를 지정하세요.")
            return False
        if not self.ocr_reader:
            messagebox.showerror("오류", "OCR 엔진이 초기화되지 않았습니다. 프로그램을 재시작하거나 설정을 확인하세요.")
            return False
        if not self.excel_data:
             messagebox.showwarning("경고", "처리할 데이터가 없습니다. Excel 파일을 로드하거나 데이터를 추가하세요.")
             return False
        return True

    def execute_ocr_workflow(self):
        """OCR 워크플로우 실행 (그리드 데이터 기반)"""
        try:
            output_dir = self.output_folder_path.get().strip()
            paste_d = self.paste_delay.get()
            load_d = self.loading_delay.get()
            coords = {
                'click': (self.click_x.get(), self.click_y.get()),
                'all': (self.allarea_x1.get(), self.allarea_y1.get(), self.allarea_x2.get(), self.allarea_y2.get()),
                'date': (self.datearea_x1.get(), self.datearea_y1.get(), self.datearea_x2.get(), self.datearea_y2.get()),
                'rate': (self.ratearea_x1.get(), self.ratearea_y1.get(), self.ratearea_x2.get(), self.ratearea_y2.get()),
            }
            save_folder = os.path.join(output_dir, "ocr_images")
            os.makedirs(save_folder, exist_ok=True)

            total_items = len(self.excel_data)
            processed_count = 0

            for grid_index, row_data in enumerate(self.excel_data):
                if self.work_controller.is_stopped:
                    self.message_queue.put(("log", "사용자가 처리를 중단했습니다."))
                    self.message_queue.put(("stopped", None))
                    return

                stock_code = str(row_data.get('종목코드', '')).strip()
                stock_name = str(row_data.get('종목명', '')).strip()
                current_item_text = f"{stock_code} ({stock_name})" if stock_code or stock_name else f"행 {grid_index+1}"

                self.message_queue.put(("grid_update", ("processing", grid_index)))
                self.message_queue.put(("progress", (grid_index + 1, total_items, f"처리 중: {current_item_text}", current_item_text)))

                if not stock_code: # 종목코드가 없으면 건너뛰기
                    self.message_queue.put(("log", f"행 {grid_index+1}: 종목코드가 없어 건너<0xEB><0><0x8A><0xEB><0x9C><0x88>니다."))
                    self.message_queue.put(("grid_update", ("error", grid_index, "종목코드 없음")))
                    continue

                self.work_controller.skip_current = False
                try:
                    date_img_src, rate_img_src = self.capture_screenshots(
                        stock_code, save_folder, coords, paste_d, load_d
                    )
                    if self.work_controller.skip_current:
                        self.message_queue.put(("log", f"종목 {stock_code}를 사용자 요청으로 건너<0xEB><0><0x8A><0xEB><0x9C><0x88>니다."))
                        self.message_queue.put(("grid_update", ("error", grid_index, "건너<0xEB><0><0x8A><0xEB><0x9C><0x88>")))
                        continue
                    if date_img_src is None or rate_img_src is None: # 캡처 실패 또는 중단
                        if self.work_controller.is_stopped: break
                        self.message_queue.put(("grid_update", ("error", grid_index, "캡처 실패")))
                        continue

                    date_result, rate_result = self.process_single_ocr(date_img_src, rate_img_src)

                    status_msg = "완료"
                    # 결과가 없는 경우에도 '완료' 상태 유지 (실패로 간주하지 않음)
                    # if not date_result and not rate_result: status_msg = "OCR 실패"
                    # elif not date_result: status_msg = "날짜 인식 실패"
                    # elif not rate_result: status_msg = "금리 인식 실패"

                    self.message_queue.put(("grid_update", ("complete", grid_index, date_result, rate_result, status_msg)))
                    self.message_queue.put(("log", f"[{stock_code}] {status_msg} - 날짜: '{date_result}', 금리: '{rate_result}'"))
                    if status_msg == "완료": processed_count += 1

                except Exception as e:
                    self.message_queue.put(("error", f"종목 {stock_code} 처리 중 오류: {e}"))
                    self.message_queue.put(("grid_update", ("error", grid_index, "처리 오류")))
                    self.logger.exception(f"종목 {stock_code} 처리 중 예외 발생") # 스택 트레이스 로깅
                    continue # 오류 발생 시 다음 항목으로

            if not self.work_controller.is_stopped:
                self.export_grid_to_excel()
                summary = self.generate_ocr_summary(processed_count, total_items)
                self.message_queue.put(("complete", summary))
            elif self.work_controller.is_stopped: # 명시적 중단 처리
                 self.message_queue.put(("stopped", None))

        except Exception as e:
            self.message_queue.put(("error", f"OCR 전체 워크플로우 오류: {e}"))
            self.logger.exception("OCR 전체 워크플로우에서 예외 발생")
            self.message_queue.put(("stopped", None)) # 오류 발생 시 작업 중단 상태로

    def capture_screenshots(self, stock_code, save_folder, coords, paste_d, load_d):
        """스크린샷 캡처 로직 (이미지 저장 옵션 적용)"""
        if self.work_controller.is_stopped: return None, None
        pyperclip.copy(stock_code)
        pyautogui.click(x=coords['click'][0], y=coords['click'][1], clicks=2, interval=self.settings_manager.get_advanced('click_interval', 0.1))
        if self.work_controller.is_stopped: return None, None
        time.sleep(paste_d)
        pyautogui.hotkey('ctrl', 'v')

        # 로딩 대기 (분할하여 중단 체크)
        slept_time = 0
        while slept_time < load_d:
            if self.work_controller.is_stopped: return None, None
            time.sleep(min(0.1, load_d - slept_time))
            slept_time += 0.1

        safe_stock_code = re.sub(r'[\\/*?:"<>|]', "_", stock_code) # 파일명으로 부적합한 문자 변경
        save_details = self.save_detail_images.get()

        # 전체 영역 스크린샷 (항상 저장)
        x1_all, y1_all, x2_all, y2_all = coords['all']
        if not (x2_all > x1_all and y2_all > y1_all) : # 유효하지 않은 좌표면 None 반환
            self.message_queue.put(("error", f"[{safe_stock_code}] 전체 영역 좌표 오류: {coords['all']}"))
            return None, None
        screenshot_all = pyautogui.screenshot(region=(x1_all, y1_all, x2_all - x1_all, y2_all - y1_all))
        allarea_path = os.path.join(save_folder, f"{safe_stock_code}.png")
        screenshot_all.save(allarea_path)
        self.message_queue.put(("log", f"전체 영역 이미지 저장: {allarea_path}"))

        date_img_src, rate_img_src = None, None
        # 날짜 영역
        x1_date, y1_date, x2_date, y2_date = coords['date']
        if not (x2_date > x1_date and y2_date > y1_date):
            self.message_queue.put(("error", f"[{safe_stock_code}] 날짜 영역 좌표 오류: {coords['date']}"))
        else:
            screenshot_date = pyautogui.screenshot(region=(x1_date, y1_date, x2_date - x1_date, y2_date - y1_date))
            if save_details:
                date_img_src = os.path.join(save_folder, f"{safe_stock_code}_date.png")
                screenshot_date.save(date_img_src)
                self.message_queue.put(("log", f"날짜 영역 이미지 저장: {date_img_src}"))
            else:
                date_img_src = screenshot_date # PIL Image 객체

        # 금리 영역
        x1_rate, y1_rate, x2_rate, y2_rate = coords['rate']
        if not (x2_rate > x1_rate and y2_rate > y1_rate):
            self.message_queue.put(("error", f"[{safe_stock_code}] 금리 영역 좌표 오류: {coords['rate']}"))
        else:
            screenshot_rate = pyautogui.screenshot(region=(x1_rate, y1_rate, x2_rate - x1_rate, y2_rate - y1_rate))
            if save_details:
                rate_img_src = os.path.join(save_folder, f"{safe_stock_code}_rate.png")
                screenshot_rate.save(rate_img_src)
                self.message_queue.put(("log", f"금리 영역 이미지 저장: {rate_img_src}"))
            else:
                rate_img_src = screenshot_rate # PIL Image 객체

        return date_img_src, rate_img_src

    def process_single_ocr(self, date_img_src, rate_img_src):
        """단일 이미지 쌍에 대한 OCR 처리 (리팩토링된 추출 함수 사용)"""
        date_result, rate_result = "", ""
        try:
            if date_img_src:
                date_result = self._extract_text_with_ocr_attempts(date_img_src, self.analyze_date_results, "날짜")
            if rate_img_src:
                rate_result = self._extract_text_with_ocr_attempts(rate_img_src, self.analyze_rate_results, "금리")
        except Exception as e:
            self.message_queue.put(("error", f"단일 OCR 처리 중 오류: {e}"))
            self.logger.exception("단일 OCR 처리 중 예외 발생")
        return date_result, rate_result

    def _extract_text_with_ocr_attempts(self, image_source, analysis_function, field_name):
        """
        초단순화된 OCR 추출 로직 (원본 이미지만 사용, 신뢰도 무시).
        image_source: 이미지 파일 경로(str) 또는 PIL Image 객체.
        analysis_function: OCR 결과 분석 함수 (analyze_date_results 또는 analyze_rate_results).
        field_name: 로그 출력을 위한 필드명 ("날짜" 또는 "금리").
        """
        if self.work_controller.is_stopped: return ""

        try:
            # 이미지 로드 (경로 또는 PIL 객체)
            original_img = Image.open(image_source) if isinstance(image_source, str) else image_source
            if original_img is None:
                self.message_queue.put(("log", f"{field_name} 이미지 소스 로드 실패: {image_source}"))
                return ""

            # 원본 이미지 OCR 1회만 실행
            if self.work_controller.is_stopped: return ""
            img_array = np.array(original_img)
            ocr_results = self.ocr_reader.readtext(img_array, detail=0)  # detail=0: 텍스트만 반환
            
            # 모든 텍스트를 단순히 연결해서 반환 (신뢰도 무시)
            all_text = " ".join(ocr_results) if ocr_results else ""
            
            self.message_queue.put(("log", f"[{field_name}] 원본 OCR 결과: '{all_text}'"))
            
            # 분석 함수 호출 (하지만 실제로는 정제만 수행)
            return analysis_function(all_text, field_name)

        except Exception as e:
            self.message_queue.put(("error", f"{field_name} 추출 중 오류: {e}"))
            self.logger.exception(f"{field_name} 추출 중 예외 발생")
            return ""
        finally:
            # 임시 파일 정리
            if isinstance(image_source, str) and not self.save_detail_images.get():
                if os.path.exists(image_source) and ("_date.png" in image_source or "_rate.png" in image_source):
                    try:
                        os.remove(image_source)
                        self.message_queue.put(("log", f"임시 {field_name} 이미지 파일 삭제: {image_source}"))
                    except Exception as e_remove:
                        self.message_queue.put(("log", f"임시 {field_name} 이미지 파일 삭제 실패: {e_remove}"))


    def analyze_date_results(self, raw_text, field_name="날짜"):
        """날짜 텍스트 분석 및 정제 (신뢰도 무시)"""
        if not raw_text or not raw_text.strip():
            self.message_queue.put(("log", f"[{field_name}] 텍스트가 비어있습니다."))
            return ""
        
        self.message_queue.put(("log", f"[{field_name}] 원본 텍스트: '{raw_text}'"))
        
        # 텍스트 정제
        cleaned_text = self.clean_date_text(raw_text)
        
        if self.is_valid_date_format(cleaned_text):
            self.message_queue.put(("log", f"[{field_name}] 유효한 날짜: '{cleaned_text}'"))
            return cleaned_text
        else:
            self.message_queue.put(("log", f"[{field_name}] 유효하지 않은 날짜 형식: '{cleaned_text}' (원본: '{raw_text}')"))
            return ""


    def analyze_rate_results(self, raw_text, field_name="금리"):
        """금리 텍스트 분석 및 정제 (신뢰도 무시)"""
        if not raw_text or not raw_text.strip():
            self.message_queue.put(("log", f"[{field_name}] 텍스트가 비어있습니다."))
            return ""
        
        self.message_queue.put(("log", f"[{field_name}] 원본 텍스트: '{raw_text}'"))
        
        # 텍스트 정제
        cleaned_text = self.clean_rate_text(raw_text)
        
        if self.is_valid_rate_format(cleaned_text):
            self.message_queue.put(("log", f"[{field_name}] 유효한 금리: '{cleaned_text}'"))
            return cleaned_text
        else:
            self.message_queue.put(("log", f"[{field_name}] 유효하지 않은 금리 형식: '{cleaned_text}' (원본: '{raw_text}')"))
            return ""


    def is_valid_date_format(self, date_str):
        """날짜 형식 검증 (YYYY/MM/DD)"""
        return bool(re.fullmatch(r'\d{4}/\d{2}/\d{2}', date_str))

    def is_valid_rate_format(self, rate_str):
        """금리 형식 검증 (숫자.숫자)"""
        return bool(re.fullmatch(r'\d+\.\d+', rate_str))


    def clean_date_text(self, text):
        """날짜 텍스트 정제 (YYYY/MM/DD 형식 목표)"""
        cleaned = re.sub(r'[^\d]', '', text) # 숫자만 추출
        if len(cleaned) == 8: # YYYYMMDD
            return f"{cleaned[:4]}/{cleaned[4:6]}/{cleaned[6:]}"
        elif len(cleaned) == 6: # YYMMDD (20YY로 가정)
            year_prefix = "20"
            # 특정 연도 범위 (예: 70~99는 19xx, 00~69는 20xx) 로직 추가 가능
            if int(cleaned[:2]) > 50 : year_prefix = "19" # 간단한 추론
            return f"{year_prefix}{cleaned[:2]}/{cleaned[2:4]}/{cleaned[4:]}"
        # 추가적인 길이 및 패턴 처리 (예: 2025529 -> 2025/05/29)
        elif len(cleaned) == 7 and cleaned.startswith('202') and int(cleaned[4]) <=1: # 202YMDD -> 202Y/M/DD
             return f"{cleaned[:4]}/{cleaned[4:5].zfill(2)}/{cleaned[5:].zfill(2)}"
        # 더 많은 예외 케이스 처리 필요
        return text # 정제 실패 시 원본 반환 (분석 함수에서 재검증)

    def clean_rate_text(self, text):
        """금리 텍스트 정제 (X.XXX 또는 XX.XXX 형식 목표)"""
        # 퍼센트 기호, 특정 문자 제거, 쉼표를 점으로
        cleaned = text.replace('%','').replace(' ','').replace(',','.').replace('·','.')
        cleaned = re.sub(r'[^\d.]', '', cleaned) # 숫자와 점만 남김

        # 점이 여러 개거나, 숫자가 아닌 문자가 포함된 경우 추가 처리
        if cleaned.count('.') > 1: # 점이 여러 개면 첫번째 점만 남기고 나머지는 제거 시도
            parts = cleaned.split('.')
            cleaned = parts[0] + '.' + ''.join(parts[1:])

        # 유효한 숫자 형식인지 확인 (예: "3.500", "12.125")
        if re.fullmatch(r'\d+\.\d+', cleaned):
            try:
                # 너무 큰 값이나 작은 값 보정 (예시 로직)
                val = float(cleaned)
                if val > 50.0 and val < 1000: val /= 100.0 # 987.0 -> 9.870
                elif val > 1000.0 : val /= 1000.0 # 3500 -> 3.500
                return f"{val:.3f}" # 소수점 3자리로 통일
            except ValueError:
                return cleaned # 변환 실패 시 원래 정리된 값 반환
        elif re.fullmatch(r'\d+', cleaned) and len(cleaned) >=2 and len(cleaned) <= 5: # 점이 없는 숫자 (3500 -> 3.500)
            try:
                if len(cleaned) == 2: # 35 -> 3.500 (가정)
                    return f"{cleaned[0]}.{cleaned[1]}00"
                elif len(cleaned) == 3: # 350 -> 3.500
                    return f"{cleaned[0]}.{cleaned[1:]}0"
                elif len(cleaned) == 4: # 3500 -> 3.500
                    return f"{cleaned[0]}.{cleaned[1:]}"
                elif len(cleaned) == 5: # 12500 -> 12.500
                     return f"{cleaned[:2]}.{cleaned[2:]}"
            except:
                pass # 변환 실패 시 아래로

        return cleaned # 정제 실패 시 정리된 텍스트 반환 (분석 함수에서 재검증)

    def load_excel_to_grid(self):
        """Excel 파일을 읽어 그리드에 로드"""
        file_path = self.input_excel_path.get()
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("오류", "Excel 파일을 먼저 선택해주세요.")
            return
        try:
            df = pd.read_excel(file_path, dtype=str) # 모든 데이터를 문자열로 읽기
            self.clear_all_data() # 기존 데이터 삭제

            # 컬럼명 매핑 (대소문자 구분 없이, 일반적인 이름들 포함)
            col_map = {}
            expected_cols = {'종목코드': ['종목코드', 'code', 'item code'],
                             '종목명': ['종목명', 'name', 'item name', '회사명'],
                             '날짜': ['날짜', 'date', '만기일'],
                             '금리': ['금리', 'rate', '수익률', '표면금리']}
            df_cols_lower = {str(col).lower(): str(col) for col in df.columns}

            for target_col, possible_names in expected_cols.items():
                for p_name in possible_names:
                    if p_name in df_cols_lower:
                        col_map[target_col] = df_cols_lower[p_name]
                        break
                if target_col not in col_map: # 필수 컬럼이 없으면 경고 (또는 빈 컬럼으로 처리)
                     self.logger.warning(f"Excel 파일에 '{target_col}'에 해당하는 컬럼을 찾을 수 없습니다.")
                     col_map[target_col] = None # 찾지 못한 경우 None으로 설정

            for _, row in df.iterrows():
                self.excel_data.append({
                    '종목코드': str(row[col_map['종목코드']]) if col_map['종목코드'] and col_map['종목코드'] in row else '',
                    '종목명': str(row[col_map['종목명']]) if col_map['종목명'] and col_map['종목명'] in row else '',
                    '날짜': '', # OCR로 채울 필드는 비워둠
                    '금리': '', # OCR로 채울 필드는 비워둠
                    '상태': '대기 중'
                })
            self.refresh_grid()
            messagebox.showinfo("성공", f"{len(self.excel_data)}행의 데이터를 로드했습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"Excel 파일 로드 중 오류: {e}")
            self.logger.exception("Excel 파일 로드 실패")

    def add_empty_row(self):
        """그리드에 빈 행 추가"""
        self.excel_data.append({'종목코드': '', '종목명': '', '날짜': '', '금리': '', '상태': '대기 중'})
        self.refresh_grid()

    def paste_from_clipboard(self):
        """클립보드에서 데이터 붙여넣기 (탭 또는 줄바꿈 기준)"""
        try:
            clipboard_data = self.clipboard_get()
            lines = clipboard_data.strip().split('\n')
            added_count = 0
            for line in lines:
                parts = line.split('\t') # 탭으로 구분된 데이터 가정
                if len(parts) >= 1 and parts[0].strip(): # 최소한 첫번째 열에 데이터가 있어야 함
                    self.excel_data.append({
                        '종목코드': parts[0].strip() if len(parts) > 0 else '',
                        '종목명': parts[1].strip() if len(parts) > 1 else '',
                        '날짜': '', '금리': '', '상태': '대기 중'
                    })
                    added_count +=1
            if added_count > 0:
                self.refresh_grid()
                messagebox.showinfo("성공", f"{added_count}행을 추가했습니다.")
            else:
                messagebox.showwarning("경고", "붙여넣을 유효한 데이터가 없습니다 (탭으로 구분된 데이터 필요).")
        except tk.TclError:
            messagebox.showerror("오류", "클립보드에 텍스트 데이터가 없습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"붙여넣기 중 오류: {e}")
            self.logger.exception("클립보드 붙여넣기 실패")

    def delete_selected_rows(self):
        """그리드에서 선택된 행 삭제"""
        if not self.grid_tree: return
        selected_items = self.grid_tree.selection()
        if not selected_items:
            messagebox.showwarning("경고", "삭제할 행을 선택해주세요.")
            return
        if not messagebox.askyesno("확인", f"{len(selected_items)}개의 행을 삭제하시겠습니까?"):
            return
        indices_to_delete = sorted([self.grid_tree.index(item) for item in selected_items], reverse=True)
        for index in indices_to_delete:
            if 0 <= index < len(self.excel_data):
                del self.excel_data[index]
        self.refresh_grid()

    def clear_all_data(self):
        """그리드의 모든 데이터 삭제"""
        if self.excel_data and not messagebox.askyesno("확인", "모든 데이터를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다."):
            return
        self.excel_data.clear()
        self.current_processing_index = -1
        self.refresh_grid()

    def copy_selected_rows(self):
        """그리드에서 선택된 행을 클립보드로 복사 (탭으로 구분)"""
        if not self.grid_tree: return
        selected_items = self.grid_tree.selection()
        if not selected_items: return
        copied_data_str = ""
        for item in selected_items:
            index = self.grid_tree.index(item)
            if 0 <= index < len(self.excel_data):
                row = self.excel_data[index]
                copied_data_str += f"{row['종목코드']}\t{row['종목명']}\t{row['날짜']}\t{row['금리']}\t{row['상태']}\n"
        if copied_data_str:
            self.clipboard_clear()
            self.clipboard_append(copied_data_str.strip()) # 마지막 줄바꿈 제거

    def refresh_grid(self):
        """Excel 그리드 내용 새로고침"""
        if not self.grid_tree: return
        for item in self.grid_tree.get_children(): self.grid_tree.delete(item)
        for i, row in enumerate(self.excel_data):
            tags = []
            if i == self.current_processing_index: tags.append('processing')
            elif row['상태'] == '완료': tags.append('completed')
            elif '오류' in row['상태'] or '실패' in row['상태'] or '없음' in row['상태']: tags.append('error') # 다양한 오류 상태 처리
            self.grid_tree.insert('', 'end', values=(row['종목코드'], row['종목명'], row['날짜'], row['금리'], row['상태']), tags=tags)

        self.grid_tree.tag_configure('processing', background=self.colors.get('warning', '#FFF3CD'), foreground=self.colors.get('dark', '#856404'))
        self.grid_tree.tag_configure('completed', background=self.colors.get('success', '#D4EDDA'), foreground=self.colors.get('dark', '#155724'))
        self.grid_tree.tag_configure('error', background=self.colors.get('danger', '#F8D7DA'), foreground=self.colors.get('white', '#721C24')) # 오류 텍스트 색상 변경
        self.update_grid_status()

    def update_grid_status(self):
        """그리드 하단 상태 레이블 업데이트"""
        if not hasattr(self, 'grid_status_label'): return
        total = len(self.excel_data)
        completed = sum(1 for row in self.excel_data if row['상태'] == '완료')
        waiting = sum(1 for row in self.excel_data if row['상태'] == '대기 중')
        errors = sum(1 for row in self.excel_data if '오류' in row['상태'] or '실패' in row['상태'] or '없음' in row['상태'])
        self.grid_status_label.config(text=f"총 {total}행 | 완료: {completed} | 대기: {waiting} | 오류: {errors}")
        progress = (completed / total * 100) if total > 0 else 0
        if hasattr(self, 'grid_progress_label'): self.grid_progress_label.config(text=f"진행률: {progress:.1f}%")

    def on_cell_double_click(self, event):
        """그리드 셀 더블 클릭 시 편집 대화상자 호출"""
        if not self.grid_tree: return
        item = self.grid_tree.identify_row(event.y) # 클릭된 행 식별
        column = self.grid_tree.identify_column(event.x) # 클릭된 열 식별
        if not item or not column : return

        col_index = int(column.replace('#','')) -1
        col_name = self.grid_tree['columns'][col_index]
        row_index = self.grid_tree.index(item)

        if not (0 <= row_index < len(self.excel_data)): return
        current_value = self.excel_data[row_index].get(col_name, "")

        # 간단한 입력 대화상자 사용
        new_value = simpledialog.askstring(f"{col_name} 편집", f"새로운 값을 입력하세요 (현재: {current_value}):", parent=self)
        if new_value is not None: # 사용자가 취소하지 않은 경우
            self.excel_data[row_index][col_name] = new_value
            self.refresh_grid()

    def show_context_menu(self, event):
        """그리드 우클릭 컨텍스트 메뉴 표시"""
        if not self.grid_tree: return
        context_menu = tk.Menu(self, tearoff=0)
        context_menu.add_command(label="➕ 행 추가", command=self.add_empty_row)
        context_menu.add_command(label="🗑️ 선택 행 삭제", command=self.delete_selected_rows)
        context_menu.add_separator()
        context_menu.add_command(label="📋 선택 행 복사", command=self.copy_selected_rows)
        context_menu.add_command(label="📝 클립보드에서 붙여넣기", command=self.paste_from_clipboard)
        context_menu.add_separator()
        context_menu.add_command(label="🧹 전체 데이터 삭제", command=self.clear_all_data)
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def export_grid_to_excel(self):
        """현재 그리드 데이터를 새 Excel 파일로 저장"""
        if not self.excel_data:
            self.message_queue.put(("log", "내보낼 데이터가 없습니다."))
            return

        input_file = self.input_excel_path.get().strip()
        output_dir = self.output_folder_path.get().strip()
        base_name = os.path.basename(input_file) if input_file else "ocr_results"
        new_file_name = os.path.splitext(base_name)[0] + '_updated.xlsx'
        new_file_path = os.path.join(output_dir, new_file_name)

        try:
            df_export = pd.DataFrame(self.excel_data)
            # 필요한 컬럼만 선택하거나 순서 지정 가능
            df_export = df_export[['종목코드', '종목명', '날짜', '금리', '상태']]
            with pd.ExcelWriter(new_file_path, engine='openpyxl') as writer:
                df_export.to_excel(writer, sheet_name='OCR_Results', index=False)
            self.message_queue.put(("log", f"결과 Excel 파일 저장 완료: {new_file_path}"))
        except Exception as e:
            self.message_queue.put(("error", f"Excel 파일 저장 실패: {e}"))
            self.logger.exception("Excel 파일 저장 중 예외 발생")


    def generate_ocr_summary(self, processed_count, total_items):
        """OCR 처리 결과 요약 메시지 생성"""
        date_success = sum(1 for row in self.excel_data if row.get('날짜','').strip() and row['상태'] == '완료')
        rate_success = sum(1 for row in self.excel_data if row.get('금리','').strip() and row['상태'] == '완료')
        # processed_count는 실제 성공적으로 처리된 항목 수 (날짜 또는 금리 중 하나라도 인식 성공)
        # 여기서는 status가 '완료'인 항목을 기준으로 함.
        actual_processed_for_stats = sum(1 for row in self.excel_data if row['상태'] == '완료')

        date_accuracy = (date_success / actual_processed_for_stats * 100) if actual_processed_for_stats > 0 else 0
        rate_accuracy = (rate_success / actual_processed_for_stats * 100) if actual_processed_for_stats > 0 else 0

        summary = f"""📊 OCR 처리 완료!
        ------------------------------------
        총 시도 항목: {total_items}개
        성공적으로 처리된 항목: {actual_processed_for_stats}개
        ------------------------------------
        📅 날짜 인식 성공: {date_success}개 ({date_accuracy:.1f}%)
        💰 금리 인식 성공: {rate_success}개 ({rate_accuracy:.1f}%)
        ------------------------------------
        📁 결과는 그리드 및 Excel 파일로 저장되었습니다.
        📝 상세 로그는 ocr_app.log 파일에서 확인 가능합니다.
        """
        return summary

if __name__ == "__main__":
    app = CheckCaptureOCRApp()
    app.mainloop()
