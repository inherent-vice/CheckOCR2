import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import pandas as pd
import pyperclip
import pyautogui
import time
import os
from PIL import Image, ImageTk
import numpy as np
import easyocr
import json
import logging
from datetime import datetime
import threading
import queue
import re
import subprocess
import platform # OS 정보 확인용
from typing import Optional

############################################
# 로깅 설정
############################################
class TkinterLogHandler(logging.Handler):
    """커스텀 로깅 핸들러: 로그 메시지를 Tkinter Text 위젯으로 전달"""
    def __init__(self, text_widget, message_queue):
        super().__init__()
        self.text_widget = text_widget
        self.message_queue = message_queue
        self.formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')

    def emit(self, record):
        if not self.text_widget or not self.text_widget.winfo_exists():
            return # 위젯이 없거나 파괴된 경우 무시

        msg = self.format(record)
        # 메인 스레드에서 UI 업데이트를 안전하게 하기 위해 큐 사용
        self.message_queue.put(("log_display", record.levelname, msg))

def setup_logging(log_queue):
    """로깅 기본 설정 및 Tkinter 핸들러 추가"""
    logger = logging.getLogger("OCRApp") # 고유 로거 이름 사용
    logger.handlers = [] # 기존 핸들러 초기화 (중복 로깅 방지)
    logger.setLevel(logging.INFO) # 로거 레벨 설정

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # 파일 핸들러
    file_handler = logging.FileHandler('ocr_app.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 콘솔 핸들러 (디버깅용)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # Tkinter 핸들러는 App 클래스 내에서 text_widget이 생성된 후 추가
    return logger

############################################
# 통합 설정 관리 시스템
############################################
class UnifiedSettingsManager:
    def __init__(self):
        self.settings_file = "settings.json"
        self.data = self.load_settings()

        if 'presets' not in self.data: self.data['presets'] = {}
        if 'current' not in self.data: self.data['current'] = {}
        if 'advanced' not in self.data: self.data['advanced'] = self._get_default_advanced_settings()

    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"설정 로드 오류: {e}")
        return {}

    def save_settings(self):
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"설정 저장 오류: {e}")

    def save_preset(self, name, settings):
        self.data['presets'][name] = {
            'click_point': settings['click_point'],
            'all_area': settings['all_area'],
            'date_area': settings['date_area'],
            'rate_area': settings['rate_area'],
            'delays': settings['delays'],
            'save_detail_images': settings.get('save_detail_images', True),
            'advanced': settings.get('advanced', {}),
            'created_at': datetime.now().isoformat()
        }
        self.save_settings()

    def get_preset_names(self):
        return list(self.data['presets'].keys())

    def apply_preset(self, name):
        return self.data['presets'].get(name, None)

    def delete_preset(self, name):
        if name in self.data['presets']:
            del self.data['presets'][name]
            self.save_settings()

    def save_current_settings(self, settings):
        self.data['current'] = settings
        self.save_settings()

    def get_current_settings(self):
        return self.data.get('current', {})

    def _get_default_advanced_settings(self):
        return {
            'ocr_languages': ['en'],
            'ocr_max_attempts': 1,
            'ocr_detail_level': 0,
            'click_interval': 0.1,
            'min_date_confidence': 0.0,
            'min_rate_confidence': 0.0,
            'ui_theme': 'modern_blue', # 기본 테마 추가
            'skip_kbp_code': True # KBP 코드 건너뛰기 기본값 추가
        }

    def _get_optimal_thread_count(self):
        cpu_count = os.cpu_count() or 4
        return min(max(cpu_count, 2), 8)

    def get_advanced(self, key, default=None):
        return self.data['advanced'].get(key, default)

    def set_advanced(self, key, value):
        self.data['advanced'][key] = value
        self.save_settings()

    def reset_advanced_settings(self):
        self.data['advanced'] = self._get_default_advanced_settings()
        self.save_settings()

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
# 진행 상황 추적기
############################################
class ProgressTracker:
    def __init__(self, parent_frame, theme_manager):
        self.parent_frame = parent_frame
        self.theme_manager = theme_manager
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar()
        self.current_item_var = tk.StringVar()
        self.setup_ui()

    def setup_ui(self):
        self.progress_frame = tk.Frame(self.parent_frame)
        # ThemeManager에 등록
        self.theme_manager.register_widget(self.progress_frame, {'bg': 'surface'})


        self.current_label = tk.Label(self.progress_frame, textvariable=self.current_item_var, font=('Arial', 9, 'bold'))
        self.theme_manager.register_widget(self.current_label, {'bg': 'surface', 'fg': 'primary'})
        self.current_label.pack(pady=(0, 3))

        self.progress_bar = ttk.Progressbar(self.progress_frame, variable=self.progress_var, maximum=100, style="TProgressbar")
        self.progress_bar.pack(fill='x', pady=(0, 5))

        self.status_label = tk.Label(self.progress_frame, textvariable=self.status_var, font=('Arial', 9))
        self.theme_manager.register_widget(self.status_label, {'bg': 'surface', 'fg': 'on_surface'})
        self.status_label.pack()
        
        self.progress_frame.pack_forget()

    def show(self):
        try:
            if self.progress_frame.winfo_exists():
                self.progress_frame.pack(fill='x', padx=5, pady=5)
        except tk.TclError: pass

    def hide(self):
        try:
            if self.progress_frame.winfo_exists():
                self.progress_frame.pack_forget()
        except tk.TclError: pass

    def update_progress(self, current, total, status_text, current_item=""):
        if total > 0:
            progress = (current / total) * 100
            self.progress_var.set(progress)
            self.status_var.set(f"{status_text} ({current}/{total}) - {progress:.1f}%")
            self.current_item_var.set(current_item)
        else:
            self.progress_var.set(0)
            self.status_var.set(status_text)
            self.current_item_var.set(current_item)


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
            df = pd.read_excel(file_path, dtype=str)
            self.clear_all_data_internal()

            col_map = {}
            expected_cols = {'종목코드': ['종목코드', 'code', 'item code'],
                             '종목명': ['종목명', 'name', 'item name', '회사명']}
            df_cols_lower = {str(col).lower(): str(col) for col in df.columns}

            for target_col, possible_names in expected_cols.items():
                for p_name in possible_names:
                    if p_name in df_cols_lower:
                        col_map[target_col] = df_cols_lower[p_name]
                        break
                if target_col not in col_map:
                    self.logger.warning(f"Excel 파일에 '{target_col}'에 해당하는 컬럼을 찾을 수 없습니다.")
                    col_map[target_col] = None
            
            new_data = []
            for _, row in df.iterrows():
                new_data.append({
                    '종목코드': str(row[col_map['종목코드']]) if col_map.get('종목코드') and col_map['종목코드'] in row else '',
                    '종목명': str(row[col_map['종목명']]) if col_map.get('종목명') and col_map['종목명'] in row else '',
                    '날짜': '', '금리': '', '상태': '대기 중'
                })
            self.excel_data = new_data
            return len(self.excel_data)
        except Exception as e:
            self.logger.exception("Excel 파일 로드 실패")
            self.message_queue.put(("error_messagebox", "Excel 파일 로드 중 오류", f"{e}"))
            return 0
            
    def add_empty_row_data(self):
        self.excel_data.append({'종목코드': '', '종목명': '', '날짜': '', '금리': '', '상태': '대기 중'})

    def paste_from_clipboard_data(self, clipboard_content):
        try:
            lines = clipboard_content.strip().split('\n')
            added_count = 0
            for line in lines:
                parts = line.split('\t')
                if len(parts) >= 1 and parts[0].strip():
                    self.excel_data.append({
                        '종목코드': parts[0].strip() if len(parts) > 0 else '',
                        '종목명': parts[1].strip() if len(parts) > 1 else '',
                        '날짜': '', '금리': '', '상태': '대기 중'
                    })
                    added_count +=1
            return added_count
        except Exception as e:
            self.logger.exception("클립보드 붙여넣기 실패")
            self.message_queue.put(("error_messagebox", "붙여넣기 중 오류", f"{e}"))
            return 0

    def delete_rows_data(self, indices_to_delete):
        for index in sorted(indices_to_delete, reverse=True):
            if 0 <= index < len(self.excel_data):
                del self.excel_data[index]
    
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
            row = self.excel_data[index]
            return f"{row['종목코드']}\t{row['종목명']}\t{row['날짜']}\t{row['금리']}\t{row['상태']}"
        return ""

    def export_grid_to_excel_data(self, output_dir, input_file_path_str):
        if not self.excel_data:
            self.message_queue.put(("log", "내보낼 데이터가 없습니다.", "INFO"))
            return

        base_name = os.path.basename(input_file_path_str) if input_file_path_str else "ocr_results"
        new_file_name = os.path.splitext(base_name)[0] + '_updated.xlsx'
        new_file_path = os.path.join(output_dir, new_file_name)

        try:
            # 디버그 로그: 엑셀 내보내기 직전 데이터 상태 확인
            self.logger.debug(f"[export_grid_to_excel_data] 내보내기 직전 데이터: {self.excel_data}")
            
            df_export = pd.DataFrame(self.excel_data)
            df_export = df_export[['종목코드', '종목명', '날짜', '금리', '상태']]
            
            # Excel 내보내기 시 '중단됨' 상태를 빈 문자열로 변경
            df_export['상태'] = df_export['상태'].apply(lambda x: '' if x == '중단됨' else x)

            with pd.ExcelWriter(new_file_path, engine='openpyxl') as writer:
                df_export.to_excel(writer, sheet_name='OCR_Results', index=False)
            self.message_queue.put(("log", f"결과 Excel 파일 저장 완료: {new_file_path}", "SUCCESS"))
        except Exception as e:
            self.message_queue.put(("log", f"Excel 파일 저장 실패: {e}", "ERROR"))
            self.logger.exception("Excel 파일 저장 중 예외 발생")


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

    def initialize_ocr(self):
        try:
            self.logger.info("EasyOCR 초기화 중... (영어 전용)")
            # gpu_enabled = self.settings_manager.get_advanced('ocr_gpu_enabled', False) # GPU 설정 제거
            gpu_enabled = False # GPU 사용 비활성화로 고정
            languages = ['en'] # 영어로 고정
            self.ocr_reader = easyocr.Reader(languages, gpu=gpu_enabled)
            self.logger.info(f"EasyOCR 초기화 완료 - 언어: {languages}, GPU: {gpu_enabled}")
        except Exception as e:
            self.logger.error(f"EasyOCR 초기화 실패: {e}")
            try:
                self.logger.info("기본 모드(영어, CPU)로 EasyOCR 재초기화 시도...")
                self.ocr_reader = easyocr.Reader(['en'], gpu=False)
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
            
            # 이미지 저장 폴더를 입력 Excel 파일명 기반으로 설정
            input_excel_file = self.app.input_excel_path.get()
            if input_excel_file:
                base_name = os.path.splitext(os.path.basename(input_excel_file))[0]
                save_folder = os.path.join(output_dir_str, base_name) # _images 접미사 제거
            else:
                save_folder = os.path.join(output_dir_str, "ocr_images") # 기본 폴더

            os.makedirs(save_folder, exist_ok=True)

            total_items = len(self.data_manager.excel_data)
            processed_count = 0

            for grid_index, row_data in enumerate(self.data_manager.excel_data):
                # 각 항목 처리 시작 시 중단 확인
                if self.work_controller.is_stopped:
                    self.message_queue.put(("log", "사용자가 처리를 중단했습니다.", "INFO"))
                    self.message_queue.put(("stopped", None))
                    return # 전체 워크플로우 중단

                stock_code = str(row_data.get('종목코드', '')).strip()
                stock_name = str(row_data.get('종목명', '')).strip()
                current_item_text = f"{stock_code} ({stock_name})" if stock_code or stock_name else f"행 {grid_index+1}"
                
                self.data_manager.current_processing_index = grid_index # DataManager의 인덱스 업데이트
                self.message_queue.put(("grid_update", ("processing", grid_index)))
                self.message_queue.put(("progress", (grid_index + 1, total_items, f"처리 중: {current_item_text}", current_item_text)))

                # 'kbp' 코드 건너뛰기 설정 확인
                skip_kbp = self.settings_manager.get_advanced('skip_kbp_code', True) # 설정에서 가져옴, 기본값 True
                if skip_kbp and stock_code.lower().startswith('kbp'):
                    self.message_queue.put(("log", f"[{stock_code}] 'kbp'로 시작하는 종목코드, 설정에 따라 건너뛰고 완료 처리.", "INFO"))
                    self.data_manager.excel_data[grid_index]['날짜'] = '' # 날짜 빈 값
                    self.data_manager.excel_data[grid_index]['금리'] = '' # 금리 빈 값
                    self.message_queue.put(("grid_update", ("complete", grid_index, '', '', "완료")))
                    processed_count += 1
                    continue # 다음 항목으로 넘어감

                if not stock_code:
                    self.message_queue.put(("log", f"행 {grid_index+1}: 종목코드가 없어 건너뜁니다.", "WARNING"))
                    self.message_queue.put(("grid_update", ("error", grid_index, "종목코드 없음")))
                    continue

                self.work_controller.skip_current = False
                try:
                    date_img_src, rate_img_src = self._capture_screenshots_internal(
                        stock_code, save_folder, coords, paste_d, load_d, save_detail_images_bool
                    )
                    if self.work_controller.skip_current:
                        self.message_queue.put(("log", f"종목 {stock_code}를 사용자 요청으로 건너뜁니다.", "INFO"))
                        self.message_queue.put(("grid_update", ("error", grid_index, "건너뜀")))
                        continue
                    if date_img_src is None or rate_img_src is None:
                        if self.work_controller.is_stopped: break
                        self.message_queue.put(("grid_update", ("error", grid_index, "캡처 실패")))
                        continue

                    date_result, rate_result = self._process_single_ocr_internal(date_img_src, rate_img_src, save_detail_images_bool)
                    
                    status_msg = "완료"
                    self.message_queue.put(("grid_update", ("complete", grid_index, date_result, rate_result, status_msg)))
                    self.message_queue.put(("log", f"[{stock_code}] {status_msg} - 날짜: '{date_result}', 금리: '{rate_result}'", "SUCCESS" if status_msg == "완료" else "INFO"))
                    if status_msg == "완료": processed_count += 1

                except Exception as e_item:
                    self.message_queue.put(("log", f"종목 {stock_code} 처리 중 오류: {e_item}", "ERROR"))
                    self.message_queue.put(("grid_update", ("error", grid_index, "처리 오류")))
                    self.logger.exception(f"종목 {stock_code} 처리 중 예외 발생")
                    continue

            # for 루프 완료 후 최종 상태 정리 및 완료 메시지 전송
            # 작업이 중단되지 않았을 경우에만 실행
            if not self.work_controller.is_stopped:
                self._finalize_processing_states()
                self.data_manager.export_grid_to_excel_data(output_dir_str, self.app.input_excel_path.get()) # App의 경로 사용
                summary = self._generate_ocr_summary_internal(processed_count, total_items)
                self.message_queue.put(("complete", summary))

        except Exception as e_workflow:
            self.message_queue.put(("log", f"OCR 전체 워크플로우 오류: {e_workflow}", "ERROR"))
            self.logger.exception("OCR 전체 워크플로우에서 예외 발생")
            # 오류 발생 시 작업 중단 상태로 전환 및 중단 메시지 전송
            if not self.work_controller.is_stopped: # 이미 중단되지 않았다면 중단 신호 발생
                 self.work_controller.stop_work()
            self.message_queue.put(("stopped", None))

    def _capture_screenshots_internal(self, stock_code, save_folder, coords, paste_d, load_d, save_details):
        if self.work_controller.is_stopped: return None, None
        pyperclip.copy(stock_code)
        pyautogui.click(x=coords['click'][0], y=coords['click'][1], clicks=2, interval=self.settings_manager.get_advanced('click_interval', 0.1))
        
        # time.sleep 대신 work_controller.stop_event.wait 사용
        if self.work_controller.stop_event.wait(timeout=paste_d): return None, None # 중단되면 None 반환
        
        pyautogui.hotkey('ctrl', 'v')

        if self.work_controller.stop_event.wait(timeout=load_d): return None, None

        safe_stock_code = re.sub(r'[\\/*?:"<>|]', "_", stock_code)
        date_img_src, rate_img_src = None, None

        # 전체 영역
        x1_all, y1_all, x2_all, y2_all = coords['all']
        if not (x2_all > x1_all and y2_all > y1_all):
            self.message_queue.put(("log", f"[{safe_stock_code}] 전체 영역 좌표 오류: {coords['all']}", "ERROR"))
            return None, None
        screenshot_all = pyautogui.screenshot(region=(x1_all, y1_all, x2_all - x1_all, y2_all - y1_all))
        allarea_path = os.path.join(save_folder, f"{safe_stock_code}.png")
        screenshot_all.save(allarea_path)
        self.message_queue.put(("log", f"전체 영역 이미지 저장: {allarea_path}", "INFO"))

        # 날짜 영역
        x1_date, y1_date, x2_date, y2_date = coords['date']
        if not (x2_date > x1_date and y2_date > y1_date):
            self.message_queue.put(("log", f"[{safe_stock_code}] 날짜 영역 좌표 오류: {coords['date']}", "ERROR"))
        else:
            screenshot_date = pyautogui.screenshot(region=(x1_date, y1_date, x2_date - x1_date, y2_date - y1_date))
            if save_details:
                date_img_src = os.path.join(save_folder, f"{safe_stock_code}_date.png")
                screenshot_date.save(date_img_src)
                self.message_queue.put(("log", f"날짜 영역 이미지 저장: {date_img_src}", "INFO"))
            else: date_img_src = screenshot_date

        # 금리 영역
        x1_rate, y1_rate, x2_rate, y2_rate = coords['rate']
        if not (x2_rate > x1_rate and y2_rate > y1_rate):
            self.message_queue.put(("log", f"[{safe_stock_code}] 금리 영역 좌표 오류: {coords['rate']}", "ERROR"))
        else:
            screenshot_rate = pyautogui.screenshot(region=(x1_rate, y1_rate, x2_rate - x1_rate, y2_rate - y1_rate))
            if save_details:
                rate_img_src = os.path.join(save_folder, f"{safe_stock_code}_rate.png")
                screenshot_rate.save(rate_img_src)
                self.message_queue.put(("log", f"금리 영역 이미지 저장: {rate_img_src}", "INFO"))
            else: rate_img_src = screenshot_rate
        
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
        try:
            original_img = Image.open(image_source) if isinstance(image_source, str) else image_source
            if original_img is None:
                self.message_queue.put(("log", f"{field_name} 이미지 소스 로드 실패: {image_source}", "WARNING"))
                return ""

            if self.work_controller.is_stopped: return ""
            img_array = np.array(original_img)
            ocr_results = self.ocr_reader.readtext(img_array, detail=0)
            all_text = " ".join(ocr_results) if ocr_results else ""
            self.message_queue.put(("log", f"[{field_name}] 원본 OCR 결과: '{all_text}'", "INFO"))
            return analysis_function(all_text, field_name)
        except Exception as e:
            self.message_queue.put(("log", f"{field_name} 추출 중 오류: {e}", "ERROR"))
            self.logger.exception(f"{field_name} 추출 중 예외 발생")
            return ""
        finally:
            if isinstance(image_source, str) and not save_details:
                if os.path.exists(image_source) and ("_date.png" in image_source or "_rate.png" in image_source):
                    try:
                        os.remove(image_source)
                        self.message_queue.put(("log", f"임시 {field_name} 이미지 파일 삭제: {image_source}", "DEBUG"))
                    except Exception as e_remove:
                        self.message_queue.put(("log", f"임시 {field_name} 이미지 파일 삭제 실패: {e_remove}", "WARNING"))
    
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
        return bool(re.fullmatch(r'\d{4}/\d{2}/\d{2}', date_str))

    def _is_valid_rate_format_internal(self, rate_str):
        return bool(re.fullmatch(r'\d+\.\d+', rate_str))

    def _clean_date_text_internal(self, text):
        cleaned = re.sub(r'[^\d]', '', text)
        if len(cleaned) == 8: return f"{cleaned[:4]}/{cleaned[4:6]}/{cleaned[6:]}"
        elif len(cleaned) == 6:
            year_prefix = "20" if int(cleaned[:2]) < 70 else "19" # 70년 기준 20xx/19xx
            return f"{year_prefix}{cleaned[:2]}/{cleaned[2:4]}/{cleaned[4:]}"
        elif len(cleaned) == 7 and cleaned.startswith('202') and int(cleaned[4]) <=1 : # 202YMDD
             # 2024101 -> 2024/01/01, 2024501 -> 2024/05/01
            month_part = cleaned[4]
            day_part = cleaned[5:]
            if len(day_part) == 1: day_part = "0" + day_part # 5 -> 05
            if len(day_part) == 2 and int(day_part) > 31 : # 2024131 -> 2024/01/31, 2024140 (x)
                 # 이 경우는 YYYYMMD 로 간주. 202413 -> 2024/01/03
                 if len(cleaned) == 7: # YYYYMMD
                     return f"{cleaned[:4]}/{cleaned[4:6]}/{cleaned[6].zfill(2)}"


            return f"{cleaned[:4]}/{month_part.zfill(2)}/{day_part.zfill(2)}"


        return text # 정제 실패 시 원본 반환 (분석 함수에서 재검증)


    def _clean_rate_text_internal(self, text):
        cleaned = text.replace('%','').replace(' ','').replace(',','.').replace('·','.')
        cleaned = re.sub(r'[^\d.]', '', cleaned)
        if cleaned.count('.') > 1:
            parts = cleaned.split('.')
            cleaned = parts[0] + '.' + ''.join(parts[1:])
        
        if re.fullmatch(r'\d+\.\d+', cleaned):
            try:
                val = float(cleaned)
                # 소수점 3자리로 포맷팅, 불필요한 0 제거 안 함 (예: 3.500)
                return f"{val:.3f}" 
            except ValueError: return cleaned
        elif re.fullmatch(r'\d+', cleaned) and 2 <= len(cleaned) <= 5:
            try: # 35 -> 3.500, 350 -> 3.500, 3500 -> 3.500, 12500 -> 12.500
                if len(cleaned) == 2: return f"{cleaned[0]}.{cleaned[1]}00"
                elif len(cleaned) == 3: return f"{cleaned[0]}.{cleaned[1:]}0" if cleaned[1:] != "00" else f"{cleaned[0]}.000" # 300 -> 3.000
                elif len(cleaned) == 4: return f"{cleaned[0]}.{cleaned[1:]}"
                elif len(cleaned) == 5: return f"{cleaned[:2]}.{cleaned[2:]}"
            except: pass
        return cleaned

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
                if row_data['상태'] == '처리 중...' or row_data['상태'] == '대기 중':
                    row_data['상태'] = '중단됨'
                    # 그리드 업데이트는 _on_work_complete 또는 _on_work_stopped에서 일괄 처리되므로 여기서 별도 호출 불필요
                    # self.message_queue.put(("grid_update", ("error", i, "중단됨")))
            # 상태 변경 후 그리드 일괄 새로고침은 _on_work_complete/_on_work_stopped에서 진행
            self.message_queue.put(("log", "모든 처리 상태를 최종화했습니다.", "INFO"))
        except Exception as e:
            self.message_queue.put(("log", f"상태 최종화 중 오류: {e}", "ERROR"))
            self.logger.exception("처리 상태 최종화 중 예외 발생")

    def _clean_folder_path(self, path: Optional[str]) -> str:
        if not path:
            return self.settings_manager.get_advanced('default_output_dir', ".")
        
        cleaned_path = str(path).strip()
        original_path = cleaned_path # UNC prefix 감지용

        is_unc = False
        prefix = ""
        if original_path.startswith("//"):
            is_unc = True
            prefix = "//"
            cleaned_path = original_path[2:]
        elif original_path.startswith("\\\\"):
            is_unc = True
            prefix = "\\\\"
            cleaned_path = original_path[4:]

        if is_unc:
            # UNC 경로는 내부적으로 \ 사용을 가정 (Windows 표준)
            parts = [part for part in cleaned_path.split("/") if part] # / 기준 분리
            cleaned_path = "\\".join(parts) # \ 기준으로 재조합
            cleaned_path = prefix + cleaned_path
        else:
            cleaned_path = cleaned_path.replace("\\", "/")
            while "//" in cleaned_path:
                cleaned_path = cleaned_path.replace("//", "/")
        
        # 공통 정리 (다중 공백 -> 단일 공백)
        cleaned_path = " ".join(cleaned_path.split())
        
        # 최종적으로 os.path.normpath 사용 시 UNC도 어느정도 처리되나, 
        # Windows UNC는 \\server\share 형태이므로 이에 맞추는 것이 좋음
        if platform.system() == "Windows" and is_unc:
            pass # 이미 \\ 형태로 처리됨
        elif is_unc: # 비윈도우 환경 UNC (smb:// 등은 여기서 다루지 않음)
            pass # prefix + cleaned_path 유지
        else:
            cleaned_path = os.path.normpath(cleaned_path)
        return cleaned_path

