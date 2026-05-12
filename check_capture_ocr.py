import queue
import threading
import tkinter as tk
from tkinter import messagebox

from checkocr2.data_manager import DataManager
from checkocr2.logging_config import setup_logging
from checkocr2.ocr_workflow_manager import OCRWorkflowManager
from checkocr2.paths import clean_folder_path
from checkocr2.runtime_state import RuntimeState
from checkocr2.settings_compat import UnifiedSettingsManager
from checkocr2.ui.completion_actions import (
    build_ocr_summary as build_ocr_summary_action,
)
from checkocr2.ui.completion_actions import (
    complete_stopped_work as complete_stopped_work_action,
)
from checkocr2.ui.completion_actions import (
    complete_work as complete_work_action,
)
from checkocr2.ui.completion_actions import (
    finalize_export_and_complete as finalize_export_and_complete_action,
)
from checkocr2.ui.completion_actions import (
    finalize_processing_states_for_app as finalize_processing_states_action,
)
from checkocr2.ui.coordinate_actions import (
    relocate_area as relocate_area_action,
)
from checkocr2.ui.coordinate_actions import (
    relocate_clickpoint as relocate_clickpoint_action,
)
from checkocr2.ui.coordinate_actions import (
    show_area_preview as show_area_preview_action,
)
from checkocr2.ui.dialogs import show_about_dialog, show_shortcuts_dialog
from checkocr2.ui.folder_actions import (
    browse_input_excel as browse_input_excel_action,
)
from checkocr2.ui.folder_actions import (
    browse_output_folder as browse_output_folder_action,
)
from checkocr2.ui.folder_actions import (
    load_excel_to_grid as load_excel_to_grid_action,
)
from checkocr2.ui.folder_actions import (
    open_output_folder as open_output_folder_action,
)
from checkocr2.ui.grid_actions import (
    add_empty_row,
    clear_all_data,
    copy_selected_rates,
    copy_selected_rows,
    delete_selected_rows,
    paste_from_clipboard,
    show_context_menu,
)
from checkocr2.ui.grid_edit_actions import (
    cancel_cell_edit,
    on_cell_double_click,
    save_cell_edit,
    save_cell_edit_on_focus_out,
)
from checkocr2.ui.grid_refresh_actions import (
    refresh_grid as refresh_grid_action,
)
from checkocr2.ui.grid_refresh_actions import (
    refresh_grid_tags as refresh_grid_tags_action,
)
from checkocr2.ui.grid_refresh_actions import (
    update_grid_status_labels as update_grid_status_labels_action,
)
from checkocr2.ui.grid_update_actions import handle_grid_update
from checkocr2.ui.icons import apply_application_icon
from checkocr2.ui.keyboard_actions import handle_f5_key as handle_f5_key_action
from checkocr2.ui.keyboard_actions import setup_keyboard_shortcuts
from checkocr2.ui.lifecycle_actions import quit_app as quit_app_action
from checkocr2.ui.log_actions import append_log_text
from checkocr2.ui.main_window import (
    build_main_window,
    create_center_excel_grid,
    create_coordinates_section,
    create_file_section,
    create_left_panel_content,
    create_menu_bar,
    create_options_section,
    create_preset_section,
    create_right_panel_content,
    create_timing_section,
    create_toolbar,
)
from checkocr2.ui.ocr_actions import (
    run_ocr_process as run_ocr_process_action,
)
from checkocr2.ui.ocr_actions import (
    stop_processing as stop_processing_action,
)
from checkocr2.ui.ocr_actions import (
    validate_inputs_for_ocr as validate_inputs_for_ocr_action,
)
from checkocr2.ui.ocr_initialization_actions import (
    start_ocr_initialization as start_ocr_initialization_action,
)
from checkocr2.ui.options_actions import (
    toggle_upscaling_details as toggle_upscaling_details_action,
)
from checkocr2.ui.overlays import (  # noqa: F401
    AreaVisualizationOverlay,
    DragCaptureOverlay,
    PointCaptureOverlay,
)
from checkocr2.ui.presets import (
    apply_selected_preset as apply_selected_preset_action,
)
from checkocr2.ui.presets import (
    delete_selected_preset as delete_selected_preset_action,
)
from checkocr2.ui.presets import (
    save_current_as_preset as save_current_as_preset_action,
)
from checkocr2.ui.presets import (
    update_preset_combo as update_preset_combo_action,
)
from checkocr2.ui.queue_dispatcher import process_legacy_message_queue, queue_check_interval
from checkocr2.ui.runtime_status_actions import (
    ready_or_error_state as ready_or_error_state_action,
)
from checkocr2.ui.runtime_status_actions import (
    set_ocr_ready_ui as set_ocr_ready_ui_action,
)
from checkocr2.ui.runtime_status_actions import (
    set_runtime_state as set_runtime_state_action,
)
from checkocr2.ui.runtime_status_actions import (
    write_package_smoke_status_for_app as write_package_smoke_status_action,
)
from checkocr2.ui.section_frame import (
    create_section_frame_styled as create_section_frame_action,
)
from checkocr2.ui.settings_actions import (
    load_last_settings as load_last_settings_action,
)
from checkocr2.ui.settings_actions import (
    quick_save_settings as quick_save_settings_action,
)
from checkocr2.ui.settings_actions import (
    reset_advanced_settings_and_ui as reset_advanced_settings_action,
)
from checkocr2.ui.settings_binding import (
    apply_ui_settings,
    collect_ui_settings,
    save_advanced_settings,
)
from checkocr2.ui.theme import ThemeManager
from checkocr2.ui.window_actions import center_window as center_window_action
from checkocr2.work_controller import WorkController


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
        start_ocr_initialization_action(self, thread_factory=threading.Thread)

    def _set_runtime_state(self, state):
        set_runtime_state_action(self, state)

    def _set_ocr_ready_ui(self, ready):
        set_ocr_ready_ui_action(self, ready)

    def _ready_or_error_state(self):
        return ready_or_error_state_action(self)

    def _write_package_smoke_status(self):
        write_package_smoke_status_action(self)

    def _setup_application_icon(self):
        apply_application_icon(self)

    def center_window(self):
        center_window_action(self)

    def _setup_keyboard_shortcuts(self):
        setup_keyboard_shortcuts(self)

    def handle_f5_key(self):
        handle_f5_key_action(self)

    def check_queue(self):
        process_legacy_message_queue(self, show_error=messagebox.showerror)
        check_interval = queue_check_interval(self.work_controller.is_running)
        self.after(check_interval, self.check_queue)

    def _update_log_text_widget(self, message, level_name="INFO"):
        append_log_text(self, message, level_name)

    def _build_ui(self):
        build_main_window(self)

    def _create_menu(self):
        create_menu_bar(self)

    def _create_simple_toolbar(self):
        create_toolbar(self)

    def _create_left_panel_content(self, parent):
        create_left_panel_content(self, parent)

    def _create_right_panel_content(self, parent):
        create_right_panel_content(self, parent)

    def _create_file_section(self, parent):
        create_file_section(self, parent)

    def _create_coordinates_section(self, parent):
        create_coordinates_section(self, parent)

    def _create_timing_section(self, parent):
        create_timing_section(self, parent)

    def _create_options_section(self, parent):
        create_options_section(self, parent)

    def _create_preset_section(self, parent):
        create_preset_section(self, parent)

    def _create_center_excel_grid(self, parent):
        create_center_excel_grid(self, parent)

    def refresh_grid_tags(self):
        refresh_grid_tags_action(self)

    def get_current_ui_settings(self):
        return collect_ui_settings(self)

    def apply_settings_to_ui(self, settings_dict):
        apply_ui_settings(self, settings_dict)

    def save_advanced_ui_to_settings(self):
        save_advanced_settings(self)

    def reset_advanced_settings_and_ui(self):
        reset_advanced_settings_action(self)

    def browse_input_excel(self):
        browse_input_excel_action(self)

    def _clean_output_folder_path(self, path: str | None) -> str:
        return clean_folder_path(
            path,
            default=self.settings_manager.get_advanced("default_output_dir", "."),
            logger=self.logger,
        )

    def browse_output_folder(self):
        browse_output_folder_action(self)

    def open_output_folder(self):
        open_output_folder_action(self)

    def relocate_clickpoint(self):
        relocate_clickpoint_action(self)

    def _relocate_area_generic(self, x1_var, y1_var, x2_var, y2_var, color_key):
        relocate_area_action(self, x1_var, y1_var, x2_var, y2_var, color_key)

    def relocate_allarea(self): self._relocate_area_generic(self.allarea_x1, self.allarea_y1, self.allarea_x2, self.allarea_y2, "primary")
    def relocate_datearea(self): self._relocate_area_generic(self.datearea_x1, self.datearea_y1, self.datearea_x2, self.datearea_y2, "success")
    def relocate_ratearea(self): self._relocate_area_generic(self.ratearea_x1, self.ratearea_y1, self.ratearea_x2, self.ratearea_y2, "warning")

    def update_preset_combo(self):
        update_preset_combo_action(self)

    def apply_selected_preset(self):
        apply_selected_preset_action(self)

    def save_current_as_preset(self):
        save_current_as_preset_action(self)

    def delete_selected_preset(self):
        delete_selected_preset_action(self)

    def show_area_preview(self):
        show_area_preview_action(self)

    def stop_processing_ui_initiated(self):
        stop_processing_action(self)

    def _on_work_complete_ui_only(self, summary_message):
        complete_work_action(self, summary_message)

    def _handle_grid_update(self, data):
        handle_grid_update(self, data)

    def show_shortcuts(self):
        show_shortcuts_dialog(parent=self)

    def show_about(self):
        show_about_dialog(parent=self)

    def run_ocr_process(self):
        run_ocr_process_action(self)

    def _validate_inputs_for_ocr(self):
        return validate_inputs_for_ocr_action(
            self,
            showerror=messagebox.showerror,
            showwarning=getattr(messagebox, "showwarning", messagebox.showinfo),
        )

    def load_excel_to_grid(self):
        load_excel_to_grid_action(self)

    def add_empty_row_ui(self):
        add_empty_row(self)

    def paste_from_clipboard_ui(self):
        paste_from_clipboard(self)

    def delete_selected_rows_ui(self):
        delete_selected_rows(self)

    def clear_all_data_ui(self):
        clear_all_data(self)

    def copy_selected_rows_ui(self):
        copy_selected_rows(self)

    def copy_selected_rates_ui(self):
        copy_selected_rates(self)

    def refresh_grid_ui(self):
        refresh_grid_action(self)

    def update_grid_status_labels(self):
        update_grid_status_labels_action(self)

    def on_cell_double_click_ui(self, event):
        on_cell_double_click(self, event)

    def _save_cell_edit_on_focus_out(self, row_index, col_name):
        save_cell_edit_on_focus_out(self, row_index, col_name)

    def _save_cell_edit(self, row_index, col_name):
        return save_cell_edit(self, row_index, col_name)

    def _cancel_cell_edit(self):
        return cancel_cell_edit(self)

    def show_context_menu_ui(self, event):
        show_context_menu(self, event)
            
    def quit_app(self):
        quit_app_action(self)

    def load_last_settings(self):
        load_last_settings_action(self)

    def quick_save_settings(self):
        """현재 UI 설정을 빠르게 저장"""
        quick_save_settings_action(self)

    def _create_section_frame_styled(self, parent, title, fill_parent=False):
        """스타일이 적용된 섹션 프레임을 생성하고 반환합니다."""
        return create_section_frame_action(self, parent, title, fill_parent=fill_parent)

    # DataManager 클래스의 finalize_processing_states 함수를 CheckCaptureOCRApp으로 옮김 (Worker 스레드가 아닌 Main 스레드에서 호출하기 위함)
    def _finalize_processing_states(self):
        finalize_processing_states_action(self)


    # 엑셀 내보내기 및 최종 완료 처리를 담당하는 함수 (메인 스레드에서 호출됨)
    def _finalize_export_and_complete(self, output_dir_str, input_excel_path_str, summary_message):
        finalize_export_and_complete_action(
            self,
            output_dir_str,
            input_excel_path_str,
            summary_message,
            showerror=messagebox.showerror,
            showinfo=messagebox.showinfo,
        )

    def _generate_ocr_summary_internal(self, processed_count, total_items):
        return build_ocr_summary_action(self.data_manager.excel_data, total_items)

    # 작업 중단 시 호출되는 함수 (Main Thread에서 호출)
    def _on_work_stopped(self):
        complete_stopped_work_action(self)

    def on_upscaling_toggle(self):
        toggle_upscaling_details_action(self)


if __name__ == "__main__":
    app = CheckCaptureOCRApp()
    app.protocol("WM_DELETE_WINDOW", app.quit_app)
    app.mainloop()
