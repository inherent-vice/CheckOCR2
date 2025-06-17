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
            print(f"설정 로드 오류: {e}") # 초기 로드 실패는 print로 처리
        return {}

    def save_settings(self):
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"설정 저장 오류: {e}") # 저장 실패는 print로 처리

    def save_preset(self, name, settings):
        self.data['presets'][name] = {
            'click_point': settings['click_point'],
            'all_area': settings['all_area'],
            'date_area': settings['date_area'],
            'rate_area': settings['rate_area'],
            'delays': settings['delays'],
            'save_detail_images': settings.get('save_detail_images', True),
            'advanced': settings.get('advanced', {}), # 고급 설정도 프리셋에 포함
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
            'ocr_languages': ['en'], # EasyOCR은 현재 영어 전용으로 고정됨
            'ocr_max_attempts': 1, # 현재 코드에서 직접 사용되지는 않음
            'ocr_detail_level': 0, # EasyOCR detail 파라미터 (0 또는 1)
            'click_interval': 0.1,
            'min_date_confidence': 0.0, # 현재 코드에서 직접 사용되지는 않음
            'min_rate_confidence': 0.0, # 현재 코드에서 직접 사용되지는 않음
            'ui_theme': 'modern_blue',
            'skip_kbp_code': True,
            'default_output_dir': "." # 기본 출력 디렉토리
        }

    def _get_optimal_thread_count(self): # 현재 사용되지 않음
        cpu_count = os.cpu_count() or 4
        return min(max(cpu_count, 2), 8)

    def get_advanced(self, key, default=None):
        # 기본값이 _get_default_advanced_settings에 정의되어 있다면 그것을 사용
        default_val_from_method = self._get_default_advanced_settings().get(key)
        if default is None and default_val_from_method is not None:
            default = default_val_from_method
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
        if widget: # widget이 None이 아닌지 확인
            self.themed_widgets[widget] = style_map

    def get_color(self, key, default=None):
        return self.colors.get(key, default if default is not None else '#000000')

    def apply_theme_to_all_widgets(self):
        """등록된 모든 위젯에 현재 테마 적용"""
        self.root_app.configure(bg=self.get_color('surface'))

        non_color_props = {'relief', 'bd', 'borderwidth', 'width', 'height', 'padx', 'pady', 
                           'state', 'cursor', 'font', 'justify', 'anchor', 'wrap'}

        for widget, style_map in list(self.themed_widgets.items()): # list()로 복사본 순회 (삭제 대비)
            if not widget or not widget.winfo_exists():
                if widget in self.themed_widgets: # 파괴된 위젯 확실히 제거
                    del self.themed_widgets[widget]
                continue

            config_options = {}
            for tk_prop, value in style_map.items():
                if tk_prop in non_color_props:
                    config_options[tk_prop] = value
                else:
                    config_options[tk_prop] = self.get_color(value)
            
            if config_options:
                try:
                    widget.configure(**config_options)
                except tk.TclError as e:
                    self.logger.warning(f"위젯 스타일 적용 오류 ({widget}): {e}")

        # ttk 스타일 업데이트
        s = ttk.Style()
        s.theme_use('clam') 

        # Treeview
        s.configure("Treeview", 
                    background=self.get_color('treeview_bg'), 
                    foreground=self.get_color('treeview_fg'),
                    fieldbackground=self.get_color('treeview_bg'),
                    font=('Segoe UI', 9))
        s.map("Treeview", background=[('selected', self.get_color('treeview_selected_bg'))],
                          foreground=[('selected', self.get_color('treeview_fg'))]) 
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
                    selectbackground=self.get_color('light'), 
                    selectforeground=self.get_color('on_surface'))
        s.map('TCombobox', fieldbackground=[('readonly', self.get_color('white'))])

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
        self.skip_current = False # 현재 아이템 건너뛰기 플래그 (현재 미사용, 필요시 활용)
        self.current_item = "" # 현재 처리 중인 아이템 정보 (로깅/표시용)
        self.stop_event = threading.Event()

    def start_work(self):
        self.is_stopped = False
        self.is_running = True
        self.skip_current = False
        self.stop_event.clear()

    def stop_work(self):
        self.is_stopped = True # 즉시 중단 상태로 변경
        self.is_running = False
        self.stop_event.set() # 스레드에 중단 신호
        return "작업이 중단되었습니다" # 메시지는 여기서 반환하지만, 실제 UI 표시는 큐를 통해

    def skip_current_item(self): # 현재 미사용
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
        self.theme_manager = theme_manager
        self.auto_close = auto_close

        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        overlay_bg = self.theme_manager.get_color('dark', 'black') 
        self.configure(bg=overlay_bg)
        self.attributes("-alpha", 0.7)

        self.canvas = tk.Canvas(self, bg=overlay_bg, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.draw_areas()

        if auto_close:
            self.after(3000, self.destroy_overlay) # destroy 대신 destroy_overlay 호출

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

        if "click_point" in self.areas_info and self.areas_info["click_point"]:
            x, y = self.areas_info["click_point"]
            r = 10
            self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=colors[0], outline=text_color, width=3)
            self.canvas.create_text(x, y-25, text=labels[0], fill=text_color, font=("Arial", 12, "bold"))

        area_keys = ["all_area", "date_area", "rate_area"]
        for i, key in enumerate(area_keys):
            if key in self.areas_info and self.areas_info[key] and len(self.areas_info[key]) == 4:
                x1, y1, x2, y2 = self.areas_info[key]
                if x1 is None or y1 is None or x2 is None or y2 is None: continue # 좌표 누락 시 건너뛰기
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
            self.destroy_overlay()

    def destroy_overlay(self): # 창 파괴 전 마스터 포커스 복원 시도
        if self.master and self.master.winfo_exists():
            self.master.focus_set()
        if self.winfo_exists():
            self.destroy()

############################################
# 드래그로 좌표를 지정하는 Overlay Window
############################################
class DragCaptureOverlay(tk.Toplevel):
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

        self.start_x, self.start_y = None, None
        self.rect_id = None
        self.x1, self.y1, self.x2, self.y2 = None, None, None, None

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.bind("<KeyPress-Escape>", lambda e: self.destroy_overlay()) 

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
        self.destroy_overlay()

    def destroy_overlay(self):
        if self.master and self.master.winfo_exists():
            self.master.focus_set()
        if self.winfo_exists():
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
        self.bind("<KeyPress-Escape>", lambda e: self.destroy_overlay())

    def on_click(self, event):
        self.click_x, self.click_y = event.x, event.y
        r = 5
        self.canvas.create_oval(self.click_x - r, self.click_y - r, self.click_x + r, self.click_y + r, fill=self.color, outline=self.color)
        self.after(100, self.destroy_overlay)

    def destroy_overlay(self):
        if self.master and self.master.winfo_exists():
            self.master.focus_set()
        if self.winfo_exists():
            self.destroy()

