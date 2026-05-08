import copy
import json
import os
import platform  # OS 정보 확인용
import queue
import subprocess
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from time import perf_counter
from tkinter import filedialog, messagebox, simpledialog, ttk

import numpy as np
from PIL import Image

from checkocr2.build_metadata import format_build_metadata, load_build_metadata
from checkocr2.excel_io import export_grid_rows, load_grid_rows
from checkocr2.exceptions import SettingsError
from checkocr2.image_processing import upscale_image
from checkocr2.logging_config import TkinterLogHandler, setup_logging
from checkocr2.ocr_engine import (
    confidence_is_accepted,
    create_easyocr_reader,
    extract_text_with_confidence,
    normalize_confidence_threshold,
    read_ocr_text,
)
from checkocr2.ocr_text import (
    clean_date_text,
    clean_rate_text,
    is_valid_date_format,
    is_valid_rate_format,
)
from checkocr2.paths import clean_folder_path as normalize_folder_path
from checkocr2.paths import sanitize_filename, updated_workbook_path
from checkocr2.run_report import (
    create_run_report,
    finalize_run_report,
    record_row_reports,
    report_output_path,
    write_run_report,
)
from checkocr2.runtime_state import RuntimeState, runtime_state_ui
from checkocr2.screen_automation import click, copy_text, hotkey, screenshot
from checkocr2.settings import DEFAULT_SETTINGS, SettingsStore
from checkocr2.table_model import delete_rows, empty_row, row_for_copy, rows_from_clipboard
from checkocr2.ui.panels.coordinates_panel import create_coordinates_panel
from checkocr2.ui.panels.file_panel import create_file_panel
from checkocr2.ui.panels.log_panel import create_log_panel
from checkocr2.ui.panels.options_panel import create_options_panel
from checkocr2.ui.panels.timing_panel import create_timing_panel
from checkocr2.ui.queue_dispatcher import process_legacy_message_queue, queue_check_interval
from checkocr2.worker import start_daemon_worker
from checkocr2.workflow import (
    CapturedImages,
    OcrResult,
    WorkflowOptions,
    WorkflowRunner,
)
from checkocr2.workflow import (
    finalize_processing_states as finalize_workflow_processing_states,
)

PACKAGE_SMOKE_FAST_OCR_ENV = "CHECKOCR2_PACKAGE_SMOKE_FAST_OCR"
PACKAGE_SMOKE_STATUS_FILE_ENV = "CHECKOCR2_PACKAGE_SMOKE_STATUS_FILE"


############################################
# 통합 설정 관리 시스템
############################################
class UnifiedSettingsManager(SettingsStore):
    """Compatibility adapter around the package settings store."""

    def __init__(self):
        try:
            super().__init__()
        except SettingsError as e:
            print(f"설정 로드 오류: {e}")
            self.settings_file = "settings.json"
            self.legacy_settings_file = "settings.json"
            self.data = copy.deepcopy(DEFAULT_SETTINGS)

    def save_preset(self, name, settings):
        settings = dict(settings)
        settings["created_at"] = datetime.now().isoformat()
        super().save_preset(name, settings)

############################################
# 테마 관리 시스템
############################################
class ThemeManager:
    def __init__(self, root_app):
        self.root_app = root_app # CheckCaptureOCRApp 인스턴스
        self.settings_manager = root_app.settings_manager
        self.logger = root_app.logger

        self.available_themes = {
            'modern_blue': {'name': '🔵 모던 블루', 'primary': '#1976D2', 'secondary': '#42A5F5', 'success': '#4CAF50', 'warning': '#FF9800', 'danger': '#F44336', 'light': '#F5F5F5', 'dark': '#212121', 'white': '#FFFFFF', 'accent': '#9C27B0', 'surface': '#FFFFFF', 'on_surface': '#212121', 'outline': '#79747E', 'treeview_bg': '#FFFFFF', 'treeview_fg': '#000000', 'treeview_selected_bg': '#AED6F1'},
            'dark_pro': {'name': '🌙 다크 프로', 'primary': '#BB86FC', 'secondary': '#03DAC6', 'success': '#4CAF50', 'warning': '#FFC107', 'danger': '#CF6679', 'light': '#121212', 'dark': '#000000', 'white': '#FFFFFF', 'accent': '#03DAC6', 'surface': '#1E1E1E', 'on_surface': '#E1E1E1', 'outline': '#938F99', 'treeview_bg': '#2C2C2C', 'treeview_fg': '#E1E1E1', 'treeview_selected_bg': '#555555'},
            'elegant_purple': {'name': '💜 엘레간트 퍼플', 'primary': '#6750A4', 'secondary': '#958DA5', 'success': '#4CAF50', 'warning': '#F57C00', 'danger': '#BA1A1A', 'light': '#FEF7FF', 'dark': '#21005D', 'white': '#FFFFFF', 'accent': '#D0BCFF', 'surface': '#FFFBFE', 'on_surface': '#1D1B20', 'outline': '#79747E', 'treeview_bg': '#FFFBFE', 'treeview_fg': '#1D1B20', 'treeview_selected_bg': '#E8DEF8'},
            'green_nature': {'name': '🌿 그린 네이처', 'primary': '#006E26', 'secondary': '#52634F', 'success': '#4CAF50', 'warning': '#F57C00', 'danger': '#BA1A1A', 'light': '#F6FFF6', 'dark': '#00210A', 'white': '#FFFFFF', 'accent': '#006E26', 'surface': '#FEFFFE', 'on_surface': '#1A1C18', 'outline': '#72796F', 'treeview_bg': '#FEFFFE', 'treeview_fg': '#1A1C18', 'treeview_selected_bg': '#C8E6C9'},
            'orange_warm': {'name': '🧡 오렌지 웜', 'primary': '#8F4E00', 'secondary': '#77574B', 'success': '#4CAF50', 'warning': '#FF8F00', 'danger': '#BA1A1A', 'light': '#FFFBF8', 'dark': '#2F1500', 'white': '#FFFFFF', 'accent': '#FFB59D', 'surface': '#FFFBF8', 'on_surface': '#201A16', 'outline': '#837568', 'treeview_bg': '#FFFBF8', 'treeview_fg': '#201A16', 'treeview_selected_bg': '#FFCCBC'}
        }
        
        saved_theme_key = self.settings_manager.get_advanced('ui_theme', 'modern_blue')
        self.current_theme_key = saved_theme_key if saved_theme_key in self.available_themes else 'modern_blue'
        self.colors = self.available_themes[self.current_theme_key].copy()
        
        self.themed_widgets = {} # {widget_ref: {'bg': 'color_key', 'fg': 'color_key', ...}}

    def register_widget(self, widget, style_map):
        """위젯과 스타일 매핑을 등록"""
        if widget:
            self.themed_widgets[widget] = style_map

    def get_color(self, key, default=None):
        return self.colors.get(key, default if default is not None else '#000000')

    def apply_theme_to_all_widgets(self):
        """등록된 모든 위젯에 현재 테마 적용"""
        self.root_app.configure(bg=self.get_color('surface'))

        # 색상이 아닌 속성들 (그대로 적용)
        non_color_props = {'relief', 'bd', 'borderwidth', 'width', 'height', 'padx', 'pady', 
                          'state', 'cursor', 'font', 'justify', 'anchor', 'wrap'}

        for widget, style_map in list(self.themed_widgets.items()): # list()로 복사본 순회 (삭제 대비)
            if not widget or not widget.winfo_exists():
                del self.themed_widgets[widget] # 파괴된 위젯 제거
                continue

            config_options = {}
            for tk_prop, value in style_map.items():
                if tk_prop in non_color_props:
                    # 색상이 아닌 속성은 그대로 적용
                    config_options[tk_prop] = value
                else:
                    # 색상 속성은 테마에서 가져오기
                    config_options[tk_prop] = self.get_color(value)
            
            if config_options:
                try:
                    widget.configure(**config_options)
                except tk.TclError as e:
                    self.logger.warning(f"위젯 스타일 적용 오류 ({widget}): {e}")

        # ttk 스타일 업데이트
        s = ttk.Style()
        s.theme_use('clam') # 'clam', 'alt', 'default', 'classic' 등 사용 가능

        # Treeview
        s.configure("Treeview", 
                    background=self.get_color('treeview_bg'), 
                    foreground=self.get_color('treeview_fg'),
                    fieldbackground=self.get_color('treeview_bg'),
                    font=('Segoe UI', 9))
        s.map("Treeview", background=[('selected', self.get_color('treeview_selected_bg'))],
                          foreground=[('selected', self.get_color('treeview_fg'))]) # 선택 시 텍스트 색 유지 또는 변경
        s.configure("Treeview.Heading", 
                    background=self.get_color('primary'), 
                    foreground=self.get_color('white'), 
                    relief="flat", font=('Segoe UI', 9, 'bold'))
        s.map("Treeview.Heading", background=[('active', self.get_color('secondary'))])

        # Progressbar
        s.configure("TProgressbar", 
                    background=self.get_color('success'), 
                    troughcolor=self.get_color('light'),
                    bordercolor=self.get_color('primary'), troughrelief='flat')
        
        # Scrollbar
        s.configure("TScrollbar", 
                    gripcount=0,
                    background=self.get_color('primary'), 
                    darkcolor=self.get_color('light'), 
                    lightcolor=self.get_color('light'),
                    troughcolor=self.get_color('surface'), 
                    bordercolor=self.get_color('outline'), 
                    arrowcolor=self.get_color('white'))
        s.map('TScrollbar', background=[('active', self.get_color('secondary'))])

        # Combobox
        s.configure("TCombobox", 
                    fieldbackground=self.get_color('white'), 
                    background=self.get_color('secondary'), 
                    foreground=self.get_color('on_surface'),
                    arrowcolor=self.get_color('primary'),
                    selectbackground=self.get_color('light'), # 드롭다운 리스트 배경
                    selectforeground=self.get_color('on_surface')) # 드롭다운 리스트 텍스트
        s.map('TCombobox', fieldbackground=[('readonly', self.get_color('white'))])

        # 로그 텍스트 위젯 태그 색상도 업데이트
        if hasattr(self.root_app, 'log_text_widget') and self.root_app.log_text_widget and self.root_app.log_text_widget.winfo_exists():
            log_widget = self.root_app.log_text_widget
            log_widget.tag_configure("INFO", foreground=self.get_color('primary'))
            log_widget.tag_configure("WARNING", foreground=self.get_color('warning'))
            log_widget.tag_configure("ERROR", foreground=self.get_color('danger'))
            log_widget.tag_configure("SUCCESS", foreground=self.get_color('success'))
            log_widget.tag_configure("DEBUG", foreground=self.get_color('secondary'))

        # 태그 색상도 업데이트 (CheckCaptureOCRApp에서 호출)
        if hasattr(self.root_app, 'refresh_grid_tags'):
             self.root_app.refresh_grid_tags()


    def change_theme(self, theme_key):
        if theme_key in self.available_themes:
            self.current_theme_key = theme_key
            self.colors = self.available_themes[theme_key].copy()
            self.settings_manager.set_advanced('ui_theme', theme_key)
            self.apply_theme_to_all_widgets()
            self.logger.info(f"테마 변경됨: {self.available_themes[theme_key]['name']}")
        else:
            self.logger.warning(f"알 수 없는 테마 키: {theme_key}")

############################################
# 작업 제어 시스템
############################################
class WorkController:
    def __init__(self):
        self.is_stopped = False
        self.is_running = False
        self.skip_current = False
        self.current_item = ""
        self.stop_event = threading.Event() # 중단 신호용 이벤트

    def start_work(self):
        self.is_stopped = False
        self.is_running = True
        self.skip_current = False
        self.stop_event.clear() # 이벤트 초기화

    def stop_work(self):
        self.is_stopped = True
        self.is_running = False
        self.stop_event.set() # 이벤트 설정하여 중단 신호
        return "작업이 중단되었습니다"

    def skip_current_item(self):
        self.skip_current = True
        return f"현재 항목 '{self.current_item}'을 건너뛰었습니다"

    def reset(self):
        self.is_stopped = False
        self.is_running = False
        self.skip_current = False
        self.current_item = ""
        self.stop_event.clear()

############################################
# 영역 시각화 오버레이 창
############################################
class AreaVisualizationOverlay(tk.Toplevel):
    def __init__(self, master, areas_info, theme_manager, auto_close=True):
        super().__init__(master)
        self.master = master
        self.areas_info = areas_info
        self.theme_manager = theme_manager # 테마 매니저 전달
        self.auto_close = auto_close

        # 아이콘 적용
        try:
            if hasattr(master, '_icon_photos') and master._icon_photos:
                self.iconphoto(True, *master._icon_photos)
            elif os.path.exists("eye_ocr_02_scanline.ico"):
                self.iconbitmap("eye_ocr_02_scanline.ico")
        except Exception:
            pass  # 아이콘 설정 실패해도 계속 진행

        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        overlay_bg = self.theme_manager.get_color('dark', 'black') # 어두운 배경 사용
        self.configure(bg=overlay_bg)
        self.attributes("-alpha", 0.7)

        self.canvas = tk.Canvas(self, bg=overlay_bg, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.draw_areas()

        if auto_close:
            self.after(3000, self.destroy)

        self.bind("<KeyPress>", self.on_key_press)
        self.focus_set()

    def draw_areas(self):
        colors = [
            self.theme_manager.get_color('danger'),  # 클릭 포인트
            self.theme_manager.get_color('primary'), # 전체 영역
            self.theme_manager.get_color('success'), # 날짜 영역
            self.theme_manager.get_color('warning')  # 금리 영역
        ]
        labels = ["클릭 포인트", "전체 영역", "날짜 영역", "금리 영역"]
        text_color = self.theme_manager.get_color('white', 'white')


        if "click_point" in self.areas_info:
            x, y = self.areas_info["click_point"]
            r = 10
            self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=colors[0], outline=text_color, width=3)
            self.canvas.create_text(x, y-25, text=labels[0], fill=text_color, font=("Arial", 12, "bold"))

        area_keys = ["all_area", "date_area", "rate_area"]
        for i, key in enumerate(area_keys):
            if key in self.areas_info and self.areas_info[key]:
                x1, y1, x2, y2 = self.areas_info[key]
                color = colors[i+1]
                self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=4, fill="")
                center_x = (x1 + x2) // 2
                center_y = y1 - 20 if y1 > 30 else y2 + 20
                self.canvas.create_text(center_x, center_y, text=labels[i+1], fill=color, font=("Arial", 14, "bold"))
                width, height = x2 - x1, y2 - y1
                size_text = f"{width}x{height}"
                self.canvas.create_text(center_x, center_y + 20, text=size_text, fill=text_color, font=("Arial", 10))

        screen_width = self.winfo_screenwidth()
        info_text = "설정된 영역들이 표시됩니다"
        if self.auto_close: info_text += " (3초 후 자동 종료)"
        info_text += " | ESC: 종료"
        self.canvas.create_text(screen_width//2, 50, text=info_text, fill=text_color, font=("Arial", 16, "bold"))

    def on_key_press(self, event):
        if event.keysym == "Escape":
            self.destroy()

############################################
# 드래그로 좌표를 지정하는 Overlay Window
############################################
class DragCaptureOverlay(tk.Toplevel):
    def __init__(self, master=None, color_key="danger", theme_manager=None): # color 대신 color_key 사용
        super().__init__(master)
        self.master = master
        self.theme_manager = theme_manager
        self.color = self.theme_manager.get_color(color_key, "red") # 테마에서 색상 가져오기

        # 아이콘 적용
        try:
            if hasattr(master, '_icon_photos') and master._icon_photos:
                self.iconphoto(True, *master._icon_photos)
            elif os.path.exists("eye_ocr_02_scanline.ico"):
                self.iconbitmap("eye_ocr_02_scanline.ico")
        except Exception:
            pass  # 아이콘 설정 실패해도 계속 진행

        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        overlay_bg = self.theme_manager.get_color('dark', 'black')
        self.configure(bg=overlay_bg)
        self.attributes("-alpha", 0.3)

        self.canvas = tk.Canvas(self, bg=overlay_bg, highlightthickness=0) # 투명 효과를 위해 bg를 부모와 동일하게
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.start_x, self.start_y = None, None
        self.rect_id = None
        self.x1, self.y1, self.x2, self.y2 = None, None, None, None

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.bind("<KeyPress-Escape>", lambda e: self.destroy()) # ESC로 닫기

    def on_button_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline=self.color, width=2)

    def on_move_press(self, event):
        curX, curY = (event.x, event.y)
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, curX, curY)

    def on_button_release(self, event):
        end_x, end_y = (event.x, event.y)
        self.x1, self.y1 = min(self.start_x, end_x), min(self.start_y, end_y)
        self.x2, self.y2 = max(self.start_x, end_x), max(self.start_y, end_y)
        self.destroy()

