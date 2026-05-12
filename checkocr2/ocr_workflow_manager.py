"""OCR workflow manager compatibility adapter."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter

import numpy as np
from PIL import Image

from checkocr2.capture_adapter import capture_screenshots
from checkocr2.image_processing import cleanup_temp_ocr_image, upscale_image_source
from checkocr2.ocr_engine import (
    confidence_is_accepted,
    extract_text_with_confidence,
    normalize_confidence_threshold,
    read_ocr_text,
)
from checkocr2.ocr_field_analysis import analyze_date_field, analyze_rate_field
from checkocr2.ocr_field_extraction import extract_ocr_field_text
from checkocr2.ocr_pair_processing import process_ocr_image_pair
from checkocr2.ocr_reader_lifecycle import initialize_easyocr_reader_with_fallback
from checkocr2.ocr_runtime_options import minimum_confidence, ocr_detail_level
from checkocr2.ocr_text import (
    clean_date_text,
    clean_rate_text,
    is_valid_date_format,
    is_valid_rate_format,
)
from checkocr2.run_report import write_run_report
from checkocr2.screen_automation import click, copy_text, hotkey, screenshot
from checkocr2.ui.completion_actions import build_ocr_summary as build_ocr_summary_action
from checkocr2.ui.completion_actions import (
    finalize_export_and_complete as finalize_export_and_complete_action,
)
from checkocr2.ui.completion_actions import (
    finalize_processing_states_for_app as finalize_processing_states_action,
)
from checkocr2.workflow_execution import (
    WorkflowExecutionCallbacks,
    execute_legacy_workflow,
)
from checkocr2.workflow_report_finalization import (
    finalize_workflow_report_failure,
)


class OCRWorkflowManager:
    def __init__(
        self,
        app_ref,
        logger,
        message_queue,
        work_controller,
        settings_manager,
        data_manager,
        *,
        show_export_error: Callable[..., object] | None = None,
        show_export_info: Callable[..., object] | None = None,
    ):
        self.app = app_ref # CheckCaptureOCRApp 참조
        self.logger = logger
        self.message_queue = message_queue
        self.work_controller = work_controller
        self.settings_manager = settings_manager
        self.data_manager = data_manager # DataManager 인스턴스
        self.show_export_error = show_export_error
        self.show_export_info = show_export_info
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

            input_excel_file = self.app.input_excel_path.get()
            self._last_capture_timing = {}
            self._last_ocr_timings = {}
            self._last_ocr_confidences = {}

            def clear_ocr_tracking():
                self._last_ocr_timings = {}
                self._last_ocr_confidences = {}

            execute_legacy_workflow(
                ui_settings=ui_settings,
                output_dir=output_dir_str,
                input_excel_file=input_excel_file,
                rows=self.data_manager.excel_data,
                save_detail_images=save_detail_images_bool,
                skip_kbp_code=self.settings_manager.get_advanced('skip_kbp_code', True),
                message_queue=self.message_queue,
                data_manager=self.data_manager,
                work_controller=self.work_controller,
                logger=self.logger,
                callbacks=WorkflowExecutionCallbacks(
                    capture_screenshots=self._capture_screenshots_internal,
                    process_single_ocr=self._process_single_ocr_internal,
                    clear_ocr_tracking=clear_ocr_tracking,
                    get_capture_timing=lambda: self._last_capture_timing,
                    get_ocr_timings=lambda: self._last_ocr_timings,
                    get_ocr_confidences=lambda: self._last_ocr_confidences,
                    elapsed_ms=self._elapsed_ms,
                    flush_report=self._flush_current_run_report,
                    set_current_run_report=self._set_current_run_report,
                ),
            )

        except Exception as e_workflow:
            self.message_queue.put(("log", f"OCR 전체 워크플로우 오류: {e_workflow}", "ERROR"))
            self.logger.exception("OCR 전체 워크플로우에서 예외 발생")
            # 워크플로우 자체에서 예외 발생 시에도 중단 처리 및 stopped 메시지 보냄
            if self._current_run_report is not None:
                finalize_workflow_report_failure(
                    report=self._current_run_report,
                    rows=self.data_manager.excel_data,
                    error=str(e_workflow),
                    flush_report=self._flush_current_run_report,
                )
            if not self.work_controller.is_stopped:
                 self.work_controller.stop_work() # is_stopped 플래그 설정 및 stop_event 설정
            # 예외 발생 후에도 stopped 메시지를 보내 UI 상태를 중단됨으로 변경
            self.message_queue.put(("stopped", None))

    def _set_current_run_report(self, report, report_path):
        self._current_run_report = report
        self._current_run_report_path = report_path

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
        return process_ocr_image_pair(
            date_img_src,
            rate_img_src,
            save_details=save_details,
            extract_text=self._extract_text_with_ocr_attempts_internal,
            analyze_date=self._analyze_date_results_internal,
            analyze_rate=self._analyze_rate_results_internal,
            emit_log=lambda message, level: self.message_queue.put(("log", message, level)),
            logger=self.logger,
        )

    def _extract_text_with_ocr_attempts_internal(self, image_source, analysis_function, field_name, save_details):
        if self.work_controller.is_stopped:
            return ""
        field_key = "date" if "date" in getattr(analysis_function, "__name__", "") else "rate"
        result = extract_ocr_field_text(
            image_source,
            reader=self.ocr_reader,
            field_key=field_key,
            field_name=field_name,
            save_details=save_details,
            get_advanced=self.settings_manager.get_advanced,
            get_detail_level=self._ocr_detail_level,
            get_min_confidence=self._minimum_confidence,
            is_stopped=lambda: self.work_controller.is_stopped,
            emit_log=lambda message, level: self.message_queue.put(("log", message, level)),
            analyze_text=analysis_function,
            apply_upscaling=self._apply_image_upscaling,
            logger=self.logger,
            record_timing=lambda name, value: self._last_ocr_timings.__setitem__(name, value),
            record_confidence=lambda value: self._last_ocr_confidences.__setitem__(
                f"{field_key}_confidence",
                value,
            ),
            array_factory=np.array,
            read_ocr_text_func=read_ocr_text,
            extract_text_with_confidence_func=extract_text_with_confidence,
            confidence_is_accepted_func=confidence_is_accepted,
            normalize_confidence_threshold_func=normalize_confidence_threshold,
            cleanup_temp_ocr_image_func=cleanup_temp_ocr_image,
        )
        return result.value

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
            showerror=getattr(self, "show_export_error", None),
            showinfo=getattr(self, "show_export_info", None),
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
