import os
import queue
import threading
import tkinter as tk
from time import perf_counter
from tkinter import messagebox

import numpy as np
from PIL import Image

from checkocr2.capture_adapter import capture_screenshots
from checkocr2.data_manager import DataManager
from checkocr2.events import parse_legacy_grid_update
from checkocr2.exceptions import OCREngineError
from checkocr2.image_processing import upscale_image_source
from checkocr2.logging_config import setup_logging
from checkocr2.ocr_engine import (
    confidence_is_accepted,
    extract_text_with_confidence,
    normalize_confidence_threshold,
    read_ocr_text,
)
from checkocr2.ocr_field_analysis import analyze_date_field, analyze_rate_field
from checkocr2.ocr_reader_lifecycle import initialize_easyocr_reader_with_fallback
from checkocr2.ocr_runtime_options import (
    minimum_confidence,
    ocr_detail_level,
)
from checkocr2.ocr_text import (
    clean_date_text,
    clean_rate_text,
    is_valid_date_format,
    is_valid_rate_format,
)
from checkocr2.paths import clean_folder_path
from checkocr2.run_report import (
    create_run_report,
    finalize_run_report,
    record_row_reports,
    report_output_path,
    write_run_report,
)
from checkocr2.runtime_state import RuntimeState
from checkocr2.screen_automation import click, copy_text, hotkey, screenshot
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
from checkocr2.workflow import (
    CapturedImages,
    OcrResult,
    WorkflowOptions,
    WorkflowRunner,
)
from checkocr2.workflow import (
    finalize_processing_states as finalize_workflow_processing_states,
)


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
        self.ocr_reader = initialize_easyocr_reader_with_fallback(
            logger=self.logger,
            settings_manager=self.settings_manager,
            message_queue=self.message_queue,
        )

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
                    grid_update = parse_legacy_grid_update(legacy_event[1])
                    row_index = grid_update.row_index
                    if grid_update.update_type == "processing":
                        row_started_by_index[row_index] = perf_counter()
                        self.data_manager.current_processing_index = row_index
                    elif grid_update.update_type in {"complete", "error"} and row_index in row_started_by_index:
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
        except (OSError, TypeError, ValueError) as report_error:
            self.message_queue.put(("log", f"OCR run report save failed: {report_error}", "WARNING"))
            self.logger.exception("OCR run report save failed")

    @staticmethod
    def _elapsed_ms(started_at):
        return round((perf_counter() - started_at) * 1000, 3)

    def _capture_screenshots_internal(self, stock_code, save_folder, coords, paste_d, load_d, save_details):
        result = capture_screenshots(
            stock_code,
            save_folder,
            coords,
            paste_d,
            load_d,
            save_details,
            work_controller=self.work_controller,
            settings_manager=self.settings_manager,
            message_queue=self.message_queue,
            copy_text_func=copy_text,
            click_func=click,
            hotkey_func=hotkey,
            screenshot_func=screenshot,
        )
        self._last_capture_timing = result.timing_ms
        return result.date_image, result.rate_image

    def _process_single_ocr_internal(self, date_img_src, rate_img_src, save_details):
        date_result, rate_result = "", ""
        try:
            if date_img_src:
                date_result = self._extract_text_with_ocr_attempts_internal(date_img_src, self._analyze_date_results_internal, "날짜", save_details)
            if rate_img_src:
                rate_result = self._extract_text_with_ocr_attempts_internal(rate_img_src, self._analyze_rate_results_internal, "금리", save_details)
        except (OSError, RuntimeError, TypeError, ValueError, OCREngineError) as e:
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
        except (OSError, RuntimeError, TypeError, ValueError, OCREngineError) as e:
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
                    except OSError as e_remove:
                        self.message_queue.put(("log", f"임시 {field_name} 이미지 파일 삭제 실패: {e_remove}", "WARNING"))

    def _ocr_detail_level(self):
        return ocr_detail_level(self.settings_manager)

    def _minimum_confidence(self, field_key):
        return minimum_confidence(self.settings_manager, field_key)
    
    def _analyze_date_results_internal(self, raw_text, field_name="날짜"):
        result = analyze_date_field(raw_text, field_name)
        for message, level in result.log_events:
            self.message_queue.put(("log", message, level))
        return result.value

    def _analyze_rate_results_internal(self, raw_text, field_name="금리"):
        result = analyze_rate_field(raw_text, field_name)
        for message, level in result.log_events:
            self.message_queue.put(("log", message, level))
        return result.value

    def _is_valid_date_format_internal(self, date_str):
        return is_valid_date_format(date_str)

    def _is_valid_rate_format_internal(self, rate_str):
        return is_valid_rate_format(rate_str)

    def _clean_date_text_internal(self, text):
        return clean_date_text(text)


    def _clean_rate_text_internal(self, text):
        return clean_rate_text(text)

    def _generate_ocr_summary_internal(self, processed_count, total_items):
        return build_ocr_summary_action(self.data_manager.excel_data, total_items)

    def _finalize_processing_states(self):
        finalize_processing_states_action(self)

    # 엑셀 내보내기 및 최종 완료 처리를 담당하는 함수 (메인 스레드에서 호출됨)
    def _finalize_export_and_complete(self, output_dir_str, input_excel_path_str, summary_message):
        finalize_export_and_complete_action(
            self.app,
            output_dir_str,
            input_excel_path_str,
            summary_message,
            report_manager=self,
            reset_work_state=False,
            showerror=messagebox.showerror,
            showinfo=messagebox.showinfo,
        )

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
            result = upscale_image_source(
                image_source,
                enabled=enable_upscaling,
                factor=upscaling_factor,
                method=upscaling_method,
            )
            original_width, original_height = result.original_size
            new_width, new_height = result.new_size
            if result.was_upscaled:
                self.message_queue.put(("log", f"이미지 업스케일링 완료: {original_width}x{original_height} → {new_width}x{new_height} ({upscaling_method})", "DEBUG"))
            
            return result.image
            
        except (AttributeError, OSError, TypeError, ValueError) as e:
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