############################################
# 데이터 관리자
############################################
class DataManager:
    def __init__(self, app_ref, logger, message_queue):
        self.app = app_ref 
        self.logger = logger
        self.message_queue = message_queue
        self.excel_data = [] 
        self.current_processing_index = -1 # 현재 OCR 처리 중인 행의 인덱스

    def load_excel_to_grid_data(self, file_path):
        try:
            df = pd.read_excel(file_path, dtype=str) # 모든 데이터를 문자열로 읽기
            self.clear_all_data_internal() # 기존 데이터 초기화

            col_map = {}
            expected_cols = {'종목코드': ['종목코드', 'code', 'item code'],
                             '종목명': ['종목명', 'name', 'item name', '회사명']}
            df_cols_lower = {str(col).lower().strip(): str(col) for col in df.columns} # 컬럼명 공백 제거 및 소문자화

            for target_col, possible_names in expected_cols.items():
                for p_name in possible_names:
                    if p_name in df_cols_lower:
                        col_map[target_col] = df_cols_lower[p_name]
                        break
                if target_col not in col_map:
                    self.logger.warning(f"Excel 파일에 '{target_col}'에 해당하는 컬럼을 찾을 수 없습니다.")
                    col_map[target_col] = None # 해당 컬럼이 없음을 명시
            
            new_data = []
            for _, row in df.iterrows():
                item_code = ''
                item_name = ''
                if col_map.get('종목코드') and col_map['종목코드'] in row:
                    item_code = str(row[col_map['종목코드']]).strip()
                if col_map.get('종목명') and col_map['종목명'] in row:
                    item_name = str(row[col_map['종목명']]).strip()
                
                new_data.append({
                    '종목코드': item_code,
                    '종목명': item_name,
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
                # 첫 번째 열(종목코드)이라도 내용이 있어야 유효한 데이터로 간주
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
        # indices_to_delete는 이미 역순으로 정렬되어 전달됨을 가정
        for index in indices_to_delete: # sorted(indices_to_delete, reverse=True)는 호출부에서 처리
            if 0 <= index < len(self.excel_data):
                del self.excel_data[index]
    
    def clear_all_data_internal(self):
        self.excel_data.clear()
        self.current_processing_index = -1

    def update_grid_cell_data(self, row_index, col_name, new_value):
        if 0 <= row_index < len(self.excel_data):
            if col_name in self.excel_data[row_index]:
                self.excel_data[row_index][col_name] = new_value
                return True
            else:
                self.logger.warning(f"잘못된 컬럼명({col_name})으로 셀 업데이트 시도.")
                return False
        return False

    def get_row_for_copy(self, index):
        if 0 <= index < len(self.excel_data):
            row = self.excel_data[index]
            # 모든 필드가 문자열인지 확인하고, 누락된 경우 빈 문자열로 대체
            return f"{row.get('종목코드','')}\t{row.get('종목명','')}\t{row.get('날짜','')}\t{row.get('금리','')}\t{row.get('상태','')}"
        return ""

    def export_grid_to_excel_data(self, output_dir, input_file_path_str):
        if not self.excel_data:
            self.message_queue.put(("log", "내보낼 데이터가 없습니다.", "INFO"))
            return

        base_name = os.path.basename(input_file_path_str) if input_file_path_str else "ocr_results"
        new_file_name = os.path.splitext(base_name)[0] + '_updated.xlsx'
        new_file_path = os.path.join(output_dir, new_file_name)

        try:
            self.logger.debug(f"[export_grid_to_excel_data] 내보내기 직전 데이터: {self.excel_data}")
            
            df_export = pd.DataFrame(self.excel_data)
            # 컬럼 순서 및 존재 여부 확인
            export_cols = ['종목코드', '종목명', '날짜', '금리', '상태']
            df_export = df_export.reindex(columns=export_cols).fillna('') # 누락된 컬럼은 빈 값으로 채움
            
            # Excel 내보내기 시 '중단됨' 상태를 빈 문자열로 변경 (선택적)
            # df_export['상태'] = df_export['상태'].apply(lambda x: '' if x == '중단됨' else x)

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
        self.app = app_ref 
        self.logger = logger
        self.message_queue = message_queue
        self.work_controller = work_controller
        self.settings_manager = settings_manager
        self.data_manager = data_manager 
        self.ocr_reader = None

    def initialize_ocr(self):
        try:
            self.logger.info("EasyOCR 초기화 중... (영어 전용)")
            gpu_enabled = False # GPU 사용 비활성화로 고정 (사용자 설정 제거)
            languages = ['en'] # 영어로 고정
            self.ocr_reader = easyocr.Reader(languages, gpu=gpu_enabled)
            self.logger.info(f"EasyOCR 초기화 완료 - 언어: {languages}, GPU: {gpu_enabled}")
        except Exception as e:
            self.logger.error(f"EasyOCR 초기화 실패: {e}")
            try: # CPU 폴백 시도
                self.logger.info("기본 모드(영어, CPU)로 EasyOCR 재초기화 시도...")
                self.ocr_reader = easyocr.Reader(['en'], gpu=False)
                # GPU 관련 설정을 settings_manager에서 업데이트할 필요는 없음 (이미 비활성화 고정)
                self.logger.info("EasyOCR 영어 모드(CPU)로 초기화 완료.")
            except Exception as e2:
                self.message_queue.put(("error_messagebox", "치명적 오류", f"OCR 엔진 초기화에 완전히 실패했습니다: {e2}"))
                self.logger.critical(f"OCR 엔진 초기화 완전 실패: {e2}")
                self.ocr_reader = None

    def execute_ocr_workflow_threaded(self, ui_settings, output_dir_str, save_detail_images_bool):
        try:
            if not self.ocr_reader:
                self.message_queue.put(("error_messagebox", "오류", "OCR 엔진이 초기화되지 않았습니다."))
                self.message_queue.put(("stopped", None)) # UI 상태를 중단으로 변경
                return

            paste_d = ui_settings['delays']['paste']
            load_d = ui_settings['delays']['loading']
            coords = {
                'click': ui_settings['click_point'],
                'all': ui_settings['all_area'],
                'date': ui_settings['date_area'],
                'rate': ui_settings['rate_area'],
            }
            
            input_excel_file = self.app.input_excel_path.get() # 메인 앱의 경로 참조
            base_name = os.path.splitext(os.path.basename(input_excel_file))[0] if input_excel_file else "ocr_images"
            save_folder = os.path.join(output_dir_str, base_name)
            os.makedirs(save_folder, exist_ok=True)

            total_items = len(self.data_manager.excel_data)
            processed_count = 0 # 성공적으로 '완료'된 항목 수

            for grid_index, row_data in enumerate(self.data_manager.excel_data):
                if self.work_controller.is_stopped: # 중단 플래그 확인
                    self.message_queue.put(("log", "사용자가 처리를 중단했습니다.", "INFO"))
                    # self.message_queue.put(("stopped", None)) # 이미 stop_work에서 처리되거나, 루프 종료 후 처리
                    break # 루프 즉시 중단

                stock_code = str(row_data.get('종목코드', '')).strip()
                # stock_name = str(row_data.get('종목명', '')).strip() # 현재 미사용
                
                self.data_manager.current_processing_index = grid_index
                self.message_queue.put(("grid_update", ("processing", grid_index)))
                
                skip_kbp = self.settings_manager.get_advanced('skip_kbp_code', True)
                if skip_kbp and stock_code.lower().startswith('kbp'):
                    self.message_queue.put(("log", f"[{stock_code}] 'kbp'로 시작, 건너뛰고 완료 처리.", "INFO"))
                    self.data_manager.excel_data[grid_index]['날짜'] = '' # 데이터 직접 업데이트
                    self.data_manager.excel_data[grid_index]['금리'] = ''
                    self.message_queue.put(("grid_update", ("complete", grid_index, '', '', "완료")))
                    processed_count += 1
                    continue

                if not stock_code:
                    self.message_queue.put(("log", f"행 {grid_index+1}: 종목코드가 없어 건너뜁니다.", "WARNING"))
                    self.message_queue.put(("grid_update", ("error", grid_index, "종목코드 없음")))
                    continue

                # self.work_controller.skip_current = False # 현재 미사용 플래그
                try:
                    date_img_src, rate_img_src = self._capture_screenshots_internal(
                        stock_code, save_folder, coords, paste_d, load_d, save_detail_images_bool
                    )
                    
                    if self.work_controller.is_stopped: break # 캡처 중 중단 확인

                    if date_img_src is None or rate_img_src is None: # 캡처 실패 (이미 로그 처리됨)
                        if not self.work_controller.is_stopped: # 중단된 게 아니라면 오류 처리
                             self.message_queue.put(("grid_update", ("error", grid_index, "캡처 실패")))
                        continue 

                    date_result, rate_result = self._process_single_ocr_internal(date_img_src, rate_img_src, save_detail_images_bool)
                    
                    if self.work_controller.is_stopped: break # OCR 처리 중 중단 확인

                    status_msg = "완료" # 기본 완료, 유효성 검사는 분석 함수에서 처리
                    self.message_queue.put(("grid_update", ("complete", grid_index, date_result, rate_result, status_msg)))
                    self.message_queue.put(("log", f"[{stock_code}] {status_msg} - 날짜: '{date_result}', 금리: '{rate_result}'", "SUCCESS"))
                    processed_count += 1

                except Exception as e_item:
                    if self.work_controller.is_stopped: break # 예외 처리 중 중단 확인
                    self.message_queue.put(("log", f"종목 {stock_code} 처리 중 오류: {e_item}", "ERROR"))
                    self.logger.exception(f"종목 {stock_code} 처리 중 예외 발생")
                    self.message_queue.put(("grid_update", ("error", grid_index, "처리 오류")))
                    continue
            # --- 루프 종료 ---

            if self.work_controller.is_stopped:
                self.logger.info("[OCRWorkflowManager] 작업 루프 중단됨 (사용자 또는 오류).")
                self.message_queue.put(("stopped", None)) # 최종 중단 메시지 (UI 상태 정리용)
            else: # 모든 항목 순회 완료
                self.logger.info("[OCRWorkflowManager] 모든 항목 처리 완료.")
                self.message_queue.put(("finalize_export_and_complete", output_dir_str, self.app.input_excel_path.get(), processed_count, total_items))
        
        except Exception as e_workflow: # 워크플로우 전체에서 예외 발생 시
            self.logger.exception("OCR 전체 워크플로우에서 예외 발생")
            self.message_queue.put(("log", f"OCR 전체 워크플로우 오류: {e_workflow}", "ERROR"))
            if not self.work_controller.is_stopped: # 이미 중단된 상태가 아니라면
                self.work_controller.stop_work() # 컨트롤러 상태 변경 및 이벤트 설정
            self.message_queue.put(("stopped", None)) # UI 중단 처리 요청


    def _capture_screenshots_internal(self, stock_code, save_folder, coords, paste_d, load_d, save_details):
        if self.work_controller.stop_event.is_set(): return None, None 
        
        try:
            pyperclip.copy(stock_code)
        except pyperclip.PyperclipException as e:
            self.message_queue.put(("log", f"클립보드 복사 실패: {e}. Pyperclip 설정 확인 필요.", "ERROR"))
            # 클립보드 오류 시 pyautogui 작업 시도하지 않고 실패 반환
            return None, None

        pyautogui.click(x=coords['click'][0], y=coords['click'][1], clicks=2, interval=self.settings_manager.get_advanced('click_interval', 0.1))
        
        if self.work_controller.stop_event.wait(timeout=paste_d): return None, None 
        
        pyautogui.hotkey('ctrl', 'v')

        if self.work_controller.stop_event.wait(timeout=load_d): return None, None

        safe_stock_code = re.sub(r'[\\/*?:"<>|]', "_", stock_code)
        date_img_pil, rate_img_pil = None, None # Pillow 이미지 객체 저장용
        date_img_path, rate_img_path = None, None # 저장 경로 (save_details=True일 때만 사용)

        # 전체 영역 (항상 저장)
        x1_all, y1_all, x2_all, y2_all = coords['all']
        if not (x1_all is not None and y1_all is not None and x2_all is not None and y2_all is not None and x2_all > x1_all and y2_all > y1_all):
            self.message_queue.put(("log", f"[{safe_stock_code}] 전체 영역 좌표 오류: {coords['all']}", "ERROR"))
            return None, None # 전체 영역 캡처 실패 시 하위 영역도 의미 없음
        screenshot_all = pyautogui.screenshot(region=(x1_all, y1_all, x2_all - x1_all, y2_all - y1_all))
        allarea_path = os.path.join(save_folder, f"{safe_stock_code}.png")
        screenshot_all.save(allarea_path)
        self.message_queue.put(("log", f"전체 영역 이미지 저장: {allarea_path}", "DEBUG")) # DEBUG 레벨로 변경

        # 날짜 영역
        x1_date, y1_date, x2_date, y2_date = coords['date']
        if not (x1_date is not None and y1_date is not None and x2_date is not None and y2_date is not None and x2_date > x1_date and y2_date > y1_date):
            self.message_queue.put(("log", f"[{safe_stock_code}] 날짜 영역 좌표 오류: {coords['date']}", "WARNING"))
        else:
            date_img_pil = pyautogui.screenshot(region=(x1_date, y1_date, x2_date - x1_date, y2_date - y1_date))
            if save_details:
                date_img_path = os.path.join(save_folder, f"{safe_stock_code}_date.png")
                date_img_pil.save(date_img_path)
                self.message_queue.put(("log", f"날짜 영역 이미지 저장: {date_img_path}", "DEBUG"))

        # 금리 영역
        x1_rate, y1_rate, x2_rate, y2_rate = coords['rate']
        if not (x1_rate is not None and y1_rate is not None and x2_rate is not None and y2_rate is not None and x2_rate > x1_rate and y2_rate > y1_rate):
            self.message_queue.put(("log", f"[{safe_stock_code}] 금리 영역 좌표 오류: {coords['rate']}", "WARNING"))
        else:
            rate_img_pil = pyautogui.screenshot(region=(x1_rate, y1_rate, x2_rate - x1_rate, y2_rate - y1_rate))
            if save_details:
                rate_img_path = os.path.join(save_folder, f"{safe_stock_code}_rate.png")
                rate_img_pil.save(rate_img_path)
                self.message_queue.put(("log", f"금리 영역 이미지 저장: {rate_img_path}", "DEBUG"))
        
        # 반환 값: 저장 경로(save_details=True) 또는 Pillow 객체(save_details=False)
        return date_img_path if save_details else date_img_pil, \
               rate_img_path if save_details else rate_img_pil


    def _process_single_ocr_internal(self, date_img_src, rate_img_src, save_details):
        date_result, rate_result = "", ""
        try:
            if date_img_src: # Pillow 객체 또는 경로 문자열일 수 있음
                date_result = self._extract_text_with_ocr_attempts_internal(date_img_src, self._analyze_date_results_internal, "날짜")
            if rate_img_src:
                rate_result = self._extract_text_with_ocr_attempts_internal(rate_img_src, self._analyze_rate_results_internal, "금리")
        except Exception as e:
            self.message_queue.put(("log", f"단일 OCR 처리 중 오류: {e}", "ERROR"))
            self.logger.exception("단일 OCR 처리 중 예외 발생")
        return date_result, rate_result

    def _extract_text_with_ocr_attempts_internal(self, image_source, analysis_function, field_name):
        if self.work_controller.stop_event.is_set(): return ""
        try:
            if isinstance(image_source, str): # 경로 문자열인 경우
                if not os.path.exists(image_source):
                    self.message_queue.put(("log", f"{field_name} 이미지 파일 없음: {image_source}", "WARNING"))
                    return ""
                img_array = np.array(Image.open(image_source))
            elif isinstance(image_source, Image.Image): # Pillow 이미지 객체인 경우
                 img_array = np.array(image_source)
            else: # 알 수 없는 타입
                self.message_queue.put(("log", f"{field_name} 이미지 소스 타입 오류: {type(image_source)}", "ERROR"))
                return ""

            if img_array is None or img_array.size == 0:
                self.message_queue.put(("log", f"{field_name} 이미지가 비어있거나 로드 실패.", "WARNING"))
                return ""
                
            ocr_results = self.ocr_reader.readtext(img_array, detail=self.settings_manager.get_advanced('ocr_detail_level', 0))
            
            if self.settings_manager.get_advanced('ocr_detail_level', 0) == 1: # detail=1 이면 결과가 다름
                all_text = " ".join([res[1] for res in ocr_results]) if ocr_results else ""
            else: # detail=0 (기본값)
                all_text = " ".join(ocr_results) if ocr_results else ""

            self.message_queue.put(("log", f"[{field_name}] 원본 OCR 결과: '{all_text}'", "DEBUG"))
            return analysis_function(all_text, field_name)
        except Exception as e:
            self.message_queue.put(("log", f"{field_name} 추출 중 오류: {e}", "ERROR"))
            self.logger.exception(f"{field_name} 추출 중 예외 발생")
            return ""
        # 임시 파일 삭제 로직은 _capture_screenshots_internal에서 save_details 플래그로 제어하므로 여기서 불필요

    def _analyze_date_results_internal(self, raw_text, field_name="날짜"):
        if not raw_text or not raw_text.strip():
            self.message_queue.put(("log", f"[{field_name}] 분석할 텍스트가 비어있습니다.", "DEBUG"))
            return ""
        self.message_queue.put(("log", f"[{field_name}] 날짜 분석 원본: '{raw_text}'", "DEBUG"))
        cleaned_text = self._clean_date_text_internal(raw_text)
        if self._is_valid_date_format_internal(cleaned_text):
            self.message_queue.put(("log", f"[{field_name}] 유효한 날짜 추출: '{cleaned_text}'", "DEBUG"))
            return cleaned_text
        else:
            self.message_queue.put(("log", f"[{field_name}] 유효하지 않은 날짜 형식: '{cleaned_text}' (원본: '{raw_text}')", "DEBUG"))
            return "" 

    def _analyze_rate_results_internal(self, raw_text, field_name="금리"):
        if not raw_text or not raw_text.strip():
            self.message_queue.put(("log", f"[{field_name}] 분석할 텍스트가 비어있습니다.", "DEBUG"))
            return ""
        self.message_queue.put(("log", f"[{field_name}] 금리 분석 원본: '{raw_text}'", "DEBUG"))
        cleaned_text = self._clean_rate_text_internal(raw_text)
        if self._is_valid_rate_format_internal(cleaned_text):
            self.message_queue.put(("log", f"[{field_name}] 유효한 금리 추출: '{cleaned_text}'", "DEBUG"))
            return cleaned_text
        else:
            self.message_queue.put(("log", f"[{field_name}] 유효하지 않은 금리 형식: '{cleaned_text}' (원본: '{raw_text}')", "DEBUG"))
            return ""

    def _is_valid_date_format_internal(self, date_str):
        return bool(re.fullmatch(r'\d{4}/\d{2}/\d{2}', date_str))

    def _is_valid_rate_format_internal(self, rate_str):
        # 소수점 포함 숫자 (예: 3.500) 또는 정수 (예: 3) 허용하도록 수정 고려
        # 현재는 소수점 필수: \d+\.\d+
        return bool(re.fullmatch(r'\d+\.\d{1,3}', rate_str)) # 소수점 1~3자리 허용


    def _clean_date_text_internal(self, text):
        # 공백, '-', '.' 등을 '/'로 대체 시도 후 숫자만 추출
        text = text.replace('.', '/').replace('-', '/')
        cleaned = re.sub(r'[^\d/]', '', text) # 숫자와 /만 남김
        
        # "YYYY/MM/DD" 패턴 직접 찾기
        match = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})', cleaned)
        if match:
            year, month, day = match.groups()
            return f"{year}/{month.zfill(2)}/{day.zfill(2)}"

        # 숫자만 있는 경우 (YYYYMMDD 또는 YYMMDD)
        digits_only = re.sub(r'[^\d]', '', cleaned)
        if len(digits_only) == 8: # YYYYMMDD
            return f"{digits_only[:4]}/{digits_only[4:6]}/{digits_only[6:]}"
        elif len(digits_only) == 6: # YYMMDD
            year_prefix = "20" if int(digits_only[:2]) < 70 else "19" 
            return f"{year_prefix}{digits_only[:2]}/{digits_only[2:4]}/{digits_only[4:]}"
        
        # 기타 복잡한 케이스 (예: 20241 1 -> 2024/01/01) - 추가 정제 로직 필요시 여기에
        # 예시: "2024 1 1", "20241 1" 등 공백이 포함된 경우
        parts = re.findall(r'\d+', cleaned) # 숫자 덩어리들 추출
        if len(parts) == 3: # YYYY, M, D 또는 YYYY, MM, DD
            if len(parts[0]) == 4 and 1 <= len(parts[1]) <= 2 and 1 <= len(parts[2]) <= 2:
                 return f"{parts[0]}/{parts[1].zfill(2)}/{parts[2].zfill(2)}"
        if len(parts) == 1 and len(parts[0]) == 7 and parts[0].startswith('202'): # 202YMDD (2024101)
            # 2024101 -> 2024/01/01 (M이 한자리)
            # 20241101 -> 2024/11/01 (MM이 두자리 - 이 경우는 len 8에서 처리됨)
            year_part = parts[0][:4]
            month_part = parts[0][4]
            day_part = parts[0][5:]
            return f"{year_part}/{month_part.zfill(2)}/{day_part.zfill(2)}"


        return text # 정제 실패 시 원본 반환 (분석 함수에서 최종 검증)

    def _clean_rate_text_internal(self, text):
        # % 제거, 공백 제거, 쉼표를 점으로, 가운데 점을 점으로
        cleaned = text.replace('%','').replace(' ','').replace(',','.').replace('·','.')
        # 숫자와 점 이외의 문자 제거
        cleaned = re.sub(r'[^\d.]', '', cleaned)
        
        # 점이 여러 개 있는 경우, 첫 번째 점만 남기고 나머지는 제거 (예: 3.5.0 -> 3.50)
        if cleaned.count('.') > 1:
            parts = cleaned.split('.')
            cleaned = parts[0] + '.' + ''.join(parts[1:])
        
        # 유효한 소수점 형식인지 확인 (숫자.숫자)
        if re.fullmatch(r'\d+\.\d+', cleaned):
            try:
                val = float(cleaned)
                return f"{val:.3f}" # 소수점 3자리로 포맷팅
            except ValueError: 
                return cleaned # float 변환 실패 시 정제된 문자열 반환
        # 정수 형태이지만 소수점으로 변환 가능한 경우 (예: 35 -> 3.500)
        elif re.fullmatch(r'\d+', cleaned) and 1 <= len(cleaned) <= 5 : # 1자리도 허용 (예: 3 -> 3.000)
            try:
                if len(cleaned) == 1: # 3 -> 3.000
                    return f"{cleaned}.000"
                if len(cleaned) == 2: # 35 -> 3.500
                    return f"{cleaned[0]}.{cleaned[1]}00"
                elif len(cleaned) == 3: # 350 -> 3.500 (300 -> 3.000)
                    return f"{cleaned[0]}.{cleaned[1:]}0" if cleaned[1:] != "00" else f"{cleaned[0]}.000"
                elif len(cleaned) == 4: # 3500 -> 3.500
                    return f"{cleaned[0]}.{cleaned[1:]}"
                elif len(cleaned) == 5: # 12500 -> 12.500
                    return f"{cleaned[:2]}.{cleaned[2:]}"
            except: pass # 변환 실패 시 아래 cleaned 반환
        return cleaned # 위 조건에 맞지 않으면 원래 정제된 문자열 반환

    def _clean_folder_path(self, path: Optional[str]) -> str: # settings_manager에서 가져옴
        if not path:
            # settings_manager가 None일 수 있으므로 직접 기본값 사용
            return "." 
        
        cleaned_path = str(path).strip()
        # Windows UNC 경로 핸들링 (예: \\server\share)
        if platform.system() == "Windows" and cleaned_path.startswith("\\\\"):
            # 추가적인 정규화는 os.path.normpath에 맡기되, UNC 특성 유지 시도
            # os.path.normpath는 \\?\UNC\server\share 형태로 변경할 수 있음
            return os.path.normpath(cleaned_path)

        # 일반 경로 또는 비 Windows UNC (예: //server/share)
        # 모든 역슬래시를 슬래시로 변경 후 중복 슬래시 제거
        cleaned_path = cleaned_path.replace("\\", "/")
        while "//" in cleaned_path:
            cleaned_path = cleaned_path.replace("//", "/")
        
        return os.path.normpath(cleaned_path)