############################################
# 메인 GUI
############################################
class CheckCaptureOCRApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("📊 Check Capture OCR V6.1")
        self.geometry("1200x750") # 창 크기 증가
        self.resizable(True, True)
        self.minsize(1100, 700) # 최소 크기 증가
        self.center_window()

        self.message_queue = queue.Queue()
        self.logger = setup_logging(self.message_queue) # 로거 설정 (큐 전달)
        
        self.settings_manager = UnifiedSettingsManager()
        self.theme_manager = ThemeManager(self) # ThemeManager 초기화
        self.progress_tracker = ProgressTracker(self, self.theme_manager) # 부모프레임, 테마매니저 전달
        self.work_controller = WorkController()
        self.data_manager = DataManager(self, self.logger, self.message_queue)
        self.ocr_workflow_manager = OCRWorkflowManager(self, self.logger, self.message_queue, self.work_controller, self.settings_manager, self.data_manager)
        
        self.worker_thread = None

        # UI 변수
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
        
        # self.use_gpu = tk.BooleanVar(value=False) # GPU 설정 제거
        self.confidence_threshold = tk.DoubleVar(value=20.0) # OCR 신뢰도 (UI 표시용, 실제로는 EasyOCR detail=0이라 미사용)
        # self.max_threads = tk.IntVar(value=4) # UI 표시용 (실제 스레드는 1개) # Max Threads 설정 제거
        self.theme_var = tk.StringVar()

        self.grid_tree = None # Treeview 참조
        self.log_text_widget = None # 로그 텍스트 위젯 참조

        self.ocr_workflow_manager.initialize_ocr() # OCR 초기화
        self._build_ui()
        self._setup_keyboard_shortcuts()
        self.check_queue()
        self.load_last_settings() # 마지막 설정 로드 (UI 빌드 후)
        self.theme_manager.apply_theme_to_all_widgets() # 초기 테마 적용

    def center_window(self):
        self.update_idletasks()
        screen_width, screen_height = self.winfo_screenwidth(), self.winfo_screenheight()
        window_width, window_height = self.winfo_width(), self.winfo_height() # 현재 창 크기 사용
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
        try:
            while True:
                msg_type, *data = self.message_queue.get_nowait()
                if msg_type == "progress":
                    current, total, status, current_item_text = data[0]
                    self.progress_tracker.update_progress(current, total, status, current_item_text)
                    self.work_controller.current_item = current_item_text
                elif msg_type == "log": # 로거를 통해 직접 로깅 (TkinterLogHandler가 UI 업데이트)
                    if len(data) >= 2:
                        message, level_str = data[0], data[1]
                        level = getattr(logging, level_str.upper(), logging.INFO)
                        self.logger.log(level, message) # TkinterLogHandler가 처리
                    else:
                        message = data[0] if data else "알 수 없는 로그 메시지"
                        self.logger.info(message)
                elif msg_type == "log_display": # TkinterLogHandler로부터 온 메시지
                    level_name, formatted_message = data[0], data[1]
                    self._update_log_text_widget(formatted_message, level_name)
                elif msg_type == "error_messagebox":
                    title, message = data[0], data[1]
                    messagebox.showerror(title, message)
                elif msg_type == "complete":
                    self._on_work_complete(data[0])
                elif msg_type == "stopped":
                    self._on_work_stopped()
                elif msg_type == "grid_update":
                    self._handle_grid_update(data[0])
        except queue.Empty: pass
        self.after(100, self.check_queue)

    def _update_log_text_widget(self, message, level_name="INFO"):
        if self.log_text_widget and self.log_text_widget.winfo_exists():
            self.log_text_widget.config(state='normal')
            tag = level_name.upper()
            if tag not in self.log_text_widget.tag_names(): # 태그가 없으면 기본 INFO 사용
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
        main_container.grid_columnconfigure(0, weight=1) # 좌측 패널 weight 1로 변경
        main_container.grid_columnconfigure(1, weight=1)
        main_container.grid_columnconfigure(2, weight=0, minsize=220) # 우측 패널 너비 고정

        left_panel = tk.Frame(main_container, width=250) # 좌측 패널 너비 더 축소
        self.theme_manager.register_widget(left_panel, {'bg': 'surface'})
        left_panel.grid(row=0, column=0, sticky='nsew', padx=(5,0), pady=5)
        left_panel.pack_propagate(False)

        center_panel = tk.Frame(main_container)
        self.theme_manager.register_widget(center_panel, {'bg': 'surface'})
        center_panel.grid(row=0, column=1, sticky='nsew', padx=5, pady=5)

        right_panel = tk.Frame(main_container, width=220)
        self.theme_manager.register_widget(right_panel, {'bg': 'surface'})
        right_panel.grid(row=0, column=2, sticky='nsew', padx=(0,5), pady=5)
        right_panel.pack_propagate(False)

        self._create_left_panel_content(left_panel)
        self._create_center_excel_grid(center_panel)
        self._create_right_panel_content(right_panel)
        
        # ProgressTracker UI를 main_container의 하단에 배치 (grid 사용)
        # main_container의 row 1에 ProgressTracker 배치
        main_container.grid_rowconfigure(1, weight=0) # progress tracker는 확장 안 함
        self.progress_tracker.progress_frame.grid(row=1, column=0, columnspan=3, sticky='ew', padx=5, pady=(0,5))
        self.progress_tracker.hide() # 처음에는 숨김

        # TkinterLogHandler 설정 (log_text_widget이 생성된 후)
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
        settings_menu.add_command(label="고급 설정 저장", command=self.save_advanced_ui_to_settings)
        settings_menu.add_command(label="고급 설정 초기화", command=self.reset_advanced_settings_and_ui)

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
        
        self.run_btn = tk.Button(controls_frame, text="🚀 OCR 시작 (F5)", command=self.run_ocr_process, font=('Segoe UI', 9, 'bold'), relief='flat', cursor='hand2')
        self.theme_manager.register_widget(self.run_btn, {'bg': 'success', 'fg': 'white', 'activebackground':'dark', 'activeforeground':'white'})
        self.run_btn.pack(side='left', padx=(0, 5))
        
        self.stop_btn = tk.Button(controls_frame, text="⏹️ 중단", command=self.stop_processing_ui_initiated, font=('Segoe UI', 9, 'bold'), relief='flat', cursor='hand2')
        self.theme_manager.register_widget(self.stop_btn, {'bg': 'danger', 'fg': 'white', 'activebackground':'dark', 'activeforeground':'white'})
        self.stop_btn.pack(side='left', padx=(0, 15))
        
        theme_lbl = tk.Label(toolbar, text="테마:", font=('Segoe UI', 9))
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
        # 스크롤 기능을 위해 사용되던 canvas 및 scrollbar 제거
        # canvas = tk.Canvas(parent, highlightthickness=0)
        # self.theme_manager.register_widget(canvas, {'bg': 'surface'})
        
        # # 캔버스를 인스턴스 변수에 즉시 할당
        # self.left_panel_canvas = canvas
        
        # scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.left_panel_canvas.yview, style="TScrollbar")
        
        # scrollable_frame = tk.Frame(self.left_panel_canvas)
        
        scrollable_frame = tk.Frame(parent) # 내용 프레임을 부모에 직접 배치

        self.theme_manager.register_widget(scrollable_frame, {'bg': 'surface'})

        # scrollable_frame.bind("<Configure>", lambda e: self.left_panel_canvas.configure(scrollregion=self.left_panel_canvas.bbox("all")))
        # self.left_panel_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        # self.left_panel_canvas.configure(yscrollcommand=scrollbar.set)

        # self.left_panel_canvas.pack(side="left", fill="both", expand=True)
        # scrollbar.pack(side="right", fill="y")
        
        # 마우스휠 바인딩 (캔버스에만) 제거
        # def _on_left_panel_mousewheel(event):
        #     # Windows에서는 delta가 120의 배수, Linux에서는 1의 배수일 수 있음
        #     scroll_val = -1 * (event.delta // 120) if os.name == 'nt' else -1 * event.delta
        #     self.left_panel_canvas.yview_scroll(scroll_val, "units")

        # self.left_panel_canvas.bind('<MouseWheel>', _on_left_panel_mousewheel)
        # self.left_panel_canvas.bind('<Button-4>', _on_left_panel_mousewheel)

        scrollable_frame.pack(fill="both", expand=True)

        self._create_file_section(scrollable_frame)
        self._create_coordinates_section(scrollable_frame)
        self._create_timing_section(scrollable_frame)
        self._create_options_section(scrollable_frame)
        self._create_preset_section(scrollable_frame)

    def _create_right_panel_content(self, parent):
        # 로그 섹션
        log_section_frame = self._create_section_frame_styled(parent, "📊 상태 및 로그", fill_parent=True)
        
        log_text_frame = tk.Frame(log_section_frame) # 로그 텍스트와 스크롤바를 담을 프레임
        self.theme_manager.register_widget(log_text_frame, {'bg': 'white'})
        log_text_frame.pack(fill='both', expand=True, pady=(0,5))

        self.log_text_widget = tk.Text(log_text_frame, font=('Consolas', 8), relief='solid', bd=1, wrap='word', state='disabled')
        self.theme_manager.register_widget(self.log_text_widget, {'bg': 'white', 'fg': 'on_surface', 'insertbackground': 'on_surface'})
        
        log_scroll = ttk.Scrollbar(log_text_frame, orient="vertical", command=self.log_text_widget.yview, style="TScrollbar")
        self.log_text_widget.configure(yscrollcommand=log_scroll.set)
        
        self.log_text_widget.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")

        # 로그 태그 설정
        self.log_text_widget.tag_configure("INFO", foreground=self.theme_manager.get_color('primary'))
        self.log_text_widget.tag_configure("WARNING", foreground=self.theme_manager.get_color('warning'))
        self.log_text_widget.tag_configure("ERROR", foreground=self.theme_manager.get_color('danger'))
        self.log_text_widget.tag_configure("SUCCESS", foreground=self.theme_manager.get_color('success'))
        self.log_text_widget.tag_configure("DEBUG", foreground=self.theme_manager.get_color('secondary')) # DEBUG 레벨 추가

        # 로그 컨트롤 버튼들 제거됨 (사용자 요청에 따라)

    def _create_section_frame_styled(self, parent, title, fill_parent=False):
        section_container = tk.Frame(parent)
        self.theme_manager.register_widget(section_container, {'bg': 'surface'})
        section_container.pack(fill='x' if not fill_parent else 'both', expand=fill_parent, pady=(0, 2)) # 간격 더 줄임

        title_frame = tk.Frame(section_container, height=18) # 높이 더 줄임
        self.theme_manager.register_widget(title_frame, {'bg': 'primary'})
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)
        
        title_lbl = tk.Label(title_frame, text=title, font=('Segoe UI', 7, 'bold')) # 폰트 더 줄임
        self.theme_manager.register_widget(title_lbl, {'bg': 'primary', 'fg': 'white'})
        title_lbl.pack(side='left', padx=4, pady=1) # 패딩 더 줄임

        content_frame_outer = tk.Frame(section_container, relief='solid', bd=1)
        self.theme_manager.register_widget(content_frame_outer, {'bg': 'outline'}) # 테두리 색상
        content_frame_outer.pack(fill='both', expand=True, padx=0, pady=0)
        
        content_frame_inner = tk.Frame(content_frame_outer)
        self.theme_manager.register_widget(content_frame_inner, {'bg': 'white'}) # 내부 배경은 흰색 계열
        content_frame_inner.pack(fill='both', expand=True, padx=4, pady=3) # 내부 패딩 더 줄임
        return content_frame_inner

    def _create_file_section(self, parent):
        section = self._create_section_frame_styled(parent, "📁 파일 설정")
        
        excel_frame = tk.Frame(section)
        self.theme_manager.register_widget(excel_frame, {'bg': 'white'})
        excel_frame.pack(fill='x', pady=(0, 0)) # 간격 최소화
        
        excel_lbl = tk.Label(excel_frame, text="Excel 입력 파일:", font=('Segoe UI', 7, 'bold'))
        self.theme_manager.register_widget(excel_lbl, {'bg': 'white', 'fg': 'on_surface'})
        excel_lbl.pack(anchor='w')
        
        excel_input_frame = tk.Frame(excel_frame)
        self.theme_manager.register_widget(excel_input_frame, {'bg': 'white'})
        excel_input_frame.pack(fill='x', pady=(0,0)) # 패딩 최소화
        
        self.excel_entry = tk.Entry(excel_input_frame, textvariable=self.input_excel_path, font=('Segoe UI', 7), relief='solid', bd=1)
        self.theme_manager.register_widget(self.excel_entry, {'bg': 'white', 'fg': 'on_surface'})
        self.excel_entry.pack(side='left', fill='x', expand=True, padx=(0,1))
        
        excel_browse_btn = tk.Button(excel_input_frame, text="찾기", command=self.browse_input_excel, font=('Segoe UI', 6), relief='flat', cursor='hand2', width=4)
        self.theme_manager.register_widget(excel_browse_btn, {'bg': 'secondary', 'fg': 'white', 'activebackground':'dark'})
        excel_browse_btn.pack(side='right')

        # 출력 폴더
        output_frame = tk.Frame(section)
        self.theme_manager.register_widget(output_frame, {'bg': 'white'})
        output_frame.pack(fill='x', pady=(1,0)) # 간격 최소화
        output_lbl = tk.Label(output_frame, text="출력 폴더:", font=('Segoe UI', 7, 'bold'))
        self.theme_manager.register_widget(output_lbl, {'bg': 'white', 'fg': 'on_surface'})
        output_lbl.pack(anchor='w')
        output_input_frame = tk.Frame(output_frame)
        self.theme_manager.register_widget(output_input_frame, {'bg': 'white'})
        output_input_frame.pack(fill='x', pady=(0,0)) # 패딩 최소화
        self.output_entry = tk.Entry(output_input_frame, textvariable=self.output_folder_path, font=('Segoe UI', 7), relief='solid', bd=1)
        self.theme_manager.register_widget(self.output_entry, {'bg': 'white', 'fg': 'on_surface', 'relief': 'solid', 'bd': 1})
        self.output_entry.pack(side='left', fill='x', expand=True, padx=(0,1))
        output_browse_btn = tk.Button(output_input_frame, text="찾기", command=self.browse_output_folder, font=('Segoe UI', 6), relief='flat', cursor='hand2', width=4)
        self.theme_manager.register_widget(output_browse_btn, {'bg': 'secondary', 'fg': 'white', 'activebackground':'dark'})
        output_browse_btn.pack(side='right')

        # 출력 폴더 열기 버튼
        self.open_folder_btn = tk.Button(output_input_frame, text="📂", command=self.open_output_folder, font=('Segoe UI', 6), relief='flat', cursor='hand2', width=2)
        self.theme_manager.register_widget(self.open_folder_btn, {'bg': 'primary', 'fg': 'white', 'activebackground':'dark'})
        self.open_folder_btn.pack(side='left', padx=(1,0))

    def _create_coordinates_section(self, parent):
        section = self._create_section_frame_styled(parent, "🎯 좌표 및 영역 설정")
        
        click_frame = tk.Frame(section)
        self.theme_manager.register_widget(click_frame, {'bg': 'white'})
        click_frame.pack(fill='x', pady=(0,1)) # 간격 더 줄임
        click_lbl = tk.Label(click_frame, text="클릭 포인트:", font=('Segoe UI', 7, 'bold'))
        self.theme_manager.register_widget(click_lbl, {'bg': 'white', 'fg': 'on_surface'})
        click_lbl.pack(side='left')
        click_btn = tk.Button(click_frame, text="위치지정", command=self.relocate_clickpoint, font=('Segoe UI', 6), relief='flat', cursor='hand2', width=6)
        self.theme_manager.register_widget(click_btn, {'bg': 'accent', 'fg': 'white', 'activebackground':'dark'})
        click_btn.pack(side='right')

        areas = [
            ("전체 영역", self.relocate_allarea, 'danger'), # color_key 전달
            ("날짜 영역", self.relocate_datearea, 'primary'),
            ("금리 영역", self.relocate_ratearea, 'success')
        ]
        for area_name, func, color_key in areas:
            area_frame = tk.Frame(section)
            self.theme_manager.register_widget(area_frame, {'bg': 'white'})
            area_frame.pack(fill='x', pady=(0,1)) # 간격 더 줄임
            area_lbl = tk.Label(area_frame, text=f"{area_name}:", font=('Segoe UI', 7, 'bold'))
            self.theme_manager.register_widget(area_lbl, {'bg': 'white', 'fg': 'on_surface'})
            area_lbl.pack(side='left')
            area_btn = tk.Button(area_frame, text="영역지정", command=func, font=('Segoe UI', 6), relief='flat', cursor='hand2', width=6)
            # 버튼 색상은 테마 매니저를 통해 동적으로 설정되도록 color_key 사용
            self.theme_manager.register_widget(area_btn, {'bg': color_key, 'fg': 'white', 'activebackground':'dark'})
            area_btn.pack(side='right')

        preview_frame = tk.Frame(section)
        self.theme_manager.register_widget(preview_frame, {'bg': 'white'})
        preview_frame.pack(fill='x', pady=(1,0)) # 간격 더 줄임
        preview_all_btn = tk.Button(preview_frame, text="🔍 전체 영역 미리보기", command=self.show_area_preview, font=('Segoe UI', 7, 'bold'), relief='flat', cursor='hand2', width=22, pady=0) # 패딩 최소화
        self.theme_manager.register_widget(preview_all_btn, {'bg': 'warning', 'fg': 'white', 'activebackground':'dark'})
        preview_all_btn.pack(fill='x')

    def _create_timing_section(self, parent):
        section = self._create_section_frame_styled(parent, "⏱️ 타이밍 설정")
        
        timing_grid = tk.Frame(section)
        self.theme_manager.register_widget(timing_grid, {'bg': 'white'})
        timing_grid.pack(fill='x')

        left_timing = tk.Frame(timing_grid)
        self.theme_manager.register_widget(left_timing, {'bg': 'white'})
        left_timing.pack(side='left', fill='x', expand=True, padx=(0,2)) # 간격 더 줄임
        paste_lbl = tk.Label(left_timing, text="붙여넣기 딜레이(초):", font=('Segoe UI', 7, 'bold'))
        self.theme_manager.register_widget(paste_lbl, {'bg': 'white', 'fg': 'on_surface'})
        paste_lbl.pack(anchor='w')
        paste_entry = tk.Entry(left_timing, textvariable=self.paste_delay, font=('Segoe UI', 7), width=5, relief='solid', bd=1)
        self.theme_manager.register_widget(paste_entry, {'bg': 'white', 'fg': 'on_surface'})
        paste_entry.pack(fill='x', pady=(0,0)) # 패딩 최소화

        right_timing = tk.Frame(timing_grid)
        self.theme_manager.register_widget(right_timing, {'bg': 'white'})
        right_timing.pack(side='left', fill='x', expand=True)
        load_lbl = tk.Label(right_timing, text="로딩 딜레이(초):", font=('Segoe UI', 7, 'bold'))
        self.theme_manager.register_widget(load_lbl, {'bg': 'white', 'fg': 'on_surface'})
        load_lbl.pack(anchor='w')
        load_entry = tk.Entry(right_timing, textvariable=self.loading_delay, font=('Segoe UI', 7), width=5, relief='solid', bd=1)
        self.theme_manager.register_widget(load_entry, {'bg': 'white', 'fg': 'on_surface'})
        load_entry.pack(fill='x', pady=(0,0)) # 패딩 최소화

    def _create_options_section(self, parent):
        section = self._create_section_frame_styled(parent, "⚙️ 옵션 설정")
        
        # 상세 이미지 저장 체크박스
        save_img_cb = tk.Checkbutton(section, text="상세 이미지 저장 (영역별 개별 파일)", variable=self.save_detail_images, font=('Segoe UI', 7)) # 폰트 더 줄임
        self.theme_manager.register_widget(save_img_cb, {'bg': 'white', 'fg': 'on_surface', 'selectcolor': 'light', 'activebackground': 'white', 'activeforeground': 'on_surface'})
        save_img_cb.pack(anchor='w', pady=(0,2)) # 간격 최소화

        # 'KBP' 코드 건너뛰기 체크박스
        self.skip_kbp_var = tk.BooleanVar(value=self.settings_manager.get_advanced('skip_kbp_code', True)) # 기본값은 설정에서
        skip_kbp_cb = tk.Checkbutton(section, text="'KBP' 코드 건너뛰기 (빈 값으로 완료 처리)", variable=self.skip_kbp_var, font=('Segoe UI', 7), command=self.save_advanced_ui_to_settings) # 폰트 더 줄임, 변경 시 바로 저장
        self.theme_manager.register_widget(skip_kbp_cb, {'bg': 'white', 'fg': 'on_surface', 'selectcolor': 'light', 'activebackground': 'white', 'activeforeground': 'on_surface'})
        skip_kbp_cb.pack(anchor='w', pady=(0,2)) # 간격 최소화

        # Max Threads UI 제거됨 (conversation_summary 요청에 따라)

    def _create_preset_section(self, parent):
        section = self._create_section_frame_styled(parent, "💾 프리셋 관리")

        preset_load_frame = tk.Frame(section)
        self.theme_manager.register_widget(preset_load_frame, {'bg': 'white'})
        preset_load_frame.pack(fill='x', pady=(0,2)) # 간격 최소화
        preset_lbl = tk.Label(preset_load_frame, text="저장된 프리셋:", font=('Segoe UI', 7, 'bold')) # 폰트 더 줄임
        self.theme_manager.register_widget(preset_lbl, {'bg': 'white', 'fg': 'on_surface'})
        preset_lbl.pack(anchor='w')
        
        preset_control_frame = tk.Frame(preset_load_frame)
        self.theme_manager.register_widget(preset_control_frame, {'bg': 'white'})
        preset_control_frame.pack(fill='x', pady=(1,0)) # 패딩 최소화
        
        self.preset_combo = ttk.Combobox(preset_control_frame, state="readonly", font=('Segoe UI', 7), style="TCombobox") # 폰트 더 줄임
        self.preset_combo.pack(side='left', fill='x', expand=True, padx=(0,2)) # 패딩 최소화
        
        apply_preset_btn = tk.Button(preset_control_frame, text="적용", command=self.apply_selected_preset, font=('Segoe UI', 6), relief='flat', cursor='hand2', width=4) # 폰트와 크기 더 줄임
        self.theme_manager.register_widget(apply_preset_btn, {'bg': 'success', 'fg': 'white', 'activebackground':'dark'})
        apply_preset_btn.pack(side='right', padx=(0,2)) # 패딩 최소화
        
        delete_preset_btn = tk.Button(preset_control_frame, text="삭제", command=self.delete_selected_preset, font=('Segoe UI', 6), relief='flat', cursor='hand2', width=4) # 폰트와 크기 더 줄임
        self.theme_manager.register_widget(delete_preset_btn, {'bg': 'danger', 'fg': 'white', 'activebackground':'dark'})
        delete_preset_btn.pack(side='right')

        preset_save_frame = tk.Frame(section)
        self.theme_manager.register_widget(preset_save_frame, {'bg': 'white'})
        preset_save_frame.pack(fill='x', pady=(4,0)) # 간격 최소화
        save_preset_lbl = tk.Label(preset_save_frame, text="새 프리셋 저장:", font=('Segoe UI', 7, 'bold')) # 폰트 더 줄임
        self.theme_manager.register_widget(save_preset_lbl, {'bg': 'white', 'fg': 'on_surface'})
        save_preset_lbl.pack(anchor='w')
        
        save_control_frame = tk.Frame(preset_save_frame)
        self.theme_manager.register_widget(save_control_frame, {'bg': 'white'})
        save_control_frame.pack(fill='x', pady=(1,0)) # 패딩 최소화
        
        self.preset_name_entry = tk.Entry(save_control_frame, font=('Segoe UI', 7), relief='solid', bd=1) # 폰트 더 줄임
        self.theme_manager.register_widget(self.preset_name_entry, {'bg': 'white', 'fg': 'on_surface'})
        self.preset_name_entry.pack(side='left', fill='x', expand=True, padx=(0,2)) # 패딩 최소화
        self.preset_name_entry.insert(0, "새 프리셋 이름")
        
        save_preset_btn = tk.Button(save_control_frame, text="저장", command=self.save_current_as_preset, font=('Segoe UI', 6), relief='flat', cursor='hand2', width=4) # 폰트와 크기 더 줄임
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
            'skip_kbp_code': self.skip_kbp_var.get()
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

        if 'advanced' in settings_dict:
            self.settings_manager.data['advanced'].update(settings_dict['advanced'])

    def save_advanced_ui_to_settings(self):
        try:
            self.settings_manager.set_advanced('skip_kbp_code', self.skip_kbp_var.get())
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
            base_path = os.path.dirname(file_path)
            if not self.output_folder_path.get(): self.output_folder_path.set(base_path)

    def browse_output_folder(self):
        folder_path = filedialog.askdirectory(title="출력 폴더 선택")
        if folder_path: 
            cleaned_path = self.ocr_workflow_manager._clean_folder_path(folder_path)
            self.output_folder_path.set(cleaned_path)

    def open_output_folder(self):
        output_path = self.output_folder_path.get().strip()
        if not output_path:
            messagebox.showwarning("경고", "출력 폴더가 설정되지 않았습니다.")
            return
        
        try:
            cleaned_path = self.ocr_workflow_manager._clean_folder_path(output_path)
            
            if not os.path.exists(cleaned_path):
                if messagebox.askyesno("폴더 생성", f"폴더가 존재하지 않습니다.\n생성하시겠습니까?\n\n경로: {cleaned_path}"):
                    os.makedirs(cleaned_path, exist_ok=True)
                    self.logger.info(f"출력 폴더 생성됨: {cleaned_path}")
                else:
                    return
            
            system = platform.system()
            if system == "Windows":
                subprocess.run(['explorer', cleaned_path], check=False, timeout=10)
            elif system == "Darwin":
                if cleaned_path.startswith(("//", "\\\\")):
                    messagebox.showwarning("UNC 경로", "macOS에서는 UNC 네트워크 경로를 직접 열 수 없습니다.\nFinder에서 수동으로 연결하세요.")
                    return
                subprocess.run(['open', cleaned_path], check=False, timeout=10)
            else:
                if cleaned_path.startswith(("//", "\\\\")):
                    messagebox.showwarning("UNC 경로", "Linux에서는 UNC 네트워크 경로를 직접 열 수 없습니다.\n파일 매니저에서 수동으로 연결하세요.")
                    return
                subprocess.run(['xdg-open', cleaned_path], check=False, timeout=10)
            
            self.logger.info(f"출력 폴더 열기: {cleaned_path}")
        except subprocess.TimeoutExpired:
            messagebox.showerror("오류", "폴더 열기 시간 초과")
        except Exception as e:
            messagebox.showerror("오류", f"폴더를 열 수 없습니다: {e}")
            self.logger.error(f"폴더 열기 실패: {e}")

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
            self.message_queue.put(("log", message, "INFO"))

    def _on_work_complete(self, summary_message):
        self.logger.info("[_on_work_complete] 함수 호출됨")
        self.work_controller.reset()
        self.progress_tracker.hide()
        if hasattr(self, 'run_btn'): self.run_btn.config(text="🚀 OCR 시작 (F5)", state='normal')
        self.data_manager.current_processing_index = -1
        self.refresh_grid_ui()
        messagebox.showinfo("처리 완료", summary_message)
        self.quick_save_settings()

    def _on_work_stopped(self):
        self.work_controller.reset()
        self.progress_tracker.hide()
        if hasattr(self, 'run_btn'): self.run_btn.config(text="🚀 OCR 시작 (F5)", state='normal')
        self.data_manager.current_processing_index = -1
        self.refresh_grid_ui()
        messagebox.showinfo("중단됨", "작업이 사용자에 의해 중단되었습니다.")

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
        about_text = """📋 Check Capture OCR - V6
OCR 자동화 애플리케이션 (EasyOCR 기반)"""
        messagebox.showinfo("프로그램 정보", about_text, parent=self)

    def run_ocr_process(self):
        if self.work_controller.is_running:
            self.stop_processing_ui_initiated()
            return
        if not self._validate_inputs_for_ocr(): return

        self.work_controller.start_work()
        self.progress_tracker.show()
        if hasattr(self, 'run_btn'): self.run_btn.config(text="⏹️ 처리 중단 (F5)", state='normal')
        
        current_ui_settings = self.get_current_ui_settings()
        output_dir = self.output_folder_path.get().strip()
        save_details = self.save_detail_images.get()

        self.worker_thread = threading.Thread(
            target=self.ocr_workflow_manager.execute_ocr_workflow_threaded,
            args=(current_ui_settings, output_dir, save_details),
            daemon=True
        )
        self.worker_thread.start()

    def _validate_inputs_for_ocr(self):
        output_dir = self.output_folder_path.get().strip()
        if not self.data_manager.excel_data:
             messagebox.showwarning("경고", "처리할 데이터가 없습니다. Excel 파일을 로드하거나 데이터를 추가하세요.", parent=self)
             return False
        if not output_dir or not os.path.isdir(output_dir):
            messagebox.showwarning("경고", "유효한 Output 폴더를 지정하세요.", parent=self)
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
            self.refresh_grid_ui()
            messagebox.showinfo("성공", f"{loaded_rows}행의 데이터를 로드했습니다.", parent=self)

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

    def refresh_grid_ui(self):
        if not self.grid_tree: return
        for item in self.grid_tree.get_children(): self.grid_tree.delete(item)
        
        for i, row in enumerate(self.data_manager.excel_data):
            tags = []
            if i == self.data_manager.current_processing_index and self.work_controller.is_running : tags.append('processing')
            elif row['상태'] == '완료': tags.append('completed')
            elif any(err_keyword in row['상태'] for err_keyword in ['오류', '실패', '없음', '건너']): tags.append('error')
            
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
        item_id = self.grid_tree.identify_row(event.y)
        column_id = self.grid_tree.identify_column(event.x)
        if not item_id or not column_id: return

        col_index = int(column_id.replace('#','')) - 1
        col_name = self.grid_tree['columns'][col_index]
        row_index = self.grid_tree.index(item_id)

        if not (0 <= row_index < len(self.data_manager.excel_data)): return
        current_value = self.data_manager.excel_data[row_index].get(col_name, "")

        new_value = simpledialog.askstring(f"{col_name} 편집", f"새로운 값을 입력하세요 (현재: {current_value}):", parent=self)
        if new_value is not None:
            if self.data_manager.update_grid_cell_data(row_index, col_name, new_value):
                self.refresh_grid_ui()

    def show_context_menu_ui(self, event):
        if not self.grid_tree: return
        context_menu = tk.Menu(self, tearoff=0)
        self.theme_manager.register_widget(context_menu, {'bg': 'surface', 'fg': 'on_surface', 
                                                          'activebackground': 'primary', 'activeforeground': 'white'})

        context_menu.add_command(label="➕ 행 추가", command=self.add_empty_row_ui)
        context_menu.add_command(label="🗑️ 선택 행 삭제", command=self.delete_selected_rows_ui)
        context_menu.add_separator()
        context_menu.add_command(label="📋 선택 행 복사 (Ctrl+C)", command=self.copy_selected_rows_ui)
        context_menu.add_command(label="📝 클립보드에서 붙여넣기 (Ctrl+V)", command=self.paste_from_clipboard_ui)
        context_menu.add_separator()
        context_menu.add_command(label="🧹 전체 데이터 삭제", command=self.clear_all_data_ui)
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
            
    def quit_app(self):
        if self.work_controller.is_running:
            if messagebox.askyesno("확인", "작업이 진행 중입니다. 정말로 종료하시겠습니까?", parent=self):
                self.work_controller.stop_work()
                if self.worker_thread and self.worker_thread.is_alive():
                    self.worker_thread.join(timeout=2)
                self.destroy()
            else:
                return
        else:
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


if __name__ == "__main__":
    app = CheckCaptureOCRApp()
    app.protocol("WM_DELETE_WINDOW", app.quit_app)
    app.mainloop()