############################################
# 포인터 한 번 클릭으로 좌표를 지정하는 Overlay
############################################
class PointCaptureOverlay(tk.Toplevel):
    def __init__(self, master=None, color_key="danger", theme_manager=None):
        super().__init__(master)
        self.master = master
        self.theme_manager = theme_manager
        self.color = self.theme_manager.get_color(color_key, "red")

        # 아이콘 적용
        try:
            if hasattr(master, '_icon_photos') and master._icon_photos:
                self.iconphoto(True, *master._icon_photos)
            elif os.path.exists("eye_ocr_02_scanline.ico"):
                self.iconbitmap("eye_ocr_02_scanline.ico")
        except Exception:
            pass  # 아이콘 설정 실패해도 계속 진행

        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        overlay_bg = self.theme_manager.get_color('dark', 'black')
        self.configure(bg=overlay_bg)
        self.attributes("-alpha", 0.3)

        self.canvas = tk.Canvas(self, bg=overlay_bg, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.click_x, self.click_y = None, None
        self.canvas.bind("<ButtonPress-1>", self.on_click)
        self.bind("<KeyPress-Escape>", lambda e: self.destroy()) # ESC로 닫기

    def on_click(self, event):
        self.click_x, self.click_y = event.x, event.y
        r = 5
        self.canvas.create_oval(self.click_x - r, self.click_y - r, self.click_x + r, self.click_y + r, fill=self.color, outline=self.color)
        self.after(100, self.destroy) # 클릭 후 바로 닫기 (약간의 딜레이로 시각적 피드백)


############################################
# 데이터 관리자
############################################
class DataManager:
    def __init__(self, app_ref, logger, message_queue):
        self.app = app_ref # CheckCaptureOCRApp 참조
        self.logger = logger
        self.message_queue = message_queue
        self.excel_data = [] # [{'종목코드': '', '종목명': '', '날짜': '', '금리': '', '상태': ''}, ...]
        self.current_processing_index = -1

    def load_excel_to_grid_data(self, file_path):
        try:
            new_data, missing_columns = load_grid_rows(file_path)
            self.clear_all_data_internal()
            for target_col in missing_columns:
                self.logger.warning(f"Excel 파일에 '{target_col}'에 해당하는 컬럼을 찾을 수 없습니다.")
            self.excel_data = new_data
            return len(self.excel_data)
        except Exception as e:
            self.logger.exception("Excel 파일 로드 실패")
            self.message_queue.put(("error_messagebox", "Excel 파일 로드 중 오류", f"{e}"))
            return 0
            
    def add_empty_row_data(self):
        self.excel_data.append(empty_row())

    def paste_from_clipboard_data(self, clipboard_content):
        try:
            rows = rows_from_clipboard(clipboard_content)
            self.excel_data.extend(rows)
            return len(rows)
        except Exception as e:
            self.logger.exception("클립보드 붙여넣기 실패")
            self.message_queue.put(("error_messagebox", "붙여넣기 중 오류", f"{e}"))
            return 0

    def delete_rows_data(self, indices_to_delete):
        delete_rows(self.excel_data, indices_to_delete)
    
    def clear_all_data_internal(self):
        self.excel_data.clear()
        self.current_processing_index = -1

    def update_grid_cell_data(self, row_index, col_name, new_value):
        if 0 <= row_index < len(self.excel_data):
            self.excel_data[row_index][col_name] = new_value
            return True
        return False

    def get_row_for_copy(self, index):
        if 0 <= index < len(self.excel_data):
            return row_for_copy(self.excel_data[index])
        return ""

    def export_grid_to_excel_data(self, output_dir, input_file_path_str):
        if not self.excel_data:
            self.message_queue.put(("log", "내보낼 데이터가 없습니다.", "INFO"))
            return None

        new_file_path = updated_workbook_path(output_dir, input_file_path_str)

        try:
            # 디버그 로그: 엑셀 내보내기 직전 데이터 상태 확인
            self.logger.debug(f"[export_grid_to_excel_data] 내보내기 직전 데이터: {self.excel_data}")
            
            export_grid_rows(self.excel_data, new_file_path)
            export_success_path = new_file_path
            self.message_queue.put(("log", f"결과 Excel 파일 저장 완료: {new_file_path}", "SUCCESS"))
            return export_success_path
        except Exception as e:
            self.message_queue.put(("log", f"Excel 파일 저장 실패: {e}", "ERROR"))
            self.logger.exception("Excel 파일 저장 중 예외 발생")
            raise


############################################
# OCR 워크플로우 관리자
############################################
class OCRWorkflowManager:
    def __init__(self, app_ref, logger, message_queue, work_controller, settings_manager, data_manager):
        self.app = app_ref # CheckCaptureOCRApp 참조
        self.logger = logger
        self.message_queue = message_queue
        self.work_controller = work_controller
        self.settings_manager = settings_manager
        self.data_manager = data_manager # DataManager 인스턴스
        self.ocr_reader = None
        self._current_run_report = None
        self._current_run_report_path = None
        self._last_capture_timing = {}
        self._last_ocr_timings = {}
        self._last_ocr_confidences = {}

    def initialize_ocr(self):
        try:
            self.logger.info("EasyOCR 초기화 중... (영어 전용)")
            # gpu_enabled = self.settings_manager.get_advanced('ocr_gpu_enabled', False) # GPU 설정 제거
            gpu_enabled = False # GPU 사용 비활성화로 고정
            languages = ['en'] # 영어로 고정
            self.ocr_reader = create_easyocr_reader(languages, gpu=gpu_enabled)
            self.logger.info(f"EasyOCR 초기화 완료 - 언어: {languages}, GPU: {gpu_enabled}")
        except Exception as e:
            self.logger.error(f"EasyOCR 초기화 실패: {e}")
            try:
                self.logger.info("기본 모드(영어, CPU)로 EasyOCR 재초기화 시도...")
                self.ocr_reader = create_easyocr_reader(['en'], gpu=False)
                self.settings_manager.set_advanced('ocr_gpu_enabled', False)
                self.settings_manager.set_advanced('ocr_languages', ['en'])
                self.logger.info("EasyOCR 영어 모드(CPU)로 초기화 완료.")
            except Exception as e2:
                self.message_queue.put(("error_messagebox", "치명적 오류", f"OCR 엔진 초기화에 완전히 실패했습니다: {e2}"))
                self.logger.critical(f"OCR 엔진 초기화 완전 실패: {e2}")
                self.ocr_reader = None # 명시적으로 None 설정

    def execute_ocr_workflow_threaded(self, ui_settings, output_dir_str, save_detail_images_bool):
        """OCR 워크플로우 실행 (그리드 데이터 기반) - 스레드에서 호출됨"""
        try:
            if not self.ocr_reader:
                self.message_queue.put(("error_messagebox", "오류", "OCR 엔진이 초기화되지 않았습니다."))
                self.message_queue.put(("stopped", None))
                return

            paste_d = ui_settings['delays']['paste']
            load_d = ui_settings['delays']['loading']
            coords = {
                'click': ui_settings['click_point'],
                'all': ui_settings['all_area'],
                'date': ui_settings['date_area'],
                'rate': ui_settings['rate_area'],
            }
            
            input_excel_file = self.app.input_excel_path.get()
            if input_excel_file:
                base_name = os.path.splitext(os.path.basename(input_excel_file))[0]
                save_folder = os.path.join(output_dir_str, base_name)
            else:
                save_folder = os.path.join(output_dir_str, "ocr_images")

            os.makedirs(save_folder, exist_ok=True)
            self._last_capture_timing = {}
            self._last_ocr_timings = {}
            self._last_ocr_confidences = {}
            row_timing_by_index = {}
            row_metadata_by_index = {}
            row_started_by_index = {}
            self._current_run_report_path = report_output_path(output_dir_str, input_excel_file)
            self._current_run_report = create_run_report(
                output_dir=output_dir_str,
                input_excel_path=input_excel_file or "",
                total_items=len(self.data_manager.excel_data),
                save_detail_images=save_detail_images_bool,
            )

            class TkAutomationAdapter:
                def capture(_adapter_self, row, context):
                    capture_started = perf_counter()
                    date_img_src, rate_img_src = self._capture_screenshots_internal(
                        row.code, save_folder, coords, paste_d, load_d, save_detail_images_bool
                    )
                    capture_timing = dict(self._last_capture_timing)
                    capture_timing.setdefault("capture_adapter_ms", self._elapsed_ms(capture_started))
                    row_timing_by_index.setdefault(context.index, {})["capture_timing_ms"] = capture_timing
                    if date_img_src is None or rate_img_src is None:
                        return None
                    return CapturedImages(date_img_src, rate_img_src, metadata={"timing_ms": capture_timing})

            class EasyOcrAdapter:
                def read(_adapter_self, images, row, context):
                    ocr_started = perf_counter()
                    self._last_ocr_timings = {}
                    self._last_ocr_confidences = {}
                    date_result, rate_result = self._process_single_ocr_internal(
                        images.date_image,
                        images.rate_image,
                        save_detail_images_bool,
                    )
                    ocr_timing = dict(self._last_ocr_timings)
                    ocr_timing.setdefault("ocr_adapter_ms", self._elapsed_ms(ocr_started))
                    timing = row_timing_by_index.setdefault(context.index, {})
                    timing["ocr_timing_ms"] = ocr_timing
                    if self._last_ocr_confidences:
                        row_metadata_by_index.setdefault(context.index, {})["ocr_confidence"] = dict(
                            self._last_ocr_confidences
                        )
                    return OcrResult(date_result, rate_result, metadata={"timing_ms": timing})

            def emit_to_tk_queue(event):
                legacy_event = event.as_legacy_tuple()
                if legacy_event[0] == "grid_update":
                    update_payload = legacy_event[1]
                    update_type = update_payload[0]
                    row_index = update_payload[1]
                    if update_type == "processing":
                        row_started_by_index[row_index] = perf_counter()
                        self.data_manager.current_processing_index = row_index
                    elif update_type in {"complete", "error"} and row_index in row_started_by_index:
                        row_timing_by_index.setdefault(row_index, {})["row_total_ms"] = self._elapsed_ms(
                            row_started_by_index[row_index]
                        )
                self.message_queue.put(legacy_event)

            runner = WorkflowRunner(
                TkAutomationAdapter(),
                EasyOcrAdapter(),
                stop_token=self.work_controller,
                event_sink=emit_to_tk_queue,
            )
            result = runner.process_rows(
                self.data_manager.excel_data,
                WorkflowOptions(
                    skip_kbp_code=self.settings_manager.get_advanced('skip_kbp_code', True),
                    save_detail_images=save_detail_images_bool,
                    output_dir=output_dir_str,
                    input_excel_path=input_excel_file,
                ),
            )
            if result.stopped:
                finalize_workflow_processing_states(self.data_manager.excel_data)
                self.logger.info("[OCRWorkflowManager] 작업 루프 종료됨 (사용자 중단).")
            else:
                self.logger.info("[OCRWorkflowManager] 모든 항목 처리 완료. 최종 처리 메시지 전송 중.")

            if self._current_run_report is not None:
                finalize_workflow_processing_states(self.data_manager.excel_data)
                record_row_reports(
                    self._current_run_report,
                    self.data_manager.excel_data,
                    row_timing_by_index,
                    row_metadata_by_index,
                )
                finalize_run_report(
                    self._current_run_report,
                    self.data_manager.excel_data,
                    processed_count=result.processed_count,
                    total_items=result.total_items,
                    stopped=result.stopped,
                )
                self._flush_current_run_report()

        except Exception as e_workflow:
            self.message_queue.put(("log", f"OCR 전체 워크플로우 오류: {e_workflow}", "ERROR"))
            self.logger.exception("OCR 전체 워크플로우에서 예외 발생")
            # 워크플로우 자체에서 예외 발생 시에도 중단 처리 및 stopped 메시지 보냄
            if self._current_run_report is not None:
                finalize_workflow_processing_states(self.data_manager.excel_data)
                finalize_run_report(
                    self._current_run_report,
                    self.data_manager.excel_data,
                    processed_count=0,
                    total_items=len(self.data_manager.excel_data),
                    stopped=True,
                    error=str(e_workflow),
                )
                self._flush_current_run_report()
            if not self.work_controller.is_stopped:
                 self.work_controller.stop_work() # is_stopped 플래그 설정 및 stop_event 설정
            # 예외 발생 후에도 stopped 메시지를 보내 UI 상태를 중단됨으로 변경
            self.message_queue.put(("stopped", None))

    def _flush_current_run_report(self):
        if self._current_run_report is None or self._current_run_report_path is None:
            return
        try:
            report_path = write_run_report(self._current_run_report, self._current_run_report_path)
            self.message_queue.put(("log", f"OCR run report saved: {report_path}", "INFO"))
        except Exception as report_error:
            self.message_queue.put(("log", f"OCR run report save failed: {report_error}", "WARNING"))
            self.logger.exception("OCR run report save failed")

    @staticmethod
    def _elapsed_ms(started_at):
        return round((perf_counter() - started_at) * 1000, 3)

    def _capture_screenshots_internal(self, stock_code, save_folder, coords, paste_d, load_d, save_details):
        capture_started = perf_counter()
        timing = {}
        self._last_capture_timing = timing
        if self.work_controller.is_stopped:
            timing["capture_total_ms"] = self._elapsed_ms(capture_started)
            return None, None
        copy_started = perf_counter()
        copy_text(stock_code)
        timing["copy_ms"] = self._elapsed_ms(copy_started)
        click_started = perf_counter()
        click(
            coords['click'][0],
            coords['click'][1],
            clicks=2,
            interval=self.settings_manager.get_advanced('click_interval', 0.1),
        )
        timing["click_ms"] = self._elapsed_ms(click_started)
        wait_started = perf_counter()
        
        # time.sleep 대신 work_controller.stop_event.wait 사용
        if self.work_controller.stop_event.wait(timeout=paste_d):
            timing["paste_wait_ms"] = self._elapsed_ms(wait_started)
            timing["capture_total_ms"] = self._elapsed_ms(capture_started)
            return None, None
        
        timing["paste_wait_ms"] = self._elapsed_ms(wait_started)
        paste_started = perf_counter()
        hotkey('ctrl', 'v')
        timing["paste_hotkey_ms"] = self._elapsed_ms(paste_started)

        wait_started = perf_counter()
        if self.work_controller.stop_event.wait(timeout=load_d):
            timing["load_wait_ms"] = self._elapsed_ms(wait_started)
            timing["capture_total_ms"] = self._elapsed_ms(capture_started)
            return None, None
        timing["load_wait_ms"] = self._elapsed_ms(wait_started)

        safe_stock_code = sanitize_filename(stock_code)
        date_img_src, rate_img_src = None, None

        # 전체 영역
        x1_all, y1_all, x2_all, y2_all = coords['all']
        if not (x2_all > x1_all and y2_all > y1_all):
            self.message_queue.put(("log", f"[{safe_stock_code}] 전체 영역 좌표 오류: {coords['all']}", "ERROR"))
            timing["capture_total_ms"] = self._elapsed_ms(capture_started)
            return None, None
        if save_details:
            screenshot_started = perf_counter()
            screenshot_all = screenshot(region=(x1_all, y1_all, x2_all - x1_all, y2_all - y1_all))
            timing["capture_all_ms"] = self._elapsed_ms(screenshot_started)
            save_started = perf_counter()
            allarea_path = os.path.join(save_folder, f"{safe_stock_code}.png")
            screenshot_all.save(allarea_path)
            timing["save_all_ms"] = self._elapsed_ms(save_started)
            self.message_queue.put(("log", f"전체 영역 이미지 저장: {allarea_path}", "INFO"))
        else:
            timing["capture_all_ms"] = 0.0

        # 날짜 영역
        if not save_details:
            timing["save_all_ms"] = 0.0

        x1_date, y1_date, x2_date, y2_date = coords['date']
        if not (x2_date > x1_date and y2_date > y1_date):
            self.message_queue.put(("log", f"[{safe_stock_code}] 날짜 영역 좌표 오류: {coords['date']}", "ERROR"))
        else:
            screenshot_started = perf_counter()
            screenshot_date = screenshot(region=(x1_date, y1_date, x2_date - x1_date, y2_date - y1_date))
            timing["capture_date_ms"] = self._elapsed_ms(screenshot_started)
            if save_details:
                save_started = perf_counter()
                date_img_src = os.path.join(save_folder, f"{safe_stock_code}_date.png")
                screenshot_date.save(date_img_src)
                timing["save_date_ms"] = self._elapsed_ms(save_started)
                self.message_queue.put(("log", f"날짜 영역 이미지 저장: {date_img_src}", "INFO"))
            else:
                timing["save_date_ms"] = 0.0
                date_img_src = screenshot_date

        # 금리 영역
        x1_rate, y1_rate, x2_rate, y2_rate = coords['rate']
        if not (x2_rate > x1_rate and y2_rate > y1_rate):
            self.message_queue.put(("log", f"[{safe_stock_code}] 금리 영역 좌표 오류: {coords['rate']}", "ERROR"))
        else:
            screenshot_started = perf_counter()
            screenshot_rate = screenshot(region=(x1_rate, y1_rate, x2_rate - x1_rate, y2_rate - y1_rate))
            timing["capture_rate_ms"] = self._elapsed_ms(screenshot_started)
            if save_details:
                save_started = perf_counter()
                rate_img_src = os.path.join(save_folder, f"{safe_stock_code}_rate.png")
                screenshot_rate.save(rate_img_src)
                timing["save_rate_ms"] = self._elapsed_ms(save_started)
                self.message_queue.put(("log", f"금리 영역 이미지 저장: {rate_img_src}", "INFO"))
            else:
                timing["save_rate_ms"] = 0.0
                rate_img_src = screenshot_rate
        
        timing["capture_total_ms"] = self._elapsed_ms(capture_started)
        return date_img_src, rate_img_src

    def _process_single_ocr_internal(self, date_img_src, rate_img_src, save_details):
        date_result, rate_result = "", ""
        try:
            if date_img_src:
                date_result = self._extract_text_with_ocr_attempts_internal(date_img_src, self._analyze_date_results_internal, "날짜", save_details)
            if rate_img_src:
                rate_result = self._extract_text_with_ocr_attempts_internal(rate_img_src, self._analyze_rate_results_internal, "금리", save_details)
        except Exception as e:
            self.message_queue.put(("log", f"단일 OCR 처리 중 오류: {e}", "ERROR"))
            self.logger.exception("단일 OCR 처리 중 예외 발생")
        return date_result, rate_result

    def _extract_text_with_ocr_attempts_internal(self, image_source, analysis_function, field_name, save_details):
        if self.work_controller.is_stopped: return ""
        field_key = "date" if "date" in getattr(analysis_function, "__name__", "") else "rate"
        extract_started = perf_counter()
        try:
            image_load_started = perf_counter()
            original_img = Image.open(image_source) if isinstance(image_source, str) else image_source
            self._last_ocr_timings[f"{field_key}_image_load_ms"] = self._elapsed_ms(image_load_started)
            if original_img is None:
                self.message_queue.put(("log", f"{field_name} 이미지 소스 로드 실패: {image_source}", "WARNING"))
                return ""

            if self.work_controller.is_stopped: return ""
            
            # 업스케일링 설정 가져오기
            enable_upscaling = self.settings_manager.get_advanced('upscaling_enabled', True)
            upscaling_factor = self.settings_manager.get_advanced('upscaling_factor', 2.0)
            upscaling_method = self.settings_manager.get_advanced('upscaling_method', 'LANCZOS')
            
            # 업스케일링 적용
            preprocess_started = perf_counter()
            processed_img = self._apply_image_upscaling(original_img, enable_upscaling, upscaling_factor, upscaling_method)
            
            # 업스케일링된 이미지를 numpy 배열로 변환하여 OCR 수행
            img_array = np.array(processed_img)
            self._last_ocr_timings[f"{field_key}_preprocess_ms"] = self._elapsed_ms(preprocess_started)
            ocr_started = perf_counter()
            ocr_detail = self._ocr_detail_level()
            ocr_results = read_ocr_text(self.ocr_reader, img_array, detail=ocr_detail)
            self._last_ocr_timings[f"{field_key}_ocr_ms"] = self._elapsed_ms(ocr_started)
            all_text, confidence = extract_text_with_confidence(ocr_results, ocr_detail)
            if confidence is not None:
                self._last_ocr_confidences[f"{field_key}_confidence"] = round(confidence, 4)
            min_confidence = self._minimum_confidence(field_key)
            if ocr_detail == 1 and not confidence_is_accepted(confidence, min_confidence):
                threshold = normalize_confidence_threshold(min_confidence)
                self.message_queue.put(
                    (
                        "log",
                        f"[{field_name}] OCR confidence below threshold: {confidence} < {threshold}",
                        "WARNING",
                    )
                )
                return ""
            
            # 업스케일링 정보 포함한 로그 메시지
            scale_info = f" (업스케일링: {upscaling_factor}x {upscaling_method})" if enable_upscaling and upscaling_factor > 1.0 else ""
            self.message_queue.put(("log", f"[{field_name}] OCR 결과{scale_info}: '{all_text}'", "INFO"))
            
            parse_started = perf_counter()
            parsed_text = analysis_function(all_text, field_name)
            self._last_ocr_timings[f"{field_key}_parse_ms"] = self._elapsed_ms(parse_started)
            return parsed_text
        except Exception as e:
            self.message_queue.put(("log", f"{field_name} 추출 중 오류: {e}", "ERROR"))
            self.logger.exception(f"{field_name} 추출 중 예외 발생")
            return ""
        finally:
            self._last_ocr_timings[f"{field_key}_total_ms"] = self._elapsed_ms(extract_started)
            if isinstance(image_source, str) and not save_details:
                if os.path.exists(image_source) and ("_date.png" in image_source or "_rate.png" in image_source):
                    try:
                        os.remove(image_source)
                        self.message_queue.put(("log", f"임시 {field_name} 이미지 파일 삭제: {image_source}", "DEBUG"))
                    except Exception as e_remove:
                        self.message_queue.put(("log", f"임시 {field_name} 이미지 파일 삭제 실패: {e_remove}", "WARNING"))

    def _ocr_detail_level(self):
        try:
            return 1 if int(self.settings_manager.get_advanced("ocr_detail_level", 0)) == 1 else 0
        except (TypeError, ValueError):
            return 0

    def _minimum_confidence(self, field_key):
        return self.settings_manager.get_advanced(f"min_{field_key}_confidence", 0.0)
    
    def _analyze_date_results_internal(self, raw_text, field_name="날짜"):
        if not raw_text or not raw_text.strip():
            self.message_queue.put(("log", f"[{field_name}] 텍스트가 비어있습니다.", "DEBUG"))
            return ""
        self.message_queue.put(("log", f"[{field_name}] 원본 텍스트: '{raw_text}'", "DEBUG"))
        cleaned_text = self._clean_date_text_internal(raw_text)
        if self._is_valid_date_format_internal(cleaned_text):
            self.message_queue.put(("log", f"[{field_name}] 유효한 날짜: '{cleaned_text}'", "DEBUG"))
            return cleaned_text
        else:
            self.message_queue.put(("log", f"[{field_name}] 유효하지 않은 날짜 형식: '{cleaned_text}' (원본: '{raw_text}')", "DEBUG"))
            return "" # 빈 문자열 반환하여 그리드에 표시되지 않도록

    def _analyze_rate_results_internal(self, raw_text, field_name="금리"):
        if not raw_text or not raw_text.strip():
            self.message_queue.put(("log", f"[{field_name}] 텍스트가 비어있습니다.", "DEBUG"))
            return ""
        self.message_queue.put(("log", f"[{field_name}] 원본 텍스트: '{raw_text}'", "DEBUG"))
        cleaned_text = self._clean_rate_text_internal(raw_text)
        if self._is_valid_rate_format_internal(cleaned_text):
            self.message_queue.put(("log", f"[{field_name}] 유효한 금리: '{cleaned_text}'", "DEBUG"))
            return cleaned_text
        else:
            self.message_queue.put(("log", f"[{field_name}] 유효하지 않은 금리 형식: '{cleaned_text}' (원본: '{raw_text}')", "DEBUG"))
            return ""

    def _is_valid_date_format_internal(self, date_str):
        return is_valid_date_format(date_str)

    def _is_valid_rate_format_internal(self, rate_str):
        return is_valid_rate_format(rate_str)

    def _clean_date_text_internal(self, text):
        return clean_date_text(text)


    def _clean_rate_text_internal(self, text):
        return clean_rate_text(text)

    def _generate_ocr_summary_internal(self, processed_count, total_items):
        date_success = sum(1 for row in self.data_manager.excel_data if row.get('날짜','').strip() and row['상태'] == '완료')
        rate_success = sum(1 for row in self.data_manager.excel_data if row.get('금리','').strip() and row['상태'] == '완료')
        actual_processed_for_stats = sum(1 for row in self.data_manager.excel_data if row['상태'] == '완료')
        date_accuracy = (date_success / actual_processed_for_stats * 100) if actual_processed_for_stats > 0 else 0
        rate_accuracy = (rate_success / actual_processed_for_stats * 100) if actual_processed_for_stats > 0 else 0
        summary = f"""📊 OCR 처리 완료!
        ------------------------------------
        총 시도 항목: {total_items}개
        성공적으로 처리된 항목: {actual_processed_for_stats}개
        ------------------------------------
        📁 결과는 그리드 및 Excel 파일로 저장되었습니다.
        📝 상세 로그는 ocr_app.log 파일에서 확인 가능합니다.
        """
        return summary

    def _finalize_processing_states(self):
        """처리 완료 후 모든 항목의 상태를 최종화"""
        try:
            for i, row_data in enumerate(self.data_manager.excel_data):
                # '처리 중...' 상태이거나, 처리되지 않은 항목들을 '중단됨'으로 표시
                # 이미 완료/오류 상태인 항목은 그대로 둠
                if row_data['상태'] == '처리 중...' or row_data['상태'] == '대기 중':
                    row_data['상태'] = '중단됨'
            self.message_queue.put(("log", "모든 처리 상태를 최종화했습니다.", "INFO"))
        except Exception as e:
            self.message_queue.put(("log", f"상태 최종화 중 오류: {e}", "ERROR"))
            self.logger.exception("처리 상태 최종화 중 예외 발생")

    def _clean_folder_path(self, path: str | None) -> str:
        default_dir = self.settings_manager.get_advanced('default_output_dir', ".")
        return normalize_folder_path(path, default=default_dir, logger=self.logger)

    # 엑셀 내보내기 및 최종 완료 처리를 담당하는 함수 (메인 스레드에서 호출됨)
    def _finalize_export_and_complete(self, output_dir_str, input_excel_path_str, summary_message):
        self.logger.info("[_finalize_export_and_complete] 함수 호출됨 (Main Thread)")

        # 엑셀 내보내기 직전에 최종 상태를 다시 한번 정리 (안정성 강화)
        # 이전에 모든 grid_update 메시지가 처리되었음을 가정하고 finalize_processing_states 호출
        self._finalize_processing_states() # 이 함수는 이제 data_manager.excel_data를 직접 업데이트

        # 데이터 내보내기 호출
        export_started = perf_counter()
        export_error = None
        output_workbook = updated_workbook_path(output_dir_str, input_excel_path_str)
        try:
            output_workbook = self.data_manager.export_grid_to_excel_data(
                output_dir=output_dir_str,
                input_file_path_str=input_excel_path_str,
            ) or output_workbook
        except Exception as export_exc:
            export_error = f"Excel export failed: {export_exc}"
        export_timing_ms = {"export_ms": round((perf_counter() - export_started) * 1000, 3)}
        report_manager = self
        if report_manager._current_run_report is not None:
            existing_timings = {
                row_report.get("index"): row_report.get("timing_ms", {})
                for row_report in report_manager._current_run_report.get("rows", [])
            }
            existing_metadata = {
                row_report.get("index"): {"ocr_confidence": row_report.get("ocr_confidence")}
                for row_report in report_manager._current_run_report.get("rows", [])
                if row_report.get("ocr_confidence")
            }
            record_row_reports(
                report_manager._current_run_report,
                self.data_manager.excel_data,
                existing_timings,
                existing_metadata,
            )
            summary = report_manager._current_run_report.get("summary", {})
            if export_error is None and not output_workbook.exists():
                export_error = f"Export workbook was not found after export: {output_workbook}"
            finalize_run_report(
                report_manager._current_run_report,
                self.data_manager.excel_data,
                processed_count=int(summary.get("processed_count", 0) or 0),
                total_items=int(summary.get("total_items", len(self.data_manager.excel_data)) or 0),
                stopped=bool(summary.get("stopped", False)),
                output_workbook_path=output_workbook,
                export_timing_ms=export_timing_ms,
                error=export_error,
            )
            report_manager._flush_current_run_report()

        if export_error is not None:
            self.refresh_grid_ui()
            messagebox.showerror("Excel export failed", export_error)
            return

        # 그리드 UI 최종 새로고침
        # _finalize_processing_states 및 export_grid_to_excel_data 후에 UI를 새로고침하여 최종 상태와 데이터를 표시
        self.refresh_grid_ui() # 상태 최종화 결과 반영 및 최종 데이터 표시

        # 최종 완료 메시지 박스 표시
        if export_error is not None:
            messagebox.showerror("Excel export failed", export_error)
            return
        messagebox.showinfo("처리 완료", summary_message)

    def _apply_image_upscaling(self, image_source, enable_upscaling, upscaling_factor, upscaling_method):
        """
        이미지 업스케일링 적용 함수
        
        Args:
            image_source: PIL Image 객체 또는 파일 경로
            enable_upscaling: 업스케일링 활성화 여부
            upscaling_factor: 확대 배율 (1.5, 2.0, 2.5, 3.0, 4.0)
            upscaling_method: 리샘플링 방법 ('LANCZOS', 'BICUBIC', 'BILINEAR')
        
        Returns:
            PIL Image 객체 (업스케일링 적용된)
        """
        try:
            # 이미지 로드
            if isinstance(image_source, str):
                original_img = Image.open(image_source)
            else:
                original_img = image_source
            
            original_width, original_height = original_img.size
            upscaled_img = upscale_image(
                original_img,
                enabled=enable_upscaling,
                factor=upscaling_factor,
                method=upscaling_method,
            )
            new_width, new_height = upscaled_img.size
            if upscaled_img is not original_img:
                self.message_queue.put(("log", f"이미지 업스케일링 완료: {original_width}x{original_height} → {new_width}x{new_height} ({upscaling_method})", "DEBUG"))
            
            return upscaled_img
            
        except Exception as e:
            self.message_queue.put(("log", f"이미지 업스케일링 실패: {e}, 원본 이미지 사용", "WARNING"))
            self.logger.exception("이미지 업스케일링 중 예외 발생")
            # 업스케일링 실패 시 원본 이미지 반환
            if isinstance(image_source, str):
                return Image.open(image_source)
            else:
                return image_source

############################################
# 메인 GUI
############################################
class CheckCaptureOCRApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("📊 Check Capture OCR V6.1")
        self.geometry("1200x850")
        
        # 아이콘 설정 개선 (창과 작업표시줄 모두 적용)
        self._setup_application_icon()
        
        self.resizable(True, True)
        self.minsize(1000, 600)
        self.center_window()

        self.message_queue = queue.Queue()
        self.logger = setup_logging(self.message_queue)
        
        self.settings_manager = UnifiedSettingsManager()
        self.theme_manager = ThemeManager(self)
        self.work_controller = WorkController()
        self.data_manager = DataManager(self, self.logger, self.message_queue)
        self.ocr_workflow_manager = OCRWorkflowManager(self, self.logger, self.message_queue, self.work_controller, self.settings_manager, self.data_manager)
        
        self.worker_thread = None
        self.ocr_init_thread = None
        self.ocr_initializing = False
        self.runtime_state = RuntimeState.STARTING

        self.input_excel_path = tk.StringVar()
        self.output_folder_path = tk.StringVar()
        self.click_x, self.click_y = tk.IntVar(value=340), tk.IntVar(value=165)
        self.allarea_x1, self.allarea_y1 = tk.IntVar(value=15), tk.IntVar(value=200)
        self.allarea_x2, self.allarea_y2 = tk.IntVar(value=1845), tk.IntVar(value=870)
        self.datearea_x1, self.datearea_y1 = tk.IntVar(value=826), tk.IntVar(value=88)
        self.datearea_x2, self.datearea_y2 = tk.IntVar(value=1064), tk.IntVar(value=127)
        self.ratearea_x1, self.ratearea_y1 = tk.IntVar(value=1069), tk.IntVar(value=89)
        self.ratearea_x2, self.ratearea_y2 = tk.IntVar(value=1326), tk.IntVar(value=126)
        self.paste_delay = tk.DoubleVar(value=0.5)
        self.loading_delay = tk.DoubleVar(value=2.5)
        self.save_detail_images = tk.BooleanVar(value=True)
        self.confidence_threshold = tk.DoubleVar(value=20.0)
        self.theme_var = tk.StringVar()
        
        # 업스케일링 옵션 추가
        self.enable_upscaling = tk.BooleanVar(value=True)
        self.upscaling_factor = tk.DoubleVar(value=2.0)
        self.upscaling_method = tk.StringVar(value="LANCZOS")

        self.grid_tree = None
        self.log_text_widget = None

        self._build_ui()
        self._setup_keyboard_shortcuts()
        self.check_queue()
        self.load_last_settings()
        self.theme_manager.apply_theme_to_all_widgets()
        self._set_runtime_state(RuntimeState.STARTING)
        self.after(100, self.start_ocr_initialization_async)

    def start_ocr_initialization_async(self):
        if self.ocr_initializing or self.ocr_workflow_manager.ocr_reader:
            return
        self.ocr_initializing = True
        self._set_runtime_state(RuntimeState.OCR_LOADING)

        if os.environ.get(PACKAGE_SMOKE_FAST_OCR_ENV) == "1":
            self.ocr_workflow_manager.ocr_reader = object()
            self.message_queue.put(("ocr_ready", True))
            return

        def initialize():
            self.ocr_workflow_manager.initialize_ocr()
            self.message_queue.put(("ocr_ready", self.ocr_workflow_manager.ocr_reader is not None))

        self.ocr_init_thread = threading.Thread(target=initialize, daemon=True)
        self.ocr_init_thread.start()

    def _set_runtime_state(self, state):
        self.runtime_state = state
        ui_state = runtime_state_ui(state)
        if not hasattr(self, "run_btn") or not self.run_btn:
            self._write_package_smoke_status()
            return
        self.run_btn.config(state=ui_state.run_button_state, text=ui_state.run_button_text)
        if hasattr(self, "stop_btn") and self.stop_btn:
            self.stop_btn.config(state=ui_state.stop_button_state)
        self._write_package_smoke_status()

    def _set_ocr_ready_ui(self, ready):
        self._set_runtime_state(RuntimeState.READY if ready else RuntimeState.OCR_LOADING)

    def _ready_or_error_state(self):
        return RuntimeState.READY if self.ocr_workflow_manager.ocr_reader else RuntimeState.ERROR

    def _write_package_smoke_status(self):
        status_file = os.environ.get(PACKAGE_SMOKE_STATUS_FILE_ENV)
        if not status_file:
            return

        try:
            payload = {
                "runtime_state": self.runtime_state.value,
                "ocr_ready": bool(self.ocr_workflow_manager.ocr_reader),
                "settings_file": getattr(self.settings_manager, "settings_file", None),
                "written_at": datetime.now().isoformat(),
            }
            path = Path(status_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        except OSError as exc:
            if hasattr(self, "logger"):
                self.logger.debug("Package smoke status write failed: %s", exc)

    def _setup_application_icon(self):
        """애플리케이션 아이콘을 창과 작업표시줄에 모두 설정"""
        try:
            # ICO 파일 설정 (Windows 창 제목표시줄용)
            ico_path = None
            if os.path.exists("eye_ocr_02_scanline.ico"):
                ico_path = "eye_ocr_02_scanline.ico"
            elif os.path.exists("app_icon.ico"):
                ico_path = "app_icon.ico"

            if ico_path:
                self.iconbitmap(ico_path)
                print(f"ICO 아이콘 설정 완료: {ico_path}")

            # PNG 파일 설정 (작업표시줄 및 추가 지원용)
            png_path = None
            if os.path.exists("eye_ocr_02_scanline.png"):
                png_path = "eye_ocr_02_scanline.png"
            elif os.path.exists("app_icon.png"):
                png_path = "app_icon.png"

            if png_path:
                try:
                    from PIL import Image, ImageTk
                    # PNG 이미지를 PhotoImage로 변환
                    pil_image = Image.open(png_path)
                    # 다양한 크기로 아이콘 설정 (16x16, 32x32, 48x48)
                    icon_sizes = [16, 32, 48]
                    photo_images = []

                    for size in icon_sizes:
                        resized_image = pil_image.resize((size, size), Image.Resampling.LANCZOS)
                        photo_image = ImageTk.PhotoImage(resized_image)
                        photo_images.append(photo_image)

                    # PhotoImage 객체들을 인스턴스 변수로 저장 (가비지 컬렉션 방지)
                    self._icon_photos = photo_images

                    # 가장 큰 크기 아이콘을 기본으로 설정
                    if photo_images:
                        self.iconphoto(True, *photo_images)  # True는 모든 창에 적용
                        print(f"PNG 아이콘 설정 완료: {png_path} ({len(photo_images)}개 크기)")

                except ImportError:
                    print("PIL 라이브러리를 찾을 수 없어 PNG 아이콘 설정을 건너뜁니다.")
                except Exception as e:
                    print(f"PNG 아이콘 설정 중 오류: {e}")

            if not ico_path and not png_path:
                print("아이콘 파일을 찾을 수 없습니다.")

        except Exception as e:
            print(f"아이콘 설정 중 전체 오류: {e}")

    def center_window(self):
        self.update_idletasks()
        screen_width, screen_height = self.winfo_screenwidth(), self.winfo_screenheight()
        window_width, window_height = self.winfo_width(), self.winfo_height()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")

    def _setup_keyboard_shortcuts(self):
        self.focus_set()
        self.bind_all('<Control-s>', lambda e: self.quick_save_settings())
        self.bind_all('<Control-l>', lambda e: self.load_last_settings())
        self.bind_all('<Control-o>', lambda e: self.load_excel_to_grid())
        self.bind_all('<F5>', lambda e: self.handle_f5_key())
        self.bind_all('<Escape>', lambda e: self.stop_processing_ui_initiated())
        self.bind_all('<F1>', lambda e: self.show_shortcuts())

    def handle_f5_key(self):
        if self.work_controller.is_running:
            self.stop_processing_ui_initiated()
        else:
            self.run_ocr_process()

    def check_queue(self):
        process_legacy_message_queue(self, show_error=messagebox.showerror)
        check_interval = queue_check_interval(self.work_controller.is_running)
        self.after(check_interval, self.check_queue)

    def _update_log_text_widget(self, message, level_name="INFO"):
        if self.log_text_widget and self.log_text_widget.winfo_exists():
            self.log_text_widget.config(state='normal')
            tag = level_name.upper()
            if tag not in self.log_text_widget.tag_names():
                tag = "INFO" 
            self.log_text_widget.insert(tk.END, f"{message}\n", tag)
            self.log_text_widget.see(tk.END)
            self.log_text_widget.config(state='disabled')

    def _build_ui(self):
        self.configure(bg=self.theme_manager.get_color('surface'))
        self._create_menu()
        self._create_simple_toolbar()

        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        main_container = tk.Frame(self)
        self.theme_manager.register_widget(main_container, {'bg': 'surface'})
        main_container.grid(row=1, column=0, sticky='nsew', padx=0, pady=0)

        main_container.grid_rowconfigure(0, weight=1)

        main_container.grid_columnconfigure(0, weight=0, minsize=280) # 좌측 패널 너비 고정 (필요시 조정)
        main_container.grid_columnconfigure(1, weight=6) # 중앙 패널 확장 비율 더 증가
        main_container.grid_columnconfigure(2, weight=1, minsize=200) # 우측 로그 패널 weight 유지 및 minsize 더 축소

        left_panel = tk.Frame(main_container)
        self.theme_manager.register_widget(left_panel, {'bg': 'surface'})
        left_panel.grid(row=0, column=0, sticky='nsew', padx=(5, 2), pady=5)

        center_panel = tk.Frame(main_container)
        self.theme_manager.register_widget(center_panel, {'bg': 'surface'})
        center_panel.grid(row=0, column=1, sticky='nsew', padx=3, pady=5)

        right_panel = tk.Frame(main_container)
        self.theme_manager.register_widget(right_panel, {'bg': 'surface'})
        right_panel.grid(row=0, column=2, sticky='nsew', padx=(2, 5), pady=5)

        self._create_left_panel_content(left_panel)
        self._create_center_excel_grid(center_panel)
        self._create_right_panel_content(right_panel)

        if self.log_text_widget:
            tkinter_handler = TkinterLogHandler(self.log_text_widget, self.message_queue)
            self.logger.addHandler(tkinter_handler)

    def _create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        # ... (메뉴 생성 코드는 기존과 유사하게 유지, 필요시 테마 적용)
        # 파일 메뉴
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="파일", menu=file_menu)
        file_menu.add_command(label="Excel 파일 로드 (Ctrl+O)", command=self.load_excel_to_grid, accelerator="Ctrl+O")
        file_menu.add_command(label="Excel 파일 선택", command=self.browse_input_excel)
        file_menu.add_command(label="출력 폴더 선택", command=self.browse_output_folder)
        file_menu.add_command(label="출력 폴더 열기", command=self.open_output_folder) # 출력 폴더 열기 메뉴 항목 추가
        file_menu.add_separator()
        file_menu.add_command(label="종료 (Alt+F4)", command=self.quit_app, accelerator="Alt+F4")

        # 설정 메뉴
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="설정", menu=settings_menu)
        settings_menu.add_command(label="현재 설정 저장 (Ctrl+S)", command=self.quick_save_settings, accelerator="Ctrl+S")
        settings_menu.add_command(label="마지막 설정 불러오기 (Ctrl+L)", command=self.load_last_settings, accelerator="Ctrl+L")
        settings_menu.add_separator()

        # 미리보기 메뉴
        preview_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="미리보기", menu=preview_menu)
        preview_menu.add_command(label="전체 영역 미리보기", command=self.show_area_preview)

        # 실행 메뉴
        run_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="실행", menu=run_menu)
        run_menu.add_command(label="OCR 시작/중단 (F5)", command=self.handle_f5_key, accelerator="F5")
        run_menu.add_command(label="처리 중단 (Esc)", command=self.stop_processing_ui_initiated, accelerator="Esc")

        # 도움말 메뉴
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="도움말", menu=help_menu)
        help_menu.add_command(label="키보드 단축키 (F1)", command=self.show_shortcuts, accelerator="F1")
        help_menu.add_command(label="프로그램 정보", command=self.show_about)


    def _create_simple_toolbar(self):
        toolbar = tk.Frame(self, height=35)
        self.theme_manager.register_widget(toolbar, {'bg': 'primary'})
        toolbar.grid(row=0, column=0, sticky='ew', padx=0, pady=0)
        toolbar.pack_propagate(False)
        
        title_lbl = tk.Label(toolbar, text="📊 Check Capture OCR V6.1", font=('Segoe UI', 11, 'bold'))
        self.theme_manager.register_widget(title_lbl, {'bg': 'primary', 'fg': 'white'})
        title_lbl.pack(side='left', padx=8, pady=6)
        
        # 컨트롤 프레임을 중앙에 배치하기 위해 별도의 컨테이너 사용
        center_controls_container = tk.Frame(toolbar)
        self.theme_manager.register_widget(center_controls_container, {'bg': 'primary'})
        center_controls_container.pack(side='left', expand=True, fill='none') # 중앙 정렬 및 확장 방지

        controls_frame = tk.Frame(center_controls_container)
        self.theme_manager.register_widget(controls_frame, {'bg': 'primary'})
        controls_frame.pack(side='top', anchor='center') # 컨트롤을 컨테이너 내 중앙에 배치
        
        self.run_btn = tk.Button(controls_frame, text="🚀 OCR 시작 (F5)", command=self.run_ocr_process, font=('Segoe UI', 11, 'bold'), relief='flat', cursor='hand2')
        self.theme_manager.register_widget(self.run_btn, {'bg': 'success', 'fg': 'white', 'activebackground':'dark', 'activeforeground':'white'})
        self.run_btn.pack(side='left', padx=(0, 5))
        
        self.stop_btn = tk.Button(controls_frame, text="⏹️ 중단", command=self.stop_processing_ui_initiated, font=('Segoe UI', 11, 'bold'), relief='flat', cursor='hand2')
        self.theme_manager.register_widget(self.stop_btn, {'bg': 'danger', 'fg': 'white', 'activebackground':'dark', 'activeforeground':'white'})
        self.stop_btn.pack(side='left', padx=(0, 15))
        
        theme_lbl = tk.Label(toolbar, text="", font=('Segoe UI', 9))
        self.theme_manager.register_widget(theme_lbl, {'bg': 'primary', 'fg': 'white'})
        theme_lbl.pack(side='right', padx=(0, 3)) # 테마 레이블 우측 정렬
        
        self.theme_combo = ttk.Combobox(toolbar, textvariable=self.theme_var, width=12, state="readonly", font=('Segoe UI', 8), style="TCombobox")
        self.theme_combo['values'] = [theme['name'] for theme in self.theme_manager.available_themes.values()]
        self.theme_combo.set(self.theme_manager.available_themes[self.theme_manager.current_theme_key]['name'])
        self.theme_combo.pack(side='right', padx=(0, 8)) # 테마 콤보박스 우측 정렬
        self.theme_combo.bind('<<ComboboxSelected>>', lambda e: self.theme_manager.change_theme(
            next(key for key, theme_val in self.theme_manager.available_themes.items() if theme_val['name'] == self.theme_var.get())
        ))

    def _create_left_panel_content(self, parent):
        scrollable_frame = tk.Frame(parent)
        self.theme_manager.register_widget(scrollable_frame, {'bg': 'surface'})
        scrollable_frame.pack(fill="both", expand=True, padx=0, pady=0) # left_panel에 이미 패딩이 있으므로 0으로 설정

        self._create_file_section(scrollable_frame)
        self._create_coordinates_section(scrollable_frame)
        self._create_timing_section(scrollable_frame)
        self._create_options_section(scrollable_frame)
        self._create_preset_section(scrollable_frame) # fill_parent=True 인자 유지

    def _create_right_panel_content(self, parent):
        self.log_text_widget = create_log_panel(self, parent)

    def _create_file_section(self, parent):
        create_file_panel(self, parent)

    def _create_coordinates_section(self, parent):
        create_coordinates_panel(self, parent)

    def _create_timing_section(self, parent):
        create_timing_panel(self, parent)

    def _create_options_section(self, parent):
        create_options_panel(self, parent)

    def _create_preset_section(self, parent):
        section = self._create_section_frame_styled(parent, "💾 프리셋 관리", fill_parent=True)
        common_font = ('Segoe UI', 9)
        btn_font = ('Segoe UI', 9)
        btn_width = 6
        btn_height = 1

        preset_load_frame = tk.Frame(section)
        self.theme_manager.register_widget(preset_load_frame, {'bg': 'white'})
        preset_load_frame.pack(fill='x', pady=(0, 8))
        preset_lbl = tk.Label(preset_load_frame, text="저장된 프리셋:", font=(common_font[0], common_font[1], 'bold'))
        self.theme_manager.register_widget(preset_lbl, {'bg': 'white', 'fg': 'on_surface'})
        preset_lbl.pack(anchor='w', pady=(0,2))

        preset_control_frame = tk.Frame(preset_load_frame)
        self.theme_manager.register_widget(preset_control_frame, {'bg': 'white'})
        preset_control_frame.pack(fill='x')

        self.preset_combo = ttk.Combobox(preset_control_frame, state="readonly", font=common_font, style="TCombobox")
        self.preset_combo.pack(side='left', fill='x', expand=True, padx=(0, 5))

        apply_preset_btn = tk.Button(preset_control_frame, text="적용", command=self.apply_selected_preset, font=btn_font, relief='flat', cursor='hand2', width=btn_width, height=btn_height, pady=0)
        self.theme_manager.register_widget(apply_preset_btn, {'bg': 'success', 'fg': 'white', 'activebackground':'dark'})
        apply_preset_btn.pack(side='right', padx=(0, 5))

        delete_preset_btn = tk.Button(preset_control_frame, text="삭제", command=self.delete_selected_preset, font=btn_font, relief='flat', cursor='hand2', width=btn_width, height=btn_height, pady=0)
        self.theme_manager.register_widget(delete_preset_btn, {'bg': 'danger', 'fg': 'white', 'activebackground':'dark'})
        delete_preset_btn.pack(side='right')

        preset_save_frame = tk.Frame(section)
        self.theme_manager.register_widget(preset_save_frame, {'bg': 'white'})
        preset_save_frame.pack(fill='x', pady=(15, 0))
        save_preset_lbl = tk.Label(preset_save_frame, text="새 프리셋 저장:", font=(common_font[0], common_font[1], 'bold'))
        self.theme_manager.register_widget(save_preset_lbl, {'bg': 'white', 'fg': 'on_surface'})
        save_preset_lbl.pack(anchor='w', pady=(0,2))

        save_control_frame = tk.Frame(preset_save_frame)
        self.theme_manager.register_widget(save_control_frame, {'bg': 'white'})
        save_control_frame.pack(fill='x')

        self.preset_name_entry = tk.Entry(save_control_frame, font=common_font, relief='solid', bd=1)
        self.theme_manager.register_widget(self.preset_name_entry, {'bg': 'white', 'fg': 'on_surface'})
        self.preset_name_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        self.preset_name_entry.insert(0, "새 프리셋 이름")

        save_preset_btn = tk.Button(save_control_frame, text="저장", command=self.save_current_as_preset, font=btn_font, relief='flat', cursor='hand2', width=btn_width, height=btn_height, pady=0)
        self.theme_manager.register_widget(save_preset_btn, {'bg': 'accent', 'fg': 'white', 'activebackground':'dark'})
        save_preset_btn.pack(side='right')

        self.update_preset_combo()

    def _create_center_excel_grid(self, parent):
        grid_section = self._create_section_frame_styled(parent, "📊 Excel 데이터 그리드", fill_parent=True)
        
        control_frame = tk.Frame(grid_section)
        self.theme_manager.register_widget(control_frame, {'bg': 'white'})
        control_frame.pack(fill='x', pady=(0,10))

        # 좌측 컨트롤
        left_controls = tk.Frame(control_frame)
        self.theme_manager.register_widget(left_controls, {'bg': 'white'})
        left_controls.pack(side='left', fill='x', expand=True, padx=(0,5))
        
        load_excel_btn = tk.Button(left_controls, text="📁 Excel 로드", command=self.load_excel_to_grid, font=('Segoe UI', 9), relief='flat', cursor='hand2')
        self.theme_manager.register_widget(load_excel_btn, {'bg': 'primary', 'fg': 'white', 'activebackground':'dark'})
        load_excel_btn.pack(side='left', padx=(0,5))

        add_row_btn = tk.Button(left_controls, text="➕ 행 추가", command=self.add_empty_row_ui, font=('Segoe UI', 9), relief='flat', cursor='hand2')
        self.theme_manager.register_widget(add_row_btn, {'bg': 'success', 'fg': 'white', 'activebackground':'dark'})
        add_row_btn.pack(side='left', padx=(0,5))

        paste_btn = tk.Button(left_controls, text="📋 붙여넣기", command=self.paste_from_clipboard_ui, font=('Segoe UI', 9), relief='flat', cursor='hand2')
        self.theme_manager.register_widget(paste_btn, {'bg': 'secondary', 'fg': 'white', 'activebackground':'dark'})
        paste_btn.pack(side='left', padx=(0,5))

        # 우측 컨트롤
        right_controls = tk.Frame(control_frame)
        self.theme_manager.register_widget(right_controls, {'bg': 'white'})
        right_controls.pack(side='right')

        delete_rows_btn = tk.Button(right_controls, text="🗑️ 선택 삭제", command=self.delete_selected_rows_ui, font=('Segoe UI', 9), relief='flat', cursor='hand2')
        self.theme_manager.register_widget(delete_rows_btn, {'bg': 'danger', 'fg': 'white', 'activebackground':'dark'})
        delete_rows_btn.pack(side='right', padx=(5,0))

        clear_all_btn = tk.Button(right_controls, text="🧹 전체 삭제", command=self.clear_all_data_ui, font=('Segoe UI', 9), relief='flat', cursor='hand2')
        self.theme_manager.register_widget(clear_all_btn, {'bg': 'warning', 'fg': 'on_surface', 'activebackground':'dark'})
        clear_all_btn.pack(side='right', padx=(5,0))

        tree_frame = tk.Frame(grid_section)
        self.theme_manager.register_widget(tree_frame, {'bg': 'white'})
        tree_frame.pack(fill='both', expand=True)

        columns = ('종목코드', '종목명', '날짜', '금리', '상태')
        self.grid_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', style="Treeview")
        
        for col_name in columns: self.grid_tree.heading(col_name, text=col_name)
        col_widths = {'종목코드': 95, '종목명': 180, '날짜': 120, '금리': 95, '상태': 100}
        for col_name, width in col_widths.items():
            self.grid_tree.column(col_name, width=width, anchor='center', minwidth=width-20, stretch=tk.YES)

        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.grid_tree.yview, style="TScrollbar")
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.grid_tree.xview, style="TScrollbar")
        self.grid_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        self.grid_tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.grid_tree.bind('<Double-1>', self.on_cell_double_click_ui)
        self.grid_tree.bind('<Button-3>', self.show_context_menu_ui)
        self.grid_tree.bind('<Delete>', lambda e: self.delete_selected_rows_ui())
        self.grid_tree.bind('<Control-c>', lambda e: self.copy_selected_rows_ui())
        self.grid_tree.bind('<Control-v>', lambda e: self.paste_from_clipboard_ui())

        # 상태 레이블
        status_frame = tk.Frame(grid_section)
        self.theme_manager.register_widget(status_frame, {'bg': 'white'})
        status_frame.pack(fill='x', pady=(10,0))
        self.grid_status_label = tk.Label(status_frame, text="총 0행 | 완료: 0 | 대기: 0 | 오류: 0", font=('Segoe UI', 9))
        self.theme_manager.register_widget(self.grid_status_label, {'bg': 'white', 'fg': 'on_surface'})
        self.grid_status_label.pack(side='left')
        self.grid_progress_label = tk.Label(status_frame, text="진행률: 0.0%", font=('Segoe UI', 9, 'bold'))
        self.theme_manager.register_widget(self.grid_progress_label, {'bg': 'white', 'fg': 'primary'})
        self.grid_progress_label.pack(side='right')
        
        self.refresh_grid_tags()

    def refresh_grid_tags(self):
        if not self.grid_tree: return
        self.grid_tree.tag_configure('processing', background=self.theme_manager.get_color('warning', '#FFF3CD'), foreground=self.theme_manager.get_color('dark', '#856404'))
        self.grid_tree.tag_configure('completed', background=self.theme_manager.get_color('success', '#D4EDDA'), foreground=self.theme_manager.get_color('dark', '#155724'))
        self.grid_tree.tag_configure('error', background=self.theme_manager.get_color('danger', '#F8D7DA'), foreground=self.theme_manager.get_color('white', '#721C24'))

    def get_current_ui_settings(self):
        return {
            'click_point': (self.click_x.get(), self.click_y.get()),
            'all_area': (self.allarea_x1.get(), self.allarea_y1.get(), self.allarea_x2.get(), self.allarea_y2.get()),
            'date_area': (self.datearea_x1.get(), self.datearea_y1.get(), self.datearea_x2.get(), self.datearea_y2.get()),
            'rate_area': (self.ratearea_x1.get(), self.ratearea_y1.get(), self.ratearea_x2.get(), self.ratearea_y2.get()),
            'delays': {
                'paste': self.paste_delay.get(),
                'loading': self.loading_delay.get()
            },
            'save_detail_images': self.save_detail_images.get(),
            'skip_kbp_code': self.skip_kbp_var.get(),
            'upscaling': {
                'enabled': self.enable_upscaling.get(),
                'factor': self.upscaling_factor.get(),
                'method': self.upscaling_method.get()
            }
        }

    def apply_settings_to_ui(self, settings_dict):
        if not settings_dict: return
        cp = settings_dict.get('click_point', (0,0))
        self.click_x.set(cp[0]); self.click_y.set(cp[1])
        
        areas = {'all_area': (self.allarea_x1, self.allarea_y1, self.allarea_x2, self.allarea_y2),
                 'date_area': (self.datearea_x1, self.datearea_y1, self.datearea_x2, self.datearea_y2),
                 'rate_area': (self.ratearea_x1, self.ratearea_y1, self.ratearea_x2, self.ratearea_y2)}
        for key, tk_vars in areas.items():
            coords = settings_dict.get(key)
            if coords and len(coords) == 4:
                tk_vars[0].set(coords[0]); tk_vars[1].set(coords[1])
                tk_vars[2].set(coords[2]); tk_vars[3].set(coords[3])

        delays = settings_dict.get('delays', {})
        self.paste_delay.set(delays.get('paste', 0.5))
        self.loading_delay.set(delays.get('loading', 2.5))
        self.save_detail_images.set(settings_dict.get('save_detail_images', True))
        self.skip_kbp_var.set(settings_dict.get('skip_kbp_code', True))

        # 업스케일링 설정 적용
        upscaling_settings = settings_dict.get('upscaling', {})
        self.enable_upscaling.set(upscaling_settings.get('enabled', True))
        self.upscaling_factor.set(upscaling_settings.get('factor', 2.0))
        self.upscaling_method.set(upscaling_settings.get('method', 'LANCZOS'))

        if 'advanced' in settings_dict:
            self.settings_manager.data['advanced'].update(settings_dict['advanced'])

    def save_advanced_ui_to_settings(self):
        try:
            self.settings_manager.set_advanced('skip_kbp_code', self.skip_kbp_var.get())
            
            # 업스케일링 설정 저장
            self.settings_manager.set_advanced('upscaling_enabled', self.enable_upscaling.get())
            self.settings_manager.set_advanced('upscaling_factor', self.upscaling_factor.get())
            self.settings_manager.set_advanced('upscaling_method', self.upscaling_method.get())
            
            self.settings_manager.save_settings()
            self.logger.info("고급 설정이 저장되었습니다.")
        except Exception as e:
            self.logger.error(f"고급 설정 저장 실패: {e}")

    def reset_advanced_settings_and_ui(self):
        if messagebox.askyesno("확인", "모든 고급 설정을 기본값으로 되돌리시겠습니까?"):
            self.settings_manager.reset_advanced_settings()
            self.skip_kbp_var.set(self.settings_manager.get_advanced('skip_kbp_code', True))
            messagebox.showinfo("완료", "고급 설정이 초기화되었습니다.")
            self.logger.info("고급 설정이 기본값으로 초기화되었습니다.")

    def browse_input_excel(self):
        file_path = filedialog.askopenfilename(title="엑셀 파일 선택", filetypes=[("Excel files", "*.xlsx;*.xls")])
        if file_path:
            self.input_excel_path.set(file_path)
            # Excel 파일의 디렉토리를 항상 출력 폴더로 설정
            base_path = os.path.dirname(file_path)
            # 경로 정리 및 UNC 정규화 적용
            cleaned_base_path = self.ocr_workflow_manager._clean_folder_path(base_path)
            self.output_folder_path.set(cleaned_base_path)
            self.logger.info(f"Excel 파일 선택됨: {file_path}")
            self.logger.info(f"출력 폴더 자동 설정됨: {cleaned_base_path}")

    def browse_output_folder(self):
        try:
            # 현재 설정된 경로를 초기 디렉토리로 사용
            current_path = self.output_folder_path.get().strip()
            initial_dir = None
            
            if current_path:
                # UNC 경로 정규화
                if current_path.startswith('\\') and not current_path.startswith('\\\\'):
                    current_path = '\\' + current_path
                
                # 경로 존재 여부 확인
                if os.path.exists(current_path):
                    initial_dir = current_path
                else:
                    # UNC 경로인 경우 상위 디렉토리 확인
                    if current_path.startswith('\\\\'):
                        path_parts = current_path.split('\\')
                        if len(path_parts) >= 4:
                            # 서버\공유 레벨까지 확인
                            server_share = '\\\\' + path_parts[2] + '\\' + path_parts[3]
                            if os.path.exists(server_share):
                                initial_dir = server_share
            
            # 폴더 선택 대화상자 열기
            folder_path = filedialog.askdirectory(
                title="출력 폴더 선택", 
                initialdir=initial_dir,
                mustexist=False  # 네트워크 폴더의 경우 False로 설정
            )
            
            if folder_path: 
                # 경로 정리 및 UNC 정규화
                cleaned_path = self.ocr_workflow_manager._clean_folder_path(folder_path)
                self.output_folder_path.set(cleaned_path)
                self.logger.info(f"출력 폴더 선택됨: {cleaned_path}")
                
                # 네트워크 경로인 경우 사용자에게 안내
                if cleaned_path.startswith('\\\\'):
                    messagebox.showinfo("네트워크 폴더 선택", 
                                      f"네트워크 폴더가 선택되었습니다.\n\n"
                                      f"경로: {cleaned_path}\n\n"
                                      f"• 네트워크 연결 상태를 확인하세요\n"
                                      f"• 쓰기 권한이 있는지 확인하세요")
                
        except Exception as e:
            self.logger.error(f"폴더 선택 중 오류: {e}")
            messagebox.showerror("오류", f"폴더 선택 중 오류가 발생했습니다.\n\n{e}")

    def open_output_folder(self):
        output_path = self.output_folder_path.get().strip()
        if not output_path:
            messagebox.showwarning("경고", "출력 폴더가 설정되지 않았습니다.")
            return
        
        try:
            system = platform.system()
            cleaned_path = str(output_path).strip()

            self.logger.info(f"출력 폴더 열기 시도 - 시스템: {system}, 원본 경로: {cleaned_path}")

            if system == "Windows":
                # UNC 경로 정규화 (단일 백슬래시를 이중 백슬래시로 변환)
                if cleaned_path.startswith('\\') and not cleaned_path.startswith('\\\\'):
                    cleaned_path = '\\' + cleaned_path  # \경로 -> \\경로
                    self.logger.info(f"UNC 경로 정규화: {cleaned_path}")
                
                # 슬래시를 백슬래시로 변환
                cleaned_path_windows = cleaned_path.replace('/', '\\')
                self.logger.info(f"Windows 형식 경로 변환 후: {cleaned_path_windows}")

                # UNC 경로 여부 확인
                is_unc = cleaned_path_windows.startswith('\\\\')
                
                # 폴더 존재 여부 확인 및 생성
                try:
                    if not os.path.exists(cleaned_path_windows):
                        if is_unc:
                            self.logger.info("UNC 경로입니다. 네트워크 연결을 확인합니다.")
                            # UNC 경로의 경우 네트워크 접근 시도
                            try:
                                # 상위 디렉토리까지만 확인 (서버 접근 가능 여부)
                                path_parts = cleaned_path_windows.split('\\')
                                if len(path_parts) >= 4:  # \\server\share\...
                                    server_share = '\\\\' + path_parts[2] + '\\' + path_parts[3]
                                    if os.path.exists(server_share):
                                        # 하위 디렉토리 생성 시도
                                        os.makedirs(cleaned_path_windows, exist_ok=True)
                                        self.logger.info(f"UNC 네트워크 폴더 생성됨: {cleaned_path_windows}")
                                    else:
                                        self.logger.warning(f"네트워크 서버에 접근할 수 없습니다: {server_share}")
                                        messagebox.showwarning("네트워크 오류", 
                                                             f"네트워크 서버에 접근할 수 없습니다.\n\n"
                                                             f"서버: {server_share}\n"
                                                             f"• 네트워크 연결을 확인하세요\n"
                                                             f"• 접근 권한을 확인하세요\n"
                                                             f"• VPN 연결이 필요할 수 있습니다")
                                        return
                            except Exception as e:
                                self.logger.error(f"UNC 경로 접근 오류: {e}")
                                if messagebox.askyesno("네트워크 폴더 오류", 
                                                     f"네트워크 폴더에 접근할 수 없습니다.\n\n"
                                                     f"오류: {e}\n\n"
                                                     f"그래도 폴더 열기를 시도하시겠습니까?"):
                                    pass  # 계속 진행
                                else:
                                    return
                        else:
                            # 로컬 경로인 경우 폴더 생성 확인
                            if messagebox.askyesno("폴더 생성", 
                                                 f"폴더가 존재하지 않습니다.\n생성하시겠습니까?\n\n경로: {cleaned_path_windows}"):
                                os.makedirs(cleaned_path_windows, exist_ok=True)
                                self.logger.info(f"로컬 폴더 생성됨: {cleaned_path_windows}")
                            else:
                                return
                    else:
                        self.logger.info(f"폴더가 이미 존재합니다: {cleaned_path_windows}")
                
                except Exception as path_error:
                    self.logger.warning(f"경로 접근 확인 중 오류: {path_error}")
                    # 경로 확인 실패해도 열기 시도는 계속

                # Windows 탐색기로 폴더 열기
                try:
                    os.startfile(cleaned_path_windows)
                    self.logger.info("출력 폴더 열기 (Windows Explorer) 완료")
                    
                    # 성공 메시지 제거 - 사용자가 요청함
                    # if is_unc:
                    #     messagebox.showinfo("폴더 열기 완료", 
                    #                       f"네트워크 폴더가 Windows 탐색기에서 열렸습니다.\n\n경로: {cleaned_path_windows}")
                
                except Exception as startfile_error:
                    self.logger.error(f"os.startfile 실패: {startfile_error}")
                    # 대안 방법 시도: explorer.exe 직접 호출
                    try:
                        subprocess.run(['explorer', cleaned_path_windows], check=True, timeout=10)
                        self.logger.info("출력 폴더 열기 (explorer.exe) 완료")
                    except Exception as explorer_error:
                        self.logger.error(f"explorer.exe 호출 실패: {explorer_error}")
                        raise explorer_error

            elif system == "Darwin": # macOS
                # macOS는 open 명령어로 파일/폴더/URL을 엽니다.
                if cleaned_path.startswith(('\\', '//')):
                     # \\server\share -> smb://server/share
                     smb_path = 'smb:' + cleaned_path.replace('\\', '/')
                     self.logger.info(f"macOS SMB 경로 변환 후: {smb_path}")
                     subprocess.run(['open', smb_path], check=True, timeout=10)
                     self.logger.info(f"출력 폴더 열기 시도 (macOS smb) 완료")
                else:
                    # 일반 로컬 경로는 그대로 open
                    self.logger.info(f"macOS 로컬 경로: {cleaned_path}")
                    subprocess.run(['open', cleaned_path], check=True, timeout=10)
                    self.logger.info(f"출력 폴더 열기 시도 (macOS) 완료")

            else: # Linux 등 Unix-like 시스템
                # Linux는 xdg-open 명령어로 파일/폴더/URL을 엽니다.
                if cleaned_path.startswith(('\\', '//')):
                     # \\server\share -> smb://server/share
                     smb_path = 'smb:' + cleaned_path.replace('\\', '/')
                     self.logger.info(f"Linux SMB 경로 변환 후: {smb_path}")
                     subprocess.run(['xdg-open', smb_path], check=True, timeout=10)
                     self.logger.info(f"출력 폴더 열기 시도 (Linux smb) 완료")
                else:
                    # 일반 로컬 경로는 그대로 xdg-open
                    self.logger.info(f"Linux 로컬 경로: {cleaned_path}")
                    subprocess.run(['xdg-open', cleaned_path], check=True, timeout=10)
                    self.logger.info(f"출력 폴더 열기 시도 (Linux) 완료")
            
        except FileNotFoundError:
             messagebox.showerror("오류", f"폴더 또는 파일을 찾을 수 없습니다.\n경로를 확인해주세요.\n\n경로: {output_path}")
             self.logger.error(f"폴더 열기 실패: FileNotFoundError for {output_path}")
        except subprocess.CalledProcessError as e:
             messagebox.showerror("오류", f"폴더 열기 명령어 실행 실패: {e}\n\n경로: {output_path}")
             self.logger.error(f"폴더 열기 명령어 실행 실패: {e} for {output_path}")
        except subprocess.TimeoutExpired:
            messagebox.showerror("오류", "폴더 열기 시간 초과\n네트워크 연결을 확인하세요.")
            self.logger.error("폴더 열기 시간 초과")
        except Exception as e:
            # 기타 예외 처리
            messagebox.showerror("오류", f"알 수 없는 오류 발생: {e}\n\n경로: {output_path}\n\n네트워크 연결 및 접근 권한을 확인하세요.")
            self.logger.error(f"알 수 없는 오류 발생: {e} for {output_path}")

    def relocate_clickpoint(self):
        overlay = PointCaptureOverlay(self, color_key="danger", theme_manager=self.theme_manager)
        self.wait_window(overlay)
        if overlay.click_x is not None:
            self.click_x.set(overlay.click_x); self.click_y.set(overlay.click_y)

    def _relocate_area_generic(self, x1_var, y1_var, x2_var, y2_var, color_key):
        overlay = DragCaptureOverlay(self, color_key=color_key, theme_manager=self.theme_manager)
        self.wait_window(overlay)
        if overlay.x1 is not None:
            x1_var.set(overlay.x1); y1_var.set(overlay.y1)
            x2_var.set(overlay.x2); y2_var.set(overlay.y2)

    def relocate_allarea(self): self._relocate_area_generic(self.allarea_x1, self.allarea_y1, self.allarea_x2, self.allarea_y2, "primary")
    def relocate_datearea(self): self._relocate_area_generic(self.datearea_x1, self.datearea_y1, self.datearea_x2, self.datearea_y2, "success")
    def relocate_ratearea(self): self._relocate_area_generic(self.ratearea_x1, self.ratearea_y1, self.ratearea_x2, self.ratearea_y2, "warning")

    def update_preset_combo(self):
        if hasattr(self, 'preset_combo') and self.preset_combo:
            preset_names = self.settings_manager.get_preset_names()
            self.preset_combo['values'] = preset_names
            if preset_names: self.preset_combo.current(0)
            else: self.preset_combo.set('')

    def apply_selected_preset(self):
        if not hasattr(self, 'preset_combo'): return
        selected = self.preset_combo.get()
        if selected:
            preset_settings = self.settings_manager.apply_preset(selected)
            if preset_settings:
                self.apply_settings_to_ui(preset_settings)
                messagebox.showinfo("정보", f"프리셋 '{selected}'이 적용되었습니다.")
                self.logger.info(f"프리셋 '{selected}' 적용됨.")

    def save_current_as_preset(self):
        name_entry_widget = getattr(self, 'preset_name_entry', None)
        name = ""
        if name_entry_widget:
            name = name_entry_widget.get().strip()
            if name == "새 프리셋 이름" or not name:
                messagebox.showwarning("경고", "유효한 프리셋 이름을 입력해주세요.")
                return
        else:
            name = simpledialog.askstring("프리셋 저장", "프리셋 이름을 입력하세요:", parent=self)
            if not name: return

        current_settings = self.get_current_ui_settings()
        self.settings_manager.save_preset(name, current_settings)
        self.update_preset_combo()
        if name_entry_widget:
            name_entry_widget.delete(0, tk.END)
            name_entry_widget.insert(0, "새 프리셋 이름")
        messagebox.showinfo("완료", f"'{name}' 프리셋이 저장되었습니다.")
        self.logger.info(f"프리셋 '{name}' 저장됨.")

    def delete_selected_preset(self):
        if not hasattr(self, 'preset_combo'): return
        selected = self.preset_combo.get()
        if not selected:
            messagebox.showwarning("경고", "삭제할 프리셋을 선택해주세요.")
            return
        if messagebox.askyesno("확인", f"프리셋 '{selected}'을(를) 삭제하시겠습니까?"):
            self.settings_manager.delete_preset(selected)
            self.update_preset_combo()
            messagebox.showinfo("완료", f"프리셋 '{selected}'이 삭제되었습니다.")
            self.logger.info(f"프리셋 '{selected}' 삭제됨.")

    def show_area_preview(self):
        areas_info = {
            "click_point": (self.click_x.get(), self.click_y.get()),
            "all_area": (self.allarea_x1.get(), self.allarea_y1.get(), self.allarea_x2.get(), self.allarea_y2.get()),
            "date_area": (self.datearea_x1.get(), self.datearea_y1.get(), self.datearea_x2.get(), self.datearea_y2.get()),
            "rate_area": (self.ratearea_x1.get(), self.ratearea_y1.get(), self.ratearea_x2.get(), self.ratearea_y2.get())
        }
        AreaVisualizationOverlay(self, areas_info, self.theme_manager, auto_close=True)

    def stop_processing_ui_initiated(self):
        if self.work_controller.is_running:
            message = self.work_controller.stop_work()
            self._set_runtime_state(RuntimeState.STOPPING)
            self.message_queue.put(("log", message, "INFO"))

    def _on_work_complete_ui_only(self, summary_message):
        self.logger.info("[_on_work_complete_ui_only] 함수 호출됨 (Main Thread)")
        self.work_controller.reset()
        self.data_manager.current_processing_index = -1
        self._set_runtime_state(self._ready_or_error_state())
        self.refresh_grid_ui()
        # 메시지 박스 표시는 finalize_export_and_complete에서 수행
        self.quick_save_settings() # 완료 시 설정 저장

    def _handle_grid_update(self, data):
        try:
            update_type, grid_idx, *payload = data
            if 0 <= grid_idx < len(self.data_manager.excel_data):
                if update_type == "processing":
                    self.data_manager.excel_data[grid_idx]['상태'] = '처리 중...'
                    if self.grid_tree:
                        children = self.grid_tree.get_children()
                        if grid_idx < len(children):
                             self.grid_tree.see(children[grid_idx])
                elif update_type == "complete" and len(payload) >= 3:
                    date_res, rate_res, status_res = payload[0], payload[1], payload[2]
                    if date_res is not None: self.data_manager.excel_data[grid_idx]['날짜'] = date_res
                    if rate_res is not None: self.data_manager.excel_data[grid_idx]['금리'] = rate_res
                    self.data_manager.excel_data[grid_idx]['상태'] = status_res
                elif update_type == "error" and len(payload) >= 1:
                    self.data_manager.excel_data[grid_idx]['상태'] = payload[0]
                
                # 디버그 로그: 그리드 데이터 업데이트 후 상태 확인
                if 0 <= grid_idx < len(self.data_manager.excel_data):
                    self.logger.debug(f"[_handle_grid_update] {grid_idx}번 항목 업데이트 후: {self.data_manager.excel_data[grid_idx]}")

                self.refresh_grid_ui()
        except Exception as e:
            self.logger.error(f"그리드 업데이트 중 오류: {e}, 데이터: {data}")

    def show_shortcuts(self):
        shortcuts = """🎹 키보드 단축키:
• F5: OCR 처리 실행/중단
• Escape: 처리 중단
• F1: 단축키 도움말 (이 창)
• Ctrl+S: 모든 설정 저장
• Ctrl+L: 마지막 설정 불러오기
• Ctrl+O: Excel 파일 로드 (그리드)"""
        messagebox.showinfo("키보드 단축키", shortcuts, parent=self)

    def show_about(self):
        build_summary = format_build_metadata(load_build_metadata())
        about_text = f"""📋 Check Capture OCR - V6
OCR 자동화 애플리케이션 (EasyOCR 기반)

{build_summary}"""
        messagebox.showinfo("프로그램 정보", about_text, parent=self)

    def run_ocr_process(self):
        if self.work_controller.is_running:
            self.stop_processing_ui_initiated()
            return
        if not self._validate_inputs_for_ocr(): return

        self.work_controller.start_work()
        self._set_runtime_state(RuntimeState.RUNNING)
        current_ui_settings = self.get_current_ui_settings()
        output_dir = self.output_folder_path.get().strip()
        save_details = self.save_detail_images.get()

        self.worker_thread = start_daemon_worker(
            self.ocr_workflow_manager.execute_ocr_workflow_threaded,
            current_ui_settings,
            output_dir,
            save_details,
            name="checkocr2-ocr-workflow",
        )

    def _validate_inputs_for_ocr(self):
        output_dir = self.output_folder_path.get().strip()
        if not self.data_manager.excel_data:
             messagebox.showwarning("경고", "처리할 데이터가 없습니다. Excel 파일을 로드하거나 데이터를 추가하세요.", parent=self)
             return False
        if not output_dir or not os.path.isdir(output_dir):
            messagebox.showwarning("경고", "유효한 Output 폴더를 지정하세요.", parent=self)
            return False
        if self.ocr_initializing:
            messagebox.showwarning("OCR 준비 중", "OCR 엔진을 초기화하고 있습니다. 잠시 후 다시 시작하세요.", parent=self)
            return False
        if not self.ocr_workflow_manager.ocr_reader:
            messagebox.showerror("오류", "OCR 엔진이 초기화되지 않았습니다. 프로그램을 재시작하거나 설정을 확인하세요.", parent=self)
            return False
        return True

    def load_excel_to_grid(self):
        file_path = self.input_excel_path.get()
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("오류", "Excel 파일을 먼저 선택해주세요.", parent=self)
            return
        
        loaded_rows = self.data_manager.load_excel_to_grid_data(file_path)
        if loaded_rows > 0:
            # Excel 파일 로드 성공 시 출력 폴더도 자동 설정
            base_path = os.path.dirname(file_path)
            cleaned_base_path = self.ocr_workflow_manager._clean_folder_path(base_path)
            self.output_folder_path.set(cleaned_base_path)
            self.logger.info(f"Excel 파일 로드 완료: {loaded_rows}행")
            self.logger.info(f"출력 폴더 자동 설정됨: {cleaned_base_path}")
            self.refresh_grid_ui()

    def add_empty_row_ui(self):
        self.data_manager.add_empty_row_data()
        self.refresh_grid_ui()
        if self.grid_tree:
            children = self.grid_tree.get_children()
            if children:
                self.grid_tree.see(children[-1])

    def paste_from_clipboard_ui(self):
        try:
            clipboard_content = self.clipboard_get()
            added_count = self.data_manager.paste_from_clipboard_data(clipboard_content)
            if added_count > 0:
                self.refresh_grid_ui()
                messagebox.showinfo("성공", f"{added_count}행을 추가했습니다.", parent=self)
                if self.grid_tree:
                    children = self.grid_tree.get_children()
                    if children:
                        self.grid_tree.see(children[-1])
            else:
                messagebox.showwarning("경고", "붙여넣을 유효한 데이터가 없습니다 (탭으로 구분된 데이터 필요).", parent=self)
        except tk.TclError:
            messagebox.showerror("오류", "클립보드에 텍스트 데이터가 없습니다.", parent=self)

    def delete_selected_rows_ui(self):
        if not self.grid_tree: return
        selected_items = self.grid_tree.selection()
        if not selected_items:
            messagebox.showwarning("경고", "삭제할 행을 선택해주세요.", parent=self)
            return
        if not messagebox.askyesno("확인", f"{len(selected_items)}개의 행을 삭제하시겠습니까?", parent=self):
            return
        
        indices_to_delete = [self.grid_tree.index(item) for item in selected_items]
        self.data_manager.delete_rows_data(indices_to_delete)
        self.refresh_grid_ui()

    def clear_all_data_ui(self):
        if self.data_manager.excel_data and \
           not messagebox.askyesno("확인", "모든 데이터를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.", parent=self):
            return
        self.data_manager.clear_all_data_internal()
        self.refresh_grid_ui()

    def copy_selected_rows_ui(self):
        if not self.grid_tree: return
        selected_items = self.grid_tree.selection()
        if not selected_items: return
        
        copied_data_str_list = []
        for item in selected_items:
            index = self.grid_tree.index(item)
            row_str = self.data_manager.get_row_for_copy(index)
            if row_str:
                copied_data_str_list.append(row_str)
        
        if copied_data_str_list:
            final_str = "\n".join(copied_data_str_list)
            self.clipboard_clear()
            self.clipboard_append(final_str)
            self.logger.info(f"{len(copied_data_str_list)}개 행이 클립보드에 복사되었습니다.")

    def copy_selected_rates_ui(self):
        if not self.grid_tree: return
        selected_items = self.grid_tree.selection()
        if not selected_items:
            messagebox.showwarning("경고", "복사할 행을 선택해주세요.", parent=self)
            return

        copied_rates = []
        for item in selected_items:
            index = self.grid_tree.index(item)
            if 0 <= index < len(self.data_manager.excel_data):
                rate_value = self.data_manager.excel_data[index].get('금리', '')
                copied_rates.append(str(rate_value)) # 문자열로 변환하여 추가

        if copied_rates:
            final_str = "\n".join(copied_rates) # 각 금리 값을 줄바꿈으로 연결
            self.clipboard_clear()
            self.clipboard_append(final_str)
            self.logger.info(f"선택된 {len(copied_rates)}개 행의 금리가 클립보드에 복사되었습니다.")
        else:
             self.logger.info("선택된 행에 금리 데이터가 없습니다.")

    def refresh_grid_ui(self):
        if not self.grid_tree: return
        for item in self.grid_tree.get_children(): self.grid_tree.delete(item)
        
        for i, row in enumerate(self.data_manager.excel_data):
            tags = []
            # 상태가 '완료'인 항목에 'completed' 태그 적용 (녹색) - 최우선 순위
            if row['상태'] == '완료':
                tags.append('completed')
            # 상태가 오류/실패/없음/건너뜀 인 경우 'error' 태그 적용
            elif any(err_keyword in row['상태'] for err_keyword in ['오류', '실패', '없음', '건너']):
                tags.append('error')
            # 그 외의 경우 중 현재 처리 중인 항목에 'processing' 태그 적용 (주황색)
            elif i == self.data_manager.current_processing_index and self.work_controller.is_running:
                tags.append('processing')

            self.grid_tree.insert('', 'end', values=(row['종목코드'], row['종목명'], row['날짜'], row['금리'], row['상태']), tags=tags)
        self.update_grid_status_labels()

    def update_grid_status_labels(self):
        if not hasattr(self, 'grid_status_label'): return
        total = len(self.data_manager.excel_data)
        completed = sum(1 for row in self.data_manager.excel_data if row['상태'] == '완료')
        waiting = sum(1 for row in self.data_manager.excel_data if row['상태'] == '대기 중')
        errors = sum(1 for row in self.data_manager.excel_data if any(err_keyword in row['상태'] for err_keyword in ['오류', '실패', '없음', '건너']))
        
        self.grid_status_label.config(text=f"총 {total}행 | 완료: {completed} | 대기: {waiting} | 오류: {errors}")
        progress = (completed / total * 100) if total > 0 else 0
        if hasattr(self, 'grid_progress_label'): self.grid_progress_label.config(text=f"진행률: {progress:.1f}%")

    def on_cell_double_click_ui(self, event):
        if not self.grid_tree: return

        # 기존 편집 위젯이 있다면 제거
        if hasattr(self, '_editing_cell_entry') and self._editing_cell_entry.winfo_exists():
            self._editing_cell_entry.destroy()

        item_id = self.grid_tree.identify_row(event.y)
        column_id = self.grid_tree.identify_column(event.x)

        if not item_id or not column_id: return

        col_index = int(column_id.replace('#', '')) - 1
        if col_index < 0: return # 헤더 클릭 방지

        col_name = self.grid_tree['columns'][col_index]
        row_index = self.grid_tree.index(item_id)

        if not (0 <= row_index < len(self.data_manager.excel_data)): return
        
        # 셀의 경계 가져오기
        x, y, width, height = self.grid_tree.bbox(item_id, column_id)

        # 편집용 Entry 위젯 생성
        current_value = self.data_manager.excel_data[row_index].get(col_name, "")
        self._editing_cell_entry = tk.Entry(self.grid_tree, font=('Segoe UI', 9))
        self.theme_manager.register_widget(self._editing_cell_entry, {'bg': 'white', 'fg': 'on_surface', 'insertbackground': 'on_surface', 'relief': 'solid', 'bd':1})
        self.theme_manager.apply_theme_to_all_widgets() # 새로 생성된 위젯에 테마 적용

        self._editing_cell_entry.place(x=x, y=y, width=width, height=height)
        self._editing_cell_entry.insert(0, current_value)
        self._editing_cell_entry.focus_set()
        self._editing_cell_entry.select_range(0, tk.END)

        # 이벤트 바인딩
        self._editing_cell_entry.bind("<Return>", lambda e, ri=row_index, cn=col_name: self._save_cell_edit(ri, cn))
        self._editing_cell_entry.bind("<KP_Enter>", lambda e, ri=row_index, cn=col_name: self._save_cell_edit(ri, cn)) # 숫자패드 Enter
        self._editing_cell_entry.bind("<Escape>", lambda e: self._cancel_cell_edit())
        self._editing_cell_entry.bind("<FocusOut>", lambda e, ri=row_index, cn=col_name: self._save_cell_edit_on_focus_out(ri, cn))

        # 현재 편집 중인 셀 정보 저장 (FocusOut에서 사용)
        self._current_edit_info = {'row_index': row_index, 'col_name': col_name}


    def _save_cell_edit_on_focus_out(self, row_index, col_name):
        # FocusOut 이벤트가 Escape로 인한 것인지, 아니면 실제로 포커스를 잃은 것인지 확인
        # Escape를 누르면 _editing_cell_entry가 먼저 파괴될 수 있음
        if hasattr(self, '_editing_cell_entry') and self._editing_cell_entry.winfo_exists():
            # 위젯이 아직 존재하면, 정상적인 포커스 아웃으로 간주하고 저장
             self._save_cell_edit(row_index, col_name)
        # 이미 위젯이 파괴되었다면 (아마도 Escape 때문), 아무것도 안 함

    def _save_cell_edit(self, row_index, col_name):
        if hasattr(self, '_editing_cell_entry') and self._editing_cell_entry.winfo_exists():
            new_value = self._editing_cell_entry.get()
            self._editing_cell_entry.destroy()
            del self._editing_cell_entry # 참조 제거

            if self.data_manager.update_grid_cell_data(row_index, col_name, new_value):
                self.refresh_grid_ui()
                # 현재 편집 정보 초기화
                if hasattr(self, '_current_edit_info'):
                    del self._current_edit_info
        return "break" # 다른 바인딩으로 이벤트 전파 중지

    def _cancel_cell_edit(self):
        if hasattr(self, '_editing_cell_entry') and self._editing_cell_entry.winfo_exists():
            self._editing_cell_entry.destroy()
            del self._editing_cell_entry
        # 현재 편집 정보 초기화
        if hasattr(self, '_current_edit_info'):
            del self._current_edit_info
        return "break" # 다른 바인딩으로 이벤트 전파 중지

    def show_context_menu_ui(self, event):
        if not self.grid_tree: return
        context_menu = tk.Menu(self, tearoff=0)
        self.theme_manager.register_widget(context_menu, {'bg': 'surface', 'fg': 'on_surface', 
                                                          'activebackground': 'primary', 'activeforeground': 'white'})

        context_menu.add_command(label="➕ 행 추가", command=self.add_empty_row_ui)
        context_menu.add_command(label="🗑️ 선택 행 삭제", command=self.delete_selected_rows_ui)
        context_menu.add_separator()
        context_menu.add_command(label="📋 선택 행 복사 (Ctrl+C)", command=self.copy_selected_rows_ui)
        # 새로운 금리 복사 메뉴 항목 추가
        context_menu.add_command(label="📈 선택 행 금리 복사", command=self.copy_selected_rates_ui)
        context_menu.add_command(label="📝 클립보드에서 붙여넣기 (Ctrl+V)", command=self.paste_from_clipboard_ui)
        context_menu.add_separator()
        context_menu.add_command(label="🧹 전체 데이터 삭제", command=self.clear_all_data_ui)
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
            
    def quit_app(self):
        # Check if work is running
        if self.work_controller.is_running:
            # If running, stop the work immediately without asking
            self.logger.info("작업 진행 중, 종료 요청. 중단 처리 시도.") # 로그 메시지 수정
            self.work_controller.stop_work()
            # Attempt to join the worker thread for a short timeout
            # This might prevent crashes but doesn't guarantee clean exit if thread is stuck
            if self.worker_thread and self.worker_thread.is_alive:
                try:
                    self.worker_thread.join(timeout=2) # Wait up to 2 seconds
                    if self.worker_thread.is_alive:
                         self.logger.warning("작업 스레드가 종료 시간 내에 응답하지 않았습니다.")
                except Exception as e:
                     self.logger.error(f"작업 스레드 종료 중 오류 발생: {e}")
            self.destroy() # Close the main window
        else:
            # If not running, just destroy the window
            self.destroy()

    def load_last_settings(self):
        try:
            settings = self.settings_manager.get_current_settings()
            if settings:
                self.apply_settings_to_ui(settings)
                self.input_excel_path.set(settings.get('input_excel_path', ''))
                self.output_folder_path.set(settings.get('output_folder_path', ''))
                self.logger.info("마지막 설정이 성공적으로 불러와졌습니다.")
            else:
                self.logger.info("저장된 현재 설정이 없습니다. 기본값을 사용합니다.")
                self.settings_manager.data['advanced'] = self.settings_manager._get_default_advanced_settings()
            self.update_preset_combo()
            self.theme_manager.change_theme(self.settings_manager.get_advanced('ui_theme', 'modern_blue'))
        except Exception as e:
            self.logger.error(f"설정 불러오기 실패: {e}")

    def quick_save_settings(self):
        """현재 UI 설정을 빠르게 저장"""
        try:
            current_settings = self.get_current_ui_settings()
            current_settings['input_excel_path'] = self.input_excel_path.get()
            current_settings['output_folder_path'] = self.output_folder_path.get()
            
            self.settings_manager.save_current_settings(current_settings)
            self.save_advanced_ui_to_settings()  # 고급 설정도 함께 저장
            
            self.logger.info("현재 설정이 저장되었습니다.")
        except Exception as e:
            self.logger.error(f"설정 저장 실패: {e}")
            messagebox.showerror("오류", f"설정 저장 중 오류가 발생했습니다: {e}")

    def _create_section_frame_styled(self, parent, title, fill_parent=False):
        """스타일이 적용된 섹션 프레임을 생성하고 반환합니다."""
        frame = tk.Frame(parent)
        self.theme_manager.register_widget(frame, {'bg': 'surface', 'relief': 'groove', 'bd': 1, 'padx': 3, 'pady': 3})

        if fill_parent:
            frame.pack(fill='both', expand=True, padx=3, pady=3)
        else:
            frame.pack(fill='x', padx=3, pady=3)

        title_lbl = tk.Label(frame, text=title, anchor='w', font=('Segoe UI', 10, 'bold'))
        self.theme_manager.register_widget(title_lbl, {'bg': 'surface', 'fg': 'primary'})
        title_lbl.pack(fill='x', pady=(0, 5))

        content_frame = tk.Frame(frame)
        self.theme_manager.register_widget(content_frame, {'bg': 'white', 'padx': 3, 'pady': 3, 'relief': 'solid', 'bd': 1})
        content_frame.pack(fill='both', expand=True)

        return content_frame # 내용이 들어갈 프레임을 반환합니다.

    # DataManager 클래스의 finalize_processing_states 함수를 CheckCaptureOCRApp으로 옮김 (Worker 스레드가 아닌 Main 스레드에서 호출하기 위함)
    def _finalize_processing_states(self):
        """처리 완료 또는 중단 후 모든 항목의 상태를 최종화 (Main Thread에서 호출)"""
        self.logger.info("[_finalize_processing_states] 함수 호출됨 (Main Thread)")
        try:
            for i, row_data in enumerate(self.data_manager.excel_data):
                # '처리 중...' 상태이거나, 처리되지 않은 항목들을 '중단됨'으로 표시
                # 이미 완료/오류 상태인 항목은 그대로 둠
                if row_data['상태'] == '처리 중...' or row_data['상태'] == '대기 중':
                    # 데이터 목록 자체를 여기서 직접 업데이트
                    self.data_manager.excel_data[i]['상태'] = '중단됨'
                    # UI 업데이트는 refresh_grid_ui에서 일괄 처리되므로 여기서 별도 호출 불필요

            self.message_queue.put(("log", "모든 처리 상태를 최종화했습니다.", "INFO"))
        except Exception as e:
            self.message_queue.put(("log", f"상태 최종화 중 오류: {e}", "ERROR"))
            self.logger.exception("처리 상태 최종화 중 예외 발생")


    # 엑셀 내보내기 및 최종 완료 처리를 담당하는 함수 (메인 스레드에서 호출됨)
    def _finalize_export_and_complete(self, output_dir_str, input_excel_path_str, summary_message):
        self.logger.info("[_finalize_export_and_complete] 함수 호출됨 (Main Thread)")

        # 엑셀 내보내기 직전에 최종 상태를 다시 한번 정리 (안정성 강화)
        # 이전에 모든 grid_update 메시지가 처리되었음을 가정하고 finalize_processing_states 호출
        self._finalize_processing_states() # 이 함수는 이제 data_manager.excel_data를 직접 업데이트

        # 데이터 내보내기 호출
        export_started = perf_counter()
        export_error = None
        output_workbook = updated_workbook_path(output_dir_str, input_excel_path_str)
        try:
            output_workbook = self.data_manager.export_grid_to_excel_data(output_dir_str, input_excel_path_str) or output_workbook
        except Exception as export_exc:
            export_error = f"Excel export failed: {export_exc}"
        export_timing_ms = {"export_ms": round((perf_counter() - export_started) * 1000, 3)}
        report_manager = self.ocr_workflow_manager
        if report_manager._current_run_report is not None:
            existing_timings = {
                row_report.get("index"): row_report.get("timing_ms", {})
                for row_report in report_manager._current_run_report.get("rows", [])
            }
            existing_metadata = {
                row_report.get("index"): {"ocr_confidence": row_report.get("ocr_confidence")}
                for row_report in report_manager._current_run_report.get("rows", [])
                if row_report.get("ocr_confidence")
            }
            record_row_reports(
                report_manager._current_run_report,
                self.data_manager.excel_data,
                existing_timings,
                existing_metadata,
            )
            summary = report_manager._current_run_report.get("summary", {})
            if export_error is None and not output_workbook.exists():
                export_error = f"Export workbook was not found after export: {output_workbook}"
            finalize_run_report(
                report_manager._current_run_report,
                self.data_manager.excel_data,
                processed_count=int(summary.get("processed_count", 0) or 0),
                total_items=int(summary.get("total_items", len(self.data_manager.excel_data)) or 0),
                stopped=bool(summary.get("stopped", False)),
                output_workbook_path=output_workbook,
                export_timing_ms=export_timing_ms,
                error=export_error,
            )
            report_manager._flush_current_run_report()

        self.work_controller.reset()
        self.data_manager.current_processing_index = -1
        self._set_runtime_state(self._ready_or_error_state())

        # 그리드 UI 최종 새로고침
        # _finalize_processing_states 및 export_grid_to_excel_data 후에 UI를 새로고침하여 최종 상태와 데이터를 표시
        self.refresh_grid_ui() # 상태 최종화 결과 반영 및 최종 데이터 표시

        # 최종 완료 메시지 박스 표시
        if export_error is not None:
            messagebox.showerror("Excel export failed", export_error)
            return
        messagebox.showinfo("처리 완료", summary_message)

    def _generate_ocr_summary_internal(self, processed_count, total_items):
        date_success = sum(1 for row in self.data_manager.excel_data if row.get('날짜','').strip() and row['상태'] == '완료')
        rate_success = sum(1 for row in self.data_manager.excel_data if row.get('금리','').strip() and row['상태'] == '완료')
        actual_processed_for_stats = sum(1 for row in self.data_manager.excel_data if row['상태'] == '완료')
        date_accuracy = (date_success / actual_processed_for_stats * 100) if actual_processed_for_stats > 0 else 0
        rate_accuracy = (rate_success / actual_processed_for_stats * 100) if actual_processed_for_stats > 0 else 0
        summary = f"""📊 OCR 처리 완료!
        ------------------------------------
        총 시도 항목: {total_items}개
        성공적으로 처리된 항목: {actual_processed_for_stats}개
        ------------------------------------
        📁 결과는 그리드 및 Excel 파일로 저장되었습니다.
        📝 상세 로그는 ocr_app.log 파일에서 확인 가능합니다.
        """
        return summary

    # 작업 중단 시 호출되는 함수 (Main Thread에서 호출)
    def _on_work_stopped(self):
        self.logger.info("[_on_work_stopped] 함수 호출됨 (Main Thread)")
        self.work_controller.reset() # WorkController 상태 리셋
        self.data_manager.current_processing_index = -1
        self._set_runtime_state(self._ready_or_error_state())
        # 중단 시에도 최종 상태 정리 후 UI 새로고침하여 '중단됨' 상태 표시
        self._finalize_processing_states() # 중단된 항목들 상태 최종화
        self.refresh_grid_ui() # 최종 UI 새로고침
        messagebox.showinfo("중단됨", "작업이 사용자에 의해 중단되었습니다.")

    def on_upscaling_toggle(self):
        """업스케일링 옵션 토글 시 세부 설정 표시/숨김"""
        if self.enable_upscaling.get():
            # 업스케일링 활성화 시 세부 설정 표시
            if hasattr(self, 'upscaling_details_frame'):
                for child in self.upscaling_details_frame.winfo_children():
                    child.pack_configure()
        else:
            # 업스케일링 비활성화 시 세부 설정 숨김  
            if hasattr(self, 'upscaling_details_frame'):
                for child in self.upscaling_details_frame.winfo_children():
                    child.pack_forget()
        
        # 설정 저장
        self.save_advanced_ui_to_settings()


if __name__ == "__main__":
    app = CheckCaptureOCRApp()
    app.protocol("WM_DELETE_WINDOW", app.quit_app)
    app.mainloop()