############################################
# 메인 GUI
############################################
class CheckCaptureOCRApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("📊 Check Capture OCR V6.1 (Optimized)")
        self.geometry("1200x750")
        self.resizable(True, True)
        self.minsize(1000, 600)
        

        self.message_queue = queue.Queue()
        self.logger = setup_logging(self.message_queue)
        
        self.settings_manager = UnifiedSettingsManager()
        self.theme_manager = ThemeManager(self) # self(CheckCaptureOCRApp)를 먼저 전달
        self.work_controller = WorkController()
        self.data_manager = DataManager(self, self.logger, self.message_queue)
        self.ocr_workflow_manager = OCRWorkflowManager(self, self.logger, self.message_queue, self.work_controller, self.settings_manager, self.data_manager)
        
        self.worker_thread = None

        # UI 변수들
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
        # self.confidence_threshold = tk.DoubleVar(value=20.0) # 현재 미사용
        self.theme_var = tk.StringVar()
        self.skip_kbp_var = tk.BooleanVar() # 초기값은 load_last_settings에서 설정

        self.grid_tree = None
        self.log_text_widget = None

        self.ocr_workflow_manager.initialize_ocr() # OCR 엔진 초기화
        self._build_ui() # UI 구성
        self._setup_keyboard_shortcuts() # 단축키 설정
        self.center_window() # 창 중앙 정렬 (UI 빌드 후)
        self.check_queue() # 메시지 큐 폴링 시작
        self.load_last_settings() # 마지막 설정 로드 (UI 변수 업데이트 포함)
        self.theme_manager.apply_theme_to_all_widgets() # 테마 적용 (설정 로드 후)

        self.protocol("WM_DELETE_WINDOW", self.quit_app) # 종료 프로토콜 설정


    def center_window(self):
        self.update_idletasks() # UI 업데이트 강제하여 정확한 크기 얻기
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = self.winfo_width()
        window_height = self.winfo_height()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")

    def _setup_keyboard_shortcuts(self):
        self.focus_set() # 메인 윈도우에 포커스 설정
        self.bind_all('<Control-s>', lambda e: self.quick_save_settings())
        self.bind_all('<Control-l>', lambda e: self.load_last_settings())
        self.bind_all('<Control-o>', lambda e: self.load_excel_to_grid()) # 파일 로드 단축키
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
            while True: # 큐에 메시지가 없을 때까지 반복 처리
                msg_type, *data = self.message_queue.get_nowait()
                
                if msg_type == "log":
                    message, level_str = (data[0], data[1]) if len(data) >= 2 else (data[0] if data else "알 수 없는 로그", "INFO")
                    level = getattr(logging, level_str.upper(), logging.INFO)
                    self.logger.log(level, message) # 실제 로거에 기록 (파일, 콘솔)
                elif msg_type == "log_display": # Tkinter UI 로거 핸들러가 보낸 메시지
                    level_name, formatted_message = data[0], data[1]
                    self._update_log_text_widget(formatted_message, level_name)
                elif msg_type == "error_messagebox":
                    title, message = data[0], data[1]
                    messagebox.showerror(title, message, parent=self)
                elif msg_type == "grid_update":
                    self._handle_grid_update(data[0]) # data[0]이 실제 업데이트 정보 튜플
                elif msg_type == "stopped":
                    self._on_work_stopped() # 작업 중단 시 UI 및 상태 정리
                elif msg_type == "finalize_export_and_complete":
                    if len(data) == 4:
                        output_dir, input_path, processed_count, total_items = data
                        summary = self._generate_ocr_summary_internal(processed_count, total_items)
                        self._finalize_export_and_complete(output_dir, input_path, summary)
                    else:
                        self.logger.error(f"잘못된 finalize_export_and_complete 메시지 형식: {data}")
                # 'complete' 메시지 타입은 finalize_export_and_complete로 통합됨

        except queue.Empty:
            pass # 큐가 비었으면 통과
        except Exception as e:
            self.logger.error(f"메시지 큐 처리 중 예외: {e}", exc_info=True)
        
        check_interval = 50 if self.work_controller.is_running else 100
        self.after(check_interval, self.check_queue)


    def _update_log_text_widget(self, message, level_name="INFO"):
        if self.log_text_widget and self.log_text_widget.winfo_exists():
            self.log_text_widget.config(state='normal')
            tag = level_name.upper() # 태그 이름은 대문자로 통일
            # 태그가 정의되지 않았으면 기본 태그 사용 (예: INFO)
            # refresh_grid_tags에서 정의된 태그 외에는 기본 색상으로 표시됨
            self.log_text_widget.insert(tk.END, f"{message}\n", (tag,)) # 태그를 튜플로 전달
            self.log_text_widget.see(tk.END)
            self.log_text_widget.config(state='disabled')

    def _build_ui(self):
        self.configure(bg=self.theme_manager.get_color('surface'))
        self._create_menu()
        self._create_simple_toolbar() # 툴바 먼저 생성

        # 메인 컨테이너 설정
        self.grid_rowconfigure(0, weight=0) # 툴바 영역
        self.grid_rowconfigure(1, weight=1) # 메인 컨텐츠 영역
        self.grid_columnconfigure(0, weight=1)

        main_container = tk.Frame(self)
        self.theme_manager.register_widget(main_container, {'bg': 'surface'})
        main_container.grid(row=1, column=0, sticky='nsew', padx=0, pady=0)

        main_container.grid_rowconfigure(0, weight=1) # 모든 패널이 포함될 단일 행
        main_container.grid_columnconfigure(0, weight=0, minsize=280) # 좌측 패널
        main_container.grid_columnconfigure(1, weight=6) # 중앙 패널 (더 많은 공간 할당)
        main_container.grid_columnconfigure(2, weight=1, minsize=200) # 우측 로그 패널

        # 패널 생성
        left_panel = tk.Frame(main_container)
        self.theme_manager.register_widget(left_panel, {'bg': 'surface'})
        left_panel.grid(row=0, column=0, sticky='nsew', padx=(5, 2), pady=5)

        center_panel = tk.Frame(main_container)
        self.theme_manager.register_widget(center_panel, {'bg': 'surface'})
        center_panel.grid(row=0, column=1, sticky='nsew', padx=3, pady=5)

        right_panel = tk.Frame(main_container)
        self.theme_manager.register_widget(right_panel, {'bg': 'surface'})
        right_panel.grid(row=0, column=2, sticky='nsew', padx=(2, 5), pady=5)

        # 패널 내용 채우기
        self._create_left_panel_content(left_panel)
        self._create_center_excel_grid(center_panel)
        self._create_right_panel_content(right_panel)

        # Tkinter 로거 핸들러 추가 (log_text_widget 생성 후)
        if self.log_text_widget:
            tkinter_handler = TkinterLogHandler(self.log_text_widget, self.message_queue)
            # 핸들러 추가 전 포맷터 설정
            tkinter_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S'))
            self.logger.addHandler(tkinter_handler)


    def _create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="파일", menu=file_menu)
        file_menu.add_command(label="Excel 파일 로드 (Ctrl+O)", command=self.load_excel_to_grid, accelerator="Ctrl+O")
        file_menu.add_command(label="Excel 파일 선택...", command=self.browse_input_excel)
        file_menu.add_command(label="출력 폴더 선택...", command=self.browse_output_folder)
        file_menu.add_command(label="출력 폴더 열기", command=self.open_output_folder)
        file_menu.add_separator()
        file_menu.add_command(label="종료 (Alt+F4)", command=self.quit_app, accelerator="Alt+F4")

        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="설정", menu=settings_menu)
        settings_menu.add_command(label="현재 설정 저장 (Ctrl+S)", command=self.quick_save_settings, accelerator="Ctrl+S")
        settings_menu.add_command(label="마지막 설정 불러오기 (Ctrl+L)", command=self.load_last_settings, accelerator="Ctrl+L")
        settings_menu.add_separator()
        # 고급 설정 관련 메뉴는 필요시 추가 (예: 고급 설정 창 열기, 기본값 복원 등)
        settings_menu.add_command(label="고급 설정 초기화", command=self.reset_advanced_settings_and_ui)


        preview_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="미리보기", menu=preview_menu)
        preview_menu.add_command(label="설정 영역 미리보기", command=self.show_area_preview)

        run_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="실행", menu=run_menu)
        run_menu.add_command(label="OCR 시작/중단 (F5)", command=self.handle_f5_key, accelerator="F5")
        run_menu.add_command(label="처리 중단 (Esc)", command=self.stop_processing_ui_initiated, accelerator="Esc")

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="도움말", menu=help_menu)
        help_menu.add_command(label="키보드 단축키 (F1)", command=self.show_shortcuts, accelerator="F1")
        help_menu.add_command(label="프로그램 정보", command=self.show_about)


    def _create_simple_toolbar(self):
        toolbar = tk.Frame(self, height=35) 
        self.theme_manager.register_widget(toolbar, {'bg': 'primary'})
        toolbar.grid(row=0, column=0, sticky='ew', padx=0, pady=0) # grid 사용
        toolbar.pack_propagate(False) # 높이 고정
        
        title_lbl = tk.Label(toolbar, text="📊 Check Capture OCR V6.1", font=('Segoe UI', 11, 'bold'))
        self.theme_manager.register_widget(title_lbl, {'bg': 'primary', 'fg': 'white'})
        title_lbl.pack(side='left', padx=8, pady=6)
        
        # 중앙 컨트롤 그룹 (실행/중단 버튼)
        center_controls_container = tk.Frame(toolbar)
        self.theme_manager.register_widget(center_controls_container, {'bg': 'primary'})
        # pack을 사용하여 툴바 내에서 중앙 정렬 효과 (expand=True로 공간 차지 후 내부에서 anchor)
        center_controls_container.pack(side='left', expand=True, fill='none') 

        controls_frame = tk.Frame(center_controls_container)
        self.theme_manager.register_widget(controls_frame, {'bg': 'primary'})
        controls_frame.pack(anchor='center') # 실제 버튼들을 담는 프레임

        self.run_btn = tk.Button(controls_frame, text="🚀 OCR 시작 (F5)", command=self.run_ocr_process, font=('Segoe UI', 10, 'bold'), relief='flat', cursor='hand2', padx=5, pady=2)
        self.theme_manager.register_widget(self.run_btn, {'bg': 'success', 'fg': 'white', 'activebackground':'dark', 'activeforeground':'white'})
        self.run_btn.pack(side='left', padx=(0, 5))
        
        self.stop_btn = tk.Button(controls_frame, text="⏹️ 중단 (Esc)", command=self.stop_processing_ui_initiated, font=('Segoe UI', 10, 'bold'), relief='flat', cursor='hand2', padx=5, pady=2)
        self.theme_manager.register_widget(self.stop_btn, {'bg': 'danger', 'fg': 'white', 'activebackground':'dark', 'activeforeground':'white'})
        self.stop_btn.pack(side='left', padx=(0, 15))
        
        # 테마 선택 (우측 정렬)
        theme_combo_frame = tk.Frame(toolbar) # 테마 콤보박스용 프레임
        self.theme_manager.register_widget(theme_combo_frame, {'bg': 'primary'})
        theme_combo_frame.pack(side='right', padx=(0,8))

        theme_lbl = tk.Label(theme_combo_frame, text="테마:", font=('Segoe UI', 9))
        self.theme_manager.register_widget(theme_lbl, {'bg': 'primary', 'fg': 'white'})
        theme_lbl.pack(side='left', padx=(0, 3))
        
        self.theme_combo = ttk.Combobox(theme_combo_frame, textvariable=self.theme_var, width=12, state="readonly", font=('Segoe UI', 8), style="TCombobox")
        self.theme_combo['values'] = [theme['name'] for theme in self.theme_manager.available_themes.values()]
        # 초기값은 load_last_settings에서 테마 적용 후 설정됨
        self.theme_combo.pack(side='left')
        self.theme_combo.bind('<<ComboboxSelected>>', lambda e: self.theme_manager.change_theme(
            next(key for key, theme_val in self.theme_manager.available_themes.items() if theme_val['name'] == self.theme_var.get())
        ))

    def _create_left_panel_content(self, parent):
        # 스크롤 가능한 프레임 대신 일반 프레임 사용 (내용이 많지 않음)
        # scrollable_frame = tk.Frame(parent)
        # self.theme_manager.register_widget(scrollable_frame, {'bg': 'surface'})
        # scrollable_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        self._create_file_section(parent) # parent를 직접 사용
        self._create_coordinates_section(parent)
        self._create_timing_section(parent)
        self._create_options_section(parent)
        self._create_preset_section(parent)

    def _create_right_panel_content(self, parent):
        log_section_frame = self._create_section_frame_styled(parent, "📊 상태 및 로그", fill_parent=True)
        
        log_text_frame = tk.Frame(log_section_frame) # 로그 텍스트와 스크롤바를 담을 프레임
        self.theme_manager.register_widget(log_text_frame, {'bg': 'white'}) # 테마 적용
        log_text_frame.pack(fill='both', expand=True, pady=(0,5))

        self.log_text_widget = tk.Text(log_text_frame, font=('Segoe UI', 9), relief='solid', bd=1, wrap='word', state='disabled', width=20)
        self.theme_manager.register_widget(self.log_text_widget, {'bg': 'white', 'fg': 'on_surface', 'insertbackground': 'on_surface'})
        
        log_scroll = ttk.Scrollbar(log_text_frame, orient="vertical", command=self.log_text_widget.yview, style="TScrollbar")
        self.log_text_widget.configure(yscrollcommand=log_scroll.set)
        
        self.log_text_widget.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")

        # 로그 레벨별 태그 색상 설정 (테마 변경 시에도 업데이트되도록 refresh_grid_tags와 유사한 로직 필요)
        # 초기 설정은 여기서, 테마 변경 시 ThemeManager에서 호출하여 업데이트
        self._configure_log_tags()


    def _configure_log_tags(self): # 로그 태그 색상 설정 함수 분리
        if self.log_text_widget and self.log_text_widget.winfo_exists():
            self.log_text_widget.tag_configure("INFO", foreground=self.theme_manager.get_color('primary'))
            self.log_text_widget.tag_configure("WARNING", foreground=self.theme_manager.get_color('warning'))
            self.log_text_widget.tag_configure("ERROR", foreground=self.theme_manager.get_color('danger'))
            self.log_text_widget.tag_configure("SUCCESS", foreground=self.theme_manager.get_color('success'))
            self.log_text_widget.tag_configure("DEBUG", foreground=self.theme_manager.get_color('secondary')) # 어두운 회색 계열


    def _create_file_section(self, parent):
        section = self._create_section_frame_styled(parent, "📁 파일 설정")
        common_font = ('Segoe UI', 9)
        btn_font = ('Segoe UI', 9)
        btn_width = 5 # 버튼 너비 통일
        # btn_height = 1 # 버튼 높이는 기본값 사용 또는 pady로 조절

        # Excel 입력 파일
        excel_frame = tk.Frame(section)
        self.theme_manager.register_widget(excel_frame, {'bg': 'white'})
        excel_frame.pack(fill='x', pady=(0, 5))
        
        excel_lbl = tk.Label(excel_frame, text="Excel 입력 파일:", font=(common_font[0], common_font[1], 'bold'))
        self.theme_manager.register_widget(excel_lbl, {'bg': 'white', 'fg': 'on_surface'})
        excel_lbl.pack(anchor='w', pady=(0,2))
        
        excel_input_frame = tk.Frame(excel_frame) # Entry와 Button을 담을 프레임
        self.theme_manager.register_widget(excel_input_frame, {'bg': 'white'})
        excel_input_frame.pack(fill='x')
        
        self.excel_entry = tk.Entry(excel_input_frame, textvariable=self.input_excel_path, font=common_font, relief='solid', bd=1)
        self.theme_manager.register_widget(self.excel_entry, {'bg': 'white', 'fg': 'on_surface'})
        self.excel_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        excel_browse_btn = tk.Button(excel_input_frame, text="찾기", command=self.browse_input_excel, font=btn_font, relief='flat', cursor='hand2', width=btn_width, pady=0)
        self.theme_manager.register_widget(excel_browse_btn, {'bg': 'secondary', 'fg': 'white', 'activebackground':'dark'})
        excel_browse_btn.pack(side='right')

        # 출력 폴더
        output_frame = tk.Frame(section)
        self.theme_manager.register_widget(output_frame, {'bg': 'white'})
        output_frame.pack(fill='x', pady=(8, 0))
        output_lbl = tk.Label(output_frame, text="출력 폴더:", font=(common_font[0], common_font[1], 'bold'))
        self.theme_manager.register_widget(output_lbl, {'bg': 'white', 'fg': 'on_surface'})
        output_lbl.pack(anchor='w', pady=(0,2))

        output_input_frame = tk.Frame(output_frame)
        self.theme_manager.register_widget(output_input_frame, {'bg': 'white'})
        output_input_frame.pack(fill='x')

        self.output_entry = tk.Entry(output_input_frame, textvariable=self.output_folder_path, font=common_font, relief='solid', bd=1)
        self.theme_manager.register_widget(self.output_entry, {'bg': 'white', 'fg': 'on_surface'})
        self.output_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))

        output_browse_btn = tk.Button(output_input_frame, text="찾기", command=self.browse_output_folder, font=btn_font, relief='flat', cursor='hand2', width=btn_width, pady=0)
        self.theme_manager.register_widget(output_browse_btn, {'bg': 'secondary', 'fg': 'white', 'activebackground':'dark'})
        output_browse_btn.pack(side='right', padx=(0,3)) # 우측 버튼 간격 조정

        self.open_folder_btn = tk.Button(output_input_frame, text="📂", command=self.open_output_folder, font=btn_font, relief='flat', cursor='hand2', width=3, pady=0)
        self.theme_manager.register_widget(self.open_folder_btn, {'bg': 'primary', 'fg': 'white', 'activebackground':'dark'})
        self.open_folder_btn.pack(side='right')


    def _create_coordinates_section(self, parent):
        section = self._create_section_frame_styled(parent, "🎯 좌표 및 영역 설정")
        btn_font = ('Segoe UI', 9)
        # btn_height = 1 # 버튼 높이 통일 (pady로 조절)

        grid_container = tk.Frame(section)
        self.theme_manager.register_widget(grid_container, {'bg': 'white'})
        grid_container.pack(fill='x', pady=(0, 5))
        grid_container.grid_columnconfigure(0, weight=1)
        grid_container.grid_columnconfigure(1, weight=1)

        # 버튼 생성 및 배치 (pady=3으로 높이감 부여)
        click_btn = tk.Button(grid_container, text="🎯 클릭 포인트", command=self.relocate_clickpoint, font=btn_font, relief='flat', cursor='hand2', pady=3)
        self.theme_manager.register_widget(click_btn, {'bg': 'accent', 'fg': 'white', 'activebackground':'dark'})
        click_btn.grid(row=0, column=0, sticky='nsew', padx=(0, 2), pady=(0, 2))

        all_area_btn = tk.Button(grid_container, text="🖼️ 전체 영역", command=self.relocate_allarea, font=btn_font, relief='flat', cursor='hand2', pady=3)
        self.theme_manager.register_widget(all_area_btn, {'bg': 'primary', 'fg': 'white', 'activebackground':'dark'})
        all_area_btn.grid(row=0, column=1, sticky='nsew', padx=(2, 0), pady=(0, 2))

        date_area_btn = tk.Button(grid_container, text="📅 날짜 영역", command=self.relocate_datearea, font=btn_font, relief='flat', cursor='hand2', pady=3)
        self.theme_manager.register_widget(date_area_btn, {'bg': 'success', 'fg': 'white', 'activebackground':'dark'})
        date_area_btn.grid(row=1, column=0, sticky='nsew', padx=(0, 2), pady=(2, 0))

        rate_area_btn = tk.Button(grid_container, text="📈 금리 영역", command=self.relocate_ratearea, font=btn_font, relief='flat', cursor='hand2', pady=3)
        self.theme_manager.register_widget(rate_area_btn, {'bg': 'warning', 'fg': 'on_surface', 'activebackground':'dark'}) # 금리 버튼 글자색 변경
        rate_area_btn.grid(row=1, column=1, sticky='nsew', padx=(2, 0), pady=(2, 0))

        preview_all_btn = tk.Button(section, text="🔍 전체 영역 미리보기", command=self.show_area_preview, font=(btn_font[0], btn_font[1], 'bold'), relief='flat', cursor='hand2', pady=4)
        self.theme_manager.register_widget(preview_all_btn, {'bg': 'secondary', 'fg': 'white', 'activebackground':'dark'}) # 미리보기 버튼 색상 변경
        preview_all_btn.pack(fill='x', pady=(8, 0))


    def _create_timing_section(self, parent):
        section = self._create_section_frame_styled(parent, "⏱️ 타이밍 설정")
        common_font = ('Segoe UI', 9)
        
        timing_grid = tk.Frame(section) # 타이밍 엔트리들을 담을 프레임
        self.theme_manager.register_widget(timing_grid, {'bg': 'white'})
        timing_grid.pack(fill='x')

        # 각 타이밍 설정을 별도의 프레임에 넣어 좌우 배치
        left_timing_frame = tk.Frame(timing_grid)
        self.theme_manager.register_widget(left_timing_frame, {'bg': 'white'})
        left_timing_frame.pack(side='left', fill='x', expand=True, padx=(0, 5))

        paste_lbl = tk.Label(left_timing_frame, text="붙여넣기 딜레이(초):", font=(common_font[0], common_font[1], 'bold'))
        self.theme_manager.register_widget(paste_lbl, {'bg': 'white', 'fg': 'on_surface'})
        paste_lbl.pack(anchor='w', pady=(0,2))
        paste_entry = tk.Entry(left_timing_frame, textvariable=self.paste_delay, font=common_font, width=10, relief='solid', bd=1)
        self.theme_manager.register_widget(paste_entry, {'bg': 'white', 'fg': 'on_surface'})
        paste_entry.pack(fill='x')

        right_timing_frame = tk.Frame(timing_grid)
        self.theme_manager.register_widget(right_timing_frame, {'bg': 'white'})
        right_timing_frame.pack(side='left', fill='x', expand=True, padx=(5, 0))

        load_lbl = tk.Label(right_timing_frame, text="로딩 딜레이(초):", font=(common_font[0], common_font[1], 'bold'))
        self.theme_manager.register_widget(load_lbl, {'bg': 'white', 'fg': 'on_surface'})
        load_lbl.pack(anchor='w', pady=(0,2))
        load_entry = tk.Entry(right_timing_frame, textvariable=self.loading_delay, font=common_font, width=10, relief='solid', bd=1)
        self.theme_manager.register_widget(load_entry, {'bg': 'white', 'fg': 'on_surface'})
        load_entry.pack(fill='x')


    def _create_options_section(self, parent):
        section = self._create_section_frame_styled(parent, "⚙️ 옵션 설정")
        common_font = ('Segoe UI', 9)
        
        save_img_cb = tk.Checkbutton(section, text="상세 이미지 저장 (영역별 개별 파일)", variable=self.save_detail_images, font=common_font, anchor='w')
        self.theme_manager.register_widget(save_img_cb, {'bg': 'white', 'fg': 'on_surface', 'selectcolor': 'light', 'activebackground': 'white', 'activeforeground': 'on_surface'})
        save_img_cb.pack(fill='x', pady=(0, 8)) # fill='x'로 변경하여 왼쪽 정렬 효과

        # self.skip_kbp_var는 __init__에서 BooleanVar()로 초기화, 값은 load_last_settings에서 설정
        skip_kbp_cb = tk.Checkbutton(section, text="'KBP' 코드 건너뛰기 (빈 값으로 완료 처리)", variable=self.skip_kbp_var, font=common_font, command=self.save_advanced_ui_to_settings, anchor='w')
        self.theme_manager.register_widget(skip_kbp_cb, {'bg': 'white', 'fg': 'on_surface', 'selectcolor': 'light', 'activebackground': 'white', 'activeforeground': 'on_surface'})
        skip_kbp_cb.pack(fill='x', pady=(0, 8))


    def _create_preset_section(self, parent):
        section = self._create_section_frame_styled(parent, "💾 프리셋 관리", fill_parent=True) # fill_parent=True로 부모 채우기
        common_font = ('Segoe UI', 9)
        btn_font = ('Segoe UI', 9)
        btn_width = 6
        # btn_height = 1 # pady로 조절

        # 프리셋 로드 부분
        preset_load_frame = tk.Frame(section)
        self.theme_manager.register_widget(preset_load_frame, {'bg': 'white'})
        preset_load_frame.pack(fill='x', pady=(0, 8))
        preset_lbl = tk.Label(preset_load_frame, text="저장된 프리셋:", font=(common_font[0], common_font[1], 'bold'))
        self.theme_manager.register_widget(preset_lbl, {'bg': 'white', 'fg': 'on_surface'})
        preset_lbl.pack(anchor='w', pady=(0,2))

        preset_control_frame = tk.Frame(preset_load_frame) # Combobox와 버튼들을 담을 프레임
        self.theme_manager.register_widget(preset_control_frame, {'bg': 'white'})
        preset_control_frame.pack(fill='x')

        self.preset_combo = ttk.Combobox(preset_control_frame, state="readonly", font=common_font, style="TCombobox", width=15) # 너비 조절
        self.preset_combo.pack(side='left', fill='x', expand=True, padx=(0, 5))

        apply_preset_btn = tk.Button(preset_control_frame, text="적용", command=self.apply_selected_preset, font=btn_font, relief='flat', cursor='hand2', width=btn_width, pady=1)
        self.theme_manager.register_widget(apply_preset_btn, {'bg': 'success', 'fg': 'white', 'activebackground':'dark'})
        apply_preset_btn.pack(side='left', padx=(0, 5)) # side='left'로 변경

        delete_preset_btn = tk.Button(preset_control_frame, text="삭제", command=self.delete_selected_preset, font=btn_font, relief='flat', cursor='hand2', width=btn_width, pady=1)
        self.theme_manager.register_widget(delete_preset_btn, {'bg': 'danger', 'fg': 'white', 'activebackground':'dark'})
        delete_preset_btn.pack(side='left') # side='left'로 변경

        # 새 프리셋 저장 부분
        preset_save_frame = tk.Frame(section)
        self.theme_manager.register_widget(preset_save_frame, {'bg': 'white'})
        preset_save_frame.pack(fill='x', pady=(15, 0)) # 상단 간격 추가
        save_preset_lbl = tk.Label(preset_save_frame, text="새 프리셋 저장:", font=(common_font[0], common_font[1], 'bold'))
        self.theme_manager.register_widget(save_preset_lbl, {'bg': 'white', 'fg': 'on_surface'})
        save_preset_lbl.pack(anchor='w', pady=(0,2))

        save_control_frame = tk.Frame(preset_save_frame) # Entry와 Button을 담을 프레임
        self.theme_manager.register_widget(save_control_frame, {'bg': 'white'})
        save_control_frame.pack(fill='x')

        self.preset_name_entry = tk.Entry(save_control_frame, font=common_font, relief='solid', bd=1)
        self.theme_manager.register_widget(self.preset_name_entry, {'bg': 'white', 'fg': 'on_surface'})
        self.preset_name_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        self.preset_name_entry.insert(0, "새 프리셋 이름") # 기본 텍스트

        save_preset_btn = tk.Button(save_control_frame, text="저장", command=self.save_current_as_preset, font=btn_font, relief='flat', cursor='hand2', width=btn_width, pady=1)
        self.theme_manager.register_widget(save_preset_btn, {'bg': 'accent', 'fg': 'white', 'activebackground':'dark'})
        save_preset_btn.pack(side='left') # side='left'로 변경

        self.update_preset_combo() # 프리셋 콤보박스 초기화


    def _create_center_excel_grid(self, parent):
        grid_section = self._create_section_frame_styled(parent, "📋 Excel 데이터 그리드", fill_parent=True) # 아이콘 변경
        
        control_frame = tk.Frame(grid_section)
        self.theme_manager.register_widget(control_frame, {'bg': 'white'})
        control_frame.pack(fill='x', pady=(0,10))

        # 좌측 컨트롤 (Excel 로드, 행 추가, 붙여넣기)
        left_controls = tk.Frame(control_frame)
        self.theme_manager.register_widget(left_controls, {'bg': 'white'})
        left_controls.pack(side='left', fill='x', expand=True, padx=(0,5))
        
        load_excel_btn = tk.Button(left_controls, text="📁 Excel 로드", command=self.load_excel_to_grid, font=('Segoe UI', 9), relief='flat', cursor='hand2', pady=2)
        self.theme_manager.register_widget(load_excel_btn, {'bg': 'primary', 'fg': 'white', 'activebackground':'dark'})
        load_excel_btn.pack(side='left', padx=(0,5))

        add_row_btn = tk.Button(left_controls, text="➕ 행 추가", command=self.add_empty_row_ui, font=('Segoe UI', 9), relief='flat', cursor='hand2', pady=2)
        self.theme_manager.register_widget(add_row_btn, {'bg': 'success', 'fg': 'white', 'activebackground':'dark'})
        add_row_btn.pack(side='left', padx=(0,5))

        paste_btn = tk.Button(left_controls, text="📋 붙여넣기", command=self.paste_from_clipboard_ui, font=('Segoe UI', 9), relief='flat', cursor='hand2', pady=2)
        self.theme_manager.register_widget(paste_btn, {'bg': 'secondary', 'fg': 'white', 'activebackground':'dark'})
        paste_btn.pack(side='left', padx=(0,5))

        # 우측 컨트롤 (선택 삭제, 전체 삭제)
        right_controls = tk.Frame(control_frame)
        self.theme_manager.register_widget(right_controls, {'bg': 'white'})
        right_controls.pack(side='right')

        delete_rows_btn = tk.Button(right_controls, text="🗑️ 선택 삭제", command=self.delete_selected_rows_ui, font=('Segoe UI', 9), relief='flat', cursor='hand2', pady=2)
        self.theme_manager.register_widget(delete_rows_btn, {'bg': 'danger', 'fg': 'white', 'activebackground':'dark'})
        delete_rows_btn.pack(side='right', padx=(5,0))

        clear_all_btn = tk.Button(right_controls, text="🧹 전체 삭제", command=self.clear_all_data_ui, font=('Segoe UI', 9), relief='flat', cursor='hand2', pady=2)
        self.theme_manager.register_widget(clear_all_btn, {'bg': 'warning', 'fg': 'on_surface', 'activebackground':'dark'})
        clear_all_btn.pack(side='right', padx=(5,0))

        # Treeview 프레임
        tree_frame = tk.Frame(grid_section)
        self.theme_manager.register_widget(tree_frame, {'bg': 'white'}) # 테마 적용
        tree_frame.pack(fill='both', expand=True)

        columns = ('종목코드', '종목명', '날짜', '금리', '상태')
        self.grid_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', style="Treeview")
        
        for col_name in columns: self.grid_tree.heading(col_name, text=col_name)
        col_widths = {'종목코드': 95, '종목명': 180, '날짜': 120, '금리': 95, '상태': 100}
        for col_name, width in col_widths.items():
            self.grid_tree.column(col_name, width=width, anchor='center', minwidth=max(50, width-40), stretch=tk.YES) # minwidth 조정

        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.grid_tree.yview, style="TScrollbar")
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.grid_tree.xview, style="TScrollbar")
        self.grid_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        self.grid_tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # 이벤트 바인딩
        self.grid_tree.bind('<Double-1>', self.on_cell_double_click_ui)
        self.grid_tree.bind('<Button-3>', self.show_context_menu_ui) # 우클릭 컨텍스트 메뉴
        self.grid_tree.bind('<Delete>', lambda e: self.delete_selected_rows_ui())
        self.grid_tree.bind('<Control-c>', lambda e: self.copy_selected_rows_ui())
        self.grid_tree.bind('<Control-v>', lambda e: self.paste_from_clipboard_ui()) # 그리드 포커스 시에도 붙여넣기

        # 상태 레이블
        status_frame = tk.Frame(grid_section) # 그리드 섹션 내부에 배치
        self.theme_manager.register_widget(status_frame, {'bg': 'white'})
        status_frame.pack(fill='x', pady=(10,0))
        self.grid_status_label = tk.Label(status_frame, text="총 0행 | 완료: 0 | 대기: 0 | 오류: 0", font=('Segoe UI', 9))
        self.theme_manager.register_widget(self.grid_status_label, {'bg': 'white', 'fg': 'on_surface'})
        self.grid_status_label.pack(side='left')
        self.grid_progress_label = tk.Label(status_frame, text="진행률: 0.0%", font=('Segoe UI', 9, 'bold'))
        self.theme_manager.register_widget(self.grid_progress_label, {'bg': 'white', 'fg': 'primary'})
        self.grid_progress_label.pack(side='right')
        
        self.refresh_grid_tags() # Treeview 태그 색상 초기 설정


    def refresh_grid_tags(self): # Treeview 태그 '모양' 설정
        if not self.grid_tree: return
        # 테마 매니저에서 색상 가져오기
        processing_bg = self.theme_manager.get_color('warning', '#FFF3CD')
        processing_fg = self.theme_manager.get_color('on_surface', '#856404') # on_surface 사용
        completed_bg = self.theme_manager.get_color('success', '#D4EDDA')
        completed_fg = self.theme_manager.get_color('on_surface', '#155724') # on_surface 사용
        error_bg = self.theme_manager.get_color('danger', '#F8D7DA')
        error_fg = self.theme_manager.get_color('white', '#721C24') # 어두운 배경에 흰색 글씨

        self.grid_tree.tag_configure('processing', background=processing_bg, foreground=processing_fg)
        self.grid_tree.tag_configure('completed', background=completed_bg, foreground=completed_fg)
        self.grid_tree.tag_configure('error', background=error_bg, foreground=error_fg)
        # '중단됨' 상태도 'error' 태그를 사용하므로 별도 설정 불필요 (만약 다르게 하고 싶다면 추가)
        # self.grid_tree.tag_configure('stopped', background=..., foreground=...)

    # --- Optimized Treeview Update Logic ---
    def refresh_grid_ui(self):
        if not self.grid_tree: return
        
        for item in self.grid_tree.get_children():
            self.grid_tree.delete(item)
            
        for i, row_data in enumerate(self.data_manager.excel_data):
            self._insert_grid_row(i, row_data)

        self.update_grid_status_labels()

    def _insert_grid_row(self, index, row_data):
        if not self.grid_tree: return
        
        tags = self._get_tags_for_row(index, row_data)
        item_id = f"row_{index}" 
        
        self.grid_tree.insert('', 'end', iid=item_id, values=(
            row_data.get('종목코드', ''), 
            row_data.get('종목명', ''),
            row_data.get('날짜', ''), 
            row_data.get('금리', ''), 
            row_data.get('상태', '대기 중')
        ), tags=tags)

    def _get_tags_for_row(self, index, row_data):
        tags = []
        status = row_data.get('상태', '')
        if status == '완료':
            tags.append('completed')
        elif any(err_keyword in status for err_keyword in ['오류', '실패', '없음', '건너', '중단됨', '캡처 실패', '처리 오류', '종목코드 없음']):
            tags.append('error')
        elif self.work_controller.is_running and index == self.data_manager.current_processing_index:
            tags.append('processing')
        return tags

    def _handle_grid_update(self, data):
        try:
            update_type, grid_idx, *payload = data
            
            if not (0 <= grid_idx < len(self.data_manager.excel_data)):
                self.logger.warning(f"잘못된 grid_idx ({grid_idx})로 그리드 업데이트 시도. 데이터 크기: {len(self.data_manager.excel_data)}")
                return

            item_id_str = f"row_{grid_idx}"
            
            if not self.grid_tree.exists(item_id_str):
                self.logger.warning(f"Treeview에 {item_id_str}가 존재하지 않아 업데이트 건너뜀. 행 데이터: {self.data_manager.excel_data[grid_idx]}")
                # 누락된 행을 추가하거나 전체 새로고침을 고려할 수 있으나, 일단 로그만 남김
                # self._insert_grid_row(grid_idx, self.data_manager.excel_data[grid_idx]) # 누락된 행만 추가 시도
                # self.refresh_grid_ui() # 또는 전체 새로고침 (성능 저하 가능성)
                return

            row_data_ref = self.data_manager.excel_data[grid_idx] 

            if update_type == "processing":
                row_data_ref['상태'] = '처리 중...'
                if self.grid_tree:
                    self.grid_tree.see(item_id_str) 
            elif update_type == "complete" and len(payload) >= 3:
                date_res, rate_res, status_res = payload[0], payload[1], payload[2]
                if date_res is not None: row_data_ref['날짜'] = date_res
                if rate_res is not None: row_data_ref['금리'] = rate_res
                row_data_ref['상태'] = status_res
            elif update_type == "error" and len(payload) >= 1:
                row_data_ref['상태'] = payload[0] # payload[0]에 오류 메시지 포함
            
            new_values = (
                row_data_ref.get('종목코드', ''), 
                row_data_ref.get('종목명', ''),
                row_data_ref.get('날짜', ''), 
                row_data_ref.get('금리', ''), 
                row_data_ref.get('상태', '대기 중')
            )
            self.grid_tree.item(item_id_str, values=new_values)
            
            new_tags = self._get_tags_for_row(grid_idx, row_data_ref)
            self.grid_tree.item(item_id_str, tags=new_tags)

            self.logger.debug(f"[_handle_grid_update] {grid_idx}번 항목 업데이트 후: {row_data_ref}")
            self.update_grid_status_labels() 

        except Exception as e:
            self.logger.error(f"그리드 업데이트 중 오류: {e}, 데이터: {data}", exc_info=True)
    # --- End of Optimized Treeview Update Logic ---

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
            # 'skip_kbp_code'는 advanced 설정이므로 여기서 직접 가져오지 않고, settings_manager를 통해 관리
            'advanced': { # 현재 UI에서 직접 제어하는 고급 설정만 포함 (예시)
                 'skip_kbp_code': self.skip_kbp_var.get()
            }
        }

    def apply_settings_to_ui(self, settings_dict):
        if not settings_dict: return
        
        cp = settings_dict.get('click_point')
        if cp and len(cp) == 2: self.click_x.set(cp[0]); self.click_y.set(cp[1])
        
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

        # 고급 설정 UI 반영 (예: skip_kbp_var)
        advanced_settings = settings_dict.get('advanced', {})
        self.skip_kbp_var.set(advanced_settings.get('skip_kbp_code', self.settings_manager.get_advanced('skip_kbp_code'))) # 기본값은 settings_manager에서

        # settings_manager의 advanced 데이터도 업데이트 (선택적, UI와 동기화 목적)
        # self.settings_manager.data['advanced'].update(advanced_settings)


    def save_advanced_ui_to_settings(self): # UI의 고급 설정 항목을 settings_manager에 저장
        try:
            self.settings_manager.set_advanced('skip_kbp_code', self.skip_kbp_var.get())
            # 다른 고급 설정 UI 요소가 있다면 여기서 추가
            self.settings_manager.save_settings() # 변경사항 즉시 파일에 저장
            self.logger.info("고급 설정(UI)이 저장되었습니다.")
        except Exception as e:
            self.logger.error(f"고급 설정(UI) 저장 실패: {e}")


    def reset_advanced_settings_and_ui(self):
        if messagebox.askyesno("확인", "모든 고급 설정을 기본값으로 되돌리시겠습니까?", parent=self):
            self.settings_manager.reset_advanced_settings() # settings.json 업데이트
            # UI 업데이트
            self.skip_kbp_var.set(self.settings_manager.get_advanced('skip_kbp_code'))
            # 다른 고급 설정 UI 요소들도 기본값으로 업데이트
            messagebox.showinfo("완료", "고급 설정이 초기화되었습니다.", parent=self)
            self.logger.info("고급 설정이 기본값으로 초기화되었습니다.")


    def browse_input_excel(self):
        file_path = filedialog.askopenfilename(title="엑셀 파일 선택", filetypes=[("Excel files", "*.xlsx;*.xls")], parent=self)
        if file_path:
            self.input_excel_path.set(file_path)
            base_path = os.path.dirname(file_path)
            # 출력 폴더가 비어있으면 입력 파일 경로로 자동 설정
            if not self.output_folder_path.get().strip(): 
                self.output_folder_path.set(self.ocr_workflow_manager._clean_folder_path(base_path))


    def browse_output_folder(self):
        folder_path = filedialog.askdirectory(title="출력 폴더 선택", parent=self)
        if folder_path: 
            cleaned_path = self.ocr_workflow_manager._clean_folder_path(folder_path)
            self.output_folder_path.set(cleaned_path)

    def open_output_folder(self):
        output_path = self.output_folder_path.get().strip()
        if not output_path:
            messagebox.showwarning("경고", "출력 폴더가 설정되지 않았습니다.", parent=self)
            return
        
        try:
            # 폴더 존재 여부 확인 및 생성 (로컬 경로에만 해당)
            # UNC 경로는 os.path.exists나 os.makedirs가 불안정할 수 있음
            is_unc = (platform.system() == "Windows" and output_path.startswith("\\\\")) or \
                     (platform.system() != "Windows" and output_path.startswith("//"))

            if not is_unc and not os.path.isdir(output_path):
                if messagebox.askyesno("폴더 생성", f"폴더가 존재하지 않습니다.\n생성하시겠습니까?\n\n경로: {output_path}", parent=self):
                    os.makedirs(output_path, exist_ok=True)
                    self.logger.info(f"출력 폴더 생성됨: {output_path}")
                else:
                    return # 생성 안 하면 종료

            # OS별 폴더 열기
            system = platform.system()
            self.logger.info(f"출력 폴더 열기 시도 - 시스템: {system}, 경로: {output_path}")

            if system == "Windows":
                # Windows에서는 백슬래시 사용이 더 일반적일 수 있으나, os.startfile은 슬래시도 잘 처리함
                # UNC 경로도 os.startfile이 처리
                os.startfile(output_path)
            elif system == "Darwin": # macOS
                subprocess.run(['open', output_path], check=True, timeout=10)
            else: # Linux 등
                subprocess.run(['xdg-open', output_path], check=True, timeout=10)
            self.logger.info(f"출력 폴더 열기 명령어 실행 시도 완료: {output_path}")

        except FileNotFoundError:
            messagebox.showerror("오류", f"폴더 또는 파일을 찾을 수 없습니다: {output_path}", parent=self)
            self.logger.error(f"폴더 열기 실패 (FileNotFoundError): {output_path}")
        except subprocess.CalledProcessError as e:
            messagebox.showerror("오류", f"폴더 열기 명령어 실행 실패: {e}\n경로: {output_path}", parent=self)
            self.logger.error(f"폴더 열기 명령어 실행 실패 ({e}): {output_path}")
        except subprocess.TimeoutExpired:
            messagebox.showerror("오류", "폴더 열기 시간 초과", parent=self)
            self.logger.error(f"폴더 열기 시간 초과: {output_path}")
        except Exception as e:
            messagebox.showerror("오류", f"폴더 열기 중 알 수 없는 오류: {e}\n경로: {output_path}", parent=self)
            self.logger.exception(f"폴더 열기 중 알 수 없는 오류: {output_path}")


    def relocate_clickpoint(self):
        overlay = PointCaptureOverlay(self, color_key="danger", theme_manager=self.theme_manager)
        self.wait_window(overlay) # 오버레이 창이 닫힐 때까지 대기
        if overlay.click_x is not None and overlay.click_y is not None:
            self.click_x.set(overlay.click_x); self.click_y.set(overlay.click_y)

    def _relocate_area_generic(self, x1_var, y1_var, x2_var, y2_var, color_key):
        overlay = DragCaptureOverlay(self, color_key=color_key, theme_manager=self.theme_manager)
        self.wait_window(overlay)
        if overlay.x1 is not None and overlay.y1 is not None and \
           overlay.x2 is not None and overlay.y2 is not None:
            x1_var.set(overlay.x1); y1_var.set(overlay.y1)
            x2_var.set(overlay.x2); y2_var.set(overlay.y2)

    def relocate_allarea(self): self._relocate_area_generic(self.allarea_x1, self.allarea_y1, self.allarea_x2, self.allarea_y2, "primary")
    def relocate_datearea(self): self._relocate_area_generic(self.datearea_x1, self.datearea_y1, self.datearea_x2, self.datearea_y2, "success")
    def relocate_ratearea(self): self._relocate_area_generic(self.ratearea_x1, self.ratearea_y1, self.ratearea_x2, self.ratearea_y2, "warning")

    def update_preset_combo(self):
        if hasattr(self, 'preset_combo') and self.preset_combo:
            preset_names = self.settings_manager.get_preset_names()
            self.preset_combo['values'] = preset_names
            if preset_names: 
                # 마지막으로 선택했거나 저장된 프리셋을 기본으로 선택하는 로직 추가 가능
                self.preset_combo.current(0) 
            else: 
                self.preset_combo.set('')


    def apply_selected_preset(self):
        if not hasattr(self, 'preset_combo'): return
        selected_name = self.preset_combo.get()
        if selected_name:
            preset_settings = self.settings_manager.apply_preset(selected_name)
            if preset_settings:
                self.apply_settings_to_ui(preset_settings) # UI 변수 업데이트
                messagebox.showinfo("정보", f"프리셋 '{selected_name}'이 적용되었습니다.", parent=self)
                self.logger.info(f"프리셋 '{selected_name}' 적용됨.")
            else:
                messagebox.showwarning("경고", f"프리셋 '{selected_name}'을 불러오는 데 실패했습니다.", parent=self)
        else:
            messagebox.showwarning("경고", "적용할 프리셋을 선택해주세요.", parent=self)


    def save_current_as_preset(self):
        name_entry_widget = getattr(self, 'preset_name_entry', None)
        preset_name = ""
        if name_entry_widget:
            preset_name = name_entry_widget.get().strip()
            if preset_name == "새 프리셋 이름" or not preset_name: # 기본 텍스트이거나 비어있으면 경고
                messagebox.showwarning("경고", "유효한 프리셋 이름을 입력해주세요.", parent=self)
                return
        else: # Entry 위젯이 없는 경우 (예: UI 구성 오류) - fallback으로 simpledialog 사용
            preset_name = simpledialog.askstring("프리셋 저장", "프리셋 이름을 입력하세요:", parent=self)
            if not preset_name or not preset_name.strip(): 
                messagebox.showwarning("경고", "유효한 프리셋 이름을 입력해주세요.", parent=self)
                return
            preset_name = preset_name.strip()

        current_settings = self.get_current_ui_settings() # 현재 UI 값들 가져오기
        self.settings_manager.save_preset(preset_name, current_settings) # 설정 매니저에 저장
        self.update_preset_combo() # 콤보박스 업데이트
        if name_entry_widget: # 입력 필드 초기화
            name_entry_widget.delete(0, tk.END)
            name_entry_widget.insert(0, "새 프리셋 이름")
        messagebox.showinfo("완료", f"'{preset_name}' 프리셋이 저장되었습니다.", parent=self)
        self.logger.info(f"프리셋 '{preset_name}' 저장됨.")


    def delete_selected_preset(self):
        if not hasattr(self, 'preset_combo'): return
        selected_name = self.preset_combo.get()
        if not selected_name:
            messagebox.showwarning("경고", "삭제할 프리셋을 선택해주세요.", parent=self)
            return
        if messagebox.askyesno("확인", f"프리셋 '{selected_name}'을(를) 삭제하시겠습니까?", parent=self):
            self.settings_manager.delete_preset(selected_name)
            self.update_preset_combo()
            messagebox.showinfo("완료", f"프리셋 '{selected_name}'이 삭제되었습니다.", parent=self)
            self.logger.info(f"프리셋 '{selected_name}' 삭제됨.")


    def show_area_preview(self):
        areas_info = {
            "click_point": (self.click_x.get(), self.click_y.get()) if self.click_x.get() and self.click_y.get() else None,
            "all_area": (self.allarea_x1.get(), self.allarea_y1.get(), self.allarea_x2.get(), self.allarea_y2.get()) if self.allarea_x1.get() and self.allarea_y1.get() and self.allarea_x2.get() and self.allarea_y2.get() else None,
            "date_area": (self.datearea_x1.get(), self.datearea_y1.get(), self.datearea_x2.get(), self.datearea_y2.get()) if self.datearea_x1.get() and self.datearea_y1.get() and self.datearea_x2.get() and self.datearea_y2.get() else None,
            "rate_area": (self.ratearea_x1.get(), self.ratearea_y1.get(), self.ratearea_x2.get(), self.ratearea_y2.get()) if self.ratearea_x1.get() and self.ratearea_y1.get() and self.ratearea_x2.get() and self.ratearea_y2.get() else None,
        }
        # None인 영역은 시각화에서 제외됨
        AreaVisualizationOverlay(self, areas_info, self.theme_manager, auto_close=True)

    def stop_processing_ui_initiated(self): # UI에서 중단 버튼 클릭 시
        if self.work_controller.is_running:
            self.logger.info("사용자 요청으로 작업 중단 시도...")
            message = self.work_controller.stop_work() # stop_event 설정 및 상태 변경
            # self.message_queue.put(("log", message, "INFO")) # 로그는 큐를 통해 이미 처리됨
            # _on_work_stopped가 큐 메시지를 통해 호출되어 UI 정리
        else:
            self.logger.info("현재 실행 중인 작업이 없습니다.")


    def _on_work_complete_ui_only(self, summary_message): # 스레드에서 모든 작업 정상 완료 시 호출 (메시지 박스 제외)
        self.logger.info("[_on_work_complete_ui_only] 작업 완료 처리 시작 (UI 전용)")
        self.work_controller.reset()
        self.data_manager.current_processing_index = -1 # 현재 처리 인덱스 초기화
        # self.refresh_grid_ui() # finalize_export_and_complete에서 최종적으로 호출됨
        self.quick_save_settings() # 완료 시 현재 설정 저장
        # 메시지 박스 표시는 _finalize_export_and_complete에서 수행


    def show_shortcuts(self):
        shortcuts = """🎹 키보드 단축키:
• F5: OCR 처리 실행/중단
• Escape: 처리 중단 (실행 중일 때)
• F1: 단축키 도움말 (이 창)
• Ctrl+S: 모든 설정 저장 (현재 UI 상태)
• Ctrl+L: 마지막 저장된 설정 불러오기
• Ctrl+O: Excel 파일 로드 (그리드)"""
        messagebox.showinfo("키보드 단축키", shortcuts, parent=self)

    def show_about(self):
        about_text = """📋 Check Capture OCR - V6.1 (Optimized)
OCR 자동화 애플리케이션 (EasyOCR 기반)

제작자: (사용자 이름 또는 정보)
문의: (연락처 정보)""" # 정보 추가 가능
        messagebox.showinfo("프로그램 정보", about_text, parent=self)

    def run_ocr_process(self):
        if self.work_controller.is_running:
            # 이미 실행 중일 때 중단 로직 (F5 토글)
            self.stop_processing_ui_initiated()
            return
        
        if not self._validate_inputs_for_ocr(): return

        self.work_controller.start_work() # 작업 시작 상태로 변경
        current_ui_settings = self.get_current_ui_settings()
        output_dir = self.output_folder_path.get().strip()
        save_details = self.save_detail_images.get()

        # 이전 스레드가 있다면 join 시도 (선택적, 안정성 강화)
        if self.worker_thread and self.worker_thread.is_alive():
            try:
                self.logger.info("이전 작업 스레드가 아직 실행 중입니다. 종료 대기 중...")
                self.worker_thread.join(timeout=0.5) # 짧은 시간 대기
            except Exception as e:
                self.logger.error(f"이전 스레드 join 중 오류: {e}")

        self.worker_thread = threading.Thread(
            target=self.ocr_workflow_manager.execute_ocr_workflow_threaded,
            args=(current_ui_settings, output_dir, save_details),
            daemon=True # 메인 프로그램 종료 시 스레드도 함께 종료
        )
        self.worker_thread.start()
        self.logger.info("OCR 처리 스레드 시작됨.")
        # self.update_ui_for_running_state(True) # UI 상태 변경 (버튼 등) - 필요시


    def _validate_inputs_for_ocr(self):
        output_dir = self.output_folder_path.get().strip()
        if not self.data_manager.excel_data:
            messagebox.showwarning("경고", "처리할 데이터가 없습니다. Excel 파일을 로드하거나 데이터를 추가하세요.", parent=self)
            return False
        if not output_dir : # 폴더 존재 여부는 open_output_folder 등에서 처리, 여기서는 경로 유무만
            messagebox.showwarning("경고", "출력 폴더를 지정하세요.", parent=self)
            return False
        # 실제 폴더 생성은 OCR 워크플로우 시작 시 시도
        if not self.ocr_workflow_manager.ocr_reader:
            messagebox.showerror("오류", "OCR 엔진이 초기화되지 않았습니다. 프로그램을 재시작하거나 설정을 확인하세요.", parent=self)
            return False
        return True

    # --- Grid Data UI Actions (Optimized) ---
    def load_excel_to_grid(self):
        file_path = self.input_excel_path.get()
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("오류", "Excel 파일을 먼저 선택해주세요.", parent=self)
            return
        
        loaded_rows = self.data_manager.load_excel_to_grid_data(file_path)
        if loaded_rows > 0:
            self.refresh_grid_ui() # 전체 데이터 로드 후에는 전체 새로고침
            self.logger.info(f"Excel 파일 로드 완료: {loaded_rows} 행")
        # else: 오류 메시지는 DataManager에서 처리

    def add_empty_row_ui(self):
        new_row_index = len(self.data_manager.excel_data) # 추가될 행의 인덱스
        self.data_manager.add_empty_row_data() # 데이터 매니저에 빈 행 추가
        
        if self.grid_tree: # Treeview에 새 행만 직접 삽입
            self._insert_grid_row(new_row_index, self.data_manager.excel_data[new_row_index])
            children_iids = self.grid_tree.get_children()
            if children_iids:
                self.grid_tree.see(children_iids[-1]) # 마지막 행으로 스크롤
        self.update_grid_status_labels()


    def paste_from_clipboard_ui(self):
        try:
            clipboard_content = self.clipboard_get()
            # rows_before_paste = len(self.data_manager.excel_data) # 개별 추가 시 필요
            added_count = self.data_manager.paste_from_clipboard_data(clipboard_content)
            
            if added_count > 0:
                self.refresh_grid_ui() # 여러 행 추가 시 전체 새로고침이 간단하고 안전
                messagebox.showinfo("성공", f"{added_count}행을 추가했습니다.", parent=self)
                if self.grid_tree:
                    children = self.grid_tree.get_children()
                    if children: self.grid_tree.see(children[-1])
            else: # 추가된 행이 없을 때 (유효 데이터 없음 등)
                if not clipboard_content.strip(): # 클립보드가 아예 비었을 때
                     messagebox.showwarning("경고", "클립보드가 비어있습니다.", parent=self)
                else: # 내용은 있지만 유효 데이터가 아닐 때
                     messagebox.showwarning("경고", "붙여넣을 유효한 데이터가 없습니다 (탭으로 구분된 데이터 필요).", parent=self)

        except tk.TclError: # 클립보드에 텍스트가 아닌 다른 것이 있을 때
            messagebox.showerror("오류", "클립보드에서 텍스트 데이터를 가져올 수 없습니다.", parent=self)
        except Exception as e:
            self.logger.error(f"클립보드 붙여넣기 중 예외 발생: {e}", exc_info=True)
            messagebox.showerror("오류", f"붙여넣기 중 오류 발생: {e}", parent=self)


    def delete_selected_rows_ui(self):
        if not self.grid_tree: return
        selected_item_iids = self.grid_tree.selection() # 선택된 아이템들의 iid 리스트
        if not selected_item_iids:
            messagebox.showwarning("경고", "삭제할 행을 선택해주세요.", parent=self)
            return
        if not messagebox.askyesno("확인", f"{len(selected_item_iids)}개의 행을 삭제하시겠습니까?", parent=self):
            return
        
        # iid ("row_X")에서 X (인덱스)를 추출하여 역순 정렬
        indices_to_delete = sorted([int(iid.replace("row_", "")) for iid in selected_item_iids if iid.startswith("row_")], reverse=True)
        
        self.data_manager.delete_rows_data(indices_to_delete) # 데이터 매니저에서 삭제
        self.refresh_grid_ui() # Treeview 전체 새로고침 (iid와 데이터 인덱스 동기화)
        self.logger.info(f"{len(indices_to_delete)}개 행 삭제됨.")


    def clear_all_data_ui(self):
        if self.data_manager.excel_data and \
           not messagebox.askyesno("확인", "모든 데이터를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.", parent=self):
            return
        self.data_manager.clear_all_data_internal()
        self.refresh_grid_ui() # 전체 새로고침
        self.logger.info("모든 데이터 삭제됨.")


    def copy_selected_rows_ui(self):
        if not self.grid_tree: return
        selected_item_iids = self.grid_tree.selection()
        if not selected_item_iids: return # 선택된 항목 없으면 무시
        
        copied_data_str_list = []
        # 선택된 iid 순서대로 복사 (Treeview에서의 순서 유지)
        indices_to_copy = sorted([int(iid.replace("row_", "")) for iid in selected_item_iids if iid.startswith("row_")])

        for index in indices_to_copy:
            row_str = self.data_manager.get_row_for_copy(index) # DataManager에서 해당 인덱스 데이터 가져오기
            if row_str:
                copied_data_str_list.append(row_str)
        
        if copied_data_str_list:
            final_str = "\n".join(copied_data_str_list)
            try:
                self.clipboard_clear()
                self.clipboard_append(final_str)
                self.logger.info(f"{len(copied_data_str_list)}개 행이 클립보드에 복사되었습니다.")
            except tk.TclError as e:
                self.logger.error(f"클립보드 작업 실패: {e}")
                messagebox.showerror("오류", "클립보드 작업에 실패했습니다.", parent=self)


    def copy_selected_rates_ui(self):
        if not self.grid_tree: return
        selected_item_iids = self.grid_tree.selection()
        if not selected_item_iids:
            messagebox.showwarning("경고", "복사할 행을 선택해주세요.", parent=self)
            return

        copied_rates = []
        indices_to_copy = sorted([int(iid.replace("row_", "")) for iid in selected_item_iids if iid.startswith("row_")])

        for index in indices_to_copy:
            if 0 <= index < len(self.data_manager.excel_data):
                rate_value = self.data_manager.excel_data[index].get('금리', '')
                copied_rates.append(str(rate_value))

        if copied_rates:
            final_str = "\n".join(copied_rates)
            try:
                self.clipboard_clear()
                self.clipboard_append(final_str)
                self.logger.info(f"선택된 {len(copied_rates)}개 행의 금리가 클립보드에 복사되었습니다.")
            except tk.TclError as e:
                self.logger.error(f"클립보드 작업 실패: {e}")
                messagebox.showerror("오류", "클립보드 작업에 실패했습니다.", parent=self)
        else:
            self.logger.info("선택된 행에 복사할 금리 데이터가 없습니다.")


    def update_grid_status_labels(self):
        if not hasattr(self, 'grid_status_label') or not self.grid_status_label.winfo_exists(): return # 위젯 존재 확인
        
        total = len(self.data_manager.excel_data)
        completed = sum(1 for row in self.data_manager.excel_data if row.get('상태') == '완료')
        # '대기 중'과 '처리 중...' 상태를 합쳐서 '진행 중'으로 표시하거나, 별도 표시
        waiting = sum(1 for row in self.data_manager.excel_data if row.get('상태') == '대기 중')
        processing_now = sum(1 for row in self.data_manager.excel_data if row.get('상태') == '처리 중...')
        
        error_keywords = ['오류', '실패', '없음', '건너', '중단됨', '캡처 실패', '처리 오류', '종목코드 없음']
        errors = sum(1 for row in self.data_manager.excel_data if any(err_key in row.get('상태','') for err_key in error_keywords) and row.get('상태') != '완료')


        status_text = f"총 {total}행 | 완료: {completed} | 대기: {waiting}"
        if processing_now > 0: status_text += f" | 처리중: {processing_now}"
        status_text += f" | 오류: {errors}"
        self.grid_status_label.config(text=status_text)
        
        # 진행률은 '완료'된 항목 기준
        progress = (completed / total * 100) if total > 0 else 0
        if hasattr(self, 'grid_progress_label') and self.grid_progress_label.winfo_exists():
             self.grid_progress_label.config(text=f"진행률: {progress:.1f}%")


    def on_cell_double_click_ui(self, event):
        if not self.grid_tree: return

        if hasattr(self, '_editing_cell_entry') and self._editing_cell_entry.winfo_exists():
            # 이전 편집 위젯이 포커스를 잃으면서 _save_cell_edit_on_focus_out이 호출될 것이므로 여기서는 파괴만
            self._editing_cell_entry.destroy() 
            del self._editing_cell_entry

        item_id = self.grid_tree.identify_row(event.y)
        column_id_str = self.grid_tree.identify_column(event.x) # 예: #1, #2

        if not item_id or not column_id_str: return

        try: # column_id_str이 "#0" (헤더 외 영역)일 수 있음
            col_index = int(column_id_str.replace('#', '')) - 1
        except ValueError:
            return # 유효하지 않은 컬럼 ID

        if col_index < 0 or col_index >= len(self.grid_tree['columns']): return 

        col_name = self.grid_tree['columns'][col_index]
        
        # item_id ("row_X")에서 데이터 인덱스 X 추출
        try:
            row_index = int(item_id.replace("row_", ""))
        except ValueError:
            self.logger.warning(f"잘못된 item_id 형식: {item_id}")
            return

        if not (0 <= row_index < len(self.data_manager.excel_data)): return
        
        x, y, width, height = self.grid_tree.bbox(item_id, column_id_str)

        current_value = self.data_manager.excel_data[row_index].get(col_name, "")
        self._editing_cell_entry = tk.Entry(self.grid_tree, font=('Segoe UI', 9))
        # 테마 적용 필요
        self.theme_manager.register_widget(self._editing_cell_entry, {'bg': 'white', 'fg': 'on_surface', 'insertbackground': 'on_surface', 'relief': 'solid', 'bd':1})
        self.theme_manager.apply_theme_to_all_widgets() # 임시방편, 특정 위젯만 업데이트하는 함수가 더 좋음

        self._editing_cell_entry.place(x=x, y=y, width=width, height=height)
        self._editing_cell_entry.insert(0, str(current_value)) # 항상 문자열로 삽입
        self._editing_cell_entry.focus_set()
        self._editing_cell_entry.select_range(0, tk.END)

        # 현재 편집 중인 셀 정보 저장 (FocusOut 등에서 사용)
        self._current_edit_info = {'row_index': row_index, 'col_name': col_name, 'item_id': item_id, 'entry_widget': self._editing_cell_entry}

        self._editing_cell_entry.bind("<Return>", lambda e: self._save_cell_edit())
        self._editing_cell_entry.bind("<KP_Enter>", lambda e: self._save_cell_edit())
        self._editing_cell_entry.bind("<Escape>", lambda e: self._cancel_cell_edit())
        self._editing_cell_entry.bind("<FocusOut>", lambda e: self._save_cell_edit_on_focus_out())


    def _save_cell_edit_on_focus_out(self):
        # FocusOut 이벤트는 Escape보다 늦게 발생할 수 있음
        # _current_edit_info를 사용하여 현재 편집 중인 위젯인지 확인
        if hasattr(self, '_current_edit_info') and \
           self._current_edit_info['entry_widget'].winfo_exists():
            self._save_cell_edit()


    def _save_cell_edit(self):
        if not hasattr(self, '_current_edit_info'): return "break"
        
        edit_info = self._current_edit_info
        entry_widget = edit_info['entry_widget']
        
        if not entry_widget.winfo_exists(): # 위젯이 이미 파괴된 경우
            del self._current_edit_info # 정보 정리
            return "break"

        new_value = entry_widget.get()
        entry_widget.destroy() # 위젯 먼저 파괴

        row_idx = edit_info['row_index']
        col_name = edit_info['col_name']
        item_id = edit_info['item_id']

        if self.data_manager.update_grid_cell_data(row_idx, col_name, new_value):
            # Treeview 직접 업데이트
            updated_row_values = tuple(self.data_manager.excel_data[row_idx].get(cn, "") for cn in self.grid_tree['columns'])
            self.grid_tree.item(item_id, values=updated_row_values)
            # 상태 변경 시 태그도 업데이트 필요할 수 있음 (현재는 값만 변경)
            if col_name == '상태':
                 tags = self._get_tags_for_row(row_idx, self.data_manager.excel_data[row_idx])
                 self.grid_tree.item(item_id, tags=tags)
            self.update_grid_status_labels() # 상태 레이블 업데이트
        
        del self._current_edit_info # 편집 정보 정리
        return "break" 


    def _cancel_cell_edit(self):
        if hasattr(self, '_current_edit_info'):
            entry_widget = self._current_edit_info['entry_widget']
            if entry_widget.winfo_exists():
                entry_widget.destroy()
            del self._current_edit_info
        return "break"


    def show_context_menu_ui(self, event):
        if not self.grid_tree: return
        
        # 선택된 아이템이 없다면, 클릭된 위치의 아이템을 선택 시도
        item_id = self.grid_tree.identify_row(event.y)
        if item_id not in self.grid_tree.selection():
            self.grid_tree.selection_set(item_id) # 클릭된 아이템 선택

        context_menu = tk.Menu(self, tearoff=0)
        # 테마 적용 (ThemeManager에 등록하지 않고 직접 설정)
        context_menu.configure(
            bg=self.theme_manager.get_color('surface'), 
            fg=self.theme_manager.get_color('on_surface'),
            activebackground=self.theme_manager.get_color('primary'),
            activeforeground=self.theme_manager.get_color('white')
        )

        context_menu.add_command(label="➕ 행 추가", command=self.add_empty_row_ui)
        context_menu.add_command(label="🗑️ 선택 행 삭제", command=self.delete_selected_rows_ui, state=tk.NORMAL if self.grid_tree.selection() else tk.DISABLED)
        context_menu.add_separator()
        context_menu.add_command(label="📋 선택 행 복사 (Ctrl+C)", command=self.copy_selected_rows_ui, state=tk.NORMAL if self.grid_tree.selection() else tk.DISABLED)
        context_menu.add_command(label="📈 선택 행 금리 복사", command=self.copy_selected_rates_ui, state=tk.NORMAL if self.grid_tree.selection() else tk.DISABLED)
        context_menu.add_command(label="📝 클립보드에서 붙여넣기 (Ctrl+V)", command=self.paste_from_clipboard_ui)
        context_menu.add_separator()
        context_menu.add_command(label="🧹 전체 데이터 삭제", command=self.clear_all_data_ui)
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
            
    def quit_app(self):
        self.logger.info("애플리케이션 종료 시도...")
        if self.work_controller.is_running:
            self.logger.info("작업 진행 중, 강제 중단 및 종료 처리.")
            self.work_controller.stop_work() # 스레드에 중단 신호
            if self.worker_thread and self.worker_thread.is_alive():
                try:
                    self.worker_thread.join(timeout=1.0) # 최대 1초 대기
                    if self.worker_thread.is_alive():
                        self.logger.warning("작업 스레드가 시간 내에 종료되지 않았습니다.")
                except Exception as e:
                    self.logger.error(f"작업 스레드 join 중 오류: {e}")
        
        try:
            self.quick_save_settings() # 종료 전 현재 설정 저장
        except Exception as e:
            self.logger.error(f"종료 시 설정 저장 실패: {e}")
            
        self.destroy()
        self.logger.info("애플리케이션 종료됨.")


    def load_last_settings(self):
        try:
            settings = self.settings_manager.get_current_settings()
            if settings:
                self.apply_settings_to_ui(settings)
                self.input_excel_path.set(settings.get('input_excel_path', ''))
                # 출력 폴더 경로 정제하여 설정
                cleaned_output_path = self.ocr_workflow_manager._clean_folder_path(settings.get('output_folder_path', ''))
                self.output_folder_path.set(cleaned_output_path)
                
                self.logger.info("마지막 설정이 성공적으로 불러와졌습니다.")
            else: # 저장된 현재 설정이 없을 경우
                self.logger.info("저장된 현재 설정이 없습니다. 고급 설정 기본값을 사용합니다.")
                # settings_manager.data['advanced']는 이미 _get_default_advanced_settings로 초기화됨
                # UI에 고급 설정 기본값 반영
                self.skip_kbp_var.set(self.settings_manager.get_advanced('skip_kbp_code'))

            self.update_preset_combo() # 프리셋 콤보박스 업데이트
            # 테마 설정 (settings_manager에서 가져와 ThemeManager를 통해 적용)
            current_theme_key = self.settings_manager.get_advanced('ui_theme', 'modern_blue')
            self.theme_var.set(self.theme_manager.available_themes[current_theme_key]['name']) # 콤보박스 UI 업데이트
            self.theme_manager.change_theme(current_theme_key) # 실제 테마 변경 및 적용

        except Exception as e:
            self.logger.error(f"설정 불러오기 실패: {e}", exc_info=True)


    def quick_save_settings(self):
        try:
            current_settings = self.get_current_ui_settings() # UI 값 가져오기
            current_settings['input_excel_path'] = self.input_excel_path.get()
            current_settings['output_folder_path'] = self.output_folder_path.get()
            
            # 고급 설정은 save_advanced_ui_to_settings에서 이미 settings_manager에 저장됨
            # current_settings['advanced']는 UI에서 직접 제어하는 부분만 포함했으므로,
            # settings_manager.data['advanced']를 직접 current_settings에 병합하는 것이 더 정확할 수 있음
            # current_settings['advanced'] = self.settings_manager.data['advanced'].copy() 
            # 또는 get_current_ui_settings에서 advanced를 settings_manager.data['advanced']로 채우도록 수정

            self.settings_manager.save_current_settings(current_settings) # 'current' 키에 저장
            self.save_advanced_ui_to_settings() # UI의 고급 설정 항목도 settings_manager에 저장
            
            self.logger.info("현재 설정이 저장되었습니다.")
        except Exception as e:
            self.logger.error(f"설정 저장 실패: {e}", exc_info=True)
            messagebox.showerror("오류", f"설정 저장 중 오류가 발생했습니다: {e}", parent=self)


    def _create_section_frame_styled(self, parent, title, fill_parent=False):
        frame = tk.Frame(parent) # 테두리 역할을 할 외부 프레임
        self.theme_manager.register_widget(frame, {'bg': 'surface', 'relief': 'solid', 'bd': 1, 'padx':1, 'pady':1}) # 테두리 색상 테마 적용 위해 bd=1, relief=solid
        
        if fill_parent:
            frame.pack(fill='both', expand=True, padx=3, pady=3)
        else:
            frame.pack(fill='x', padx=3, pady=3)

        # 실제 내용이 들어갈 내부 프레임 (패딩용)
        inner_frame = tk.Frame(frame)
        self.theme_manager.register_widget(inner_frame, {'bg': 'surface', 'padx': 5, 'pady': 5})
        inner_frame.pack(fill='both', expand=True)


        title_lbl = tk.Label(inner_frame, text=title, anchor='w', font=('Segoe UI', 10, 'bold'))
        self.theme_manager.register_widget(title_lbl, {'bg': 'surface', 'fg': 'primary'})
        title_lbl.pack(fill='x', pady=(0, 5))

        content_frame = tk.Frame(inner_frame) # 실제 위젯들이 배치될 컨텐츠 프레임
        self.theme_manager.register_widget(content_frame, {'bg': 'white', 'padx': 3, 'pady': 3, 'relief': 'flat', 'bd': 0}) # 컨텐츠 프레임은 테두리 없음
        content_frame.pack(fill='both', expand=True)

        return content_frame


    def _finalize_processing_states(self):
        self.logger.info("[_finalize_processing_states] 함수 호출됨 (Main Thread)")
        try:
            changed = False
            for i, row_data in enumerate(self.data_manager.excel_data):
                current_status = row_data.get('상태', '대기 중')
                if current_status == '처리 중...' or current_status == '대기 중':
                    row_data['상태'] = '중단됨' # 데이터 직접 업데이트
                    changed = True
            if changed:
                 self.logger.info("일부 항목의 상태를 '중단됨'으로 최종화했습니다.")
            else:
                 self.logger.info("상태 최종화: 변경된 항목 없음.")
        except Exception as e:
            self.message_queue.put(("log", f"상태 최종화 중 오류: {e}", "ERROR"))
            self.logger.exception("처리 상태 최종화 중 예외 발생")


    def _finalize_export_and_complete(self, output_dir_str, input_excel_path_str, summary_message):
        self.logger.info("[_finalize_export_and_complete] 함수 호출됨 (Main Thread)")
        self._finalize_processing_states() 
        self.data_manager.export_grid_to_excel_data(output_dir_str, input_excel_path_str)
        self.refresh_grid_ui() # 최종 상태 반영
        self._on_work_complete_ui_only(summary_message) # UI 상태 정리 (메시지 박스 제외)
        messagebox.showinfo("처리 완료", summary_message, parent=self) # 메시지 박스는 여기서 표시


    def _generate_ocr_summary_internal(self, processed_count, total_items):
        # processed_count는 스레드에서 성공적으로 '완료'된 항목 수
        # DataManager의 데이터를 기반으로 최종 통계 생성
        date_success = sum(1 for row in self.data_manager.excel_data if row.get('날짜','').strip() and row.get('상태') == '완료')
        rate_success = sum(1 for row in self.data_manager.excel_data if row.get('금리','').strip() and row.get('상태') == '완료')
        
        # 실제 '완료' 상태인 항목 수 (KBP 건너뛰기 등 포함)
        actual_completed_for_stats = sum(1 for row in self.data_manager.excel_data if row.get('상태') == '완료')
        
        # 정확도 계산 시 분모는 실제 '완료'된 항목 수
        # date_accuracy = (date_success / actual_completed_for_stats * 100) if actual_completed_for_stats > 0 else 0
        # rate_accuracy = (rate_success / actual_completed_for_stats * 100) if actual_completed_for_stats > 0 else 0

        summary = f"""📊 OCR 처리 완료!
        ------------------------------------
        총 시도 항목: {total_items}개
        성공적으로 '완료'된 항목: {actual_completed_for_stats}개
        ------------------------------------
        📁 결과는 그리드 및 Excel 파일로 저장되었습니다.
        📝 상세 로그는 ocr_app.log 파일에서 확인 가능합니다.
        """
        return summary.replace("    ", "") # 들여쓰기 제거


    def _on_work_stopped(self): # 작업 중단 시 (사용자 또는 오류로 인해)
        self.logger.info("[_on_work_stopped] 함수 호출됨 (Main Thread)")
        self.work_controller.reset() 
        self.data_manager.current_processing_index = -1
        self._finalize_processing_states() # '처리 중' -> '중단됨'으로 변경
        self.refresh_grid_ui() # 변경된 상태 UI에 반영
        messagebox.showinfo("중단됨", "작업이 중단되었습니다.", parent=self)
        self.quick_save_settings() # 중단 시에도 설정 저장


if __name__ == "__main__":
    # Pyperclip이 클립보드에 접근할 수 없는 환경(예: 일부 Linux Wayland 세션)에 대한 예외 처리 추가 고려
    # pyautogui.FAILSAFE = False # 개발 중에는 True 권장
    try:
        app = CheckCaptureOCRApp()
        app.mainloop()
    except Exception as e:
        # 최상위 예외 로깅 (예: Tkinter 초기화 실패 등)
        logging.basicConfig(filename='ocr_app_critical_error.log', level=logging.ERROR,
                            format='%(asctime)s - %(levelname)s - %(message)s')
        logging.exception("애플리케이션 실행 중 치명적 오류 발생")
        # 사용자에게 간단한 오류 메시지 표시 (GUI가 뜨지 않았을 수 있으므로 print)
        print(f"치명적 오류 발생: {e}. 상세 내용은 ocr_app_critical_error.log 파일을 확인하세요.")

