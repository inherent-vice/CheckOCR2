import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import pandas as pd
import pyperclip
import pyautogui
import time
import os
from PIL import Image, ImageTk
import numpy as np
import cv2
import easyocr  # PaddleOCR 대신 EasyOCR 사용
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
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('ocr_app.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)



############################################
# 통합 설정 관리 시스템
############################################
class UnifiedSettingsManager:
    def __init__(self):
        self.settings_file = "settings.json"
        self.data = self.load_settings()
        
        # 기본 구조 초기화
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
                    return json.load(f)
        except Exception as e:
            print(f"설정 로드 오류: {e}")
        return {}
    
    def save_settings(self):
        """통합 설정 파일 저장"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"설정 저장 오류: {e}")
    
    # 프리셋 관련 메서드
    def save_preset(self, name, settings):
        """프리셋 저장"""
        self.data['presets'][name] = {
            'click_point': settings['click_point'],
            'all_area': settings['all_area'],
            'date_area': settings['date_area'],
            'rate_area': settings['rate_area'],
            'delays': settings['delays'],
            'advanced': settings.get('advanced', {}),
            'created_at': datetime.now().isoformat()
        }
        self.save_settings()
    
    def get_preset_names(self):
        """프리셋 이름 목록 반환"""
        return list(self.data['presets'].keys())
    
    def apply_preset(self, name):
        """프리셋 적용"""
        return self.data['presets'].get(name, None)
    
    def delete_preset(self, name):
        """프리셋 삭제"""
        if name in self.data['presets']:
            del self.data['presets'][name]
            self.save_settings()
    
    # 현재 설정 관련 메서드
    def save_current_settings(self, settings):
        """현재 설정 저장"""
        self.data['current'] = settings
        self.save_settings()
    
    def get_current_settings(self):
        """현재 설정 반환"""
        return self.data.get('current', {})
    
    def _get_default_advanced_settings(self):
        """기본 고급 설정 반환"""
        return {
            # OCR 설정 (데이터에 최적화)
            'ocr_gpu_enabled': False,
            'ocr_confidence_threshold': 0.2,  # 적절한 임계값으로 조정
            'ocr_languages': ['ko', 'en'],  # 한국어+영어 조합으로 숫자 인식 개선
            'ocr_max_attempts': 5,
            'ocr_detail_level': 0,
            
            # 이미지 처리 설정 (모든 전처리 활성화)
            'image_resize_factor': 3,  # 적절한 확대 배율
            'image_denoise_strength': 1,  # 가벼운 노이즈 제거
            'image_contrast_enhancement': True,  # 대비 개선
            'image_sharpening': True,  # 샤프닝
            'image_binarization_method': 'adaptive',  # 적응형 이진화
            'image_manual_threshold': 127,
            'image_morphology_enabled': True,  # 모폴로지 연산
            'image_edge_enhancement': True,  # 에지 강화
            
            # 자동화 설정
            'click_interval': 0.1,
            'thread_count': self._get_optimal_thread_count(),
            
            # 신뢰도 설정 (낮춰서 더 관대하게)
            'min_date_confidence': 0.15,  # 적절한 날짜 신뢰도
            'min_rate_confidence': 0.15,  # 적절한 금리 신뢰도
        }
    
    def _get_optimal_thread_count(self):
        """현재 PC에 최적화된 스레드 개수 계산"""
        import os
        cpu_count = os.cpu_count() or 4  # CPU 코어 개수
        # OCR 작업의 특성상 CPU 코어 수와 동일하게 설정 (I/O 대기가 많음)
        optimal_threads = min(max(cpu_count, 2), 8)  # 최소 2개, 최대 8개
        return optimal_threads
    
    # 고급 설정 접근 메서드들
    def get_advanced(self, key, default=None):
        """고급 설정 값 반환"""
        return self.data['advanced'].get(key, default)
    
    def set_advanced(self, key, value):
        """고급 설정 값 설정"""
        self.data['advanced'][key] = value
        self.save_settings()
    
    def reset_advanced_settings(self):
        """고급 설정 초기화"""
        self.data['advanced'] = self._get_default_advanced_settings()
        self.save_settings()

############################################
# 진행 상황 추적기 (확장)
############################################
class ProgressTracker:
    def __init__(self, parent):
        self.parent = parent
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar()
        self.current_item_var = tk.StringVar()
        self.setup_ui()
    
    def setup_ui(self):
        # 프로그레스 프레임 (처음에는 pack하지 않음)
        self.progress_frame = tk.Frame(self.parent)
        
        # 현재 처리 중인 항목
        self.current_label = tk.Label(
            self.progress_frame,
            textvariable=self.current_item_var,
            font=('Arial', 9, 'bold'),
            fg='blue'
        )
        self.current_label.pack(pady=(0, 3))
        
        # 프로그레스 바
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, 
            variable=self.progress_var,
            maximum=100
        )
        self.progress_bar.pack(fill='x', pady=(0, 5))
        
        # 상태 레이블
        self.status_label = tk.Label(
            self.progress_frame,
            textvariable=self.status_var,
            font=('Arial', 9)
        )
        self.status_label.pack()
        
        # 처음에는 숨김
        self.progress_frame.pack_forget()
    
    def show(self):
        """진행 상황 표시"""
        try:
            if self.progress_frame.winfo_exists():
                self.progress_frame.pack(fill='x', padx=5, pady=5)
        except tk.TclError:
            # 윈도우가 파괴되었거나 유효하지 않은 경우 무시
            pass
    
    def hide(self):
        """진행 상황 숨김"""
        try:
            if self.progress_frame.winfo_exists():
                self.progress_frame.pack_forget()
        except tk.TclError:
            # 윈도우가 파괴되었거나 유효하지 않은 경우 무시
            pass
    
    def update_progress(self, current, total, status_text, current_item=""):
        """진행 상황 업데이트"""
        if total > 0:
            progress = (current / total) * 100
            self.progress_var.set(progress)
            self.status_var.set(f"{status_text} ({current}/{total}) - {progress:.1f}%")
            self.current_item_var.set(current_item)

############################################
# 간소화된 작업 제어 시스템
############################################
class WorkController:
    def __init__(self):
        self.is_stopped = False
        self.is_running = False
        self.skip_current = False
        self.current_item = ""
        
    def start_work(self):
        """작업 시작"""
        self.is_stopped = False
        self.is_running = True
        self.skip_current = False
    
    def stop_work(self):
        """작업 중단"""
        self.is_stopped = True
        self.is_running = False
        return "작업이 중단되었습니다"
    
    def skip_current_item(self):
        """현재 항목 건너뛰기"""
        self.skip_current = True
        return f"현재 항목 '{self.current_item}'을 건너뛰었습니다"
    
    def reset(self):
        """컨트롤러 초기화"""
        self.is_stopped = False
        self.is_running = False
        self.skip_current = False
        self.current_item = ""



############################################
# 영역 시각화 오버레이 창
############################################
class AreaVisualizationOverlay(tk.Toplevel):
    """영역들을 화면에 시각화하여 표시하는 오버레이"""
    def __init__(self, master, areas_info, auto_close=True):
        super().__init__(master)
        self.master = master
        self.areas_info = areas_info
        self.auto_close = auto_close
        
        # 전체 화면으로 만들기
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.configure(bg="black")
        self.attributes("-alpha", 0.7)
        
        # 캔버스
        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 영역들 그리기
        self.draw_areas()
        
        # 자동 종료 설정
        if auto_close:
            self.after(3000, self.destroy)  # 3초 후 자동 종료
        
        # ESC 키로 종료
        self.bind("<KeyPress>", self.on_key_press)
        self.focus_set()
    
    def draw_areas(self):
        """설정된 영역들을 그리기"""
        colors = ["red", "blue", "green", "yellow", "orange"]
        labels = ["클릭 포인트", "전체 영역", "날짜 영역", "금리 영역"]
        
        # 클릭 포인트 그리기
        if "click_point" in self.areas_info:
            x, y = self.areas_info["click_point"]
            r = 10
            self.canvas.create_oval(x-r, y-r, x+r, y+r, 
                                  fill=colors[0], outline="white", width=3)
            self.canvas.create_text(x, y-25, text=labels[0], 
                                  fill="white", font=("Arial", 12, "bold"))
        
        # 사각형 영역들 그리기
        area_keys = ["all_area", "date_area", "rate_area"]
        for i, key in enumerate(area_keys):
            if key in self.areas_info:
                x1, y1, x2, y2 = self.areas_info[key]
                color = colors[i+1]
                # 사각형 그리기
                self.canvas.create_rectangle(x1, y1, x2, y2, 
                                           outline=color, width=4, fill="")
                # 레이블 추가
                center_x = (x1 + x2) // 2
                center_y = y1 - 20 if y1 > 30 else y2 + 20
                self.canvas.create_text(center_x, center_y, text=labels[i+1],
                                      fill=color, font=("Arial", 14, "bold"))
                # 크기 정보 추가
                width = x2 - x1
                height = y2 - y1
                size_text = f"{width}x{height}"
                self.canvas.create_text(center_x, center_y + 20, text=size_text,
                                      fill="white", font=("Arial", 10))
        
        # 안내 메시지
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        info_text = "설정된 영역들이 표시됩니다"
        if self.auto_close:
            info_text += " (3초 후 자동 종료)"
        info_text += " | ESC: 종료"
        
        self.canvas.create_text(screen_width//2, 50, text=info_text,
                              fill="white", font=("Arial", 16, "bold"))
    
    def on_key_press(self, event):
        """키 입력 처리"""
        if event.keysym == "Escape":
            self.destroy()



############################################
# 드래그로 좌표를 지정하는 Overlay Window #
############################################
class DragCaptureOverlay(tk.Toplevel):
    """
    전 화면에 반투명 창을 띄워서
    마우스 드래그로 영역(x1, y1, x2, y2)을 지정할 수 있는 클래스.
    color: 드래그 박스 색상 (예: "red", "blue", "white")
    """
    def __init__(self, master=None, color="red"):
        super().__init__(master)
        self.master = master
        self.color = color

        # 전체 화면으로 만들기
        self.attributes("-fullscreen", True)
        # 항상 위에 표시
        self.attributes("-topmost", True)
        # 배경색 + 투명도 설정
        self.configure(bg="black")
        self.attributes("-alpha", 0.3)

        # 캔버스
        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 드래그 시작점
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        

        # 이벤트 바인딩
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

        # 최종 좌표
        self.x1, self.y1, self.x2, self.y2 = None, None, None, None

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        # 사각형 초기화
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline=self.color, width=2
        )

    def on_move_press(self, event):
        # 마우스 드래그 중 갱신
        curX, curY = (event.x, event.y)
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, curX, curY)

    def on_button_release(self, event):
        # 드래그 끝
        end_x, end_y = (event.x, event.y)
        self.x1 = min(self.start_x, end_x)
        self.y1 = min(self.start_y, end_y)
        self.x2 = max(self.start_x, end_x)
        self.y2 = max(self.start_y, end_y)
        self.destroy()

############################################
# 포인터 한 번 클릭으로 좌표를 지정하는 Overlay
############################################
class PointCaptureOverlay(tk.Toplevel):
    """
    전 화면에 반투명 창을 띄워서
    마우스 한 번 클릭(x, y)을 지정할 수 있는 클래스.
    color: 마우스 클릭 시 표시할 점의 색상(옵션)
    """
    def __init__(self, master=None, color="red"):
        super().__init__(master)
        self.master = master
        self.color = color

        # 전체 화면으로 만들기
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.configure(bg="black")
        self.attributes("-alpha", 0.3)

        # 캔버스
        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 최종 클릭좌표
        self.click_x = None
        self.click_y = None

        # 이벤트 바인딩
        self.canvas.bind("<ButtonPress-1>", self.on_click)

    def on_click(self, event):
        self.click_x = event.x
        self.click_y = event.y
        # 선택 지점을 간단히 표시(원)
        r = 5
        self.canvas.create_oval(
            self.click_x - r, self.click_y - r,
            self.click_x + r, self.click_y + r,
            fill=self.color, outline=self.color
        )
        # 클릭 완료 후 창 닫기
        self.destroy()

############################################
# 메인 GUI + OCR 로직이 결합된 코드
############################################
class CheckCaptureOCRApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("📊 Check Capture OCR V5")
        self.geometry("1400x700")  # 3분할 레이아웃에 맞게 확장
        self.resizable(True, True)  # 크기 조정 가능
        self.minsize(950, 520)  # 최소한의 안정적 크기
        
        # 창을 화면 중앙에 배치
        self.center_window()
        
        # 창 중앙 배치 메서드를 먼저 정의 (아래에서 구현)
        
        # 테마 시스템 초기화 (Material Design 3 기반)
        self.available_themes = {
            'modern_blue': {
                'name': '🔵 모던 블루',
                'primary': '#1976D2', 'secondary': '#42A5F5', 'success': '#4CAF50',
                'warning': '#FF9800', 'danger': '#F44336', 'light': '#F5F5F5',
                'dark': '#212121', 'white': '#FFFFFF', 'accent': '#9C27B0',
                'surface': '#FFFFFF', 'on_surface': '#212121', 'outline': '#79747E'
            },
            'dark_pro': {
                'name': '🌙 다크 프로',
                'primary': '#BB86FC', 'secondary': '#03DAC6', 'success': '#4CAF50',
                'warning': '#FFC107', 'danger': '#CF6679', 'light': '#121212',
                'dark': '#000000', 'white': '#FFFFFF', 'accent': '#03DAC6',
                'surface': '#1E1E1E', 'on_surface': '#E1E1E1', 'outline': '#938F99'
            },
            'elegant_purple': {
                'name': '💜 엘레간트 퍼플',
                'primary': '#6750A4', 'secondary': '#958DA5', 'success': '#4CAF50',
                'warning': '#F57C00', 'danger': '#BA1A1A', 'light': '#FEF7FF',
                'dark': '#21005D', 'white': '#FFFFFF', 'accent': '#D0BCFF',
                'surface': '#FFFBFE', 'on_surface': '#1D1B20', 'outline': '#79747E'
            },
            'green_nature': {
                'name': '🌿 그린 네이처',
                'primary': '#006E26', 'secondary': '#52634F', 'success': '#4CAF50',
                'warning': '#F57C00', 'danger': '#BA1A1A', 'light': '#F6FFF6',
                'dark': '#00210A', 'white': '#FFFFFF', 'accent': '#006E26',
                'surface': '#FEFFFE', 'on_surface': '#1A1C18', 'outline': '#72796F'
            },
            'orange_warm': {
                'name': '🧡 오렌지 웜',
                'primary': '#8F4E00', 'secondary': '#77574B', 'success': '#4CAF50',
                'warning': '#FF8F00', 'danger': '#BA1A1A', 'light': '#FFFBF8',
                'dark': '#2F1500', 'white': '#FFFFFF', 'accent': '#FFB59D',
                'surface': '#FFFBF8', 'on_surface': '#201A16', 'outline': '#837568'
            }
        }
        
        # 관리자 클래스들 초기화 (테마 설정보다 먼저)
        self.settings_manager = UnifiedSettingsManager()
        
        # 현재 테마 설정 (설정에서 불러오거나 기본값)
        saved_theme = self.settings_manager.get_advanced('ui_theme', 'modern_blue')
        self.current_theme = saved_theme if saved_theme in self.available_themes else 'modern_blue'
        self.colors = self.available_themes[self.current_theme].copy()
        
        # 창 아이콘 및 스타일 설정
        self.configure(bg=self.colors['surface'])
        
        # 로깅 설정
        self.logger = setup_logging()
        self.progress_tracker = ProgressTracker(self)
        self.work_controller = WorkController()
        
        # 스레드 통신용 큐
        self.message_queue = queue.Queue()
        self.worker_thread = None

        # ===== 기본값 설정 =====
        self.input_excel_path = tk.StringVar()
        self.output_folder_path = tk.StringVar()

        # -- ClickPoint 기본값 --
        self.click_x = tk.IntVar(value=340)
        self.click_y = tk.IntVar(value=165)

        # -- AllArea 기본값 --
        self.allarea_x1 = tk.IntVar(value=15)
        self.allarea_y1 = tk.IntVar(value=200)
        self.allarea_x2 = tk.IntVar(value=15 + 1830)  # 1845
        self.allarea_y2 = tk.IntVar(value=200 + 670)  # 870

        # -- DateArea 기본값 --
        self.datearea_x1 = tk.IntVar(value=826)
        self.datearea_y1 = tk.IntVar(value=88)
        self.datearea_x2 = tk.IntVar(value=1064)
        self.datearea_y2 = tk.IntVar(value=127)

        # -- RateArea 기본값 --
        self.ratearea_x1 = tk.IntVar(value=1069)
        self.ratearea_y1 = tk.IntVar(value=89)
        self.ratearea_x2 = tk.IntVar(value=1326)
        self.ratearea_y2 = tk.IntVar(value=126)

        # -- 딜레이 기본값 --
        self.paste_delay = tk.DoubleVar(value=0.5)
        self.loading_delay = tk.DoubleVar(value=2.5)
        
        # -- 이미지 저장 옵션 --
        self.save_detail_images = tk.BooleanVar(value=True)
        self.save_image_var = tk.BooleanVar(value=True)  # 상세 이미지 저장 옵션
        
        # -- Excel 그리드 관련 변수들 --
        self.excel_data = []  # [{'종목코드': '', '종목명': '', '날짜': '', '금리': ''}, ...]
        self.current_processing_index = -1  # 현재 처리 중인 행 인덱스
        self.grid_tree = None  # Treeview 위젯 참조

        # -- 고급 설정 변수들 추가 --
        self.confidence_threshold = tk.DoubleVar(value=80.0)
        self.use_gpu = tk.BooleanVar(value=False)
        self.max_threads = tk.IntVar(value=4)
        
        # 이미지 전처리 변수들
        self.apply_sharpening = tk.BooleanVar(value=False)
        self.apply_contrast = tk.BooleanVar(value=True)
        self.apply_denoising = tk.BooleanVar(value=False)
        self.apply_binarization = tk.BooleanVar(value=False)
        self.image_scale_factor = tk.DoubleVar(value=1.0)
        self.image_quality = tk.IntVar(value=95)
        
        # 자동화 설정 변수들
        self.batch_size = tk.IntVar(value=10)
        self.auto_retry = tk.BooleanVar(value=True)
        self.max_retries = tk.IntVar(value=3)
        self.continue_on_error = tk.BooleanVar(value=True)
        
        # 품질 관리 변수들
        self.validate_date_format = tk.BooleanVar(value=True)
        self.validate_rate_range = tk.BooleanVar(value=True)
        self.check_duplicates = tk.BooleanVar(value=False)
        self.generate_accuracy_report = tk.BooleanVar(value=True)
        self.min_accuracy = tk.DoubleVar(value=85.0)
        self.show_quality_score = tk.BooleanVar(value=True)

        # -- 테마 및 UI 변수들 (missing 변수들 추가)
        self.theme_var = tk.StringVar()
        self.log_level_var = tk.StringVar(value="INFO")
        
        # -- 고급 설정 변수들 (NEW!)
        self.lang_var = tk.StringVar(value='ko')
        self.confidence_threshold = tk.DoubleVar(value=75.0)
        self.use_gpu = tk.BooleanVar(value=False)
        self.max_threads = tk.IntVar(value=4)
        
        # 이미지 전처리 변수들
        self.apply_sharpening = tk.BooleanVar(value=False)
        self.apply_contrast = tk.BooleanVar(value=False)
        self.apply_denoising = tk.BooleanVar(value=False)
        self.apply_binarization = tk.BooleanVar(value=False)
        
        # 로그 관련 UI 컴포넌트들 (나중에 생성)
        self.log_text = None
        self.preset_combo = None

        # EasyOCR 초기화 (한 번만)
        self.ocr_reader = None
        self.initialize_ocr()

        self._build_ui()
        self._setup_keyboard_shortcuts()
        
        # 큐 체크 스케줄 시작
        self.check_queue()
        
        # 마지막 설정 자동 로드
        self.load_last_settings()

    def center_window(self):
        """창을 화면 중앙에 배치"""
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # 창 크기 가져오기
        window_width = self.winfo_reqwidth()
        window_height = self.winfo_reqheight()
        
        # 현재 창 크기에 맞게 설정
        window_width = 1000
        window_height = 580
        
        # 중앙 좌표 계산
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # 창 위치 설정
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")

    def initialize_ocr(self):
        """EasyOCR 초기화 - 개선된 설정"""
        try:
            self.logger.info("EasyOCR 초기화 중...")
            gpu_enabled = self.settings_manager.get_advanced('ocr_gpu_enabled', False)
            # 한국어와 영어를 모두 지원하여 숫자 인식 개선
            languages = self.settings_manager.get_advanced('ocr_languages', ['ko', 'en'])
            self.ocr_reader = easyocr.Reader(languages, gpu=gpu_enabled)
            self.logger.info(f"EasyOCR 초기화 완료 - 언어: {languages}, GPU: {gpu_enabled}")
        except Exception as e:
            self.logger.error(f"EasyOCR 초기화 실패: {e}")
            # 폴백: 영어만으로 재시도
            try:
                self.logger.info("한국어 모델 실패, 영어만으로 재시도...")
                self.ocr_reader = easyocr.Reader(['en'], gpu=False)
                self.logger.info("EasyOCR 영어 모드로 초기화 완료")
            except Exception as e2:
                messagebox.showerror("오류", f"OCR 엔진 초기화 실패: {e2}")
                raise

    def _setup_keyboard_shortcuts(self):
        """키보드 단축키 설정"""
        # 전역 키보드 바인딩을 위해 focus_set과 bind_all 사용
        self.focus_set()
        self.bind_all('<Control-s>', lambda e: self.quick_save_settings())
        self.bind_all('<Control-l>', lambda e: self.load_last_settings())
        self.bind_all('<F5>', lambda e: self.handle_f5_key())
        self.bind_all('<Escape>', lambda e: self.stop_processing())
        self.bind_all('<F1>', lambda e: self.show_shortcuts())

    def handle_f5_key(self):
        """F5 키 처리 - 실행 중이면 중단, 아니면 실행"""
        if self.work_controller.is_running:
            self.stop_processing()
        else:
            self.run_ocr_process()



    def check_queue(self):
        """큐에서 메시지 체크하여 GUI 업데이트"""
        try:
            while True:
                msg_type, data = self.message_queue.get_nowait()
                
                if msg_type == "progress":
                    # progress 데이터 형식 확인 및 처리
                    if len(data) == 4:
                        current, total, status, current_item = data
                        self.progress_tracker.update_progress(current, total, status, current_item)
                        self.work_controller.current_item = current_item
                    elif len(data) == 3:
                        current, total, status = data
                        self.progress_tracker.update_progress(current, total, status, "")
                        self.work_controller.current_item = ""
                    else:
                        self.logger.warning(f"잘못된 progress 데이터 형식: {data}")
                elif msg_type == "log":
                    self.logger.info(data)
                    self.update_log_display(data)
                elif msg_type == "error":
                    self.logger.error(data)
                    self.update_log_display(f"오류: {data}")
                elif msg_type == "status":
                    self.update_status_display(data)
                elif msg_type == "complete":
                    self._on_work_complete(data)
                elif msg_type == "stopped":
                    self._on_work_stopped()
                elif msg_type == "grid_update":
                    self._handle_grid_update(data)

                    
        except queue.Empty:
            pass
        
        # 100ms마다 큐 체크
        self.after(100, self.check_queue)

    def _build_ui(self):
        """안정적인 UI 빌드 시스템"""
        # 메뉴바
        self._create_menu()
        
        # 상단 테마/설정 툴바
        self._create_simple_toolbar()
        
        # 메인 컨테이너 (극도로 컴팩트)
        main_container = tk.Frame(self, bg=self.colors['surface'])
        main_container.pack(fill='both', expand=True, padx=3, pady=2)  # 패딩 극소화
        
        # 좌측: 설정 영역 (35%)
        left_panel = tk.Frame(main_container, bg=self.colors['surface'], width=350)
        left_panel.pack(side='left', fill='y', padx=(0, 2))
        left_panel.pack_propagate(False)
        
        # 중앙: Excel 그리드 영역 (35%)
        center_panel = tk.Frame(main_container, bg=self.colors['surface'])
        center_panel.pack(side='left', fill='both', expand=True, padx=2)
        
        # 우측: 프리셋/액션 영역 (30%)
        right_panel = tk.Frame(main_container, bg=self.colors['surface'], width=280)
        right_panel.pack(side='right', fill='y', padx=(2, 0))
        right_panel.pack_propagate(False)
        
        # 좌측 패널 구성
        self._create_stable_left_panel(left_panel)
        
        # 중앙 패널 구성 (Excel 그리드)
        self._create_center_excel_grid(center_panel)
        
        # 우측 패널 구성
        self._create_stable_right_panel(right_panel)
        
        # 하단 실행 버튼
        self._create_stable_bottom_bar()

    def _create_center_excel_grid(self, parent):
        """중앙 Excel 그리드 생성"""
        # 그리드 섹션 프레임
        grid_section = self._create_section_frame(parent, "📊 Excel 데이터 그리드")
        
        # 상단 컨트롤 바
        control_frame = tk.Frame(grid_section, bg=self.colors['white'])
        control_frame.pack(fill='x', pady=(0, 5))
        
        # 좌측 버튼들
        left_controls = tk.Frame(control_frame, bg=self.colors['white'])
        left_controls.pack(side='left', fill='x', expand=True)
        
        # Excel 로드 버튼
        tk.Button(left_controls, text="📁 Excel 로드", command=self.load_excel_to_grid,
                 font=('Segoe UI', 9), bg=self.colors['primary'], fg='white',
                 relief='flat', cursor='hand2').pack(side='left', padx=(0, 5))
        
        # 행 추가 버튼
        tk.Button(left_controls, text="➕ 행 추가", command=self.add_empty_row,
                 font=('Segoe UI', 9), bg=self.colors['success'], fg='white',
                 relief='flat', cursor='hand2').pack(side='left', padx=(0, 5))
        
        # 붙여넣기 버튼
        tk.Button(left_controls, text="📋 붙여넣기", command=self.paste_from_clipboard,
                 font=('Segoe UI', 9), bg=self.colors['secondary'], fg='white',
                 relief='flat', cursor='hand2').pack(side='left', padx=(0, 5))
        
        # 우측 버튼들
        right_controls = tk.Frame(control_frame, bg=self.colors['white'])
        right_controls.pack(side='right')
        
        # 선택 삭제 버튼
        tk.Button(right_controls, text="🗑️ 삭제", command=self.delete_selected_rows,
                 font=('Segoe UI', 9), bg=self.colors['danger'], fg='white',
                 relief='flat', cursor='hand2').pack(side='right', padx=(5, 0))
        
        # 전체 클리어 버튼
        tk.Button(right_controls, text="🧹 전체삭제", command=self.clear_all_data,
                 font=('Segoe UI', 9), bg=self.colors['warning'], fg='white',
                 relief='flat', cursor='hand2').pack(side='right', padx=(5, 0))
        
        # Treeview 프레임 (스크롤바 포함)
        tree_frame = tk.Frame(grid_section, bg=self.colors['white'])
        tree_frame.pack(fill='both', expand=True)
        
        # Treeview 생성
        columns = ('종목코드', '종목명', '날짜', '금리', '상태')
        self.grid_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=12)
        
        # 열 헤더 설정
        self.grid_tree.heading('종목코드', text='종목코드')
        self.grid_tree.heading('종목명', text='종목명')
        self.grid_tree.heading('날짜', text='날짜')
        self.grid_tree.heading('금리', text='금리')
        self.grid_tree.heading('상태', text='상태')
        
        # 열 너비 설정
        self.grid_tree.column('종목코드', width=80, anchor='center')
        self.grid_tree.column('종목명', width=120, anchor='center')
        self.grid_tree.column('날짜', width=100, anchor='center')
        self.grid_tree.column('금리', width=80, anchor='center')
        self.grid_tree.column('상태', width=100, anchor='center')
        
        # 스크롤바 추가
        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.grid_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.grid_tree.xview)
        self.grid_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # 레이아웃
        self.grid_tree.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # 더블클릭 이벤트 바인딩 (편집용)
        self.grid_tree.bind('<Double-1>', self.on_cell_double_click)
        
        # 우클릭 컨텍스트 메뉴
        self.grid_tree.bind('<Button-3>', self.show_context_menu)
        
        # 키보드 단축키
        self.grid_tree.bind('<Delete>', lambda e: self.delete_selected_rows())
        self.grid_tree.bind('<Control-c>', lambda e: self.copy_selected_rows())
        self.grid_tree.bind('<Control-v>', lambda e: self.paste_from_clipboard())
        
        # 하단 상태 표시
        status_frame = tk.Frame(grid_section, bg=self.colors['white'])
        status_frame.pack(fill='x', pady=(5, 0))
        
        self.grid_status_label = tk.Label(status_frame, text="총 0행 | 처리 완료: 0행 | 대기 중: 0행",
                                         font=('Segoe UI', 9), bg=self.colors['white'], fg=self.colors['on_surface'])
        self.grid_status_label.pack(side='left')
        
        # 진행률 표시
        self.grid_progress_label = tk.Label(status_frame, text="진행률: 0%",
                                           font=('Segoe UI', 9, 'bold'), bg=self.colors['white'], fg=self.colors['primary'])
        self.grid_progress_label.pack(side='right')

    def _create_simple_toolbar(self):
        """극도로 컴팩트한 상단 툴바"""
        toolbar = tk.Frame(self, bg=self.colors['primary'], height=35)  # 50→35로 축소
        toolbar.pack(fill='x')
        toolbar.pack_propagate(False)
        
        # 왼쪽: 앱 타이틀 (축소)
        title_label = tk.Label(toolbar, text="📊 Check OCR V5", 
                              font=('Segoe UI', 11, 'bold'), bg=self.colors['primary'], fg='white')  # 14→11, 제목 축소
        title_label.pack(side='left', padx=8, pady=6)  # 20→8, 12→6으로 축소
        
        # 오른쪽: 테마 선택 (축소)
        controls_frame = tk.Frame(toolbar, bg=self.colors['primary'])
        controls_frame.pack(side='right', padx=8, pady=4)  # 20→8, 8→4로 축소
        
        tk.Label(controls_frame, text="테마:", font=('Segoe UI', 9),  # 10→9로 축소
                bg=self.colors['primary'], fg='white').pack(side='left', padx=(0, 3))  # 5→3으로 축소
        
        self.theme_combo = ttk.Combobox(controls_frame, textvariable=self.theme_var, 
                                       width=10, state="readonly", font=('Segoe UI', 8))  # 12→10, 9→8로 축소
        self.theme_combo['values'] = [theme['name'] for theme in self.available_themes.values()]
        self.theme_combo.set(self.available_themes[self.current_theme]['name'])
        self.theme_combo.pack(side='left')
        self.theme_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_theme())

    def _create_stable_left_panel(self, parent):
        """안정적인 좌측 설정 패널"""
        # 스크롤 가능한 영역
        canvas = tk.Canvas(parent, bg=self.colors['surface'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['surface'])
        
        # 스크롤 설정
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 마우스 휠 스크롤 지원
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 설정 섹션들
        self._create_file_section(scrollable_frame)
        self._create_coordinates_section(scrollable_frame)
        self._create_timing_section(scrollable_frame)
        self._create_options_section(scrollable_frame)
        self._create_advanced_section(scrollable_frame)  # 고급 설정 추가

    def _create_stable_right_panel(self, parent):
        """안정적인 우측 패널 (프리셋/액션)"""
        # 프리셋 섹션
        self._create_preset_section(parent)
        
        # 미리보기 섹션
        self._create_preview_section(parent)
        
        # 로그 섹션
        self._create_log_section(parent)

    def _create_stable_bottom_bar(self):
        """극도로 컴팩트한 하단 실행 바"""
        bottom_frame = tk.Frame(self, bg=self.colors['surface'], height=45)  # 60→45로 축소
        bottom_frame.pack(fill='x', side='bottom', pady=3)  # 8→3으로 축소
        bottom_frame.pack_propagate(False)
        
        # 버튼 컨테이너
        button_container = tk.Frame(bottom_frame, bg=self.colors['surface'])
        button_container.pack(expand=True, fill='both')
        
        # 메인 실행 버튼 (극소형)
        self.run_btn = tk.Button(button_container, text="🚀 OCR 시작 (F5)", command=self.run_ocr_process,
                               font=('Segoe UI', 11, 'bold'), bg=self.colors['success'], fg='white',  # 13→11으로 축소
                               relief='flat', cursor='hand2', height=1, width=20)  # 25→20으로 축소
        self.run_btn.pack(side='left', expand=True, fill='x', padx=(6, 3))  # 패딩 극소화
        
        # 중단 버튼 (극소형)
        self.stop_btn = tk.Button(button_container, text="⏹️ 중단", command=self.stop_processing,
                                font=('Segoe UI', 11, 'bold'), bg=self.colors['danger'], fg='white',  # 13→11으로 축소
                                relief='flat', cursor='hand2', height=1, width=10)  # 12→10으로 축소
        self.stop_btn.pack(side='right', expand=True, fill='x', padx=(3, 6))  # 패딩 극소화

    def _create_file_section(self, parent):
        """파일 설정 섹션"""
        section = self._create_section_frame(parent, "📁 파일 설정")
        
        # Excel 파일 (극소형)
        excel_frame = tk.Frame(section, bg=self.colors['white'])
        excel_frame.pack(fill='x', pady=(0, 3))  # 6→3으로 축소
        
        tk.Label(excel_frame, text="Excel 입력 파일:", font=('Segoe UI', 9, 'bold'),  # 10→9로 축소
                bg=self.colors['white']).pack(anchor='w')
        
        excel_input = tk.Frame(excel_frame, bg=self.colors['white'])
        excel_input.pack(fill='x', pady=(2, 0))  # 3→2로 축소
        
        self.excel_entry = tk.Entry(excel_input, textvariable=self.input_excel_path, 
                                   font=('Segoe UI', 9), relief='solid', bd=1)  # 10→9로 축소
        self.excel_entry.pack(side='left', fill='x', expand=True, padx=(0, 3))  # 5→3으로 축소
        
        tk.Button(excel_input, text="찾기", command=self.browse_input_excel,
                 font=('Segoe UI', 8), bg=self.colors['secondary'], fg='white',  # 9→8로 축소
                 relief='flat', cursor='hand2', width=6).pack(side='right')  # 8→6으로 축소
        
        # 출력 폴더
        output_frame = tk.Frame(section, bg=self.colors['white'])
        output_frame.pack(fill='x')
        
        tk.Label(output_frame, text="출력 폴더:", font=('Segoe UI', 9, 'bold'),  # 10→9로 축소
                bg=self.colors['white']).pack(anchor='w')
        
        output_input = tk.Frame(output_frame, bg=self.colors['white'])
        output_input.pack(fill='x', pady=(2, 0))  # 3→2로 축소
        
        self.output_entry = tk.Entry(output_input, textvariable=self.output_folder_path, 
                                    font=('Segoe UI', 9), relief='solid', bd=1)  # 10→9로 축소
        self.output_entry.pack(side='left', fill='x', expand=True, padx=(0, 3))  # 5→3으로 축소
        
        tk.Button(output_input, text="찾기", command=self.browse_output_folder,
                 font=('Segoe UI', 8), bg=self.colors['secondary'], fg='white',  # 9→8로 축소
                 relief='flat', cursor='hand2', width=6).pack(side='right')  # 8→6으로 축소

    def _create_coordinates_section(self, parent):
        """좌표 설정 섹션"""
        section = self._create_section_frame(parent, "🎯 좌표 및 영역 설정")
        
        # 클릭 포인트 (컴팩트)
        click_frame = tk.Frame(section, bg=self.colors['white'])
        click_frame.pack(fill='x', pady=(0, 8))  # 15→8로 축소
        
        tk.Label(click_frame, text="클릭 포인트:", font=('Segoe UI', 10, 'bold'), 
                bg=self.colors['white']).pack(anchor='w')
        
        click_input = tk.Frame(click_frame, bg=self.colors['white'])
        click_input.pack(fill='x', pady=(3, 0))  # 5→3으로 축소
        
        tk.Label(click_input, text="X:", font=('Segoe UI', 9), 
                bg=self.colors['white']).pack(side='left')
        tk.Entry(click_input, textvariable=self.click_x, font=('Segoe UI', 9), 
                width=8, relief='solid', bd=1).pack(side='left', padx=(2, 10))
        
        tk.Label(click_input, text="Y:", font=('Segoe UI', 9), 
                bg=self.colors['white']).pack(side='left')
        tk.Entry(click_input, textvariable=self.click_y, font=('Segoe UI', 9), 
                width=8, relief='solid', bd=1).pack(side='left', padx=(2, 10))
        
        tk.Button(click_input, text="위치지정", command=self.relocate_clickpoint,
                 font=('Segoe UI', 9), bg=self.colors['accent'], fg='white',
                 relief='flat', cursor='hand2', width=10).pack(side='right')
        
        # 영역들
        areas = [
            ("전체 영역", [self.allarea_x1, self.allarea_y1, self.allarea_x2, self.allarea_y2], self.relocate_allarea, self.colors['danger']),
            ("날짜 영역", [self.datearea_x1, self.datearea_y1, self.datearea_x2, self.datearea_y2], self.relocate_datearea, self.colors['primary']),
            ("금리 영역", [self.ratearea_x1, self.ratearea_y1, self.ratearea_x2, self.ratearea_y2], self.relocate_ratearea, self.colors['success'])
        ]
        
        for area_name, vars_list, func, color in areas:
            area_frame = tk.Frame(section, bg=self.colors['white'])
            area_frame.pack(fill='x', pady=(0, 6))  # 10→6으로 축소
            
            tk.Label(area_frame, text=f"{area_name}:", font=('Segoe UI', 10, 'bold'), 
                    bg=self.colors['white']).pack(anchor='w')
            
            coords_frame = tk.Frame(area_frame, bg=self.colors['white'])
            coords_frame.pack(fill='x', pady=(3, 0))  # 5→3으로 축소
            
            for i, (var, label) in enumerate(zip(vars_list, ['X1:', 'Y1:', 'X2:', 'Y2:'])):
                tk.Label(coords_frame, text=label, font=('Segoe UI', 9), 
                        bg=self.colors['white']).pack(side='left')
                tk.Entry(coords_frame, textvariable=var, font=('Segoe UI', 9), 
                        width=6, relief='solid', bd=1).pack(side='left', padx=(2, 8))
            
            tk.Button(coords_frame, text="영역지정", command=func,
                     font=('Segoe UI', 9), bg=color, fg='white',
                     relief='flat', cursor='hand2', width=10).pack(side='right')

    def _create_timing_section(self, parent):
        """타이밍 설정 섹션"""
        section = self._create_section_frame(parent, "⏱️ 타이밍 설정")
        
        timing_grid = tk.Frame(section, bg=self.colors['white'])
        timing_grid.pack(fill='x')
        
        # 좌측: 붙여넣기 딜레이
        left_timing = tk.Frame(timing_grid, bg=self.colors['white'])
        left_timing.pack(side='left', fill='x', expand=True, padx=(0, 15))
        
        tk.Label(left_timing, text="붙여넣기 딜레이:", font=('Segoe UI', 10, 'bold'), 
                bg=self.colors['white']).pack(anchor='w')
        
        paste_input = tk.Frame(left_timing, bg=self.colors['white'])
        paste_input.pack(fill='x', pady=(5, 0))
        
        tk.Entry(paste_input, textvariable=self.paste_delay, font=('Segoe UI', 10), 
                width=8, relief='solid', bd=1).pack(side='left', padx=(0, 5))
        tk.Label(paste_input, text="초", font=('Segoe UI', 10), 
                bg=self.colors['white']).pack(side='left')
        
        # 우측: 로딩 딜레이
        right_timing = tk.Frame(timing_grid, bg=self.colors['white'])
        right_timing.pack(side='left', fill='x', expand=True)
        
        tk.Label(right_timing, text="로딩 딜레이:", font=('Segoe UI', 10, 'bold'), 
                bg=self.colors['white']).pack(anchor='w')
        
        loading_input = tk.Frame(right_timing, bg=self.colors['white'])
        loading_input.pack(fill='x', pady=(5, 0))
        
        tk.Entry(loading_input, textvariable=self.loading_delay, font=('Segoe UI', 10), 
                width=8, relief='solid', bd=1).pack(side='left', padx=(0, 5))
        tk.Label(loading_input, text="초", font=('Segoe UI', 10), 
                bg=self.colors['white']).pack(side='left')

    def _create_options_section(self, parent):
        """옵션 설정 섹션"""
        section = self._create_section_frame(parent, "⚙️ 옵션 설정")
        
        # 이미지 저장 옵션
        tk.Checkbutton(section, text="상세 이미지 저장 (영역별 개별 파일)", 
                      variable=self.save_detail_images, font=('Segoe UI', 10),
                      bg=self.colors['white'], selectcolor=self.colors['light']).pack(anchor='w')

    def _create_advanced_section(self, parent):
        """고급 설정 섹션 (컴팩트)"""
        section = self._create_section_frame(parent, "🚀 고급 설정")
        
        # 2열 그리드 레이아웃
        advanced_grid = tk.Frame(section, bg=self.colors['white'])
        advanced_grid.pack(fill='x')
        
        # 좌측 컬럼: OCR 설정
        left_col = tk.Frame(advanced_grid, bg=self.colors['white'])
        left_col.pack(side='left', fill='both', expand=True, padx=(0, 8))
        
        # OCR 언어 설정
        tk.Label(left_col, text="OCR 언어:", font=('Segoe UI', 9, 'bold'), 
                bg=self.colors['white']).pack(anchor='w', pady=(0, 2))
        
        lang_frame = tk.Frame(left_col, bg=self.colors['white'])
        lang_frame.pack(fill='x', pady=(0, 6))
        
        ttk.Combobox(lang_frame, textvariable=self.lang_var, values=['ko', 'en', 'ko+en'], 
                    state="readonly", font=('Segoe UI', 9), width=12).pack(side='left')
        
        # 신뢰도 임계값
        tk.Label(left_col, text="신뢰도 임계값:", font=('Segoe UI', 9, 'bold'), 
                bg=self.colors['white']).pack(anchor='w', pady=(0, 2))
        
        confidence_frame = tk.Frame(left_col, bg=self.colors['white'])
        confidence_frame.pack(fill='x', pady=(0, 6))
        
        tk.Entry(confidence_frame, textvariable=self.confidence_threshold, font=('Segoe UI', 9), 
                width=8, relief='solid', bd=1).pack(side='left', padx=(0, 2))
        tk.Label(confidence_frame, text="%", font=('Segoe UI', 9), 
                bg=self.colors['white']).pack(side='left')
        
        # 우측 컬럼: 성능 설정
        right_col = tk.Frame(advanced_grid, bg=self.colors['white'])
        right_col.pack(side='right', fill='both', expand=True)
        
        # GPU 사용
        tk.Checkbutton(right_col, text="GPU 가속 사용", variable=self.use_gpu,
                      font=('Segoe UI', 9), bg=self.colors['white'],
                      selectcolor=self.colors['light']).pack(anchor='w', pady=(0, 3))
        
        # 멀티스레딩
        thread_frame = tk.Frame(right_col, bg=self.colors['white'])
        thread_frame.pack(fill='x', pady=(0, 3))
        
        tk.Label(thread_frame, text="스레드:", font=('Segoe UI', 9), 
                bg=self.colors['white']).pack(side='left')
        tk.Entry(thread_frame, textvariable=self.max_threads, font=('Segoe UI', 9), 
                width=6, relief='solid', bd=1).pack(side='left', padx=(3, 2))
        tk.Label(thread_frame, text="개", font=('Segoe UI', 9), 
                bg=self.colors['white']).pack(side='left')
        
        # 이미지 전처리 옵션들
        preprocessing_frame = tk.Frame(section, bg=self.colors['white'])
        preprocessing_frame.pack(fill='x', pady=(8, 0))
        
        tk.Label(preprocessing_frame, text="이미지 전처리:", font=('Segoe UI', 9, 'bold'), 
                bg=self.colors['white']).pack(anchor='w', pady=(0, 3))
        
        # 전처리 옵션들을 2열로 배치
        preprocessing_grid = tk.Frame(preprocessing_frame, bg=self.colors['white'])
        preprocessing_grid.pack(fill='x')
        
        # 좌측 전처리 옵션
        left_prep = tk.Frame(preprocessing_grid, bg=self.colors['white'])
        left_prep.pack(side='left', fill='both', expand=True)
        
        tk.Checkbutton(left_prep, text="샤프닝", variable=self.apply_sharpening, font=('Segoe UI', 8),
                      bg=self.colors['white'], selectcolor=self.colors['light']).pack(anchor='w')
        tk.Checkbutton(left_prep, text="명암 조정", variable=self.apply_contrast, font=('Segoe UI', 8),
                      bg=self.colors['white'], selectcolor=self.colors['light']).pack(anchor='w')
        
        # 우측 전처리 옵션
        right_prep = tk.Frame(preprocessing_grid, bg=self.colors['white'])
        right_prep.pack(side='right', fill='both', expand=True)
        
        tk.Checkbutton(right_prep, text="노이즈 제거", variable=self.apply_denoising, font=('Segoe UI', 8),
                      bg=self.colors['white'], selectcolor=self.colors['light']).pack(anchor='w')
        tk.Checkbutton(right_prep, text="이진화", variable=self.apply_binarization, font=('Segoe UI', 8),
                      bg=self.colors['white'], selectcolor=self.colors['light']).pack(anchor='w')

    def _create_preset_section(self, parent):
        """프리셋 관리 섹션"""
        section = self._create_section_frame(parent, "💾 프리셋 관리")
        
        # 저장된 프리셋 적용 (컴팩트)
        tk.Label(section, text="저장된 프리셋:", font=('Segoe UI', 9, 'bold'),  # 10→9로 축소
                bg=self.colors['white']).pack(anchor='w', pady=(0, 3))  # 5→3으로 축소
        
        preset_apply_frame = tk.Frame(section, bg=self.colors['white'])
        preset_apply_frame.pack(fill='x', pady=(0, 8))  # 15→8로 축소
        
        self.preset_combo = ttk.Combobox(preset_apply_frame, font=('Segoe UI', 9),  # 10→9로 축소
                                        state="readonly", width=28)  # 더 넓게
        self.preset_combo.pack(fill='x', pady=(0, 3))  # 5→3으로 축소
        self.update_preset_combo()
        
        preset_buttons = tk.Frame(preset_apply_frame, bg=self.colors['white'])
        preset_buttons.pack(fill='x')
        
        tk.Button(preset_buttons, text="✅ 적용", command=self.apply_selected_preset,
                 font=('Segoe UI', 9, 'bold'), bg=self.colors['success'], fg='white',
                 relief='flat', cursor='hand2', width=8).pack(side='left', padx=(0, 5))
        
        tk.Button(preset_buttons, text="🗑️ 삭제", command=self.delete_selected_preset,
                 font=('Segoe UI', 9, 'bold'), bg=self.colors['danger'], fg='white',
                 relief='flat', cursor='hand2', width=8).pack(side='right')
        
        # 새 프리셋 저장 (컴팩트)
        tk.Label(section, text="새 프리셋 저장:", font=('Segoe UI', 9, 'bold'),  # 10→9로 축소
                bg=self.colors['white']).pack(anchor='w', pady=(8, 3))  # 15→8, 5→3으로 축소
        
        preset_save_frame = tk.Frame(section, bg=self.colors['white'])
        preset_save_frame.pack(fill='x')
        
        self.preset_name_entry = tk.Entry(preset_save_frame, font=('Segoe UI', 9),  # 10→9로 축소
                                         relief='solid', bd=1, width=28)  # 더 넓게
        self.preset_name_entry.pack(fill='x', pady=(0, 3))  # 5→3으로 축소
        self.preset_name_entry.insert(0, "새 프리셋 이름")
        
        tk.Button(preset_save_frame, text="💾 저장", command=self.save_current_preset,
                 font=('Segoe UI', 10, 'bold'), bg=self.colors['warning'], fg='white',
                 relief='flat', cursor='hand2', width=20).pack(fill='x')

    def _create_preview_section(self, parent):
        """미리보기 섹션"""
        section = self._create_section_frame(parent, "👁️ 영역 미리보기")
        
        # 전체 미리보기 (컴팩트)
        tk.Button(section, text="🔍 전체 영역 미리보기", command=self.show_area_preview,
                 font=('Segoe UI', 9, 'bold'), bg=self.colors['danger'], fg='white',  # 10→9로 축소
                 relief='flat', cursor='hand2', width=28, pady=4).pack(fill='x', pady=(0, 6))  # pady 8→4, 10→6으로 축소
        
        # 개별 미리보기 버튼들
        individual_frame = tk.Frame(section, bg=self.colors['white'])
        individual_frame.pack(fill='x')
        
        preview_buttons = [
            ("🔴 전체", 'all', self.colors['danger']),
            ("🔵 날짜", 'date', self.colors['primary']),
            ("⚪ 금리", 'rate', self.colors['success'])
        ]
        
        for text, area_type, color in preview_buttons:
            tk.Button(individual_frame, text=text, 
                     command=lambda t=area_type: self.show_individual_area_preview(t),
                     font=('Segoe UI', 9, 'bold'), bg=color, fg='white',
                     relief='flat', cursor='hand2', width=8).pack(side='left', padx=1, fill='x', expand=True)

    def _create_log_section(self, parent):
        """로그 섹션"""
        section = self._create_section_frame(parent, "📊 상태 및 로그")
        
        # 로그 텍스트 영역
        log_frame = tk.Frame(section, bg=self.colors['white'])
        log_frame.pack(fill='both', expand=True)
        
        self.log_text = tk.Text(log_frame, height=4, font=('Consolas', 7),  # height 6→4, font 8→7로 극소화
                               bg=self.colors['white'], fg=self.colors['on_surface'],
                               relief='solid', bd=1, wrap='word', state='disabled')
        
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")
        
        # 로그 제어 버튼들
        log_controls = tk.Frame(section, bg=self.colors['white'])
        log_controls.pack(fill='x', pady=(6, 0))  # 10→6으로 축소
        
        tk.Button(log_controls, text="🗑️ 지우기", command=self.clear_log,
                 font=('Segoe UI', 9), bg=self.colors['danger'], fg='white',
                 relief='flat', cursor='hand2', width=8).pack(side='left', padx=(0, 5))
        
        tk.Button(log_controls, text="💾 저장", command=self.save_log,
                 font=('Segoe UI', 9), bg=self.colors['success'], fg='white',
                 relief='flat', cursor='hand2', width=8).pack(side='right')

    def _create_section_frame(self, parent, title):
        """극도로 컴팩트한 섹션 프레임 생성"""
        # 섹션 컨테이너 (여백 극소화)
        section_container = tk.Frame(parent, bg=self.colors['surface'])
        section_container.pack(fill='x', pady=(0, 4))  # 8→4로 축소
        
        # 제목 (높이 극소화)
        title_frame = tk.Frame(section_container, bg=self.colors['primary'], height=22)  # 28→22로 축소
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)
        
        tk.Label(title_frame, text=title, font=('Segoe UI', 9, 'bold'),  # 10→9로 축소
                bg=self.colors['primary'], fg='white').pack(side='left', padx=6, pady=3)  # 패딩 극소화
        
        # 내용 영역
        content_frame = tk.Frame(section_container, bg=self.colors['white'], relief='solid', bd=1)
        content_frame.pack(fill='both', expand=True, padx=0)
        
        # 패딩 극소화한 내부 프레임
        inner_frame = tk.Frame(content_frame, bg=self.colors['white'])
        inner_frame.pack(fill='both', expand=True, padx=6, pady=4)  # 10→6, 8→4로 극소화
        
        return inner_frame

    def delete_selected_preset(self):
        """선택된 프리셋 삭제"""
        if not hasattr(self, 'preset_combo') or not self.preset_combo.get():
            messagebox.showwarning("경고", "삭제할 프리셋을 선택해주세요.")
            return
            
        preset_name = self.preset_combo.get()
        if messagebox.askyesno("확인", f"'{preset_name}' 프리셋을 삭제하시겠습니까?"):
            self.settings_manager.delete_preset(preset_name)
            self.update_preset_combo()
            messagebox.showinfo("완료", f"'{preset_name}' 프리셋이 삭제되었습니다.")

    def _create_top_toolbar(self):
        """상단 툴바 - 테마 선택 및 설정 관리"""
        toolbar = tk.Frame(self, bg=self.colors['primary'], height=60)
        toolbar.pack(fill='x', padx=0, pady=0)
        toolbar.pack_propagate(False)
        
        # 왼쪽: 앱 제목
        title_frame = tk.Frame(toolbar, bg=self.colors['primary'])
        title_frame.pack(side='left', fill='y', padx=20)
        
        tk.Label(title_frame, text="📊 Check Capture OCR V5", 
                font=('Segoe UI', 16, 'bold'), bg=self.colors['primary'], 
                fg='white').pack(side='left', anchor='center', expand=True, fill='y')
        
        # 오른쪽: 테마 선택 및 설정 버튼들
        controls_frame = tk.Frame(toolbar, bg=self.colors['primary'])
        controls_frame.pack(side='right', fill='y', padx=20)
        
        # 테마 선택기
        theme_frame = tk.Frame(controls_frame, bg=self.colors['primary'])
        theme_frame.pack(side='left', padx=(0, 15), fill='y')
        
        tk.Label(theme_frame, text="🎨", font=('Segoe UI', 14), 
                bg=self.colors['primary'], fg='white').pack(side='left', padx=(0, 5))
        
        self.theme_var = tk.StringVar()
        self.theme_combo = ttk.Combobox(theme_frame, textvariable=self.theme_var, 
                                       width=15, state="readonly", font=('Segoe UI', 10))
        self.theme_combo['values'] = [theme['name'] for theme in self.available_themes.values()]
        current_theme_name = self.available_themes[self.current_theme]['name']
        self.theme_var.set(current_theme_name)
        self.theme_combo.pack(side='left', padx=(0, 10))
        self.theme_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_theme())
        
        # 설정 관리 버튼들
        btn_save = tk.Button(controls_frame, text="💾", command=self.quick_save_settings,
                           font=('Segoe UI', 12), bg=self.colors['success'], fg='white',
                           relief='flat', cursor='hand2', width=3, height=1)
        btn_save.pack(side='left', padx=2)
        
        btn_load = tk.Button(controls_frame, text="📥", command=self.load_last_settings,
                           font=('Segoe UI', 12), bg=self.colors['secondary'], fg='white',
                           relief='flat', cursor='hand2', width=3, height=1)
        btn_load.pack(side='left', padx=2)
        
        btn_export = tk.Button(controls_frame, text="📤", command=self.export_settings,
                             font=('Segoe UI', 12), bg=self.colors['warning'], fg='white',
                             relief='flat', cursor='hand2', width=3, height=1)
        btn_export.pack(side='left', padx=2)
        
        btn_import = tk.Button(controls_frame, text="📥", command=self.import_settings,
                             font=('Segoe UI', 12), bg=self.colors['accent'], fg='white',
                             relief='flat', cursor='hand2', width=3, height=1)
        btn_import.pack(side='left', padx=2)

    def _configure_notebook_style(self):
        """노트북 탭 스타일 설정"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 탭 스타일 설정
        style.configure('TNotebook.Tab', 
                       background=self.colors['surface'],
                       foreground=self.colors['on_surface'],
                       lightcolor=self.colors['outline'],
                       darkcolor=self.colors['outline'],
                       borderwidth=1,
                       focuscolor='none',
                       padding=[20, 10])
        
        style.map('TNotebook.Tab',
                 background=[('selected', self.colors['primary']),
                           ('active', self.colors['secondary'])],
                 foreground=[('selected', 'white'),
                           ('active', 'white')])

    def _create_bottom_action_bar(self, parent):
        """하단 액션 바"""
        action_bar = tk.Frame(parent, bg=self.colors['surface'], height=80)
        action_bar.pack(fill='x', side='bottom', pady=(15, 0))
        action_bar.pack_propagate(False)
        
        # 메인 실행 버튼
        self.btn_run = tk.Button(action_bar, text="🚀 OCR 처리 시작", command=self.run_ocr_process, 
                               font=('Segoe UI', 16, 'bold'), bg=self.colors['success'], fg='white', 
                               relief='flat', cursor='hand2', height=2,
                               activebackground=self.colors['primary'], activeforeground='white')
        self.btn_run.pack(fill='x', padx=20, pady=10)
        
        # 단축키 안내
        shortcut_label = tk.Label(action_bar, 
                                text="💡 F5: 실행/중단  |  Ctrl+S: 저장  |  Ctrl+L: 불러오기  |  F1: 도움말", 
                                font=('Segoe UI', 10), bg=self.colors['surface'], 
                                fg=self.colors['on_surface'])
        shortcut_label.pack(pady=(0, 5))

    def _create_basic_tab_professional(self):
        """현업 수준의 기본 설정 탭"""
        # 스크롤 가능한 메인 컨테이너
        canvas = tk.Canvas(self.basic_frame, bg=self.colors['surface'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.basic_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['surface'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 최상단: 파일 설정 (가장 중요)
        self._create_professional_card(scrollable_frame, "📁 파일 설정", "파일 경로 및 출력 설정")
        file_card = self._get_last_card_content()
        self._create_file_settings_professional(file_card)
        
        # 좌표 및 영역 설정
        self._create_professional_card(scrollable_frame, "🎯 좌표 및 영역 설정", "클릭 지점과 캡처 영역 정의")
        coord_card = self._get_last_card_content()
        self._create_coordinate_settings_professional(coord_card)
        
        # 타이밍 설정
        self._create_professional_card(scrollable_frame, "⏱️ 타이밍 설정", "딜레이 및 대기 시간 조정")
        timing_card = self._get_last_card_content()
        self._create_timing_settings_professional(timing_card)
        
        # 이미지 옵션
        self._create_professional_card(scrollable_frame, "🖼️ 이미지 저장 옵션", "상세 이미지 저장 설정")
        image_card = self._get_last_card_content()
        self._create_image_options_professional(image_card)
        
        # 프리셋 관리
        self._create_professional_card(scrollable_frame, "🔧 프리셋 관리", "설정 저장 및 불러오기")
        preset_card = self._get_last_card_content()
        self._create_preset_management_professional(preset_card)
        
        # 영역 미리보기 (복구됨!)
        self._create_professional_card(scrollable_frame, "👁️ 영역 미리보기", "설정된 영역 시각화 및 검증")
        preview_card = self._get_last_card_content()
        self._create_area_preview_professional(preview_card)

    def _create_professional_card(self, parent, title, subtitle):
        """현업 수준의 카드 레이아웃 생성"""
        self.last_card = tk.Frame(parent, bg=self.colors['white'], relief='solid', bd=1)
        self.last_card.pack(fill='x', padx=20, pady=10)
        
        # 헤더
        header = tk.Frame(self.last_card, bg=self.colors['primary'], height=50)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        # 제목
        title_label = tk.Label(header, text=title, font=('Segoe UI', 14, 'bold'), 
                              bg=self.colors['primary'], fg='white')
        title_label.pack(side='left', padx=20, pady=12)
        
        # 부제목
        subtitle_label = tk.Label(header, text=subtitle, font=('Segoe UI', 10), 
                                 bg=self.colors['primary'], fg='white')
        subtitle_label.pack(side='right', padx=20, pady=12)
        
        # 컨텐츠 영역
        self.last_card_content = tk.Frame(self.last_card, bg=self.colors['white'])
        self.last_card_content.pack(fill='both', expand=True, padx=25, pady=20)
        
    def _get_last_card_content(self):
        """마지막으로 생성된 카드의 컨텐츠 영역 반환"""
        return self.last_card_content

    def _create_file_settings_professional(self, parent):
        """현업 수준의 파일 설정"""
        # Excel 입력 파일
        excel_frame = tk.Frame(parent, bg=self.colors['white'])
        excel_frame.pack(fill='x', pady=(0, 15))
        
        tk.Label(excel_frame, text="📊 Excel 입력 파일", font=('Segoe UI', 12, 'bold'), 
                bg=self.colors['white'], fg=self.colors['on_surface']).pack(anchor='w')
        
        excel_input_frame = tk.Frame(excel_frame, bg=self.colors['white'])
        excel_input_frame.pack(fill='x', pady=(8, 0))
        
        self.excel_entry = tk.Entry(excel_input_frame, textvariable=self.input_excel_path, 
                                   font=('Segoe UI', 11), relief='solid', bd=1)
        self.excel_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        btn_browse_excel = tk.Button(excel_input_frame, text="📂 찾아보기", command=self.browse_input_excel,
                                   font=('Segoe UI', 10, 'bold'), bg=self.colors['secondary'], fg='white',
                                   relief='flat', cursor='hand2', padx=20, pady=8)
        btn_browse_excel.pack(side='right')
        
        # 출력 폴더
        output_frame = tk.Frame(parent, bg=self.colors['white'])
        output_frame.pack(fill='x')
        
        tk.Label(output_frame, text="📁 출력 폴더", font=('Segoe UI', 12, 'bold'), 
                bg=self.colors['white'], fg=self.colors['on_surface']).pack(anchor='w')
        
        output_input_frame = tk.Frame(output_frame, bg=self.colors['white'])
        output_input_frame.pack(fill='x', pady=(8, 0))
        
        self.output_entry = tk.Entry(output_input_frame, textvariable=self.output_folder_path, 
                                    font=('Segoe UI', 11), relief='solid', bd=1)
        self.output_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        btn_browse_output = tk.Button(output_input_frame, text="📂 찾아보기", command=self.browse_output_folder,
                                    font=('Segoe UI', 10, 'bold'), bg=self.colors['secondary'], fg='white',
                                    relief='flat', cursor='hand2', padx=20, pady=8)
        btn_browse_output.pack(side='right')

    def _create_coordinate_settings_professional(self, parent):
        """현업 수준의 좌표 설정"""
        # 클릭 포인트
        click_frame = tk.Frame(parent, bg=self.colors['white'])
        click_frame.pack(fill='x', pady=(0, 20))
        
        tk.Label(click_frame, text="🎯 클릭 포인트", font=('Segoe UI', 12, 'bold'), 
                bg=self.colors['white'], fg=self.colors['on_surface']).pack(anchor='w')
        
        click_input_frame = tk.Frame(click_frame, bg=self.colors['white'])
        click_input_frame.pack(fill='x', pady=(8, 0))
        
        tk.Label(click_input_frame, text="X:", font=('Segoe UI', 10), 
                bg=self.colors['white']).pack(side='left', padx=(0, 5))
        tk.Entry(click_input_frame, textvariable=self.click_x, font=('Segoe UI', 11), 
                width=8, relief='solid', bd=1).pack(side='left', padx=(0, 15))
        
        tk.Label(click_input_frame, text="Y:", font=('Segoe UI', 10), 
                bg=self.colors['white']).pack(side='left', padx=(0, 5))
        tk.Entry(click_input_frame, textvariable=self.click_y, font=('Segoe UI', 11), 
                width=8, relief='solid', bd=1).pack(side='left', padx=(0, 20))
        
        tk.Button(click_input_frame, text="📍 위치 지정", command=self.relocate_clickpoint,
                 font=('Segoe UI', 10, 'bold'), bg=self.colors['accent'], fg='white',
                 relief='flat', cursor='hand2', padx=15, pady=6).pack(side='left')
        
        # 영역 설정들
        areas = [
            ("🔴 전체 영역", [self.allarea_x1, self.allarea_y1, self.allarea_x2, self.allarea_y2], self.relocate_allarea),
            ("🔵 날짜 영역", [self.datearea_x1, self.datearea_y1, self.datearea_x2, self.datearea_y2], self.relocate_datearea),
            ("⚪ 금리 영역", [self.ratearea_x1, self.ratearea_y1, self.ratearea_x2, self.ratearea_y2], self.relocate_ratearea)
        ]
        
        for area_name, vars_list, relocate_func in areas:
            area_frame = tk.Frame(parent, bg=self.colors['white'])
            area_frame.pack(fill='x', pady=(0, 15))
            
            tk.Label(area_frame, text=f"{area_name}", font=('Segoe UI', 12, 'bold'), 
                    bg=self.colors['white'], fg=self.colors['on_surface']).pack(anchor='w')
            
            area_input_frame = tk.Frame(area_frame, bg=self.colors['white'])
            area_input_frame.pack(fill='x', pady=(8, 0))
            
            for i, (var, label) in enumerate(zip(vars_list, ['X1:', 'Y1:', 'X2:', 'Y2:'])):
                tk.Label(area_input_frame, text=label, font=('Segoe UI', 10), 
                        bg=self.colors['white']).pack(side='left', padx=(0, 5))
                tk.Entry(area_input_frame, textvariable=var, font=('Segoe UI', 11), 
                        width=8, relief='solid', bd=1).pack(side='left', padx=(0, 10))
            
            tk.Button(area_input_frame, text="🔲 영역 지정", command=relocate_func,
                     font=('Segoe UI', 10, 'bold'), bg=self.colors['secondary'], fg='white',
                     relief='flat', cursor='hand2', padx=15, pady=6).pack(side='left', padx=(20, 0))

    def _create_timing_settings_professional(self, parent):
        """현업 수준의 타이밍 설정"""
        timing_grid = tk.Frame(parent, bg=self.colors['white'])
        timing_grid.pack(fill='x')
        
        # 붙여넣기 딜레이
        paste_frame = tk.Frame(timing_grid, bg=self.colors['white'])
        paste_frame.pack(side='left', fill='x', expand=True, padx=(0, 30))
        
        tk.Label(paste_frame, text="📋 붙여넣기 딜레이", font=('Segoe UI', 12, 'bold'), 
                bg=self.colors['white'], fg=self.colors['on_surface']).pack(anchor='w')
        
        paste_input_frame = tk.Frame(paste_frame, bg=self.colors['white'])
        paste_input_frame.pack(fill='x', pady=(8, 0))
        
        tk.Entry(paste_input_frame, textvariable=self.paste_delay, font=('Segoe UI', 11), 
                width=12, relief='solid', bd=1).pack(side='left', padx=(0, 5))
        tk.Label(paste_input_frame, text="초", font=('Segoe UI', 10), 
                bg=self.colors['white']).pack(side='left')
        
        # 로딩 딜레이
        loading_frame = tk.Frame(timing_grid, bg=self.colors['white'])
        loading_frame.pack(side='left', fill='x', expand=True)
        
        tk.Label(loading_frame, text="⏳ 로딩 딜레이", font=('Segoe UI', 12, 'bold'), 
                bg=self.colors['white'], fg=self.colors['on_surface']).pack(anchor='w')
        
        loading_input_frame = tk.Frame(loading_frame, bg=self.colors['white'])
        loading_input_frame.pack(fill='x', pady=(8, 0))
        
        tk.Entry(loading_input_frame, textvariable=self.loading_delay, font=('Segoe UI', 11), 
                width=12, relief='solid', bd=1).pack(side='left', padx=(0, 5))
        tk.Label(loading_input_frame, text="초", font=('Segoe UI', 10), 
                bg=self.colors['white']).pack(side='left')

    def _create_image_options_professional(self, parent):
        """현업 수준의 이미지 옵션"""
        option_frame = tk.Frame(parent, bg=self.colors['white'])
        option_frame.pack(fill='x')
        
        self.save_images_check = tk.Checkbutton(option_frame, 
                                              text="📸 상세 이미지 저장 (날짜/금리 영역 개별 저장)", 
                                              variable=self.save_detail_images,
                                              font=('Segoe UI', 12, 'bold'),
                                              bg=self.colors['white'], fg=self.colors['on_surface'],
                                              selectcolor=self.colors['light'],
                                              activebackground=self.colors['white'])
        self.save_images_check.pack(anchor='w', pady=(0, 10))
        
        desc_label = tk.Label(option_frame, 
                            text="✅ 체크: 날짜/금리 영역을 별도 파일로 저장하여 OCR 결과 검증 가능\n❌ 해제: 전체 영역만 저장하여 디스크 공간 절약", 
                            font=('Segoe UI', 10), bg=self.colors['white'], fg=self.colors['on_surface'],
                            justify='left')
        desc_label.pack(anchor='w')

    def _create_preset_management_professional(self, parent):
        """현업 수준의 프리셋 관리"""
        # 프리셋 적용
        load_frame = tk.Frame(parent, bg=self.colors['white'])
        load_frame.pack(fill='x', pady=(0, 20))
        
        tk.Label(load_frame, text="💾 저장된 프리셋", font=('Segoe UI', 12, 'bold'), 
                bg=self.colors['white'], fg=self.colors['on_surface']).pack(anchor='w')
        
        load_input_frame = tk.Frame(load_frame, bg=self.colors['white'])
        load_input_frame.pack(fill='x', pady=(8, 0))
        
        self.preset_combo = ttk.Combobox(load_input_frame, font=('Segoe UI', 11), state="readonly", width=30)
        self.preset_combo.pack(side='left', padx=(0, 10))
        self.update_preset_combo()
        
        btn_apply = tk.Button(load_input_frame, text="✅ 적용", command=self.apply_selected_preset,
                             font=('Segoe UI', 10, 'bold'), bg=self.colors['success'], fg='white',
                             relief='flat', cursor='hand2', padx=20, pady=6)
        btn_apply.pack(side='left')
        
        # 프리셋 저장
        save_frame = tk.Frame(parent, bg=self.colors['white'])
        save_frame.pack(fill='x')
        
        tk.Label(save_frame, text="💼 새 프리셋 저장", font=('Segoe UI', 12, 'bold'), 
                bg=self.colors['white'], fg=self.colors['on_surface']).pack(anchor='w')
        
        save_input_frame = tk.Frame(save_frame, bg=self.colors['white'])
        save_input_frame.pack(fill='x', pady=(8, 0))
        
        self.preset_name_entry = tk.Entry(save_input_frame, font=('Segoe UI', 11), 
                                         relief='solid', bd=1, width=30)
        self.preset_name_entry.pack(side='left', padx=(0, 10))
        
        btn_save = tk.Button(save_input_frame, text="💾 저장", command=self.save_current_preset,
                           font=('Segoe UI', 10, 'bold'), bg=self.colors['warning'], fg='white',
                           relief='flat', cursor='hand2', padx=20, pady=6)
        btn_save.pack(side='left')

    def _create_area_preview_professional(self, parent):
        """현업 수준의 영역 미리보기 (복구됨!)"""
        preview_grid = tk.Frame(parent, bg=self.colors['white'])
        preview_grid.pack(fill='x')
        
        # 전체 미리보기
        all_preview_frame = tk.Frame(preview_grid, bg=self.colors['white'])
        all_preview_frame.pack(side='left', fill='x', expand=True, padx=(0, 15))
        
        tk.Button(all_preview_frame, text="👁️ 전체 영역 미리보기", command=self.show_area_preview,
                 font=('Segoe UI', 12, 'bold'), bg=self.colors['danger'], fg='white',
                 relief='flat', cursor='hand2', pady=12).pack(fill='x')
        
        # 개별 영역 미리보기
        individual_frame = tk.Frame(preview_grid, bg=self.colors['white'])
        individual_frame.pack(side='left', fill='x', expand=True)
        
        tk.Label(individual_frame, text="개별 영역 미리보기", font=('Segoe UI', 11, 'bold'), 
                bg=self.colors['white'], fg=self.colors['on_surface']).pack(anchor='w', pady=(0, 8))
        
        btn_grid = tk.Frame(individual_frame, bg=self.colors['white'])
        btn_grid.pack(fill='x')
        
        tk.Button(btn_grid, text="🔴 전체", command=lambda: self.show_individual_area_preview('all'),
                 font=('Segoe UI', 9), bg=self.colors['danger'], fg='white',
                 relief='flat', cursor='hand2', width=8).pack(side='left', padx=(0, 5))
        
        tk.Button(btn_grid, text="🔵 날짜", command=lambda: self.show_individual_area_preview('date'),
                 font=('Segoe UI', 9), bg=self.colors['primary'], fg='white',
                 relief='flat', cursor='hand2', width=8).pack(side='left', padx=(0, 5))
        
        tk.Button(btn_grid, text="⚪ 금리", command=lambda: self.show_individual_area_preview('rate'),
                 font=('Segoe UI', 9), bg=self.colors['secondary'], fg='white',
                 relief='flat', cursor='hand2', width=8).pack(side='left')

    def _create_advanced_tab_professional(self):
        """현업 수준의 고급 설정 탭"""
        # 스크롤 가능한 메인 컨테이너
        canvas = tk.Canvas(self.advanced_frame, bg=self.colors['surface'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.advanced_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['surface'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # OCR 엔진 설정
        self._create_professional_card(scrollable_frame, "🔤 OCR 엔진 설정", "텍스트 인식 정확도 및 성능 조정")
        ocr_card = self._get_last_card_content()
        self._create_ocr_engine_settings_professional(ocr_card)
        
        # 이미지 전처리 설정
        self._create_professional_card(scrollable_frame, "🖼️ 이미지 전처리", "OCR 정확도 향상을 위한 이미지 최적화")
        preprocessing_card = self._get_last_card_content()
        self._create_image_preprocessing_professional(preprocessing_card)
        
        # 자동화 설정
        self._create_professional_card(scrollable_frame, "🤖 자동화 설정", "배치 처리 및 오류 처리 방식")
        automation_card = self._get_last_card_content()
        self._create_automation_professional(automation_card)
        
        # 품질 관리
        self._create_professional_card(scrollable_frame, "📊 품질 관리", "결과 검증 및 품질 보증")
        quality_card = self._get_last_card_content()
        self._create_quality_management_professional(quality_card)

    def _create_log_tab_professional(self):
        """현업 수준의 로그/상태 탭"""
        # 메인 컨테이너
        main_container = tk.Frame(self.log_frame, bg=self.colors['surface'])
        main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # 상단: 실시간 로그 뷰어
        self._create_professional_card(main_container, "📝 실시간 로그", "처리 과정 및 오류 로그 모니터링")
        log_card = self._get_last_card_content()
        self._create_log_viewer_professional(log_card)
        
        # 하단 행: 통계 및 제어
        bottom_row = tk.Frame(main_container, bg=self.colors['surface'])
        bottom_row.pack(fill='x', pady=(20, 0))
        
        # 왼쪽: 처리 통계
        stats_container = tk.Frame(bottom_row, bg=self.colors['surface'])
        stats_container.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        self._create_professional_card(stats_container, "📊 처리 통계", "성능 및 정확도 지표")
        stats_card = self._get_last_card_content()
        self._create_processing_stats_professional(stats_card)
        
        # 오른쪽: 로그 제어
        control_container = tk.Frame(bottom_row, bg=self.colors['surface'])
        control_container.pack(side='right', fill='both', expand=True, padx=(10, 0))
        
        self._create_professional_card(control_container, "🎛️ 로그 제어", "로그 관리 및 내보내기")
        control_card = self._get_last_card_content()
        self._create_log_control_professional(control_card)

    def _create_ocr_engine_settings_professional(self, parent):
        """OCR 엔진 설정"""
        settings_grid = tk.Frame(parent, bg=self.colors['white'])
        settings_grid.pack(fill='x')
        
        # 왼쪽 컬럼
        left_col = tk.Frame(settings_grid, bg=self.colors['white'])
        left_col.pack(side='left', fill='both', expand=True, padx=(0, 20))
        
        # 언어 설정
        tk.Label(left_col, text="🌐 인식 언어", font=('Segoe UI', 11, 'bold'), 
                bg=self.colors['white']).pack(anchor='w', pady=(0, 5))
        
        lang_frame = tk.Frame(left_col, bg=self.colors['white'])
        lang_frame.pack(fill='x', pady=(0, 15))
        
        self.lang_var = tk.StringVar(value='ko')
        ttk.Combobox(lang_frame, textvariable=self.lang_var, values=['ko', 'en', 'ko+en'], 
                    state="readonly", font=('Segoe UI', 10), width=15).pack(side='left')
        
        # 신뢰도 임계값
        tk.Label(left_col, text="📊 신뢰도 임계값", font=('Segoe UI', 11, 'bold'), 
                bg=self.colors['white']).pack(anchor='w', pady=(0, 5))
        
        confidence_frame = tk.Frame(left_col, bg=self.colors['white'])
        confidence_frame.pack(fill='x')
        
        tk.Entry(confidence_frame, textvariable=self.confidence_threshold, font=('Segoe UI', 10), 
                width=10, relief='solid', bd=1).pack(side='left', padx=(0, 5))
        tk.Label(confidence_frame, text="%", font=('Segoe UI', 10), 
                bg=self.colors['white']).pack(side='left')
        
        # 오른쪽 컬럼
        right_col = tk.Frame(settings_grid, bg=self.colors['white'])
        right_col.pack(side='right', fill='both', expand=True)
        
        # GPU 사용
        tk.Label(right_col, text="🚀 GPU 가속", font=('Segoe UI', 11, 'bold'), 
                bg=self.colors['white']).pack(anchor='w', pady=(0, 5))
        
        tk.Checkbutton(right_col, text="GPU 사용 (CUDA)", variable=self.use_gpu,
                      font=('Segoe UI', 10), bg=self.colors['white'],
                      selectcolor=self.colors['light']).pack(anchor='w', pady=(0, 15))
        
        # 멀티스레딩
        tk.Label(right_col, text="⚡ 처리 스레드", font=('Segoe UI', 11, 'bold'), 
                bg=self.colors['white']).pack(anchor='w', pady=(0, 5))
        
        thread_frame = tk.Frame(right_col, bg=self.colors['white'])
        thread_frame.pack(fill='x')
        
        tk.Entry(thread_frame, textvariable=self.max_threads, font=('Segoe UI', 10), 
                width=10, relief='solid', bd=1).pack(side='left', padx=(0, 5))
        tk.Label(thread_frame, text="개", font=('Segoe UI', 10), 
                bg=self.colors['white']).pack(side='left')

    def _create_image_preprocessing_professional(self, parent):
        """이미지 전처리 설정"""
        preprocessing_grid = tk.Frame(parent, bg=self.colors['white'])
        preprocessing_grid.pack(fill='x')
        
        # 왼쪽: 필터 설정
        filters_frame = tk.Frame(preprocessing_grid, bg=self.colors['white'])
        filters_frame.pack(side='left', fill='both', expand=True, padx=(0, 20))
        
        tk.Label(filters_frame, text="🔧 이미지 필터", font=('Segoe UI', 11, 'bold'), 
                bg=self.colors['white']).pack(anchor='w', pady=(0, 10))
        
        filter_options = [
            ("🔍 샤프닝", self.apply_sharpening),
            ("🌓 명암 조정", self.apply_contrast),
            ("📏 노이즈 제거", self.apply_denoising),
            ("⚡ 이진화", self.apply_binarization)
        ]
        
        for text, var in filter_options:
            tk.Checkbutton(filters_frame, text=text, variable=var, font=('Segoe UI', 10),
                          bg=self.colors['white'], selectcolor=self.colors['light']).pack(anchor='w', pady=2)
        
        # 오른쪽: 크기 및 품질 설정
        quality_frame = tk.Frame(preprocessing_grid, bg=self.colors['white'])
        quality_frame.pack(side='right', fill='both', expand=True)
        
        tk.Label(quality_frame, text="📐 이미지 품질", font=('Segoe UI', 11, 'bold'), 
                bg=self.colors['white']).pack(anchor='w', pady=(0, 10))
        
        # 해상도 설정
        resolution_frame = tk.Frame(quality_frame, bg=self.colors['white'])
        resolution_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(resolution_frame, text="해상도 배율:", font=('Segoe UI', 10), 
                bg=self.colors['white']).pack(side='left', padx=(0, 5))
        tk.Entry(resolution_frame, textvariable=self.image_scale_factor, font=('Segoe UI', 10), 
                width=8, relief='solid', bd=1).pack(side='left', padx=(0, 5))
        tk.Label(resolution_frame, text="배", font=('Segoe UI', 10), 
                bg=self.colors['white']).pack(side='left')
        
        # 품질 설정
        quality_slider_frame = tk.Frame(quality_frame, bg=self.colors['white'])
        quality_slider_frame.pack(fill='x')
        
        tk.Label(quality_slider_frame, text="압축 품질:", font=('Segoe UI', 10), 
                bg=self.colors['white']).pack(anchor='w', pady=(0, 5))
        
        quality_slider = tk.Scale(quality_slider_frame, from_=1, to=100, orient='horizontal',
                                 variable=self.image_quality, bg=self.colors['white'],
                                 font=('Segoe UI', 9))
        quality_slider.pack(fill='x')

    def _create_automation_professional(self, parent):
        """자동화 설정"""
        auto_grid = tk.Frame(parent, bg=self.colors['white'])
        auto_grid.pack(fill='x')
        
        # 왼쪽: 배치 처리
        batch_frame = tk.Frame(auto_grid, bg=self.colors['white'])
        batch_frame.pack(side='left', fill='both', expand=True, padx=(0, 20))
        
        tk.Label(batch_frame, text="📦 배치 처리", font=('Segoe UI', 11, 'bold'), 
                bg=self.colors['white']).pack(anchor='w', pady=(0, 10))
        
        # 배치 크기
        batch_size_frame = tk.Frame(batch_frame, bg=self.colors['white'])
        batch_size_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(batch_size_frame, text="배치 크기:", font=('Segoe UI', 10), 
                bg=self.colors['white']).pack(side='left', padx=(0, 5))
        tk.Entry(batch_size_frame, textvariable=self.batch_size, font=('Segoe UI', 10), 
                width=8, relief='solid', bd=1).pack(side='left', padx=(0, 5))
        tk.Label(batch_size_frame, text="개", font=('Segoe UI', 10), 
                bg=self.colors['white']).pack(side='left')
        
        # 자동 재시도
        tk.Checkbutton(batch_frame, text="🔄 실패 시 자동 재시도", variable=self.auto_retry,
                      font=('Segoe UI', 10), bg=self.colors['white'],
                      selectcolor=self.colors['light']).pack(anchor='w')
        
        # 오른쪽: 오류 처리
        error_frame = tk.Frame(auto_grid, bg=self.colors['white'])
        error_frame.pack(side='right', fill='both', expand=True)
        
        tk.Label(error_frame, text="⚠️ 오류 처리", font=('Segoe UI', 11, 'bold'), 
                bg=self.colors['white']).pack(anchor='w', pady=(0, 10))
        
        # 최대 재시도 횟수
        retry_frame = tk.Frame(error_frame, bg=self.colors['white'])
        retry_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(retry_frame, text="최대 재시도:", font=('Segoe UI', 10), 
                bg=self.colors['white']).pack(side='left', padx=(0, 5))
        tk.Entry(retry_frame, textvariable=self.max_retries, font=('Segoe UI', 10), 
                width=8, relief='solid', bd=1).pack(side='left', padx=(0, 5))
        tk.Label(retry_frame, text="회", font=('Segoe UI', 10), 
                bg=self.colors['white']).pack(side='left')
        
        # 오류 시 계속 진행
        tk.Checkbutton(error_frame, text="🚀 오류 시 다음 항목 계속", variable=self.continue_on_error,
                      font=('Segoe UI', 10), bg=self.colors['white'],
                      selectcolor=self.colors['light']).pack(anchor='w')

    def _create_quality_management_professional(self, parent):
        """품질 관리 설정"""
        quality_grid = tk.Frame(parent, bg=self.colors['white'])
        quality_grid.pack(fill='x')
        
        # 왼쪽: 검증 설정
        validation_frame = tk.Frame(quality_grid, bg=self.colors['white'])
        validation_frame.pack(side='left', fill='both', expand=True, padx=(0, 20))
        
        tk.Label(validation_frame, text="✅ 결과 검증", font=('Segoe UI', 11, 'bold'), 
                bg=self.colors['white']).pack(anchor='w', pady=(0, 10))
        
        validation_options = [
            ("📅 날짜 형식 검증", self.validate_date_format),
            ("💱 금리 범위 검증", self.validate_rate_range),
            ("🔍 중복 결과 체크", self.check_duplicates),
            ("📊 정확도 리포트", self.generate_accuracy_report)
        ]
        
        for text, var in validation_options:
            tk.Checkbutton(validation_frame, text=text, variable=var, font=('Segoe UI', 10),
                          bg=self.colors['white'], selectcolor=self.colors['light']).pack(anchor='w', pady=2)
        
        # 오른쪽: 품질 임계값
        threshold_frame = tk.Frame(quality_grid, bg=self.colors['white'])
        threshold_frame.pack(side='right', fill='both', expand=True)
        
        tk.Label(threshold_frame, text="🎯 품질 임계값", font=('Segoe UI', 11, 'bold'), 
                bg=self.colors['white']).pack(anchor='w', pady=(0, 10))
        
        # 최소 정확도
        accuracy_frame = tk.Frame(threshold_frame, bg=self.colors['white'])
        accuracy_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(accuracy_frame, text="최소 정확도:", font=('Segoe UI', 10), 
                bg=self.colors['white']).pack(side='left', padx=(0, 5))
        tk.Entry(accuracy_frame, textvariable=self.min_accuracy, font=('Segoe UI', 10), 
                width=8, relief='solid', bd=1).pack(side='left', padx=(0, 5))
        tk.Label(accuracy_frame, text="%", font=('Segoe UI', 10), 
                bg=self.colors['white']).pack(side='left')
        
        # 품질 점수 표시
        tk.Checkbutton(threshold_frame, text="📈 실시간 품질 점수 표시", variable=self.show_quality_score,
                      font=('Segoe UI', 10), bg=self.colors['white'],
                      selectcolor=self.colors['light']).pack(anchor='w')

    def _create_log_viewer_professional(self, parent):
        """현업 수준 로그 뷰어"""
        # 로그 텍스트와 스크롤바 컨테이너
        log_container = tk.Frame(parent, bg=self.colors['white'], relief='solid', bd=1)
        log_container.pack(fill='both', expand=True, padx=0, pady=0)
        
        # 상단 도구바
        toolbar = tk.Frame(log_container, bg=self.colors['light'], height=35)
        toolbar.pack(fill='x', padx=0, pady=0)
        toolbar.pack_propagate(False)
        
        # 필터 버튼들
        filter_frame = tk.Frame(toolbar, bg=self.colors['light'])
        filter_frame.pack(side='left', fill='y', padx=10)
        
        self.log_filter = tk.StringVar(value='all')
        log_filters = [
            ('전체', 'all'), ('정보', 'info'), ('경고', 'warning'), ('오류', 'error')
        ]
        
        for text, value in log_filters:
            tk.Radiobutton(filter_frame, text=text, variable=self.log_filter, value=value,
                          font=('Segoe UI', 9), bg=self.colors['light'],
                          command=self.filter_logs).pack(side='left', padx=5)
        
        # 검색 상자
        search_frame = tk.Frame(toolbar, bg=self.colors['light'])
        search_frame.pack(side='right', fill='y', padx=10)
        
        tk.Label(search_frame, text="🔍", font=('Segoe UI', 10), 
                bg=self.colors['light']).pack(side='left', padx=(0, 5))
        
        self.log_search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.log_search_var, 
                               font=('Segoe UI', 9), width=20, relief='solid', bd=1)
        search_entry.pack(side='left')
        search_entry.bind('<KeyRelease>', lambda e: self.search_logs())
        
        # 로그 텍스트 영역
        text_frame = tk.Frame(log_container, bg=self.colors['white'])
        text_frame.pack(fill='both', expand=True, padx=5, pady=(0, 5))
        
        self.log_text = tk.Text(text_frame, state='disabled', wrap='word', 
                               font=('Consolas', 10), bg=self.colors['white'], 
                               fg=self.colors['on_surface'], relief='flat',
                               height=20)
        
        log_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")
        
        # 로그 색상 태그 설정
        self.log_text.tag_configure("INFO", foreground=self.colors['primary'])
        self.log_text.tag_configure("WARNING", foreground=self.colors['warning'])
        self.log_text.tag_configure("ERROR", foreground=self.colors['danger'])
        self.log_text.tag_configure("SUCCESS", foreground=self.colors['success'])

    def _create_processing_stats_professional(self, parent):
        """처리 통계 표시"""
        stats_grid = tk.Frame(parent, bg=self.colors['white'])
        stats_grid.pack(fill='both', expand=True)
        
        # 통계 카드들
        stats_data = [
            ("📊 총 처리량", "total_processed", "0"),
            ("✅ 성공", "success_count", "0"),
            ("⚠️ 경고", "warning_count", "0"),
            ("❌ 실패", "error_count", "0"),
            ("⏱️ 평균 처리시간", "avg_time", "0.0s"),
            ("🎯 정확도", "accuracy", "0.0%")
        ]
        
        for i, (label, var_name, default) in enumerate(stats_data):
            row = i // 2
            col = i % 2
            
            stat_frame = tk.Frame(stats_grid, bg=self.colors['surface'], relief='solid', bd=1)
            stat_frame.grid(row=row, column=col, padx=5, pady=5, sticky='ew')
            stats_grid.grid_columnconfigure(col, weight=1)
            
            tk.Label(stat_frame, text=label, font=('Segoe UI', 10, 'bold'), 
                    bg=self.colors['surface'], fg=self.colors['on_surface']).pack(pady=(10, 5))
            
            # 통계 변수 생성 및 저장
            stat_var = tk.StringVar(value=default)
            setattr(self, f"stat_{var_name}", stat_var)
            
            tk.Label(stat_frame, textvariable=stat_var, font=('Segoe UI', 14, 'bold'), 
                    bg=self.colors['surface'], fg=self.colors['primary']).pack(pady=(0, 10))

    def _create_log_control_professional(self, parent):
        """로그 제어 패널"""
        control_grid = tk.Frame(parent, bg=self.colors['white'])
        control_grid.pack(fill='both', expand=True)
        
        # 로그 레벨 설정
        level_frame = tk.Frame(control_grid, bg=self.colors['white'])
        level_frame.pack(fill='x', pady=(0, 15))
        
        tk.Label(level_frame, text="📋 로그 레벨", font=('Segoe UI', 11, 'bold'), 
                bg=self.colors['white']).pack(anchor='w', pady=(0, 5))
        
        self.log_level_var = tk.StringVar(value='INFO')
        log_level_combo = ttk.Combobox(level_frame, textvariable=self.log_level_var,
                                      values=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                                      state="readonly", font=('Segoe UI', 10), width=15)
        log_level_combo.pack(anchor='w')
        log_level_combo.bind('<<ComboboxSelected>>', lambda e: self.change_log_level())
        
        # 제어 버튼들
        button_frame = tk.Frame(control_grid, bg=self.colors['white'])
        button_frame.pack(fill='x')
        
        buttons_data = [
            ("🗑️ 로그 지우기", self.clear_log, self.colors['danger']),
            ("💾 로그 저장", self.save_log, self.colors['success']),
            ("📤 로그 내보내기", self.export_log, self.colors['warning']),
            ("🔄 새로고침", self.refresh_log, self.colors['secondary'])
        ]
        
        for i, (text, command, color) in enumerate(buttons_data):
            btn = tk.Button(button_frame, text=text, command=command,
                           font=('Segoe UI', 9, 'bold'), bg=color, fg='white',
                           relief='flat', cursor='hand2', width=15)
            btn.pack(fill='x', pady=2)

    def show_individual_area_preview(self, area_type):
        """개별 영역 미리보기"""
        if area_type == 'all':
            coords = (self.allarea_x1.get(), self.allarea_y1.get(), 
                     self.allarea_x2.get(), self.allarea_y2.get())
            color = "red"
            title = "전체 영역"
        elif area_type == 'date':
            coords = (self.datearea_x1.get(), self.datearea_y1.get(), 
                     self.datearea_x2.get(), self.datearea_y2.get())
            color = "blue"
            title = "날짜 영역"
        elif area_type == 'rate':
            coords = (self.ratearea_x1.get(), self.ratearea_y1.get(), 
                     self.ratearea_x2.get(), self.ratearea_y2.get())
            color = "green"
            title = "금리 영역"
        else:
            return
            
        try:
            # 스크린샷 촬영
            screenshot = pyautogui.screenshot()
            
            # PIL Image로 변환
            img = screenshot.crop(coords)
            
            # 미리보기 창 생성
            preview_window = tk.Toplevel(self)
            preview_window.title(f"{title} 미리보기")
            preview_window.geometry("400x300")
            preview_window.configure(bg=self.colors['surface'])
            
            # 이미지 크기 조정
            img.thumbnail((350, 250), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            # 이미지 레이블
            label = tk.Label(preview_window, image=photo, bg=self.colors['surface'])
            label.image = photo  # 참조 유지
            label.pack(padx=20, pady=20)
            
            # 좌표 정보
            info_text = f"좌표: ({coords[0]}, {coords[1]}) - ({coords[2]}, {coords[3]})"
            tk.Label(preview_window, text=info_text, font=('Segoe UI', 10), 
                    bg=self.colors['surface'], fg=self.colors['on_surface']).pack()
            
        except Exception as e:
            messagebox.showerror("오류", f"미리보기 생성 실패: {e}")

    def export_settings(self):
        """설정 내보내기"""
        try:
            filename = filedialog.asksaveasfilename(
                title="설정 내보내기",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                settings = self.get_current_settings()
                settings['ui_theme'] = self.current_theme
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, ensure_ascii=False, indent=2)
                
                messagebox.showinfo("완료", f"설정이 저장되었습니다:\n{filename}")
                
        except Exception as e:
            messagebox.showerror("오류", f"설정 내보내기 실패: {e}")

    def import_settings(self):
        """설정 가져오기"""
        try:
            filename = filedialog.askopenfilename(
                title="설정 가져오기",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                with open(filename, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # 테마 설정 적용
                if 'ui_theme' in settings:
                    theme = settings['ui_theme']
                    if theme in self.available_themes:
                        self.current_theme = theme
                        self.colors = self.available_themes[theme].copy()
                        self.theme_var.set(self.available_themes[theme]['name'])
                        self.settings_manager.set_advanced('ui_theme', theme)
                        self.refresh_ui()
                
                # 기본 설정 적용
                self.apply_settings(settings)
                
                messagebox.showinfo("완료", f"설정이 불러와졌습니다:\n{filename}")
                
        except Exception as e:
            messagebox.showerror("오류", f"설정 가져오기 실패: {e}")

    def filter_logs(self):
        """로그 필터링"""
        # 구현 예정 - 로그 레벨에 따른 필터링
        pass

    def search_logs(self):
        """로그 검색"""
        # 구현 예정 - 텍스트 검색 기능
        pass

    def change_log_level(self):
        """로그 레벨 변경"""
        level = self.log_level_var.get()
        # 구현 예정 - 로그 레벨 동적 변경
        self.logger.info(f"로그 레벨이 {level}로 변경되었습니다.")

    def export_log(self):
        """로그 내보내기"""
        try:
            filename = filedialog.asksaveasfilename(
                title="로그 내보내기",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            
            if filename:
                log_content = self.log_text.get("1.0", tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                
                messagebox.showinfo("완료", f"로그가 저장되었습니다:\n{filename}")
                
        except Exception as e:
            messagebox.showerror("오류", f"로그 내보내기 실패: {e}")

    def refresh_log(self):
        """로그 새로고침"""
        # 로그 디스플레이 새로고침
        self.logger.info("로그가 새로고침되었습니다.")

    def _create_basic_tab(self):
        """기본 설정 탭 생성 (컴팩트 레이아웃 - 스크롤 없음)"""
        # 메인 컨테이너
        main_container = tk.Frame(self.basic_frame, bg=self.colors['light'])
        main_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # 상단 행: 파일 설정 + 프리셋 + 테마
        top_row = tk.Frame(main_container, bg=self.colors['light'])
        top_row.pack(fill='x', pady=(0, 5))
        
        # 파일 설정 (왼쪽)
        files_frame = tk.Frame(top_row, bg=self.colors['light'])
        files_frame.pack(side='left', fill='both', expand=True, padx=(0, 3))
        self._create_excel_frame_compact(files_frame)
        
        # 프리셋 + 테마 (오른쪽)
        control_frame = tk.Frame(top_row, bg=self.colors['light'])
        control_frame.pack(side='right', fill='y', padx=(3, 0))
        self._create_preset_frame_compact(control_frame)
        self._create_theme_frame_compact(control_frame)
        
        # 중간 행: 좌표 설정
        middle_row = tk.Frame(main_container, bg=self.colors['light'])
        middle_row.pack(fill='x', pady=5)
        self._create_coordinates_compact(middle_row)
        
        # 하단 행: 옵션 + 액션
        bottom_row = tk.Frame(main_container, bg=self.colors['light'])
        bottom_row.pack(fill='x', pady=(5, 0))
        
        # 왼쪽: 타이밍 + 이미지 옵션
        options_frame = tk.Frame(bottom_row, bg=self.colors['light'])
        options_frame.pack(side='left', fill='both', expand=True, padx=(0, 3))
        self._create_timing_frame_compact(options_frame)
        self._create_image_save_frame_compact(options_frame)
        
        # 오른쪽: 액션 버튼들
        actions_frame = tk.Frame(bottom_row, bg=self.colors['light'])
        actions_frame.pack(side='right', fill='y', padx=(3, 0))
        self._create_action_frame_compact(actions_frame)

    def _create_advanced_tab(self):
        """고급 설정 탭 생성 (통일된 디자인)"""
        # 메인 컨테이너
        main_container = tk.Frame(self.advanced_frame, bg=self.colors['light'])
        main_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # 상단 행: OCR 설정 + 이미지 설정
        top_row = tk.Frame(main_container, bg=self.colors['light'])
        top_row.pack(fill='x', pady=(0, 5))
        
        # OCR 설정 (왼쪽)
        ocr_frame = tk.Frame(top_row, bg=self.colors['light'])
        ocr_frame.pack(side='left', fill='both', expand=True, padx=(0, 3))
        self._create_ocr_settings_compact(ocr_frame)
        
        # 이미지 설정 (오른쪽)
        image_frame = tk.Frame(top_row, bg=self.colors['light'])
        image_frame.pack(side='right', fill='both', expand=True, padx=(3, 0))
        self._create_image_settings_compact(image_frame)
        
        # 하단 행: 자동화 + 품질 설정
        bottom_row = tk.Frame(main_container, bg=self.colors['light'])
        bottom_row.pack(fill='x', pady=(5, 0))
        
        # 자동화 설정 (왼쪽)
        auto_frame = tk.Frame(bottom_row, bg=self.colors['light'])
        auto_frame.pack(side='left', fill='both', expand=True, padx=(0, 3))
        self._create_automation_settings_compact(auto_frame)
        
        # 품질 설정 (오른쪽)
        quality_frame = tk.Frame(bottom_row, bg=self.colors['light'])
        quality_frame.pack(side='right', fill='both', expand=True, padx=(3, 0))
        self._create_quality_settings_compact(quality_frame)



    def _create_log_tab(self):
        """로그/상태 탭 생성 (통일된 디자인)"""
        # 메인 컨테이너
        main_container = tk.Frame(self.log_frame, bg=self.colors['light'])
        main_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # 상단: 로그 영역
        log_container = self._create_compact_frame(main_container, "실시간 로그", "📝", height=400)
        
        # 로그 텍스트와 스크롤바
        log_text_frame = tk.Frame(log_container, bg=self.colors['white'])
        log_text_frame.pack(fill='both', expand=True)
        
        self.log_text = tk.Text(log_text_frame, state='disabled', wrap='word', 
                               font=('Consolas', 9), bg=self.colors['white'], 
                               fg=self.colors['dark'], relief='flat')
        log_scrollbar = ttk.Scrollbar(log_text_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")
        
        # 하단 행: 로그 제어 + 통계
        bottom_row = tk.Frame(main_container, bg=self.colors['light'])
        bottom_row.pack(fill='x', pady=(5, 0))
        
        # 로그 제어 (왼쪽)
        control_frame = tk.Frame(bottom_row, bg=self.colors['light'])
        control_frame.pack(side='left', fill='both', expand=True, padx=(0, 3))
        self._create_log_control_compact(control_frame)
        
        # 통계 (오른쪽)
        stats_frame = tk.Frame(bottom_row, bg=self.colors['light'])
        stats_frame.pack(side='right', fill='both', expand=True, padx=(3, 0))
        self._create_stats_compact(stats_frame)
    
    def _create_log_control_compact(self, parent):
        """로그 제어 프레임 (컴팩트)"""
        content = self._create_compact_frame(parent, "로그 제어", "🎛️", height=120)
        
        # 버튼들
        tk.Button(content, text="🗑️ 로그 지우기", command=self.clear_log,
                 font=('Segoe UI', 9, 'bold'), bg=self.colors['danger'], fg='white',
                 relief='flat', cursor='hand2', pady=8).pack(fill='x', pady=(0, 5))
        
        tk.Button(content, text="💾 로그 저장", command=self.save_log,
                 font=('Segoe UI', 9, 'bold'), bg=self.colors['secondary'], fg='white',
                 relief='flat', cursor='hand2', pady=8).pack(fill='x')
    
    def _create_stats_compact(self, parent):
        """통계 프레임 (컴팩트)"""
        content = self._create_compact_frame(parent, "처리 통계", "📊", height=120)
        
        self.stats_text = tk.Text(content, height=6, state='disabled', wrap='word',
                                 font=('Consolas', 9), bg=self.colors['light'], 
                                 fg=self.colors['dark'], relief='flat')
        self.stats_text.pack(fill='both', expand=True)

    def _create_menu(self):
        """메뉴바 생성"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # 파일 메뉴
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="파일", menu=file_menu)
        file_menu.add_command(label="설정 저장 (Ctrl+S)", command=self.quick_save_settings)
        file_menu.add_command(label="설정 불러오기 (Ctrl+L)", command=self.load_last_settings)
        file_menu.add_separator()
        file_menu.add_command(label="종료", command=self.quit)
        
        # 도움말 메뉴
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="도움말", menu=help_menu)
        help_menu.add_command(label="키보드 단축키", command=self.show_shortcuts)
        help_menu.add_command(label="정보", command=self.show_about)

    def _create_preset_frame(self, parent):
        """프리셋 관리 프레임"""
        frm_preset = tk.LabelFrame(parent, text="🔧 프리셋 관리", font=('Arial', 10, 'bold'))
        frm_preset.pack(padx=5, pady=5, fill="x")

        # 프리셋 선택
        preset_frame = tk.Frame(frm_preset)
        preset_frame.pack(fill="x", padx=5, pady=5)

        tk.Label(preset_frame, text="프리셋:").grid(row=0, column=0, sticky="w")
        
        self.preset_combo = ttk.Combobox(preset_frame, width=20, state="readonly")
        self.preset_combo.grid(row=0, column=1, padx=(5, 0))
        self.update_preset_combo()
        
        btn_apply = tk.Button(preset_frame, text="적용", command=self.apply_selected_preset)
        btn_apply.grid(row=0, column=2, padx=5)

        # 프리셋 저장
        save_frame = tk.Frame(frm_preset)
        save_frame.pack(fill="x", padx=5, pady=(0, 5))

        tk.Label(save_frame, text="저장할 이름:").grid(row=0, column=0, sticky="w")
        
        self.preset_name_entry = tk.Entry(save_frame, width=20)
        self.preset_name_entry.grid(row=0, column=1, padx=(5, 0))
        
        btn_save = tk.Button(save_frame, text="저장", command=self.save_current_preset)
        btn_save.grid(row=0, column=2, padx=5)

    def _create_excel_frame(self, parent):
        """엑셀 파일 프레임"""
        frm_excel = tk.LabelFrame(parent, text="📁 파일 설정", font=('Arial', 10, 'bold'))
        frm_excel.pack(padx=5, pady=5, fill="x")

        # Input Excel
        lbl_in = tk.Label(frm_excel, text="Input Excel:")
        lbl_in.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ent_in = tk.Entry(frm_excel, textvariable=self.input_excel_path, width=50)
        ent_in.grid(row=0, column=1, padx=5, pady=5)
        btn_in = tk.Button(frm_excel, text="Browse", command=self.browse_input_excel)
        btn_in.grid(row=0, column=2, padx=5, pady=5)

        # Output
        lbl_out = tk.Label(frm_excel, text="Output Folder:")
        lbl_out.grid(row=1, column=0, sticky="w", padx=5, pady=(0, 5))
        ent_out = tk.Entry(frm_excel, textvariable=self.output_folder_path, width=50)
        ent_out.grid(row=1, column=1, padx=5, pady=(0, 5))
        btn_out = tk.Button(frm_excel, text="Browse", command=self.browse_output_folder)
        btn_out.grid(row=1, column=2, padx=5, pady=(0, 5))

    def _create_click_frame(self, parent):
        """클릭 포인트 프레임"""
        frm_click = tk.LabelFrame(parent, text="🎯 클릭 포인트", font=('Arial', 10, 'bold'))
        frm_click.pack(padx=5, pady=5, fill="x")

        click_inner = tk.Frame(frm_click)
        click_inner.pack(padx=5, pady=5)

        lbl_click = tk.Label(click_inner, text="ClickPoint (x, y):")
        lbl_click.grid(row=0, column=0, sticky="w")

        ent_click_x = tk.Entry(click_inner, textvariable=self.click_x, width=8)
        ent_click_x.grid(row=0, column=1, padx=(5, 2))
        ent_click_y = tk.Entry(click_inner, textvariable=self.click_y, width=8)
        ent_click_y.grid(row=0, column=2, padx=(2, 5))

        btn_click_reloc = tk.Button(click_inner, text="📍 위치 지정", command=self.relocate_clickpoint)
        btn_click_reloc.grid(row=0, column=3, padx=5)

    def _create_area_frame(self, parent):
        """영역 설정 프레임"""
        frm_area = tk.LabelFrame(parent, text="📐 영역 설정", font=('Arial', 10, 'bold'))
        frm_area.pack(padx=5, pady=5, fill="x")

        area_inner = tk.Frame(frm_area)
        area_inner.pack(padx=5, pady=5)

        # AllArea
        lbl_all = tk.Label(area_inner, text="AllArea (x1, y1, x2, y2):")
        lbl_all.grid(row=0, column=0, sticky="w")

        ent_all_x1 = tk.Entry(area_inner, textvariable=self.allarea_x1, width=6)
        ent_all_x1.grid(row=0, column=1, padx=2)
        ent_all_y1 = tk.Entry(area_inner, textvariable=self.allarea_y1, width=6)
        ent_all_y1.grid(row=0, column=2, padx=2)
        ent_all_x2 = tk.Entry(area_inner, textvariable=self.allarea_x2, width=6)
        ent_all_x2.grid(row=0, column=3, padx=2)
        ent_all_y2 = tk.Entry(area_inner, textvariable=self.allarea_y2, width=6)
        ent_all_y2.grid(row=0, column=4, padx=2)
        btn_all_reloc = tk.Button(area_inner, text="🔴 영역 지정", command=self.relocate_allarea)
        btn_all_reloc.grid(row=0, column=5, padx=5)

        # DateArea
        lbl_date = tk.Label(area_inner, text="DateArea (x1, y1, x2, y2):")
        lbl_date.grid(row=1, column=0, sticky="w", pady=(5, 0))

        ent_date_x1 = tk.Entry(area_inner, textvariable=self.datearea_x1, width=6)
        ent_date_x1.grid(row=1, column=1, padx=2, pady=(5, 0))
        ent_date_y1 = tk.Entry(area_inner, textvariable=self.datearea_y1, width=6)
        ent_date_y1.grid(row=1, column=2, padx=2, pady=(5, 0))
        ent_date_x2 = tk.Entry(area_inner, textvariable=self.datearea_x2, width=6)
        ent_date_x2.grid(row=1, column=3, padx=2, pady=(5, 0))
        ent_date_y2 = tk.Entry(area_inner, textvariable=self.datearea_y2, width=6)
        ent_date_y2.grid(row=1, column=4, padx=2, pady=(5, 0))
        btn_date_reloc = tk.Button(area_inner, text="🔵 영역 지정", command=self.relocate_datearea)
        btn_date_reloc.grid(row=1, column=5, padx=5, pady=(5, 0))

        # RateArea
        lbl_rate = tk.Label(area_inner, text="RateArea (x1, y1, x2, y2):")
        lbl_rate.grid(row=2, column=0, sticky="w", pady=(5, 0))

        ent_rate_x1 = tk.Entry(area_inner, textvariable=self.ratearea_x1, width=6)
        ent_rate_x1.grid(row=2, column=1, padx=2, pady=(5, 0))
        ent_rate_y1 = tk.Entry(area_inner, textvariable=self.ratearea_y1, width=6)
        ent_rate_y1.grid(row=2, column=2, padx=2, pady=(5, 0))
        ent_rate_x2 = tk.Entry(area_inner, textvariable=self.ratearea_x2, width=6)
        ent_rate_x2.grid(row=2, column=3, padx=2, pady=(5, 0))
        ent_rate_y2 = tk.Entry(area_inner, textvariable=self.ratearea_y2, width=6)
        ent_rate_y2.grid(row=2, column=4, padx=2, pady=(5, 0))
        btn_rate_reloc = tk.Button(area_inner, text="⚪ 영역 지정", command=self.relocate_ratearea)
        btn_rate_reloc.grid(row=2, column=5, padx=5, pady=(5, 0))

    def _create_delay_frame(self, parent):
        """딜레이 설정 프레임"""
        frm_delay = tk.LabelFrame(parent, text="⏱️ 딜레이 설정", font=('Arial', 10, 'bold'))
        frm_delay.pack(padx=5, pady=5, fill="x")

        delay_inner = tk.Frame(frm_delay)
        delay_inner.pack(padx=5, pady=5)

        # 딜레이 설정
        lbl_paste = tk.Label(delay_inner, text="붙여넣기 딜레이(초):")
        lbl_paste.grid(row=0, column=0, sticky="w")
        ent_paste = tk.Entry(delay_inner, textvariable=self.paste_delay, width=8)
        ent_paste.grid(row=0, column=1, padx=(5, 15))

        lbl_load = tk.Label(delay_inner, text="로딩 딜레이(초):")
        lbl_load.grid(row=0, column=2, sticky="w")
        ent_load = tk.Entry(delay_inner, textvariable=self.loading_delay, width=8)
        ent_load.grid(row=0, column=3, padx=(5, 15))

    def _create_preview_frame(self, parent):
        """영역 미리보기 프레임"""
        frm_preview = tk.LabelFrame(parent, text="👁️ 영역 미리보기", font=('Arial', 10, 'bold'))
        frm_preview.pack(padx=5, pady=5, fill="x")

        preview_inner = tk.Frame(frm_preview)
        preview_inner.pack(padx=5, pady=5)

        # 미리보기 버튼들
        btn_preview_all = tk.Button(preview_inner, text="🔴 전체 영역 미리보기", 
                                   command=self.show_area_preview, 
                                   font=('Arial', 10, 'bold'), bg='#f44336', fg='white')
        btn_preview_all.grid(row=0, column=0, padx=5, pady=2, sticky='ew')



    def _create_ocr_settings_frame(self, parent):
        """OCR 설정 프레임"""
        frm_ocr = tk.LabelFrame(parent, text="🔍 OCR 설정", font=('Arial', 10, 'bold'))
        frm_ocr.pack(padx=5, pady=5, fill="x")

        # GPU 사용 여부
        self.ocr_gpu_var = tk.BooleanVar(value=self.settings_manager.get_advanced('ocr_gpu_enabled', False))
        chk_gpu = tk.Checkbutton(frm_ocr, text="GPU 가속 사용", variable=self.ocr_gpu_var,
                                command=self.on_ocr_setting_changed)
        chk_gpu.grid(row=0, column=0, sticky='w', padx=5, pady=2)

        # 신뢰도 임계값
        tk.Label(frm_ocr, text="신뢰도 임계값:").grid(row=0, column=1, sticky='w', padx=(20, 5))
        self.confidence_var = tk.DoubleVar(value=self.settings_manager.get_advanced('ocr_confidence_threshold', 0.3))
        tk.Scale(frm_ocr, from_=0.1, to=1.0, resolution=0.1, orient='horizontal',
                variable=self.confidence_var, command=self.on_ocr_setting_changed).grid(row=0, column=2, padx=5)

        # 최대 시도 횟수
        tk.Label(frm_ocr, text="최대 시도 횟수:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.max_attempts_var = tk.IntVar(value=self.settings_manager.get_advanced('ocr_max_attempts', 3))
        tk.Spinbox(frm_ocr, from_=1, to=10, textvariable=self.max_attempts_var, width=10,
                  command=self.on_ocr_setting_changed).grid(row=1, column=1, sticky='w', padx=5)

        # 상세 레벨
        tk.Label(frm_ocr, text="상세 레벨:").grid(row=1, column=2, sticky='w', padx=(20, 5))
        self.detail_level_var = tk.IntVar(value=self.settings_manager.get_advanced('ocr_detail_level', 0))
        ttk.Combobox(frm_ocr, textvariable=self.detail_level_var, values=[0, 1, 2], width=8, 
                    state="readonly").grid(row=1, column=3, padx=5)

    def _create_image_settings_frame(self, parent):
        """이미지 처리 설정 프레임"""
        frm_img = tk.LabelFrame(parent, text="🖼️ 이미지 처리 설정", font=('Arial', 10, 'bold'))
        frm_img.pack(padx=5, pady=5, fill="x")

        # 리사이즈 배율
        tk.Label(frm_img, text="크기 확대 배율:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.resize_factor_var = tk.IntVar(value=self.settings_manager.get_advanced('image_resize_factor', 4))
        tk.Spinbox(frm_img, from_=1, to=5, textvariable=self.resize_factor_var, width=10).grid(row=0, column=1, padx=5)

        # 노이즈 제거 강도
        tk.Label(frm_img, text="노이즈 제거 강도:").grid(row=0, column=2, sticky='w', padx=(20, 5))
        self.denoise_var = tk.IntVar(value=self.settings_manager.get_advanced('image_denoise_strength', 2))
        tk.Scale(frm_img, from_=1, to=5, orient='horizontal', variable=self.denoise_var).grid(row=0, column=3, padx=5)

        # 대비 향상
        self.contrast_var = tk.BooleanVar(value=self.settings_manager.get_advanced('image_contrast_enhancement', True))
        tk.Checkbutton(frm_img, text="대비 향상", variable=self.contrast_var).grid(row=1, column=0, sticky='w', padx=5, pady=2)

        # 샤프닝
        self.sharpening_var = tk.BooleanVar(value=self.settings_manager.get_advanced('image_sharpening', True))
        tk.Checkbutton(frm_img, text="샤프닝", variable=self.sharpening_var).grid(row=1, column=1, sticky='w', padx=5)

        # 이진화 방법
        tk.Label(frm_img, text="이진화 방법:").grid(row=1, column=2, sticky='w', padx=(20, 5))
        self.binary_method_var = tk.StringVar(value=self.settings_manager.get_advanced('image_binarization_method', 'adaptive'))
        ttk.Combobox(frm_img, textvariable=self.binary_method_var, 
                    values=['adaptive', 'otsu', 'manual'], width=10, state="readonly").grid(row=1, column=3, padx=5)

    def _create_automation_settings_frame(self, parent):
        """자동화 설정 프레임 (간소화)"""
        frm_auto = tk.LabelFrame(parent, text="🤖 자동화 설정", font=('Arial', 10, 'bold'))
        frm_auto.pack(padx=5, pady=5, fill="x")

        # 클릭 간격만 유지 (실제로 사용되는 설정)
        tk.Label(frm_auto, text="클릭 간격(초):").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.click_interval_var = tk.DoubleVar(value=self.settings_manager.get_advanced('click_interval', 0.1))
        tk.Entry(frm_auto, textvariable=self.click_interval_var, width=10).grid(row=0, column=1, padx=5, pady=5)

    def _create_quality_settings_frame(self, parent):
        """품질 관리 설정 프레임 (간소화)"""
        frm_quality = tk.LabelFrame(parent, text="✅ 신뢰도 설정", font=('Arial', 10, 'bold'))
        frm_quality.pack(padx=5, pady=5, fill="x")

        # 날짜 신뢰도 (실제로 사용되는 설정)
        tk.Label(frm_quality, text="날짜 최소 신뢰도:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.date_confidence_var = tk.DoubleVar(value=self.settings_manager.get_advanced('min_date_confidence', 0.2))
        tk.Scale(frm_quality, from_=0.1, to=1.0, resolution=0.1, orient='horizontal',
                variable=self.date_confidence_var, length=150).grid(row=0, column=1, padx=5, pady=5)

        # 금리 신뢰도 (실제로 사용되는 설정)
        tk.Label(frm_quality, text="금리 최소 신뢰도:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.rate_confidence_var = tk.DoubleVar(value=self.settings_manager.get_advanced('min_rate_confidence', 0.2))
        tk.Scale(frm_quality, from_=0.1, to=1.0, resolution=0.1, orient='horizontal',
                variable=self.rate_confidence_var, length=150).grid(row=1, column=1, padx=5, pady=5)
        
        # 고급 설정 저장/초기화 버튼들을 여기로 이동
        btn_frame = tk.Frame(frm_quality)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        btn_save_advanced = tk.Button(btn_frame, text="💾 고급 설정 저장", command=self.save_advanced_settings,
                                     font=('Arial', 10, 'bold'), bg='#2196F3', fg='white')
        btn_save_advanced.pack(side='left', padx=5)

        btn_reset_advanced = tk.Button(btn_frame, text="🔄 고급 설정 초기화", command=self.reset_advanced_settings,
                                      font=('Arial', 10, 'bold'), bg='#FF9800', fg='white')
        btn_reset_advanced.pack(side='left', padx=5)
    
    # ============================================
    # 고급 설정 컴팩트 프레임들
    # ============================================
    
    def _create_ocr_settings_compact(self, parent):
        """OCR 설정 프레임 (컴팩트)"""
        content = self._create_compact_frame(parent, "OCR 엔진 설정", "🔍", height=200)
        
        # GPU 설정
        gpu_frame = tk.Frame(content, bg=self.colors['white'])
        gpu_frame.pack(fill='x', pady=(0, 5))
        
        self.ocr_gpu_var = tk.BooleanVar(value=self.settings_manager.get_advanced('ocr_gpu_enabled', False))
        tk.Checkbutton(gpu_frame, text="⚡ GPU 가속", variable=self.ocr_gpu_var,
                      command=self.on_ocr_setting_changed, font=('Segoe UI', 9),
                      bg=self.colors['white']).pack(anchor='w')
        
        # 신뢰도 임계값
        conf_frame = tk.Frame(content, bg=self.colors['white'])
        conf_frame.pack(fill='x', pady=(0, 5))
        
        tk.Label(conf_frame, text="🎯 신뢰도:", font=('Segoe UI', 9, 'bold'), 
                bg=self.colors['white']).pack(side='left')
        
        self.confidence_var = tk.DoubleVar(value=self.settings_manager.get_advanced('ocr_confidence_threshold', 0.3))
        tk.Scale(conf_frame, from_=0.1, to=1.0, resolution=0.1, orient='horizontal',
                variable=self.confidence_var, command=self.on_ocr_setting_changed, 
                length=150, bg=self.colors['white']).pack(side='right')
        
        # 최대 시도 횟수
        attempts_frame = tk.Frame(content, bg=self.colors['white'])
        attempts_frame.pack(fill='x', pady=(0, 5))
        
        tk.Label(attempts_frame, text="🔄 최대 시도:", font=('Segoe UI', 9, 'bold'), 
                bg=self.colors['white']).pack(side='left')
        
        self.max_attempts_var = tk.IntVar(value=self.settings_manager.get_advanced('ocr_max_attempts', 3))
        tk.Spinbox(attempts_frame, from_=1, to=10, textvariable=self.max_attempts_var, width=8,
                  command=self.on_ocr_setting_changed, font=('Segoe UI', 9)).pack(side='right')
        
        # 상세 레벨
        detail_frame = tk.Frame(content, bg=self.colors['white'])
        detail_frame.pack(fill='x')
        
        tk.Label(detail_frame, text="📊 상세 레벨:", font=('Segoe UI', 9, 'bold'), 
                bg=self.colors['white']).pack(side='left')
        
        self.detail_level_var = tk.IntVar(value=self.settings_manager.get_advanced('ocr_detail_level', 0))
        ttk.Combobox(detail_frame, textvariable=self.detail_level_var, values=[0, 1, 2], 
                    width=8, state="readonly", font=('Segoe UI', 9)).pack(side='right')
    
    def _create_image_settings_compact(self, parent):
        """이미지 처리 설정 프레임 (컴팩트)"""
        content = self._create_compact_frame(parent, "이미지 처리", "🖼️", height=200)
        
        # 리사이즈 배율
        resize_frame = tk.Frame(content, bg=self.colors['white'])
        resize_frame.pack(fill='x', pady=(0, 5))
        
        tk.Label(resize_frame, text="🔍 확대 배율:", font=('Segoe UI', 9, 'bold'), 
                bg=self.colors['white']).pack(side='left')
        
        self.resize_factor_var = tk.IntVar(value=self.settings_manager.get_advanced('image_resize_factor', 4))
        tk.Spinbox(resize_frame, from_=1, to=5, textvariable=self.resize_factor_var, width=8,
                  font=('Segoe UI', 9)).pack(side='right')
        
        # 노이즈 제거
        denoise_frame = tk.Frame(content, bg=self.colors['white'])
        denoise_frame.pack(fill='x', pady=(0, 5))
        
        tk.Label(denoise_frame, text="🧹 노이즈 제거:", font=('Segoe UI', 9, 'bold'), 
                bg=self.colors['white']).pack(side='left')
        
        self.denoise_var = tk.IntVar(value=self.settings_manager.get_advanced('image_denoise_strength', 2))
        tk.Scale(denoise_frame, from_=1, to=5, orient='horizontal', variable=self.denoise_var,
                length=120, bg=self.colors['white']).pack(side='right')
        
        # 체크박스들
        check_frame = tk.Frame(content, bg=self.colors['white'])
        check_frame.pack(fill='x', pady=(0, 5))
        
        self.contrast_var = tk.BooleanVar(value=self.settings_manager.get_advanced('image_contrast_enhancement', True))
        tk.Checkbutton(check_frame, text="✨ 대비 향상", variable=self.contrast_var,
                      font=('Segoe UI', 9), bg=self.colors['white']).pack(anchor='w')
        
        self.sharpening_var = tk.BooleanVar(value=self.settings_manager.get_advanced('image_sharpening', True))
        tk.Checkbutton(check_frame, text="⚡ 샤프닝", variable=self.sharpening_var,
                      font=('Segoe UI', 9), bg=self.colors['white']).pack(anchor='w')
        
        # 이진화 방법
        binary_frame = tk.Frame(content, bg=self.colors['white'])
        binary_frame.pack(fill='x')
        
        tk.Label(binary_frame, text="🎯 이진화:", font=('Segoe UI', 9, 'bold'), 
                bg=self.colors['white']).pack(side='left')
        
        self.binary_method_var = tk.StringVar(value=self.settings_manager.get_advanced('image_binarization_method', 'adaptive'))
        ttk.Combobox(binary_frame, textvariable=self.binary_method_var, 
                    values=['adaptive', 'otsu', 'manual'], width=10, state="readonly",
                    font=('Segoe UI', 9)).pack(side='right')
    
    def _create_automation_settings_compact(self, parent):
        """자동화 설정 프레임 (컴팩트)"""
        content = self._create_compact_frame(parent, "자동화 설정", "🤖", height=140)
        
        # 클릭 간격
        click_frame = tk.Frame(content, bg=self.colors['white'])
        click_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(click_frame, text="⏱️ 클릭 간격 (초):", font=('Segoe UI', 9, 'bold'), 
                bg=self.colors['white']).pack(side='left')
        
        self.click_interval_var = tk.DoubleVar(value=self.settings_manager.get_advanced('click_interval', 0.1))
        tk.Entry(click_frame, textvariable=self.click_interval_var, width=8, 
                font=('Segoe UI', 9), relief='solid', bd=1).pack(side='right')
        
        # 저장 버튼
        tk.Button(content, text="💾 고급 설정 저장", command=self.save_advanced_settings,
                 font=('Segoe UI', 9, 'bold'), bg=self.colors['success'], fg='white',
                 relief='flat', cursor='hand2', pady=8).pack(fill='x', pady=(10, 5))
        
        tk.Button(content, text="🔄 설정 초기화", command=self.reset_advanced_settings,
                 font=('Segoe UI', 9, 'bold'), bg=self.colors['warning'], fg='white',
                 relief='flat', cursor='hand2', pady=8).pack(fill='x')
    
    def _create_quality_settings_compact(self, parent):
        """품질 관리 설정 프레임 (컴팩트)"""
        content = self._create_compact_frame(parent, "품질 및 신뢰도", "✅", height=140)
        
        # 날짜 신뢰도
        date_conf_frame = tk.Frame(content, bg=self.colors['white'])
        date_conf_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(date_conf_frame, text="📅 날짜 신뢰도:", font=('Segoe UI', 9, 'bold'), 
                bg=self.colors['white']).pack(anchor='w')
        
        self.date_confidence_var = tk.DoubleVar(value=self.settings_manager.get_advanced('min_date_confidence', 0.2))
        tk.Scale(date_conf_frame, from_=0.1, to=1.0, resolution=0.1, orient='horizontal',
                variable=self.date_confidence_var, length=200, bg=self.colors['white']).pack(fill='x')
        
        # 금리 신뢰도
        rate_conf_frame = tk.Frame(content, bg=self.colors['white'])
        rate_conf_frame.pack(fill='x')
        
        tk.Label(rate_conf_frame, text="💰 금리 신뢰도:", font=('Segoe UI', 9, 'bold'), 
                bg=self.colors['white']).pack(anchor='w')
        
        self.rate_confidence_var = tk.DoubleVar(value=self.settings_manager.get_advanced('min_rate_confidence', 0.2))
        tk.Scale(rate_conf_frame, from_=0.1, to=1.0, resolution=0.1, orient='horizontal',
                variable=self.rate_confidence_var, length=200, bg=self.colors['white']).pack(fill='x')

    # ============================================
    # 새로운 모던 스타일 프레임들
    # ============================================
    
    def _create_modern_frame(self, parent, title, icon=""):
        """모던 스타일 프레임 생성"""
        frame = tk.Frame(parent, bg=self.colors['white'], relief='solid', bd=1)
        frame.pack(fill='x', padx=10, pady=8)
        
        # 헤더
        header = tk.Frame(frame, bg=self.colors['primary'], height=40)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        title_label = tk.Label(header, text=f"{icon} {title}", 
                             font=('Segoe UI', 11, 'bold'), 
                             bg=self.colors['primary'], fg='white')
        title_label.pack(side='left', padx=15, pady=8)
        
        # 컨텐츠 영역
        content = tk.Frame(frame, bg=self.colors['white'])
        content.pack(fill='both', expand=True, padx=15, pady=15)
        
        return content
    
    def _create_excel_frame_modern(self, parent):
        """파일 설정 프레임 (모던 스타일)"""
        content = self._create_modern_frame(parent, "파일 설정", "📁")
        
        # Input Excel
        input_frame = tk.Frame(content, bg=self.colors['white'])
        input_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(input_frame, text="📊 Excel 입력 파일:", 
                font=('Segoe UI', 10, 'bold'), bg=self.colors['white']).pack(anchor='w')
        
        input_row = tk.Frame(input_frame, bg=self.colors['white'])
        input_row.pack(fill='x', pady=(5, 0))
        
        self.excel_entry = tk.Entry(input_row, textvariable=self.input_excel_path, 
                                   font=('Segoe UI', 10), relief='solid', bd=1)
        self.excel_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        btn_browse_excel = tk.Button(input_row, text="📂 찾아보기", command=self.browse_input_excel,
                                   font=('Segoe UI', 9), bg=self.colors['secondary'], fg='white',
                                   relief='flat', cursor='hand2', padx=20)
        btn_browse_excel.pack(side='right')
        
        # Output Folder
        output_frame = tk.Frame(content, bg=self.colors['white'])
        output_frame.pack(fill='x')
        
        tk.Label(output_frame, text="📁 출력 폴더:", 
                font=('Segoe UI', 10, 'bold'), bg=self.colors['white']).pack(anchor='w')
        
        output_row = tk.Frame(output_frame, bg=self.colors['white'])
        output_row.pack(fill='x', pady=(5, 0))
        
        self.output_entry = tk.Entry(output_row, textvariable=self.output_folder_path, 
                                    font=('Segoe UI', 10), relief='solid', bd=1)
        self.output_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        btn_browse_output = tk.Button(output_row, text="📂 찾아보기", command=self.browse_output_folder,
                                    font=('Segoe UI', 9), bg=self.colors['secondary'], fg='white',
                                    relief='flat', cursor='hand2', padx=20)
        btn_browse_output.pack(side='right')
    
    def _create_preset_frame_modern(self, parent):
        """프리셋 관리 프레임 (모던 스타일)"""
        content = self._create_modern_frame(parent, "프리셋 관리", "🔧")
        
        # 프리셋 선택
        select_frame = tk.Frame(content, bg=self.colors['white'])
        select_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(select_frame, text="💾 저장된 프리셋:", 
                font=('Segoe UI', 10, 'bold'), bg=self.colors['white']).pack(anchor='w')
        
        select_row = tk.Frame(select_frame, bg=self.colors['white'])
        select_row.pack(fill='x', pady=(5, 0))
        
        self.preset_combo = ttk.Combobox(select_row, font=('Segoe UI', 10), state="readonly", width=25)
        self.preset_combo.pack(side='left', padx=(0, 10))
        self.update_preset_combo()
        
        btn_apply = tk.Button(select_row, text="✅ 적용", command=self.apply_selected_preset,
                             font=('Segoe UI', 9), bg=self.colors['success'], fg='white',
                             relief='flat', cursor='hand2', padx=15)
        btn_apply.pack(side='left', padx=(0, 5))
        
        # 프리셋 저장
        save_frame = tk.Frame(content, bg=self.colors['white'])
        save_frame.pack(fill='x')
        
        tk.Label(save_frame, text="💼 새 프리셋 저장:", 
                font=('Segoe UI', 10, 'bold'), bg=self.colors['white']).pack(anchor='w')
        
        save_row = tk.Frame(save_frame, bg=self.colors['white'])
        save_row.pack(fill='x', pady=(5, 0))
        
        self.preset_name_entry = tk.Entry(save_row, font=('Segoe UI', 10), relief='solid', bd=1, width=25)
        self.preset_name_entry.pack(side='left', padx=(0, 10))
        
        btn_save = tk.Button(save_row, text="💾 저장", command=self.save_current_preset,
                           font=('Segoe UI', 9), bg=self.colors['warning'], fg='white',
                           relief='flat', cursor='hand2', padx=15)
        btn_save.pack(side='left')
    
    def _create_image_save_frame_modern(self, parent):
        """이미지 저장 옵션 프레임 (새로 추가)"""
        content = self._create_modern_frame(parent, "이미지 저장 설정", "🖼️")
        
        # 상세 이미지 저장 옵션
        save_frame = tk.Frame(content, bg=self.colors['white'])
        save_frame.pack(fill='x')
        
        check_frame = tk.Frame(save_frame, bg=self.colors['white'])
        check_frame.pack(anchor='w')
        
        self.save_images_check = tk.Checkbutton(check_frame, 
                                              text="📸 OCR 처리 이미지 상세 저장", 
                                              variable=self.save_detail_images,
                                              font=('Segoe UI', 10, 'bold'),
                                              bg=self.colors['white'], fg=self.colors['dark'],
                                              selectcolor=self.colors['light'],
                                              activebackground=self.colors['white'])
        self.save_images_check.pack(side='left')
        
        # 설명
        desc_label = tk.Label(save_frame, 
                            text="✅ 체크 시: 날짜/금리 영역 이미지를 상세하게 저장하여 OCR 결과 검증 가능\n❌ 해제 시: 전체 영역 이미지만 저장하여 디스크 공간 절약", 
                            font=('Segoe UI', 9), bg=self.colors['white'], fg=self.colors['dark'],
                            justify='left')
        desc_label.pack(anchor='w', pady=(10, 0))
    
    def _create_coordinates_group_modern(self, parent):
        """좌표 설정 그룹 (모던 스타일)"""
        content = self._create_modern_frame(parent, "좌표 및 영역 설정", "🎯")
        
        # 클릭 포인트
        click_frame = tk.Frame(content, bg=self.colors['white'])
        click_frame.pack(fill='x', pady=(0, 15))
        
        tk.Label(click_frame, text="🎯 클릭 포인트 (x, y):", 
                font=('Segoe UI', 10, 'bold'), bg=self.colors['white']).pack(anchor='w')
        
        click_row = tk.Frame(click_frame, bg=self.colors['white'])
        click_row.pack(fill='x', pady=(5, 0))
        
        tk.Entry(click_row, textvariable=self.click_x, font=('Segoe UI', 10), width=8, 
                relief='solid', bd=1).pack(side='left', padx=(0, 5))
        tk.Entry(click_row, textvariable=self.click_y, font=('Segoe UI', 10), width=8, 
                relief='solid', bd=1).pack(side='left', padx=(0, 10))
        
        tk.Button(click_row, text="📍 위치 지정", command=self.relocate_clickpoint,
                 font=('Segoe UI', 9), bg=self.colors['accent'], fg='white',
                 relief='flat', cursor='hand2', padx=15).pack(side='left')
        
        # 영역 설정들
        areas = [
            ("🔴 전체 영역", [self.allarea_x1, self.allarea_y1, self.allarea_x2, self.allarea_y2], self.relocate_allarea),
            ("🔵 날짜 영역", [self.datearea_x1, self.datearea_y1, self.datearea_x2, self.datearea_y2], self.relocate_datearea),
            ("⚪ 금리 영역", [self.ratearea_x1, self.ratearea_y1, self.ratearea_x2, self.ratearea_y2], self.relocate_ratearea)
        ]
        
        for area_name, vars_list, relocate_func in areas:
            area_frame = tk.Frame(content, bg=self.colors['white'])
            area_frame.pack(fill='x', pady=(0, 10))
            
            tk.Label(area_frame, text=f"{area_name} (x1, y1, x2, y2):", 
                    font=('Segoe UI', 10, 'bold'), bg=self.colors['white']).pack(anchor='w')
            
            area_row = tk.Frame(area_frame, bg=self.colors['white'])
            area_row.pack(fill='x', pady=(5, 0))
            
            for var in vars_list:
                tk.Entry(area_row, textvariable=var, font=('Segoe UI', 10), width=8, 
                        relief='solid', bd=1).pack(side='left', padx=(0, 5))
            
            tk.Button(area_row, text="🔲 영역 지정", command=relocate_func,
                     font=('Segoe UI', 9), bg=self.colors['secondary'], fg='white',
                     relief='flat', cursor='hand2', padx=15).pack(side='left', padx=(10, 0))
    
    def _create_timing_frame_modern(self, parent):
        """시간 설정 프레임 (모던 스타일)"""
        content = self._create_modern_frame(parent, "타이밍 설정", "⏱️")
        
        timing_row = tk.Frame(content, bg=self.colors['white'])
        timing_row.pack(fill='x')
        
        # 붙여넣기 딜레이
        paste_frame = tk.Frame(timing_row, bg=self.colors['white'])
        paste_frame.pack(side='left', fill='x', expand=True, padx=(0, 20))
        
        tk.Label(paste_frame, text="📋 붙여넣기 딜레이 (초):", 
                font=('Segoe UI', 10, 'bold'), bg=self.colors['white']).pack(anchor='w')
        tk.Entry(paste_frame, textvariable=self.paste_delay, font=('Segoe UI', 10), width=8, 
                relief='solid', bd=1).pack(anchor='w', pady=(5, 0))
        
        # 로딩 딜레이
        loading_frame = tk.Frame(timing_row, bg=self.colors['white'])
        loading_frame.pack(side='left', fill='x', expand=True)
        
        tk.Label(loading_frame, text="⏳ 로딩 딜레이 (초):", 
                font=('Segoe UI', 10, 'bold'), bg=self.colors['white']).pack(anchor='w')
        tk.Entry(loading_frame, textvariable=self.loading_delay, font=('Segoe UI', 10), width=8, 
                relief='solid', bd=1).pack(anchor='w', pady=(5, 0))
    
    def _create_action_frame_modern(self, parent):
        """미리보기 및 실행 프레임 (모던 스타일)"""
        content = self._create_modern_frame(parent, "미리보기 및 테스트", "👁️")
        
        # 버튼들을 그리드로 배치
        button_grid = tk.Frame(content, bg=self.colors['white'])
        button_grid.pack(fill='x')
        
        # 첫 번째 행
        row1 = tk.Frame(button_grid, bg=self.colors['white'])
        row1.pack(fill='x', pady=(0, 10))
        
        tk.Button(row1, text="👁️ 전체 영역 미리보기", command=self.show_area_preview,
                 font=('Segoe UI', 10, 'bold'), bg=self.colors['danger'], fg='white',
                 relief='flat', cursor='hand2', pady=8).pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        tk.Button(row1, text="💾 현재 설정 저장", command=self.quick_save_settings,
                 font=('Segoe UI', 10, 'bold'), bg=self.colors['warning'], fg='white',
                 relief='flat', cursor='hand2', pady=8).pack(side='left', fill='x', expand=True, padx=(5, 0))

    # ============================================
    # 컴팩트 레이아웃 프레임들
    # ============================================
    
    def _create_compact_frame(self, parent, title, icon="", height=None):
        """컴팩트 스타일 프레임 생성"""
        frame = tk.Frame(parent, bg=self.colors['white'], relief='solid', bd=1)
        if height:
            frame.configure(height=height)
            frame.pack_propagate(False)
        frame.pack(fill='both', expand=True, pady=2)
        
        # 헤더
        header = tk.Frame(frame, bg=self.colors['primary'], height=30)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        title_label = tk.Label(header, text=f"{icon} {title}", 
                             font=('Segoe UI', 9, 'bold'), 
                             bg=self.colors['primary'], fg='white')
        title_label.pack(side='left', padx=10, pady=5)
        
        # 컨텐츠 영역
        content = tk.Frame(frame, bg=self.colors['white'])
        content.pack(fill='both', expand=True, padx=8, pady=8)
        
        return content
    
    def _create_excel_frame_compact(self, parent):
        """파일 설정 프레임 (컴팩트)"""
        content = self._create_compact_frame(parent, "파일 설정", "📁", height=120)
        
        # Input Excel
        tk.Label(content, text="📊 Excel 파일:", font=('Segoe UI', 9, 'bold'), 
                bg=self.colors['white']).pack(anchor='w')
        
        input_row = tk.Frame(content, bg=self.colors['white'])
        input_row.pack(fill='x', pady=(2, 5))
        
        tk.Entry(input_row, textvariable=self.input_excel_path, font=('Segoe UI', 9), 
                relief='solid', bd=1).pack(side='left', fill='x', expand=True, padx=(0, 5))
        tk.Button(input_row, text="📂", command=self.browse_input_excel, font=('Segoe UI', 8),
                 bg=self.colors['secondary'], fg='white', relief='flat', width=3).pack(side='right')
        
        # Output Folder
        tk.Label(content, text="📁 출력 폴더:", font=('Segoe UI', 9, 'bold'), 
                bg=self.colors['white']).pack(anchor='w')
        
        output_row = tk.Frame(content, bg=self.colors['white'])
        output_row.pack(fill='x', pady=(2, 0))
        
        tk.Entry(output_row, textvariable=self.output_folder_path, font=('Segoe UI', 9), 
                relief='solid', bd=1).pack(side='left', fill='x', expand=True, padx=(0, 5))
        tk.Button(output_row, text="📂", command=self.browse_output_folder, font=('Segoe UI', 8),
                 bg=self.colors['secondary'], fg='white', relief='flat', width=3).pack(side='right')
    
    def _create_preset_frame_compact(self, parent):
        """프리셋 관리 프레임 (컴팩트)"""
        content = self._create_compact_frame(parent, "프리셋", "🔧", height=80)
        
        # 프리셋 선택
        preset_row = tk.Frame(content, bg=self.colors['white'])
        preset_row.pack(fill='x', pady=(0, 5))
        
        self.preset_combo = ttk.Combobox(preset_row, font=('Segoe UI', 8), state="readonly", width=15)
        self.preset_combo.pack(side='left', fill='x', expand=True, padx=(0, 2))
        self.update_preset_combo()
        
        tk.Button(preset_row, text="✅", command=self.apply_selected_preset, font=('Segoe UI', 8),
                 bg=self.colors['success'], fg='white', relief='flat', width=3).pack(side='right')
        
        # 프리셋 저장
        save_row = tk.Frame(content, bg=self.colors['white'])
        save_row.pack(fill='x')
        
        self.preset_name_entry = tk.Entry(save_row, font=('Segoe UI', 8), relief='solid', bd=1)
        self.preset_name_entry.pack(side='left', fill='x', expand=True, padx=(0, 2))
        
        tk.Button(save_row, text="💾", command=self.save_current_preset, font=('Segoe UI', 8),
                 bg=self.colors['warning'], fg='white', relief='flat', width=3).pack(side='right')
    
    def _create_theme_frame_compact(self, parent):
        """테마 선택 프레임 (컴팩트)"""
        content = self._create_compact_frame(parent, "테마", "🎨", height=60)
        
        theme_row = tk.Frame(content, bg=self.colors['white'])
        theme_row.pack(fill='x')
        
        self.theme_var = tk.StringVar()
        self.theme_combo = ttk.Combobox(theme_row, textvariable=self.theme_var, font=('Segoe UI', 8), 
                                       state="readonly", width=15)
        self.theme_combo['values'] = [theme['name'] for theme in self.available_themes.values()]
        # 현재 테마 이름으로 설정
        current_theme_name = self.available_themes[self.current_theme]['name']
        self.theme_var.set(current_theme_name)
        self.theme_combo.pack(side='left', fill='x', expand=True, padx=(0, 2))
        
        tk.Button(theme_row, text="🎨", command=self.apply_theme, font=('Segoe UI', 8),
                 bg=self.colors['accent'], fg='white', relief='flat', width=3).pack(side='right')
    
    def _create_coordinates_compact(self, parent):
        """좌표 설정 프레임 (컴팩트)"""
        content = self._create_compact_frame(parent, "좌표 및 영역 설정", "🎯", height=160)
        
        # 클릭 포인트
        click_frame = tk.Frame(content, bg=self.colors['white'])
        click_frame.pack(fill='x', pady=(0, 5))
        
        tk.Label(click_frame, text="🎯 클릭 포인트:", font=('Segoe UI', 9, 'bold'), 
                bg=self.colors['white']).pack(side='left')
        
        tk.Entry(click_frame, textvariable=self.click_x, font=('Segoe UI', 8), width=6, 
                relief='solid', bd=1).pack(side='left', padx=(5, 2))
        tk.Entry(click_frame, textvariable=self.click_y, font=('Segoe UI', 8), width=6, 
                relief='solid', bd=1).pack(side='left', padx=(0, 5))
        
        tk.Button(click_frame, text="📍", command=self.relocate_clickpoint, font=('Segoe UI', 8),
                 bg=self.colors['accent'], fg='white', relief='flat', width=3).pack(side='right')
        
        # 영역들 (3행으로 배치)
        areas = [
            ("🔴 전체", [self.allarea_x1, self.allarea_y1, self.allarea_x2, self.allarea_y2], self.relocate_allarea),
            ("🔵 날짜", [self.datearea_x1, self.datearea_y1, self.datearea_x2, self.datearea_y2], self.relocate_datearea),
            ("⚪ 금리", [self.ratearea_x1, self.ratearea_y1, self.ratearea_x2, self.ratearea_y2], self.relocate_ratearea)
        ]
        
        for area_name, vars_list, relocate_func in areas:
            area_frame = tk.Frame(content, bg=self.colors['white'])
            area_frame.pack(fill='x', pady=2)
            
            tk.Label(area_frame, text=f"{area_name}:", font=('Segoe UI', 9, 'bold'), 
                    bg=self.colors['white'], width=8).pack(side='left')
            
            for var in vars_list:
                tk.Entry(area_frame, textvariable=var, font=('Segoe UI', 8), width=5, 
                        relief='solid', bd=1).pack(side='left', padx=1)
            
            tk.Button(area_frame, text="🔲", command=relocate_func, font=('Segoe UI', 8),
                     bg=self.colors['secondary'], fg='white', relief='flat', width=3).pack(side='right')
    
    def _create_timing_frame_compact(self, parent):
        """타이밍 설정 프레임 (컴팩트)"""
        content = self._create_compact_frame(parent, "타이밍 설정", "⏱️", height=80)
        
        # 붙여넣기 딜레이
        paste_row = tk.Frame(content, bg=self.colors['white'])
        paste_row.pack(fill='x', pady=(0, 5))
        
        tk.Label(paste_row, text="📋 붙여넣기:", font=('Segoe UI', 9, 'bold'), 
                bg=self.colors['white']).pack(side='left')
        tk.Entry(paste_row, textvariable=self.paste_delay, font=('Segoe UI', 8), width=6, 
                relief='solid', bd=1).pack(side='right')
        
        # 로딩 딜레이
        loading_row = tk.Frame(content, bg=self.colors['white'])
        loading_row.pack(fill='x')
        
        tk.Label(loading_row, text="⏳ 로딩:", font=('Segoe UI', 9, 'bold'), 
                bg=self.colors['white']).pack(side='left')
        tk.Entry(loading_row, textvariable=self.loading_delay, font=('Segoe UI', 8), width=6, 
                relief='solid', bd=1).pack(side='right')
    
    def _create_image_save_frame_compact(self, parent):
        """이미지 저장 옵션 프레임 (컴팩트)"""
        content = self._create_compact_frame(parent, "이미지 옵션", "🖼️", height=60)
        
        self.save_images_check = tk.Checkbutton(content, 
                                              text="📸 상세 이미지 저장", 
                                              variable=self.save_detail_images,
                                              font=('Segoe UI', 9, 'bold'),
                                              bg=self.colors['white'], fg=self.colors['dark'],
                                              selectcolor=self.colors['light'],
                                              activebackground=self.colors['white'])
        self.save_images_check.pack(anchor='w')
    
    def _create_action_frame_compact(self, parent):
        """액션 프레임 (컴팩트)"""
        content = self._create_compact_frame(parent, "실행", "🚀", height=140)
        
        # 미리보기 버튼
        tk.Button(content, text="👁️ 영역 미리보기", command=self.show_area_preview,
                 font=('Segoe UI', 9, 'bold'), bg=self.colors['danger'], fg='white',
                 relief='flat', cursor='hand2', pady=5).pack(fill='x', pady=(0, 5))
        
        # 설정 저장
        tk.Button(content, text="💾 설정 저장", command=self.quick_save_settings,
                 font=('Segoe UI', 9, 'bold'), bg=self.colors['warning'], fg='white',
                 relief='flat', cursor='hand2', pady=5).pack(fill='x', pady=(0, 5))
        
        # 설정 불러오기
        tk.Button(content, text="📥 설정 불러오기", command=self.load_last_settings,
                 font=('Segoe UI', 9, 'bold'), bg=self.colors['secondary'], fg='white',
                 relief='flat', cursor='hand2', pady=5).pack(fill='x')

    def apply_theme(self):
        """테마 즉시 적용 - 모든 UI 요소에 실시간 반영"""
        try:
            # 선택된 테마 이름에서 키 찾기
            selected_name = self.theme_var.get()
            selected_theme_key = None
            
            for key, theme_data in self.available_themes.items():
                if theme_data['name'] == selected_name:
                    selected_theme_key = key
                    break
            
            if selected_theme_key:
                self.current_theme = selected_theme_key
                self.colors = self.available_themes[selected_theme_key].copy()
                
                # 전체 UI 즉시 재구성
                self.rebuild_ui_instantly()
                
                # 설정에 테마 저장
                self.settings_manager.set_advanced('ui_theme', selected_theme_key)
                
                self.logger.info(f"테마 즉시 적용됨: {selected_name}")
                
        except Exception as e:
            self.logger.error(f"테마 적용 중 오류: {e}")
    
    def rebuild_ui_instantly(self):
        """UI 즉시 재구성 - 현재 상태 유지하면서"""
        try:
            # 메인 창 배경색 변경
            self.configure(bg=self.colors['surface'])
            
            # 기존 모든 위젯 제거 (메뉴바 제외)
            for child in self.winfo_children():
                if not isinstance(child, tk.Menu):
                    child.destroy()
            
            # UI 완전히 다시 생성
            self._build_ui()
            
            # 기존 설정값들 유지 (중요!)
            current_settings = self.get_current_settings()
            self.apply_settings(current_settings)
            
        except Exception as e:
            self.logger.error(f"UI 재구성 중 오류: {e}")

    ######################
    # 프리셋 관리 메서드들 #
    ######################
    def update_preset_combo(self):
        """프리셋 콤보박스 업데이트"""
        preset_names = self.settings_manager.get_preset_names()
        self.preset_combo['values'] = preset_names
        if preset_names:
            self.preset_combo.current(0)

    def apply_selected_preset(self):
        """선택된 프리셋 적용"""
        selected = self.preset_combo.get()
        if selected:
            preset = self.settings_manager.apply_preset(selected)
            if preset:
                self.apply_settings(preset)
                messagebox.showinfo("정보", f"프리셋 '{selected}'이 적용되었습니다.")

    def save_current_preset(self):
        """현재 설정을 프리셋으로 저장"""
        if hasattr(self, 'preset_name_entry'):
            name = self.preset_name_entry.get().strip()
            if name == "새 프리셋 이름" or not name:
                messagebox.showwarning("경고", "유효한 프리셋 이름을 입력해주세요.")
                return
        else:
            name = simpledialog.askstring("프리셋 저장", "프리셋 이름을 입력하세요:")
            if not name:
                return
                
        settings = self.get_current_settings()
        self.settings_manager.save_preset(name, settings)
        self.update_preset_combo()
        
        if hasattr(self, 'preset_name_entry'):
            self.preset_name_entry.delete(0, tk.END)
            self.preset_name_entry.insert(0, "새 프리셋 이름")
            
        messagebox.showinfo("완료", f"'{name}' 프리셋이 저장되었습니다.")

    def get_current_settings(self):
        """현재 설정 반환 (통합 설정)"""
        basic_settings = {
            'click_point': (self.click_x.get(), self.click_y.get()),
            'all_area': (self.allarea_x1.get(), self.allarea_y1.get(), 
                        self.allarea_x2.get(), self.allarea_y2.get()),
            'date_area': (self.datearea_x1.get(), self.datearea_y1.get(),
                         self.datearea_x2.get(), self.datearea_y2.get()),
            'rate_area': (self.ratearea_x1.get(), self.ratearea_y1.get(),
                         self.ratearea_x2.get(), self.ratearea_y2.get()),
            'delays': {'paste': self.paste_delay.get(), 'loading': self.loading_delay.get()},
            'save_detail_images': self.save_detail_images.get()  # 이미지 저장 옵션 추가
        }
        
        # 고급 설정도 함께 저장
        basic_settings['advanced'] = self.settings_manager.data['advanced'].copy()
        return basic_settings

    def apply_settings(self, settings):
        """설정 적용 (통합 설정)"""
        # 클릭 포인트
        if 'click_point' in settings:
            self.click_x.set(settings['click_point'][0])
            self.click_y.set(settings['click_point'][1])
        
        # 영역들
        if 'all_area' in settings:
            area = settings['all_area']
            self.allarea_x1.set(area[0])
            self.allarea_y1.set(area[1])
            self.allarea_x2.set(area[2])
            self.allarea_y2.set(area[3])
        
        if 'date_area' in settings:
            area = settings['date_area']
            self.datearea_x1.set(area[0])
            self.datearea_y1.set(area[1])
            self.datearea_x2.set(area[2])
            self.datearea_y2.set(area[3])
        
        if 'rate_area' in settings:
            area = settings['rate_area']
            self.ratearea_x1.set(area[0])
            self.ratearea_y1.set(area[1])
            self.ratearea_x2.set(area[2])
            self.ratearea_y2.set(area[3])
        
        # 딜레이
        if 'delays' in settings:
            self.paste_delay.set(settings['delays'].get('paste', 0.5))
            self.loading_delay.set(settings['delays'].get('loading', 2.5))
        
        # 이미지 저장 옵션
        if 'save_detail_images' in settings:
            self.save_detail_images.set(settings['save_detail_images'])
        
        # 고급 설정 적용
        if 'advanced' in settings:
            self.settings_manager.data['advanced'].update(settings['advanced'])
            self.update_advanced_ui()

    def quick_save_settings(self):
        """통합 설정 저장"""
        settings = self.get_current_settings()
        self.settings_manager.save_current_settings(settings)
        self.logger.info("설정이 저장되었습니다")

    def load_last_settings(self):
        """통합 설정 불러오기"""
        try:
            settings = self.settings_manager.get_current_settings()
            if settings:
                self.apply_settings(settings)
                self.logger.info("설정이 불러와졌습니다")
        except Exception as e:
            self.logger.error(f"설정 불러오기 실패: {e}")

    ######################
    # 새로 추가된 설정 관리 메서드들 #
    ######################
    def on_ocr_setting_changed(self, *args):
        """OCR 설정 변경 시 호출"""
        # OCR 엔진 재초기화가 필요한 경우를 위해 플래그 설정
        if hasattr(self, 'ocr_gpu_var'):
            self.ocr_needs_reinit = True

    def save_advanced_settings(self):
        """고급 설정 저장 (통합됨)"""
        self.quick_save_settings()  # 통합 설정으로 저장
        messagebox.showinfo("성공", "설정이 저장되었습니다.")

    def reset_advanced_settings(self):
        """고급 설정 초기화"""
        if messagebox.askyesno("확인", "모든 고급 설정을 초기값으로 되돌리시겠습니까?"):
            self.settings_manager.reset_advanced_settings()
            self.update_advanced_ui()
            messagebox.showinfo("완료", "고급 설정이 초기화되었습니다.")

    def update_advanced_ui(self):
        """고급 설정 UI 업데이트"""
        try:
            # OCR 설정 UI 업데이트
            if hasattr(self, 'ocr_gpu_var'):
                self.ocr_gpu_var.set(self.settings_manager.get_advanced('ocr_gpu_enabled', False))
            if hasattr(self, 'confidence_var'):
                self.confidence_var.set(self.settings_manager.get_advanced('ocr_confidence_threshold', 0.3))
            if hasattr(self, 'max_attempts_var'):
                self.max_attempts_var.set(self.settings_manager.get_advanced('ocr_max_attempts', 3))
            if hasattr(self, 'detail_level_var'):
                self.detail_level_var.set(self.settings_manager.get_advanced('ocr_detail_level', 0))
            
            # 이미지 처리 설정
            if hasattr(self, 'resize_factor_var'):
                self.resize_factor_var.set(self.settings_manager.get_advanced('image_resize_factor', 4))
            if hasattr(self, 'denoise_var'):
                self.denoise_var.set(self.settings_manager.get_advanced('image_denoise_strength', 2))
            if hasattr(self, 'contrast_var'):
                self.contrast_var.set(self.settings_manager.get_advanced('image_contrast_enhancement', True))
            if hasattr(self, 'sharpening_var'):
                self.sharpening_var.set(self.settings_manager.get_advanced('image_sharpening', True))
            if hasattr(self, 'binary_method_var'):
                self.binary_method_var.set(self.settings_manager.get_advanced('image_binarization_method', 'adaptive'))
            
            # 자동화 및 신뢰도 설정
            if hasattr(self, 'click_interval_var'):
                self.click_interval_var.set(self.settings_manager.get_advanced('click_interval', 0.1))
            if hasattr(self, 'date_confidence_var'):
                self.date_confidence_var.set(self.settings_manager.get_advanced('min_date_confidence', 0.2))
            if hasattr(self, 'rate_confidence_var'):
                self.rate_confidence_var.set(self.settings_manager.get_advanced('min_rate_confidence', 0.2))
            
        except Exception as e:
            self.logger.error(f"고급 설정 UI 업데이트 실패: {e}")



    def clear_log(self):
        """로그 지우기"""
        if hasattr(self, 'log_text'):
            self.log_text.config(state='normal')
            self.log_text.delete(1.0, tk.END)
            self.log_text.config(state='disabled')

    def save_log(self):
        """로그 파일로 저장"""
        if hasattr(self, 'log_text'):
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

    def update_status_display(self, message):
        """상태 표시 업데이트 - 로그로 통합"""
        self.logger.info(f"상태: {message}")

    def update_log_display(self, message):
        """로그 표시 업데이트"""
        if hasattr(self, 'log_text'):
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, f"{datetime.now().strftime('%H:%M:%S')} - {message}\n")
            self.log_text.see(tk.END)
            self.log_text.config(state='disabled')

    def show_area_preview(self):
        """영역 미리보기 표시"""
        areas_info = {
            "click_point": (self.click_x.get(), self.click_y.get()),
            "all_area": (self.allarea_x1.get(), self.allarea_y1.get(), 
                        self.allarea_x2.get(), self.allarea_y2.get()),
            "date_area": (self.datearea_x1.get(), self.datearea_y1.get(),
                         self.datearea_x2.get(), self.datearea_y2.get()),
            "rate_area": (self.ratearea_x1.get(), self.ratearea_y1.get(),
                         self.ratearea_x2.get(), self.ratearea_y2.get())
        }
        
        # 임시 미리보기 표시 (3초 후 자동 종료)
        AreaVisualizationOverlay(self, areas_info, auto_close=True)
        


    ######################
    # Browse 버튼 동작들 #
    ######################
    def browse_input_excel(self):
        file_path = filedialog.askopenfilename(
            title="엑셀 파일 선택",
            filetypes=[("Excel files", "*.xlsx;*.xls")]
        )
        if file_path:
            self.input_excel_path.set(file_path)
            # 선택된 엑셀 폴더를 기본 Output으로
            base_path = os.path.dirname(file_path)
            self.output_folder_path.set(base_path)

    def browse_output_folder(self):
        folder_path = filedialog.askdirectory(title="출력 폴더 선택")
        if folder_path:
            self.output_folder_path.set(folder_path)

    ##############################
    # Relocate(영역/포인트) 부분 #
    ##############################
    def relocate_clickpoint(self):
        """ClickPoint를 마우스 한 번으로 지정"""
        overlay = PointCaptureOverlay(self, color="red")
        self.wait_window(overlay)
        if overlay.click_x is not None:
            self.click_x.set(overlay.click_x)
            self.click_y.set(overlay.click_y)

    def relocate_allarea(self):
        overlay = DragCaptureOverlay(self, color="red")
        self.wait_window(overlay)
        if overlay.x1 is not None:
            self.allarea_x1.set(overlay.x1)
            self.allarea_y1.set(overlay.y1)
            self.allarea_x2.set(overlay.x2)
            self.allarea_y2.set(overlay.y2)

    def relocate_datearea(self):
        overlay = DragCaptureOverlay(self, color="blue")
        self.wait_window(overlay)
        if overlay.x1 is not None:
            self.datearea_x1.set(overlay.x1)
            self.datearea_y1.set(overlay.y1)
            self.datearea_x2.set(overlay.x2)
            self.datearea_y2.set(overlay.y2)

    def relocate_ratearea(self):
        overlay = DragCaptureOverlay(self, color="white")
        self.wait_window(overlay)
        if overlay.x1 is not None:
            self.ratearea_x1.set(overlay.x1)
            self.ratearea_y1.set(overlay.y1)
            self.ratearea_x2.set(overlay.x2)
            self.ratearea_y2.set(overlay.y2)

    ######################
    # 작업 제어 메서드들 #
    ######################
    def stop_processing(self):
        """작업 중단"""
        if self.work_controller.is_running:
            message = self.work_controller.stop_work()
            self.message_queue.put(("log", message))
            
    def _on_work_complete(self, summary):
        """작업 완료 처리"""
        self.work_controller.reset()
        self.progress_tracker.hide()
        self.run_btn.config(text="🚀 OCR 처리 시작", state='normal')
        # 현재 처리 중인 인덱스 리셋
        self.current_processing_index = -1
        self.refresh_grid()
        messagebox.showinfo("처리 완료", summary)
        # 설정 자동 저장
        self.quick_save_settings()
        
    def _on_work_stopped(self):
        """작업 중단 처리"""
        self.work_controller.reset()
        self.progress_tracker.hide()
        self.run_btn.config(text="🚀 OCR 처리 시작", state='normal')
        # 현재 처리 중인 인덱스 리셋
        self.current_processing_index = -1
        self.refresh_grid()
        messagebox.showinfo("중단됨", "작업이 중단되었습니다.")
    
    def _handle_grid_update(self, data):
        """그리드 업데이트 처리"""
        try:
            if len(data) >= 2:
                update_type = data[0]
                grid_index = data[1]
                
                if update_type == "processing":
                    # 현재 처리 중인 행 업데이트
                    self.current_processing_index = grid_index
                    if 0 <= grid_index < len(self.excel_data):
                        self.excel_data[grid_index]['상태'] = '처리 중'
                    self.refresh_grid()
                    
                elif update_type == "complete" and len(data) >= 5:
                    # 완료된 행 업데이트
                    date_result = data[2]
                    rate_result = data[3]
                    status = data[4]
                    
                    if 0 <= grid_index < len(self.excel_data):
                        if date_result:
                            self.excel_data[grid_index]['날짜'] = date_result
                        if rate_result:
                            self.excel_data[grid_index]['금리'] = rate_result
                        self.excel_data[grid_index]['상태'] = status
                    self.refresh_grid()
                    
                elif update_type == "error" and len(data) >= 5:
                    # 오류 행 업데이트
                    status = data[4] if len(data) > 4 else "오류"
                    
                    if 0 <= grid_index < len(self.excel_data):
                        self.excel_data[grid_index]['상태'] = status
                    self.refresh_grid()
                    
        except Exception as e:
            self.logger.error(f"그리드 업데이트 중 오류: {e}")

    ######################
    # 도움말 메서드들 #
    ######################
    def show_shortcuts(self):
        """키보드 단축키 도움말"""
        shortcuts = """
🎹 키보드 단축키:

📋 기본 제어:
• F5        : OCR 처리 실행/중단
• Escape    : 처리 중단
• F1        : 단축키 도움말 (이 창)

⚙️ 설정 관리:
• Ctrl+S    : 모든 설정 저장 (기본 + 고급)
• Ctrl+L    : 마지막 설정 불러오기

👁️ 영역 시각화:
• 기본 설정 탭의 "영역 미리보기" 버튼 사용
• 🔴 전체 영역 미리보기: 3초간 설정된 모든 영역 표시 (클릭 포인트, 전체/날짜/금리 영역)

🔧 고급 기능:
• 고급 설정 탭에서 OCR 엔진 세부 조정
• 이미지 전처리 파라미터 조정
• 신뢰도 임계값 설정
• 자동화 속도 및 재시도 설정
• 품질 관리 및 검증 설정

💡 사용 팁:
- 고급 설정 탭에서 OCR 품질을 세밀하게 조정하세요
- 영역 미리보기로 캡처 영역을 정확히 확인하세요
- 로그/상태 탭에서 실시간 진행 상황을 모니터링하세요
- 프리셋 기능으로 자주 사용하는 설정을 저장하세요
- 신뢰도 임계값을 조정하여 OCR 정확도를 향상시키세요
        """
        messagebox.showinfo("키보드 단축키 및 고급 기능", shortcuts)

    def show_about(self):
        """프로그램 정보"""
        about_text = """
📋 Check Capture OCR - EasyOCR Edition (고급 버전)

📦 기술 스택:
• OCR 엔진: EasyOCR (한국어/영어 지원, GPU 가속 옵션)
• GUI 프레임워크: tkinter with ttk (탭 구조)
• 이미지 처리: PIL (Pillow), OpenCV (고급 전처리)
• 자동화 도구: pyautogui, pyperclip
• 데이터 처리: pandas, openpyxl
• 수치 연산: numpy
• 멀티스레딩: threading (백그라운드 처리)

🎯 주요 기능:
• 엑셀 파일에서 종목 정보 자동 읽기
• 지능형 스크린샷 캡처 시스템
• 고급 OCR 엔진으로 날짜/금리 정확 추출
• 실시간 이미지 전처리 및 미리보기
• 결과를 엑셀 파일로 자동 저장
• 백그라운드 처리로 GUI 완전 응답성 보장

🔧 고급 설정 기능:
• OCR 엔진 세부 조정 (GPU, 신뢰도, 시도횟수)
• 이미지 전처리 파라미터 조정 (크기, 노이즈, 대비, 이진화)
• 자동화 설정 (클릭간격, 타이핑속도, 재시도)
• 품질 관리 (결과 검증, 자동 수정, 신뢰도 임계값)
• 고급 제어 (배치 크기, 자동저장 간격, 백업)

🎮 실시간 제어:
• 처리 중 개별 항목 건너뛰기 (F2)
• 실시간 미리보기 토글 (F3)
• 건너뛸 종목 목록 사전 설정
• 실시간 로그 및 상태 모니터링
• 처리 통계 실시간 표시

⌨️ 키보드 단축키:
• F5: 실행/중단  • F1: 도움말  • ESC: 중단
• F2: 현재 항목 건너뛰기  • F3: 미리보기 토글
• Ctrl+S: 모든 설정 저장  • Ctrl+L: 설정 불러오기

💡 핵심 개선사항:
• 완전한 멀티스레딩 아키텍처로 GUI 절대 무응답 방지
• 탭 구조 UI로 기능별 체계적 분류
• 고급 설정으로 OCR 품질 세밀 조정 가능
• 실시간 제어로 작업 중에도 완전한 사용자 제어권
• 프리셋 시스템으로 설정 관리 효율화
• 실시간 미리보기로 처리 과정 투명화
        """
        messagebox.showinfo("프로그램 정보", about_text)

    ##############################
    # 실행 버튼 동작: OCR 로직
    ##############################
    def run_ocr_process(self):
        """OCR 프로세스 실행 - 별도 스레드에서 실행"""
        if self.work_controller.is_running:
            self.stop_processing()
            return
            
        if not self.validate_inputs():
            return
            
        # UI 상태 변경
        self.work_controller.start_work()
        self.progress_tracker.show()
        self.run_btn.config(text="⏹️ 처리 중단", state='normal')
        
        # 워커 스레드 시작
        self.worker_thread = threading.Thread(target=self.execute_ocr_workflow, daemon=True)
        self.worker_thread.start()

    def validate_inputs(self):
        """입력값 검증"""
        input_file = self.input_excel_path.get().strip()
        output_dir = self.output_folder_path.get().strip()
        
        if not input_file or not os.path.exists(input_file):
            messagebox.showwarning("경고", "유효한 Input Excel 파일 경로를 지정하세요.")
            return False
        if not output_dir or not os.path.isdir(output_dir):
            messagebox.showwarning("경고", "유효한 Output 폴더를 지정하세요.")
            return False
        if not self.ocr_reader:
            messagebox.showerror("오류", "OCR 엔진이 초기화되지 않았습니다.")
            return False
        return True

    def execute_ocr_workflow(self):
        """OCR 워크플로우 실행 - 그리드 데이터 기반"""
        try:
            output_dir = self.output_folder_path.get().strip()
            
            # 그리드 데이터 확인
            if not self.excel_data:
                self.message_queue.put(("error", "처리할 데이터가 없습니다. Excel을 로드하거나 데이터를 입력해주세요."))
                return

            paste_d = self.paste_delay.get()
            load_d = self.loading_delay.get()

            # 좌표값들 가져오기
            click_x = self.click_x.get()
            click_y = self.click_y.get()

            x1_all = self.allarea_x1.get()
            y1_all = self.allarea_y1.get()
            x2_all = self.allarea_x2.get()
            y2_all = self.allarea_y2.get()

            x1_date = self.datearea_x1.get()
            y1_date = self.datearea_y1.get()
            x2_date = self.datearea_x2.get()
            y2_date = self.datearea_y2.get()

            x1_rate = self.ratearea_x1.get()
            y1_rate = self.ratearea_y1.get()
            x2_rate = self.ratearea_x2.get()
            y2_rate = self.ratearea_y2.get()

            # output 디렉토리에 이미지 저장 폴더 생성
            save_folder = os.path.join(output_dir, "ocr_images")
            os.makedirs(save_folder, exist_ok=True)

            # 처리할 데이터 개수
            total_items = len(self.excel_data)
            current_item = 0
            processed_count = 0
            
            # 그리드 데이터로 처리 - 매 종목마다 즉시 OCR 처리
            for grid_index, row_data in enumerate(self.excel_data):
                # 중단 체크
                if self.work_controller.is_stopped:
                    self.message_queue.put(("log", "사용자가 처리를 중단했습니다"))
                    self.message_queue.put(("stopped", None))
                    return

                current_item += 1
                stock_code = row_data['종목코드'].strip()
                stock_name = row_data['종목명'].strip()
                
                # 현재 처리 중인 행 인덱스 업데이트
                self.current_processing_index = grid_index
                self.message_queue.put(("grid_update", ("processing", grid_index)))

                # 현재 항목 정보 업데이트
                current_item_text = f"처리 중: {stock_code} ({stock_name})"
                
                # 진행 상황 업데이트
                self.message_queue.put(("progress", (
                    current_item, total_items, 
                    f"처리 중: {stock_code} ({stock_name})", current_item_text
                )))
                
                # 상태 업데이트
                self.message_queue.put(("status", f"현재 처리 중: {stock_code} - {stock_name}"))

                if stock_code and stock_name:
                    # 건너뛰기 플래그 초기화
                    self.work_controller.skip_current = False
                    
                    try:
                        # 1단계: 스크린샷 캡처
                        self.message_queue.put(("log", f"[{stock_code}] 스크린샷 캡처 중..."))
                        date_path, rate_path = self.capture_screenshots(
                            stock_code, save_folder, click_x, click_y, paste_d, load_d,
                            x1_all, y1_all, x2_all, y2_all,
                            x1_date, y1_date, x2_date, y2_date,
                            x1_rate, y1_rate, x2_rate, y2_rate
                        )
                        
                        # 건너뛰기 체크
                        if self.work_controller.skip_current:
                            self.message_queue.put(("log", f"종목 {stock_code}를 사용자 요청으로 건너뜁니다"))
                            self.message_queue.put(("grid_update", ("error", grid_index, "", "", "건너뜀")))
                            continue
                        
                        # 중단되었거나 스크린샷 실패시 건너뛰기
                        if date_path is None or rate_path is None:
                            if self.work_controller.is_stopped:
                                break
                            self.message_queue.put(("grid_update", ("error", grid_index, "", "", "캡처 실패")))
                            continue
                        
                        # 2단계: 즉시 OCR 처리
                        if date_path and rate_path:
                            self.message_queue.put(("log", f"[{stock_code}] OCR 처리 중..."))
                            
                            # 개별 OCR 처리
                            date_result, rate_result = self.process_single_ocr(grid_index, date_path, rate_path)
                            
                            # 3단계: 즉시 그리드 업데이트
                            if date_result or rate_result:
                                status = "완료"
                                self.message_queue.put(("grid_update", ("complete", grid_index, date_result, rate_result, status)))
                                self.message_queue.put(("log", f"[{stock_code}] 완료 - 날짜: '{date_result}', 금리: '{rate_result}'"))
                                processed_count += 1
                            else:
                                self.message_queue.put(("grid_update", ("error", grid_index, "", "", "OCR 실패")))
                                self.message_queue.put(("log", f"[{stock_code}] OCR 결과 없음"))

                    except Exception as e:
                        self.message_queue.put(("error", f"종목 {stock_code} 처리 중 오류: {e}"))
                        # 오류 상태로 그리드 업데이트
                        self.message_queue.put(("grid_update", ("error", grid_index, "", "", "처리 오류")))
                        continue

            # 최종 결과 저장 및 요약
            if not self.work_controller.is_stopped:
                # 그리드 데이터를 Excel로 저장 (선택사항)
                input_file = self.input_excel_path.get().strip()
                if input_file:
                    new_file_path = os.path.splitext(input_file)[0] + '_updated.xlsx'
                    self.message_queue.put(("log", f"Excel 파일로 내보내기: {new_file_path}"))
                    
                    try:
                        # 그리드 데이터를 DataFrame으로 변환
                        export_data = []
                        for row in self.excel_data:
                            export_data.append({
                                '종목코드': row['종목코드'],
                                '종목명': row['종목명'],
                                '날짜_OCR': row['날짜'],
                                '표면금리_OCR': row['금리'],
                                '처리상태': row['상태']
                            })
                        
                        df = pd.DataFrame(export_data)
                        with pd.ExcelWriter(new_file_path, engine='openpyxl') as writer:
                            df.to_excel(writer, sheet_name='OCR_Results', index=False)
                        self.message_queue.put(("log", f"Excel 파일 저장 완료: {new_file_path}"))
                    except Exception as e:
                        self.message_queue.put(("error", f"Excel 파일 저장 실패: {e}"))

                self.message_queue.put(("log", "모든 종목 처리 완료"))
                
                # 결과 요약 생성
                summary = f"""📊 OCR 처리 완료!

🔢 총 처리 항목: {total_items}개
✅ 성공적으로 처리: {processed_count}개
📁 결과 파일: 그리드에서 확인 및 Excel로 내보내기 완료

📝 상세 로그는 하단 로그 영역에서 확인 가능합니다."""
                
                self.message_queue.put(("complete", summary))
            elif self.work_controller.is_stopped:
                self.message_queue.put(("stopped", None))
            else:
                self.message_queue.put(("complete", "처리할 데이터가 없습니다."))
                
        except Exception as e:
            self.message_queue.put(("error", f"OCR 처리 중 오류: {e}"))
            self.message_queue.put(("stopped", None))

    def capture_screenshots(self, stock_code, save_folder, click_x, click_y, paste_d, load_d,
                           x1_all, y1_all, x2_all, y2_all,
                           x1_date, y1_date, x2_date, y2_date,
                           x1_rate, y1_rate, x2_rate, y2_rate):
        """스크린샷 캡처 (이미지 저장 옵션 적용)"""
        # 중단 체크
        if self.work_controller.is_stopped:
            return None, None
            
        # 클립보드에 종목코드 복사
        pyperclip.copy(stock_code)

        # 특정 좌표에서 더블클릭 (고급 설정 적용)
        click_interval = self.settings_manager.get_advanced('click_interval', 0.1)
        pyautogui.click(x=click_x, y=click_y, clicks=2, interval=click_interval)

        # 중단 체크 (붙여넣기 전)
        if self.work_controller.is_stopped:
            return None, None

        # 붙여넣기
        time.sleep(paste_d)
        pyautogui.hotkey('ctrl', 'v')

        # 중단 체크 (로딩 대기 전)
        if self.work_controller.is_stopped:
            return None, None

        # 화면 로딩 대기 (100ms씩 나누어 중단 체크)
        total_sleep = load_d
        step_sleep = 0.1
        slept = 0
        while slept < total_sleep:
            if self.work_controller.is_stopped:
                return None, None
            current_sleep = min(step_sleep, total_sleep - slept)
            time.sleep(current_sleep)
            slept += current_sleep

        safe_stock_code = stock_code.replace('/', '_').replace('\\', '_')

        # 중단 체크 (스크린샷 전)
        if self.work_controller.is_stopped:
            return None, None

        # 상세 이미지 저장 옵션에 따라 처리
        save_details = self.save_detail_images.get()
        
        # AllArea 스크린샷 (항상 저장)
        width_all = x2_all - x1_all
        height_all = y2_all - y1_all
        screenshot_all = pyautogui.screenshot(region=(x1_all, y1_all, width_all, height_all))
        allarea_path = os.path.join(save_folder, f"{safe_stock_code}.png")
        screenshot_all.save(allarea_path)
        self.message_queue.put(("log", f"전체 영역 이미지 저장: {allarea_path}"))

        # DateArea와 RateArea 스크린샷 처리
        date_path = None
        rate_path = None
        
        if save_details:
            # 상세 이미지 저장 모드: 별도 파일로 저장
            width_date = x2_date - x1_date
            height_date = y2_date - y1_date
            screenshot_date = pyautogui.screenshot(region=(x1_date, y1_date, width_date, height_date))
            date_path = os.path.join(save_folder, f"{safe_stock_code}_date.png")
            screenshot_date.save(date_path)
            self.message_queue.put(("log", f"날짜 영역 이미지 저장: {date_path}"))

            width_rate = x2_rate - x1_rate
            height_rate = y2_rate - y1_rate
            screenshot_rate = pyautogui.screenshot(region=(x1_rate, y1_rate, width_rate, height_rate))
            rate_path = os.path.join(save_folder, f"{safe_stock_code}_rate.png")
            screenshot_rate.save(rate_path)
            self.message_queue.put(("log", f"금리 영역 이미지 저장: {rate_path}"))
        else:
            # 간단 모드: 메모리에서만 캡처 (임시 파일 없음)
            width_date = x2_date - x1_date
            height_date = y2_date - y1_date
            screenshot_date = pyautogui.screenshot(region=(x1_date, y1_date, width_date, height_date))
            
            width_rate = x2_rate - x1_rate
            height_rate = y2_rate - y1_rate
            screenshot_rate = pyautogui.screenshot(region=(x1_rate, y1_rate, width_rate, height_rate))
            
            # 임시 메모리 이미지를 OCR 처리에 전달하기 위해 PIL 이미지 객체로 반환
            date_path = screenshot_date  # PIL Image 객체
            rate_path = screenshot_rate  # PIL Image 객체
            
            self.message_queue.put(("log", f"메모리에서 날짜/금리 영역 처리 (디스크 저장 없음)"))

        return date_path, rate_path

    def perform_ocr(self, results):
        """
        EasyOCR을 사용한 OCR 처리 (개선된 버전)
        
        results: (index, date_path, rate_path) 형태의 튜플 목록
        return: [(index, date_text, rate_text), ...]
        """
        ocr_results = []
        total_ocr = len(results)
        
        for i, (index, date_path, rate_path) in enumerate(results):
            # 중단 체크
            if self.work_controller.is_stopped:
                break
                
            date_text_clean = ''
            rate_text_clean = ''

            # 진행 상황 업데이트
            self.message_queue.put(("progress", (
                i + 1, total_ocr, f"OCR 처리 중... ({i + 1}/{total_ocr})", f"이미지 {i + 1} 분석 중"
            )))

            try:
                # Date 이미지 처리 (파일 또는 메모리 이미지)
                if date_path is not None:
                    if isinstance(date_path, str):
                        # 파일 경로인 경우
                        if os.path.exists(date_path):
                            self.message_queue.put(("log", f"Date 이미지 파일 처리 중: {date_path}"))
                            date_text_clean = self.extract_date_with_multiple_attempts(date_path)
                    else:
                        # PIL 이미지 객체인 경우 (메모리 모드)
                        self.message_queue.put(("log", f"Date 이미지 메모리 처리 중"))
                        date_text_clean = self.extract_date_with_multiple_attempts_from_image(date_path)

                # Rate 이미지 처리 (파일 또는 메모리 이미지)
                if rate_path is not None:
                    if isinstance(rate_path, str):
                        # 파일 경로인 경우
                        if os.path.exists(rate_path):
                            self.message_queue.put(("log", f"Rate 이미지 파일 처리 중: {rate_path}"))
                            rate_text_clean = self.extract_rate_with_multiple_attempts(rate_path)
                    else:
                        # PIL 이미지 객체인 경우 (메모리 모드)
                        self.message_queue.put(("log", f"Rate 이미지 메모리 처리 중"))
                        rate_text_clean = self.extract_rate_with_multiple_attempts_from_image(rate_path)

                self.message_queue.put(("log", f"최종 결과 - Date: '{date_text_clean}', Rate: '{rate_text_clean}'"))

            except Exception as e:
                self.message_queue.put(("error", f"OCR 처리 중 오류 발생(Index: {index}): {e}"))
                import traceback
                self.message_queue.put(("error", f"상세 오류: {traceback.format_exc()}"))
            finally:
                # 상세 이미지 저장 옵션이 꺼져있는 경우에만 임시 파일 삭제
                try:
                    save_detailed_images = self.save_image_var.get() if hasattr(self, 'save_image_var') else False
                    
                    if not save_detailed_images:
                        # 상세 이미지 저장하지 않는 경우만 삭제
                        if isinstance(date_path, str) and os.path.exists(date_path):
                            os.remove(date_path)
                            self.message_queue.put(("log", f"임시 날짜 파일 삭제: {date_path}"))
                        if isinstance(rate_path, str) and os.path.exists(rate_path):
                            os.remove(rate_path)
                            self.message_queue.put(("log", f"임시 금리 파일 삭제: {rate_path}"))
                    else:
                        # 상세 이미지 저장하는 경우 파일 보존
                        self.message_queue.put(("log", f"상세 이미지 저장됨 - 날짜: {date_path}, 금리: {rate_path}"))
                except Exception as e:
                    self.message_queue.put(("log", f"이미지 파일 처리 중 오류: {e}"))

            ocr_results.append((index, date_text_clean, rate_text_clean))

        return ocr_results

    def process_single_ocr(self, grid_index, date_path, rate_path):
        """단일 종목에 대한 즉시 OCR 처리"""
        try:
            # 날짜 OCR 처리
            date_result = ""
            if date_path:
                try:
                    date_result = self.extract_date_with_multiple_attempts(date_path)
                    if not date_result:
                        date_result = ""
                except Exception as e:
                    self.message_queue.put(("log", f"날짜 OCR 처리 중 오류: {e}"))
                    date_result = ""
            
            # 금리 OCR 처리
            rate_result = ""
            if rate_path:
                try:
                    rate_result = self.extract_rate_with_multiple_attempts(rate_path)
                    if not rate_result:
                        rate_result = ""
                except Exception as e:
                    self.message_queue.put(("log", f"금리 OCR 처리 중 오류: {e}"))
                    rate_result = ""
            
            return date_result, rate_result
            
        except Exception as e:
            self.message_queue.put(("error", f"OCR 처리 중 오류: {e}"))
            return "", ""

    def extract_date_with_multiple_attempts(self, image_path):
        """날짜 추출을 위한 다중 시도 방식 - 개선된 버전"""
        attempts = []
        
        try:
            # 중단 체크
            if self.work_controller.is_stopped:
                return ""
                
            original_img = Image.open(image_path)
            
            # 고급 설정에서 최대 시도 횟수 가져오기
            max_attempts = self.settings_manager.get_advanced('ocr_max_attempts', 5)
            detail_level = self.settings_manager.get_advanced('ocr_detail_level', 0)
            
            # 1차 시도: 개선된 전처리
            if self.work_controller.is_stopped:
                return ""
            processed_img1 = self.preprocess_image_enhanced(original_img)
            
            # 디버깅을 위한 전처리된 이미지 저장
            try:
                debug_folder = os.path.dirname(image_path)
                debug_name = os.path.basename(image_path).replace('.png', '_processed.png')
                debug_path = os.path.join(debug_folder, debug_name)
                processed_img1.save(debug_path)
                self.logger.info(f"전처리된 이미지 저장: {debug_path}")
            except Exception as debug_e:
                self.logger.warning(f"디버그 이미지 저장 실패: {debug_e}")
            
            result1 = self.ocr_reader.readtext(np.array(processed_img1), detail=detail_level)
            attempts.append(("개선된 전처리", result1))
            
            # 최대 시도 횟수가 1이면 여기서 종료
            if max_attempts <= 1:
                return self.analyze_date_results(attempts)
            
            # 2차 시도: 단순 그레이스케일
            if self.work_controller.is_stopped:
                return ""
            gray_img = original_img.convert('L')
            result2 = self.ocr_reader.readtext(np.array(gray_img), detail=detail_level)
            attempts.append(("단순 그레이스케일", result2))
            
            # 최대 시도 횟수가 2이면 여기서 종료
            if max_attempts <= 2:
                return self.analyze_date_results(attempts)
            
            # 3차 시도: 다양한 OCR 파라미터로 시도
            if self.work_controller.is_stopped:
                return ""
            try:
                # width_ths와 height_ths 파라미터 조정으로 더 세밀한 텍스트 검출
                result3 = self.ocr_reader.readtext(
                    np.array(processed_img1), 
                    detail=detail_level,
                    width_ths=0.4,   # 기본값보다 낮춰서 작은 텍스트도 검출
                    height_ths=0.4   # 기본값보다 낮춰서 작은 텍스트도 검출
                )
                attempts.append(("세밀한 검출", result3))
            except Exception as e:
                self.logger.warning(f"세밀한 검출 시도 실패: {e}")
                attempts.append(("세밀한 검출", []))
            
            # 최대 시도 횟수가 3이면 여기서 종료
            if max_attempts <= 3:
                return self.analyze_date_results(attempts)
            
            # 4차 시도: 이미지 반전 후 처리
            if self.work_controller.is_stopped:
                return ""
            try:
                # 이미지 색상 반전 (검은 글씨 -> 흰 글씨)
                inverted_img = Image.eval(original_img.convert('L'), lambda x: 255 - x)
                processed_inverted = self.preprocess_image_enhanced(inverted_img)
                result4 = self.ocr_reader.readtext(np.array(processed_inverted), detail=detail_level)
                attempts.append(("색상 반전", result4))
            except Exception as e:
                self.logger.warning(f"색상 반전 시도 실패: {e}")
                attempts.append(("색상 반전", []))
            
            # 최대 시도 횟수가 4이면 여기서 종료
            if max_attempts <= 4:
                return self.analyze_date_results(attempts)
            
            # 5차 시도: 대비 및 밝기 향상
            if self.work_controller.is_stopped:
                return ""
            try:
                from PIL import ImageEnhance
                
                # 대비 향상
                enhancer = ImageEnhance.Contrast(original_img)
                enhanced_img = enhancer.enhance(2.0)
                
                # 밝기 조정
                brightness_enhancer = ImageEnhance.Brightness(enhanced_img)
                bright_img = brightness_enhancer.enhance(1.2)
                
                result5 = self.ocr_reader.readtext(np.array(bright_img), detail=detail_level)
                attempts.append(("대비밝기향상", result5))
            except Exception as e:
                self.logger.warning(f"대비밝기 향상 시도 실패: {e}")
                attempts.append(("대비밝기향상", []))
            
            # 중단 체크
            if self.work_controller.is_stopped:
                return ""
                
            # 모든 결과를 분석하여 최적 선택
            best_date = self.analyze_date_results(attempts)
            return best_date
            
        except Exception as e:
            self.message_queue.put(("error", f"날짜 추출 중 오류: {e}"))
            return ""

    def extract_date_with_multiple_attempts_from_image(self, pil_image):
        """메모리의 PIL 이미지에서 날짜 추출"""
        attempts = []
        
        try:
            # 중단 체크
            if self.work_controller.is_stopped:
                return ""
                
            # 고급 설정에서 최대 시도 횟수 가져오기
            max_attempts = self.settings_manager.get_advanced('ocr_max_attempts', 3)
            detail_level = self.settings_manager.get_advanced('ocr_detail_level', 0)
            
            # 1차 시도: 기본 전처리
            if self.work_controller.is_stopped:
                return ""
            processed_img1 = self.preprocess_image_enhanced(pil_image)
            result1 = self.ocr_reader.readtext(np.array(processed_img1), detail=detail_level)
            attempts.append(("기본 전처리", result1))
            
            # 최대 시도 횟수가 1이면 여기서 종료
            if max_attempts <= 1:
                return self.analyze_date_results(attempts)
            
            # 2차 시도: 단순 그레이스케일
            if self.work_controller.is_stopped:
                return ""
            gray_img = pil_image.convert('L')
            result2 = self.ocr_reader.readtext(np.array(gray_img), detail=detail_level)
            attempts.append(("단순 그레이스케일", result2))
            
            # 최대 시도 횟수가 2이면 여기서 종료
            if max_attempts <= 2:
                return self.analyze_date_results(attempts)
            
            # 3차 시도: 크기 확대 후 처리
            if pil_image.size[0] < 300:
                if self.work_controller.is_stopped:
                    return ""
                resize_factor = self.settings_manager.get_advanced('image_resize_factor', 4)
                enlarged = pil_image.resize((pil_image.size[0] * resize_factor, 
                                          pil_image.size[1] * resize_factor), 
                                         Image.Resampling.LANCZOS)
                processed_enlarged = self.preprocess_image_enhanced(enlarged)
                result3 = self.ocr_reader.readtext(np.array(processed_enlarged), detail=detail_level)
                attempts.append(("크기 확대", result3))
            
            # 중단 체크
            if self.work_controller.is_stopped:
                return ""
                
            # 모든 결과를 분석하여 최적 선택
            best_date = self.analyze_date_results(attempts)
            return best_date
            
        except Exception as e:
            self.message_queue.put(("error", f"메모리 날짜 추출 중 오류: {e}"))
            return ""

    def extract_rate_with_multiple_attempts_from_image(self, pil_image):
        """메모리의 PIL 이미지에서 금리 추출"""
        attempts = []
        
        try:
            # 중단 체크
            if self.work_controller.is_stopped:
                return ""
                
            # 고급 설정에서 최대 시도 횟수 가져오기
            max_attempts = self.settings_manager.get_advanced('ocr_max_attempts', 3)
            detail_level = self.settings_manager.get_advanced('ocr_detail_level', 0)
            
            # 1차 시도: 기본 전처리
            if self.work_controller.is_stopped:
                return ""
            processed_img1 = self.preprocess_image_enhanced(pil_image)
            result1 = self.ocr_reader.readtext(np.array(processed_img1), detail=detail_level)
            attempts.append(("기본 전처리", result1))
            
            # 최대 시도 횟수가 1이면 여기서 종료
            if max_attempts <= 1:
                return self.analyze_rate_results(attempts)
            
            # 2차 시도: 단순 그레이스케일
            if self.work_controller.is_stopped:
                return ""
            gray_img = pil_image.convert('L')
            result2 = self.ocr_reader.readtext(np.array(gray_img), detail=detail_level)
            attempts.append(("단순 그레이스케일", result2))
            
            # 최대 시도 횟수가 2이면 여기서 종료
            if max_attempts <= 2:
                return self.analyze_rate_results(attempts)
            
            # 3차 시도: 크기 확대 후 처리
            if pil_image.size[0] < 300:
                if self.work_controller.is_stopped:
                    return ""
                resize_factor = self.settings_manager.get_advanced('image_resize_factor', 4)
                enlarged = pil_image.resize((pil_image.size[0] * resize_factor, 
                                          pil_image.size[1] * resize_factor), 
                                         Image.Resampling.LANCZOS)
                processed_enlarged = self.preprocess_image_enhanced(enlarged)
                result3 = self.ocr_reader.readtext(np.array(processed_enlarged), detail=detail_level)
                attempts.append(("크기 확대", result3))
            
            # 중단 체크
            if self.work_controller.is_stopped:
                return ""
                
            # 모든 결과를 분석하여 최적 선택
            best_rate = self.analyze_rate_results(attempts)
            return best_rate
            
        except Exception as e:
            self.message_queue.put(("error", f"메모리 금리 추출 중 오류: {e}"))
            return ""

    def extract_rate_with_multiple_attempts(self, image_path):
        """금리 추출을 위한 다중 시도 방식"""
        attempts = []
        
        try:
            # 중단 체크
            if self.work_controller.is_stopped:
                return ""
                
            original_img = Image.open(image_path)
            
            # 고급 설정에서 최대 시도 횟수 가져오기
            max_attempts = self.settings_manager.get_advanced('ocr_max_attempts', 3)
            detail_level = self.settings_manager.get_advanced('ocr_detail_level', 0)
            
            # 1차 시도: 기본 전처리
            if self.work_controller.is_stopped:
                return ""
            processed_img1 = self.preprocess_image_enhanced(original_img)
            result1 = self.ocr_reader.readtext(np.array(processed_img1), detail=detail_level)
            attempts.append(("기본 전처리", result1))
            
            # 최대 시도 횟수가 1이면 여기서 종료
            if max_attempts <= 1:
                return self.analyze_rate_results(attempts)
            
            # 2차 시도: 단순 그레이스케일
            if self.work_controller.is_stopped:
                return ""
            gray_img = original_img.convert('L')
            result2 = self.ocr_reader.readtext(np.array(gray_img), detail=detail_level)
            attempts.append(("단순 그레이스케일", result2))
            
            # 최대 시도 횟수가 2이면 여기서 종료
            if max_attempts <= 2:
                return self.analyze_rate_results(attempts)
            
            # 3차 시도: 크기 확대 후 처리
            if original_img.size[0] < 300:
                if self.work_controller.is_stopped:
                    return ""
                resize_factor = self.settings_manager.get_advanced('image_resize_factor', 4)
                enlarged = original_img.resize((original_img.size[0] * resize_factor, 
                                              original_img.size[1] * resize_factor), 
                                             Image.Resampling.LANCZOS)
                processed_enlarged = self.preprocess_image_enhanced(enlarged)
                result3 = self.ocr_reader.readtext(np.array(processed_enlarged), detail=detail_level)
                attempts.append(("크기 확대", result3))
            
            # 중단 체크
            if self.work_controller.is_stopped:
                return ""
                
            # 모든 결과를 분석하여 최적 선택
            best_rate = self.analyze_rate_results(attempts)
            return best_rate
            
        except Exception as e:
            self.message_queue.put(("error", f"금리 추출 중 오류: {e}"))
            return ""

    def analyze_date_results(self, attempts):
        """날짜 결과 분석 및 최적 선택 (개선된 버전)"""
        valid_dates = []
        min_confidence = self.settings_manager.get_advanced('min_date_confidence', 0.05)  # 더욱 관대한 임계값
        
        for method, results in attempts:
            # 더 상세한 OCR 결과 로깅
            if results:
                result_details = []
                for r in results:
                    if len(r) >= 3:
                        bbox, text, conf = r[0], r[1], r[2]
                        try:
                            conf_float = float(conf)
                            result_details.append(f"'{text}'(신뢰도:{conf_float:.3f})")
                        except (ValueError, TypeError):
                            result_details.append(f"'{text}'(신뢰도:{conf})")
                    elif len(r) >= 2:
                        text, conf = r[0], r[1]
                        try:
                            conf_float = float(conf)
                            result_details.append(f"'{text}'(신뢰도:{conf_float:.3f})")
                        except (ValueError, TypeError):
                            result_details.append(f"'{text}'(신뢰도:{conf})")
                    else:
                        result_details.append(str(r))
                self.message_queue.put(("log", f"날짜 {method} 결과: {result_details}"))
            else:
                self.message_queue.put(("log", f"날짜 {method} 결과: 빈 결과"))
            
            if results:
                for result in results:
                    try:
                        # EasyOCR 결과 형태 안전 처리
                        if len(result) >= 3:
                            bbox, text, confidence = result[0], result[1], result[2]
                        elif len(result) == 2:
                            text, confidence = result[0], result[1]
                            bbox = None
                        else:
                            continue
                        
                        # 신뢰도를 float로 변환 시도
                        try:
                            confidence = float(confidence)
                        except (ValueError, TypeError):
                            self.message_queue.put(("log", f"날짜 신뢰도 변환 실패: {confidence}"))
                            continue
                        
                        # 더 관대한 신뢰도 임계값 체크
                        if confidence < min_confidence:
                            self.message_queue.put(("log", f"날짜 신뢰도 부족: {text} ({confidence:.3f} < {min_confidence})"))
                            continue
                            
                        cleaned_date = self.clean_date_text(text)
                        self.message_queue.put(("log", f"날짜 정리 후: '{text}' -> '{cleaned_date}'"))
                        
                        # 날짜 형식 검증 (더 관대하게)
                        if self.is_valid_date_format(cleaned_date):
                            valid_dates.append((cleaned_date, confidence, method))
                            self.message_queue.put(("log", f"유효한 날짜 발견: {cleaned_date} (신뢰도: {confidence:.3f})"))
                            
                    except Exception as e:
                        self.message_queue.put(("log", f"날짜 결과 처리 중 오류: {e}"))
                        continue
        
        if valid_dates:
            # 신뢰도 순으로 정렬하여 최고 품질 선택
            valid_dates.sort(key=lambda x: x[1], reverse=True)
            best_date = valid_dates[0][0]
            self.message_queue.put(("log", f"선택된 날짜: {best_date} (방법: {valid_dates[0][2]}, 신뢰도: {valid_dates[0][1]:.3f})"))
            return best_date
        
        self.message_queue.put(("log", "유효한 날짜를 찾을 수 없음"))
        return ""

    def analyze_rate_results(self, attempts):
        """금리 결과 분석 및 최적 선택 (개선된 버전)"""
        valid_rates = []
        min_confidence = self.settings_manager.get_advanced('min_rate_confidence', 0.05)  # 더욱 관대한 임계값
        
        for method, results in attempts:
            # 더 상세한 OCR 결과 로깅
            if results:
                result_details = []
                for r in results:
                    if len(r) >= 3:
                        bbox, text, conf = r[0], r[1], r[2]
                        try:
                            conf_float = float(conf)
                            result_details.append(f"'{text}'(신뢰도:{conf_float:.3f})")
                        except (ValueError, TypeError):
                            result_details.append(f"'{text}'(신뢰도:{conf})")
                    elif len(r) >= 2:
                        text, conf = r[0], r[1]
                        try:
                            conf_float = float(conf)
                            result_details.append(f"'{text}'(신뢰도:{conf_float:.3f})")
                        except (ValueError, TypeError):
                            result_details.append(f"'{text}'(신뢰도:{conf})")
                    else:
                        result_details.append(str(r))
                self.message_queue.put(("log", f"금리 {method} 결과: {result_details}"))
            else:
                self.message_queue.put(("log", f"금리 {method} 결과: 빈 결과"))
            
            if results:
                for result in results:
                    try:
                        # EasyOCR 결과 형태 안전 처리
                        if len(result) >= 3:
                            bbox, text, confidence = result[0], result[1], result[2]
                        elif len(result) == 2:
                            text, confidence = result[0], result[1]
                            bbox = None
                        else:
                            continue
                        
                        # 신뢰도를 float로 변환 시도
                        try:
                            confidence = float(confidence)
                        except (ValueError, TypeError):
                            self.message_queue.put(("log", f"금리 신뢰도 변환 실패: {confidence}"))
                            continue
                        
                        # 더 관대한 신뢰도 임계값 체크
                        if confidence < min_confidence:
                            self.message_queue.put(("log", f"금리 신뢰도 부족: {text} ({confidence:.3f} < {min_confidence})"))
                            continue
                            
                        cleaned_rate = self.clean_rate_text(text)
                        self.message_queue.put(("log", f"금리 정리 후: '{text}' -> '{cleaned_rate}'"))
                        
                        # 금리 형식 검증 (더 관대하게)
                        if self.is_valid_rate_format(cleaned_rate):
                            valid_rates.append((cleaned_rate, confidence, method))
                            self.message_queue.put(("log", f"유효한 금리 발견: {cleaned_rate} (신뢰도: {confidence:.3f})"))
                            
                    except Exception as e:
                        self.message_queue.put(("log", f"금리 결과 처리 중 오류: {e}"))
                        continue
        
        if valid_rates:
            # 신뢰도 순으로 정렬하여 최고 품질 선택
            valid_rates.sort(key=lambda x: x[1], reverse=True)
            best_rate = valid_rates[0][0]
            self.message_queue.put(("log", f"선택된 금리: {best_rate} (방법: {valid_rates[0][2]}, 신뢰도: {valid_rates[0][1]:.3f})"))
            return best_rate
        
        self.message_queue.put(("log", "유효한 금리를 찾을 수 없음"))
        return ""

    def is_valid_date_format(self, date_str):
        """날짜 형식 검증 (관대하게 처리)"""
        import re
        # 기본적인 날짜 패턴만 확인 (범위 제한 없음)
        pattern = r'^\d{4}/\d{1,2}/\d{1,2}$'
        return bool(re.match(pattern, date_str) and date_str.strip())

    def is_valid_rate_format(self, rate_str):
        """금리 형식 검증 (관대하게 처리)"""
        try:
            rate_val = float(rate_str)
            # 범위 제한 없이 숫자이기만 하면 통과
            return rate_val > 0
        except:
            return False

    def preprocess_image_enhanced(self, pil_img):
        """개선된 이미지 전처리 - OCR 인식률 극대화 및 안정성 강화"""
        try:
            # 입력 검증
            if pil_img is None:
                self.logger.warning("입력 이미지가 None입니다")
                return pil_img
                
            # PIL 이미지를 OpenCV 형식으로 변환
            img_array = np.array(pil_img)
            if img_array.size == 0:
                self.logger.warning("이미지 배열이 비어있습니다")
                return pil_img
            
            # 그레이스케일 변환
            if len(img_array.shape) == 3 and img_array.shape[2] == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            elif len(img_array.shape) == 3 and img_array.shape[2] == 4:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGBA2GRAY)
            else:
                gray = img_array.copy()
            
            # 안전한 크기 확인
            if gray.shape[0] == 0 or gray.shape[1] == 0:
                self.logger.warning("이미지 크기가 0입니다")
                return pil_img
            
            # 1단계: 크기 조정 (너무 작은 이미지는 확대)
            height, width = gray.shape
            resize_factor = self.settings_manager.get_advanced('image_resize_factor', 3)
            if width < 100 or height < 30:
                scale_x = max(1, 100 // width)
                scale_y = max(1, 30 // height)
                scale = min(resize_factor, max(scale_x, scale_y))
                new_width = width * scale
                new_height = height * scale
                gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            
            # 2단계: 적응형 히스토그램 평활화로 대비 개선
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # 3단계: 가벼운 노이즈 제거
            denoise_strength = self.settings_manager.get_advanced('image_denoise_strength', 1)
            if denoise_strength > 0:
                kernel_size = min(3, 2 * denoise_strength + 1)
                if kernel_size > 1:
                    enhanced = cv2.medianBlur(enhanced, kernel_size)
            
            # 4단계: 샤프닝 (선택적)
            if self.settings_manager.get_advanced('image_sharpening', True):
                kernel_sharpen = np.array([[-1,-1,-1],
                                         [-1, 9,-1],
                                         [-1,-1,-1]])
                enhanced = cv2.filter2D(enhanced, -1, kernel_sharpen)
                enhanced = np.clip(enhanced, 0, 255).astype(np.uint8)
            
            # 5단계: 이진화 (여러 방법 시도)
            binarization_method = self.settings_manager.get_advanced('image_binarization_method', 'adaptive')
            
            if binarization_method == 'adaptive':
                # 적응형 가우시안 이진화
                binary = cv2.adaptiveThreshold(
                    enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                    cv2.THRESH_BINARY, 11, 2
                )
            elif binarization_method == 'otsu':
                # Otsu 이진화
                _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            else:
                # 고정 임계값
                threshold = self.settings_manager.get_advanced('image_manual_threshold', 127)
                _, binary = cv2.threshold(enhanced, threshold, 255, cv2.THRESH_BINARY)
            
            # 6단계: 안전한 모폴로지 연산
            if self.settings_manager.get_advanced('image_morphology_enabled', True):
                try:
                    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
                    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
                except Exception as morph_error:
                    self.logger.warning(f"모폴로지 연산 실패: {morph_error}")
                    # 모폴로지 실패해도 이진화된 이미지는 사용
            
            # PIL 이미지로 변환하여 반환
            return Image.fromarray(binary)
            
        except Exception as e:
            self.logger.warning(f"고급 전처리 실패, 기본 처리로 폴백: {e}")
            # 기본 그레이스케일 처리로 폴백
            try:
                img_array = np.array(pil_img)
                if len(img_array.shape) == 3:
                    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                else:
                    gray = img_array
                return Image.fromarray(gray)
            except Exception as e2:
                self.logger.error(f"기본 전처리도 실패: {e2}")
                return pil_img
                self.message_queue.put(("log", f"고급 전처리 실패, 기본 처리로 폴백: {e}"))
            except:
                pass
            return pil_img.convert('L')

    def preprocess_image(self, pil_img):
        """이미지 전처리 - 고급 설정을 적용한 이미지 개선"""
        try:
            # 고급 설정 가져오기
            resize_factor = self.settings_manager.get_advanced('image_resize_factor', 4)
            denoise_strength = self.settings_manager.get_advanced('image_denoise_strength', 2)
            contrast_enhancement = self.settings_manager.get_advanced('image_contrast_enhancement', True)
            sharpening = self.settings_manager.get_advanced('image_sharpening', True)
            binarization_method = self.settings_manager.get_advanced('image_binarization_method', 'adaptive')
            
            # PIL 이미지를 OpenCV 형식으로 변환
            img_array = np.array(pil_img)
            
            # 그레이스케일 변환
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # 이미지 크기 확대 (고급 설정 적용)
            height, width = gray.shape
            if width < 200 or height < 50:
                scale_factor = max(resize_factor, 200 // width, 50 // height)
                gray = cv2.resize(gray, (width * scale_factor, height * scale_factor), 
                                interpolation=cv2.INTER_CUBIC)
            
            # 노이즈 제거 (고급 설정에 따른 강도 조절)
            if denoise_strength > 0:
                kernel_size = min(2 * denoise_strength + 1, 9)  # 1, 3, 5, 7, 9
                denoised = cv2.GaussianBlur(gray, (kernel_size, kernel_size), 0)
            else:
                denoised = gray
            
            # 대비 개선 (설정에 따라 활성화/비활성화)
            if contrast_enhancement:
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4,4))
                enhanced = clahe.apply(denoised)
            else:
                enhanced = denoised
            
            # 샤프닝 필터 적용 (설정에 따라 활성화/비활성화)
            if sharpening:
                kernel_sharpen = np.array([[-1,-1,-1],
                                         [-1, 9,-1],
                                         [-1,-1,-1]])
                sharpened = cv2.filter2D(enhanced, -1, kernel_sharpen)
            else:
                sharpened = enhanced
            
            # 이진화 방법 선택 (고급 설정 적용)
            if binarization_method == 'adaptive':
                # 적응형 이진화
                binary1 = cv2.adaptiveThreshold(
                    sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                    cv2.THRESH_BINARY, 11, 2
                )
                binary2 = cv2.adaptiveThreshold(
                    sharpened, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                    cv2.THRESH_BINARY, 9, 3
                )
                # 가장 선명한 결과 선택
                candidates = [binary1, binary2]
                stds = [np.std(img) for img in candidates]
                processed = candidates[np.argmax(stds)]
                
            elif binarization_method == 'otsu':
                # Otsu's 이진화
                _, processed = cv2.threshold(sharpened, 0, 255, 
                                           cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
            elif binarization_method == 'manual':
                # 수동 임계값
                manual_threshold = self.settings_manager.get_advanced('image_manual_threshold', 127)
                _, processed = cv2.threshold(sharpened, manual_threshold, 255, cv2.THRESH_BINARY)
            
            else:
                # 기본값: 적응형 이진화
                processed = cv2.adaptiveThreshold(
                    sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                    cv2.THRESH_BINARY, 11, 2
                )
            
            # 모폴로지 연산으로 텍스트 연결성 개선
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 1))
            processed = cv2.morphologyEx(processed, cv2.MORPH_CLOSE, kernel)
            
            # 작은 노이즈 제거
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
            processed = cv2.morphologyEx(processed, cv2.MORPH_OPEN, kernel)
            

            
            # PIL 이미지로 다시 변환
            return Image.fromarray(processed)
            
        except Exception as e:
            # 스레드에서 실행될 때만 큐 사용, 그렇지 않으면 일반 로깅 사용
            try:
                self.message_queue.put(("error", f"이미지 전처리 중 오류: {e}"))
            except:
                self.logger.error(f"이미지 전처리 중 오류: {e}")
            # 전처리 실패 시 기본 그레이스케일 변환
            try:
                return pil_img.convert('L')
            except:
                return pil_img

    def clean_date_text(self, text):
        """날짜 텍스트 정리 (실제 데이터에 최적화)"""
        import re
        
        # OCR 오인식 문자 치환 개선 (더 관대하고 정밀한 매핑)
        cleaned = (
            text.replace('I', '1')     # I -> 1 
                .replace('l', '1')     # l -> 1
                .replace('최', '25')   # "최" -> "25" (2025년 패턴)
                .replace('년', '')     # "년" 제거
                .replace('월', '/')    # "월" -> "/"
                .replace('일', '')     # "일" 제거
                .replace('@', '0')     # @ -> 0
                .replace('O', '0')     # O -> 0
                .replace('o', '0')     # o -> 0
                .replace('Q', '0')     # Q -> 0
                .replace('D', '0')     # D -> 0
                .replace('S', '5')     # S -> 5
                .replace('B', '8')     # B -> 8
                .replace('G', '6')     # G -> 6
                .replace('Z', '2')     # Z -> 2
                .replace('T', '7')     # T -> 7
                .replace('블', '')     # 불필요한 문자 제거
                .replace('V', '')
                .replace('v', '')
                .replace(',', '/')     # 구분자를 /로 통일
                .replace('.', '/')
                .replace('-', '/')
                .replace('_', '/')
                .replace('|', '/')
                .replace('\\', '/')
                .replace(' ', '')      # 모든 공백 제거
                .strip()
        )
        
        # 숫자만 추출 후 날짜 패턴 구성
        numbers = re.findall(r'\d+', cleaned)
        
        # 연속된 숫자에서 날짜 추출 시도
        if len(numbers) >= 1:
            # 하나의 긴 숫자에서 날짜 추출 시도 (예: "20250529" -> "2025/05/29")
            long_num = ''.join(numbers)
            if len(long_num) >= 6:
                if len(long_num) == 8:  # YYYYMMDD
                    year_str = long_num[:4]
                    month_str = long_num[4:6]
                    day_str = long_num[6:8]
                elif len(long_num) == 7:  # YYYYMDD
                    year_str = long_num[:4]
                    month_str = long_num[4:5]
                    day_str = long_num[5:7]
                elif len(long_num) == 6:  # YYYYMM + 추정일자
                    year_str = long_num[:4]
                    month_str = long_num[4:6]
                    day_str = "29"  # 기본값
                else:
                    year_str = long_num[:4]
                    month_str = long_num[4:6] if len(long_num) > 5 else long_num[4:5]
                    day_str = long_num[6:8] if len(long_num) > 7 else "29"
                
                try:
                    year = int(year_str)
                    month = min(max(int(month_str), 1), 12)
                    day = min(max(int(day_str), 1), 31)
                    
                    if 2020 <= year <= 2035:
                        result = f"{year:04d}/{month:02d}/{day:02d}"
                        try:
                            self.message_queue.put(("log", f"날짜 정리: '{text}' -> '{result}'"))
                        except:
                            pass
                        return result
                except ValueError:
                    pass
        
        # 개별 숫자들로 날짜 구성 시도
        if len(numbers) >= 3:
            # 첫 번째가 연도인 경우
            year_str = numbers[0]
            if len(year_str) == 4 and 2020 <= int(year_str) <= 2035:
                year = int(year_str)
                month = min(max(int(numbers[1]), 1), 12)
                day = min(max(int(numbers[2]), 1), 31)
                result = f"{year:04d}/{month:02d}/{day:02d}"
                try:
                    self.message_queue.put(("log", f"날짜 정리: '{text}' -> '{result}'"))
                except:
                    pass
                return result
        
        # 2025년을 기본으로 월/일만 추출 시도
        if len(numbers) >= 2:
            month = min(max(int(numbers[0]), 1), 12)
            day = min(max(int(numbers[1]), 1), 31)
            result = f"2025/{month:02d}/{day:02d}"
            try:
                self.message_queue.put(("log", f"날짜 추정: '{text}' -> '{result}'"))
            except:
                pass
            return result
        
        return ""

    def clean_rate_text(self, text):
        """금리 텍스트 정리 (실제 데이터에 최적화)"""
        import re
        
        # OCR 오인식 문자 치환 개선 (금리 특화)
        cleaned = (
            text.replace('U', '0')     # "2,8200U" -> "2,8200"
                .replace('D', '0')     # "3,2UDU" -> "3,200"
                .replace('g', '0')     # "2,7gUUU" -> "2,700"
                .replace('J', '0')     # "3,44UJJJ" -> "3,440"
                .replace('N', '0')     # "4 37[JNJ" -> "4 370"
                .replace('L', '1')     # "4 ZZLJjJ" -> "4 110"
                .replace('[', '')
                .replace(']', '')
                .replace('(', '')
                .replace(')', '')
                .replace('%', '')      # 퍼센트 기호 제거
                .replace(',', '.')     # 쉼표를 소수점으로
                .replace('·', '.')     # 중점을 소수점으로
                .replace('․', '.')     # 다른 종류 점을 소수점으로
                .replace('Q', '0')
                .replace('O', '0')
                .replace('o', '0')
                .replace('I', '1')
                .replace('l', '1')
                .replace('S', '5')
                .replace('B', '8')
                .replace('G', '6')
                .replace('Z', '2')
                .replace('T', '7')
                .replace('F', '7')
                .replace('j', '0')
                .replace('A', '4')     # A -> 4 (금리에서 자주 발생)
                .replace('R', '8')     # R -> 8 (금리에서 자주 발생)
                .replace(' ', '')      # 모든 공백 제거
                .strip()
        )
        
        # 숫자와 소수점만 추출
        numbers = re.findall(r'\d+\.?\d*|\d*\.\d+', cleaned)
        
        for num_str in numbers:
            try:
                rate_val = float(num_str)
                
                # 금리 범위 조정 (더 관대하게)
                if rate_val < 1.0:
                    rate_val += 2.0  # 너무 작으면 2 더하기
                elif rate_val > 100.0:
                    rate_val /= 100.0  # 너무 크면 100으로 나누기 (907800 -> 9.078)
                elif rate_val > 10.0:
                    rate_val /= 10.0  # 10보다 크면 10으로 나누기
                
                # 범위 재검증 (더 관대하게)
                if 1.0 <= rate_val <= 10.0:
                    result = f"{rate_val:.3f}"
                    try:
                        self.message_queue.put(("log", f"금리 정리: '{text}' -> '{result}'"))
                    except:
                        pass
                    return result
                    
            except ValueError:
                continue
        
        # 모든 숫자를 연결해서 재시도
        all_digits = re.sub(r'[^\d]', '', text)
        if len(all_digits) >= 2:
            try:
                # 숫자 길이에 따라 다른 처리
                if len(all_digits) <= 3:
                    # 2-3자리: 첫 자리.나머지
                    rate_val = float(all_digits[0] + '.' + all_digits[1:])
                elif len(all_digits) == 4:
                    # 4자리: 첫 자리.나머지 3자리
                    rate_val = float(all_digits[0] + '.' + all_digits[1:4])
                else:
                    # 5자리 이상: 첫 2자리.나머지 3자리
                    rate_val = float(all_digits[:2] + '.' + all_digits[2:5])
                
                if 1.0 <= rate_val <= 10.0:
                    result = f"{rate_val:.3f}"
                    try:
                        self.message_queue.put(("log", f"금리 재구성: '{text}' -> '{result}'"))
                    except:
                        pass
                    return result
            except ValueError:
                pass
        
        return ""

    # =====================================
    # Excel 그리드 관련 메서드들
    # =====================================
    
    def load_excel_to_grid(self):
        """Excel 파일을 그리드에 로드"""
        try:
            file_path = self.input_excel_path.get()
            if not file_path or not os.path.exists(file_path):
                messagebox.showerror("오류", "Excel 파일을 먼저 선택해주세요.")
                return
            
            import pandas as pd
            
            # Excel 파일 읽기
            df = pd.read_excel(file_path)
            
            # 기존 데이터 클리어
            self.clear_all_data()
            
            # 컬럼명 매핑 (유연하게 처리)
            column_mapping = {}
            for col in df.columns:
                col_lower = str(col).lower()
                if '종목코드' in col_lower or 'code' in col_lower:
                    column_mapping['종목코드'] = col
                elif '종목명' in col_lower or 'name' in col_lower or '회사' in col_lower:
                    column_mapping['종목명'] = col
                elif '날짜' in col_lower or 'date' in col_lower:
                    column_mapping['날짜'] = col
                elif '금리' in col_lower or 'rate' in col_lower or '수익률' in col_lower:
                    column_mapping['금리'] = col
            
            # 데이터 변환
            for _, row in df.iterrows():
                data_row = {
                    '종목코드': str(row.get(column_mapping.get('종목코드', ''), '')),
                    '종목명': str(row.get(column_mapping.get('종목명', ''), '')),
                    '날짜': str(row.get(column_mapping.get('날짜', ''), '')),
                    '금리': str(row.get(column_mapping.get('금리', ''), '')),
                    '상태': '대기 중'
                }
                self.excel_data.append(data_row)
            
            # 그리드 새로고침
            self.refresh_grid()
            
            messagebox.showinfo("성공", f"{len(self.excel_data)}행의 데이터를 로드했습니다.")
            
        except Exception as e:
            messagebox.showerror("오류", f"Excel 파일 로드 중 오류가 발생했습니다:\\n{e}")
    
    def add_empty_row(self):
        """빈 행 추가"""
        new_row = {
            '종목코드': '',
            '종목명': '',
            '날짜': '',
            '금리': '',
            '상태': '대기 중'
        }
        self.excel_data.append(new_row)
        self.refresh_grid()
    
    def paste_from_clipboard(self):
        """클립보드에서 데이터 붙여넣기"""
        try:
            clipboard_data = self.clipboard_get()
            lines = clipboard_data.strip().split('\\n')
            
            added_count = 0
            for line in lines:
                # 탭 또는 쉼표로 분리
                if '\\t' in line:
                    parts = line.split('\\t')
                elif ',' in line:
                    parts = line.split(',')
                else:
                    parts = [line]
                
                # 최소 1개 이상의 데이터가 있는 경우에만 추가
                if len(parts) >= 1 and parts[0].strip():
                    new_row = {
                        '종목코드': parts[0].strip() if len(parts) > 0 else '',
                        '종목명': parts[1].strip() if len(parts) > 1 else '',
                        '날짜': parts[2].strip() if len(parts) > 2 else '',
                        '금리': parts[3].strip() if len(parts) > 3 else '',
                        '상태': '대기 중'
                    }
                    self.excel_data.append(new_row)
                    added_count += 1
            
            if added_count > 0:
                self.refresh_grid()
                messagebox.showinfo("성공", f"{added_count}행을 추가했습니다.")
            else:
                messagebox.showwarning("경고", "붙여넣을 유효한 데이터가 없습니다.")
                
        except tk.TclError:
            messagebox.showerror("오류", "클립보드에 텍스트 데이터가 없습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"붙여넣기 중 오류가 발생했습니다:\\n{e}")
    
    def delete_selected_rows(self):
        """선택된 행들 삭제"""
        if not self.grid_tree:
            return
            
        selected_items = self.grid_tree.selection()
        if not selected_items:
            messagebox.showwarning("경고", "삭제할 행을 선택해주세요.")
            return
        
        # 확인 대화상자
        if not messagebox.askyesno("확인", f"{len(selected_items)}개의 행을 삭제하시겠습니까?"):
            return
        
        # 역순으로 삭제 (인덱스 변경 방지)
        indices_to_delete = []
        for item in selected_items:
            index = self.grid_tree.index(item)
            indices_to_delete.append(index)
        
        indices_to_delete.sort(reverse=True)
        
        for index in indices_to_delete:
            if 0 <= index < len(self.excel_data):
                del self.excel_data[index]
        
        self.refresh_grid()
    
    def clear_all_data(self):
        """모든 데이터 클리어"""
        if self.excel_data and not messagebox.askyesno("확인", "모든 데이터를 삭제하시겠습니까?"):
            return
        
        self.excel_data.clear()
        self.current_processing_index = -1
        self.refresh_grid()
    
    def copy_selected_rows(self):
        """선택된 행들 복사"""
        if not self.grid_tree:
            return
            
        selected_items = self.grid_tree.selection()
        if not selected_items:
            return
        
        copied_data = []
        for item in selected_items:
            index = self.grid_tree.index(item)
            if 0 <= index < len(self.excel_data):
                row = self.excel_data[index]
                copied_data.append(f"{row['종목코드']}\\t{row['종목명']}\\t{row['날짜']}\\t{row['금리']}")
        
        if copied_data:
            self.clipboard_clear()
            self.clipboard_append('\\n'.join(copied_data))
    
    def refresh_grid(self):
        """그리드 새로고침"""
        if not self.grid_tree:
            return
        
        # 기존 아이템 모두 삭제
        for item in self.grid_tree.get_children():
            self.grid_tree.delete(item)
        
        # 새 데이터 추가
        for i, row in enumerate(self.excel_data):
            # 현재 처리 중인 행은 다른 색으로 표시
            tags = []
            if i == self.current_processing_index:
                tags = ['processing']
            elif row['상태'] == '완료':
                tags = ['completed']
            elif row['상태'] == '오류':
                tags = ['error']
            
            self.grid_tree.insert('', 'end', values=(
                row['종목코드'], row['종목명'], row['날짜'], row['금리'], row['상태']
            ), tags=tags)
        
        # 태그 스타일 설정
        self.grid_tree.tag_configure('processing', background='#FFF3CD', foreground='#856404')
        self.grid_tree.tag_configure('completed', background='#D4EDDA', foreground='#155724')
        self.grid_tree.tag_configure('error', background='#F8D7DA', foreground='#721C24')
        
        # 상태 업데이트
        self.update_grid_status()
    
    def update_grid_status(self):
        """그리드 상태 표시 업데이트"""
        total = len(self.excel_data)
        completed = sum(1 for row in self.excel_data if row['상태'] == '완료')
        waiting = sum(1 for row in self.excel_data if row['상태'] == '대기 중')
        errors = sum(1 for row in self.excel_data if row['상태'] == '오류')
        
        # 상태 텍스트 업데이트
        if hasattr(self, 'grid_status_label'):
            self.grid_status_label.config(text=f"총 {total}행 | 완료: {completed}행 | 대기: {waiting}행 | 오류: {errors}행")
        
        # 진행률 계산 및 업데이트
        if total > 0:
            progress = (completed / total) * 100
            if hasattr(self, 'grid_progress_label'):
                self.grid_progress_label.config(text=f"진행률: {progress:.1f}%")
        else:
            if hasattr(self, 'grid_progress_label'):
                self.grid_progress_label.config(text="진행률: 0%")
    
    def on_cell_double_click(self, event):
        """셀 더블클릭 이벤트 (편집 모드)"""
        item = self.grid_tree.selection()[0] if self.grid_tree.selection() else None
        if not item:
            return
        
        # 편집 대화상자 열기
        self.edit_row_dialog(self.grid_tree.index(item))
    
    def edit_row_dialog(self, row_index):
        """행 편집 대화상자"""
        if not (0 <= row_index < len(self.excel_data)):
            return
        
        row_data = self.excel_data[row_index]
        
        # 편집 창 생성
        edit_window = tk.Toplevel(self)
        edit_window.title("행 편집")
        edit_window.geometry("400x250")
        edit_window.resizable(False, False)
        edit_window.configure(bg=self.colors['surface'])
        
        # 중앙 정렬
        edit_window.transient(self)
        edit_window.grab_set()
        
        # 입력 필드들
        fields = ['종목코드', '종목명', '날짜', '금리']
        entries = {}
        
        for i, field in enumerate(fields):
            tk.Label(edit_window, text=f"{field}:", font=('Segoe UI', 10),
                    bg=self.colors['surface'], fg=self.colors['on_surface']).grid(row=i, column=0, sticky='w', padx=10, pady=5)
            
            entry = tk.Entry(edit_window, font=('Segoe UI', 10), width=30)
            entry.insert(0, row_data[field])
            entry.grid(row=i, column=1, padx=10, pady=5)
            entries[field] = entry
        
        # 버튼 프레임
        button_frame = tk.Frame(edit_window, bg=self.colors['surface'])
        button_frame.grid(row=len(fields), column=0, columnspan=2, pady=20)
        
        def save_changes():
            for field in fields:
                self.excel_data[row_index][field] = entries[field].get()
            self.refresh_grid()
            edit_window.destroy()
        
        def cancel_edit():
            edit_window.destroy()
        
        tk.Button(button_frame, text="저장", command=save_changes,
                 font=('Segoe UI', 10), bg=self.colors['success'], fg='white',
                 relief='flat', cursor='hand2', width=10).pack(side='left', padx=5)
        
        tk.Button(button_frame, text="취소", command=cancel_edit,
                 font=('Segoe UI', 10), bg=self.colors['danger'], fg='white',
                 relief='flat', cursor='hand2', width=10).pack(side='left', padx=5)
    
    def show_context_menu(self, event):
        """우클릭 컨텍스트 메뉴"""
        # 간단한 컨텍스트 메뉴 구현
        context_menu = tk.Menu(self, tearoff=0)
        context_menu.add_command(label="행 추가", command=self.add_empty_row)
        context_menu.add_command(label="선택 삭제", command=self.delete_selected_rows)
        context_menu.add_separator()
        context_menu.add_command(label="복사", command=self.copy_selected_rows)
        context_menu.add_command(label="붙여넣기", command=self.paste_from_clipboard)
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def update_row_ocr_result(self, row_index, date_result, rate_result, status='완료'):
        """OCR 결과로 행 업데이트"""
        if 0 <= row_index < len(self.excel_data):
            if date_result:
                self.excel_data[row_index]['날짜'] = date_result
            if rate_result:
                self.excel_data[row_index]['금리'] = rate_result
            self.excel_data[row_index]['상태'] = status
            
            # UI 업데이트
            self.after(0, self.refresh_grid)

    def generate_ocr_summary(self, ocr_results, total_items):
        """OCR 결과 요약 생성 (간소화 버전)"""
        processed_count = len(ocr_results)
        date_success = sum(1 for _, date_text, _ in ocr_results if date_text.strip())
        rate_success = sum(1 for _, _, rate_text in ocr_results if rate_text.strip())
        
        summary = f"""📊 OCR 처리 완료!

🔢 총 처리 항목: {total_items}개
✅ 실제 처리됨: {processed_count}개
📅 날짜 인식 성공: {date_success}개 ({date_success/processed_count*100:.1f}%)
💰 금리 인식 성공: {rate_success}개 ({rate_success/processed_count*100:.1f}%)

📁 결과 파일: *_updated.xlsx로 저장됨
📝 로그 파일: ocr_app.log에서 상세 내용 확인 가능"""
            
        return summary



if __name__ == "__main__":
    app = CheckCaptureOCRApp()
    app.mainloop() 