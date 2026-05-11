"""Grid data manager used by the legacy Tk controller."""

from __future__ import annotations

from typing import Any

from .excel_io import export_grid_rows, load_grid_rows
from .exceptions import ExcelIOError
from .paths import updated_workbook_path
from .table_model import delete_rows, empty_row, rows_from_clipboard


class DataManager:
    def __init__(self, app_ref: Any, logger: Any, message_queue: Any) -> None:
        self.app = app_ref
        self.logger = logger
        self.message_queue = message_queue
        self.excel_data: list[dict[str, str]] = []
        self.current_processing_index = -1

    def load_excel_to_grid_data(self, file_path: Any) -> int:
        try:
            new_data, missing_columns = load_grid_rows(file_path)
            self.clear_all_data_internal()
            for target_col in missing_columns:
                self.logger.warning(f"Excel 파일에 '{target_col}'에 해당하는 컬럼을 찾을 수 없습니다.")
            self.excel_data = new_data
            return len(self.excel_data)
        except (OSError, ValueError, ImportError, ExcelIOError) as exc:
            self.logger.exception("Excel 파일 로드 실패")
            self.message_queue.put(("error_messagebox", "Excel 파일 로드 중 오류", f"{exc}"))
            return 0

    def add_empty_row_data(self) -> None:
        self.excel_data.append(empty_row())

    def paste_from_clipboard_data(self, clipboard_content: str | None) -> int:
        try:
            if clipboard_content is None:
                raise ValueError("클립보드 내용이 비어 있습니다.")
            rows = rows_from_clipboard(clipboard_content)
            self.excel_data.extend(rows)
            return len(rows)
        except (AttributeError, TypeError, ValueError) as exc:
            self.logger.exception("클립보드 붙여넣기 실패")
            self.message_queue.put(("error_messagebox", "붙여넣기 중 오류", f"{exc}"))
            return 0

    def delete_rows_data(self, indices_to_delete: list[int]) -> None:
        delete_rows(self.excel_data, indices_to_delete)

    def clear_all_data_internal(self) -> None:
        self.excel_data.clear()
        self.current_processing_index = -1

    def update_grid_cell_data(self, row_index: int, col_name: str, new_value: str) -> bool:
        if 0 <= row_index < len(self.excel_data):
            self.excel_data[row_index][col_name] = new_value
            return True
        return False

    def export_grid_to_excel_data(self, output_dir: Any, input_file_path_str: str) -> Any:
        if not self.excel_data:
            self.message_queue.put(("log", "내보낼 데이터가 없습니다.", "INFO"))
            return None

        new_file_path = updated_workbook_path(output_dir, input_file_path_str)

        try:
            self.logger.debug(f"[export_grid_to_excel_data] 내보내기 직전 데이터: {self.excel_data}")
            export_success_path = export_grid_rows(self.excel_data, new_file_path)
            self.message_queue.put(("log", f"결과 Excel 파일 저장 완료: {new_file_path}", "SUCCESS"))
            return export_success_path
        except (OSError, ValueError, ImportError, ExcelIOError) as exc:
            self.message_queue.put(("log", f"Excel 파일 저장 실패: {exc}", "ERROR"))
            self.logger.exception("Excel 파일 저장 중 예외 발생")
            raise
