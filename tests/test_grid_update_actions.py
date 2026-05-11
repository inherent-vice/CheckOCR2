from __future__ import annotations

from checkocr2.models import (
    CODE_COL,
    DATE_COL,
    NAME_COL,
    RATE_COL,
    STATUS_COL,
    STATUS_DONE,
    STATUS_PROCESSING,
    STATUS_WAITING,
)
from checkocr2.ui.grid_update_actions import handle_grid_update


class FakeTree:
    def __init__(self, children=("i0", "i1")):
        self.children = tuple(children)
        self.seen = []

    def get_children(self):
        return self.children

    def see(self, item):
        self.seen.append(item)


class FakeLogger:
    def __init__(self):
        self.debugs = []
        self.errors = []

    def debug(self, message):
        self.debugs.append(message)

    def error(self, message):
        self.errors.append(message)


class FakeDataManager:
    def __init__(self):
        self.excel_data = [
            {CODE_COL: "A001", NAME_COL: "Alpha", DATE_COL: "", RATE_COL: "", STATUS_COL: STATUS_WAITING},
            {CODE_COL: "B002", NAME_COL: "Beta", DATE_COL: "", RATE_COL: "", STATUS_COL: STATUS_WAITING},
        ]


class FakeApp:
    def __init__(self):
        self.data_manager = FakeDataManager()
        self.grid_tree = FakeTree()
        self.logger = FakeLogger()
        self.refresh_count = 0

    def refresh_grid_ui(self):
        self.refresh_count += 1


def test_handle_grid_update_scrolls_processing_row_and_refreshes():
    app = FakeApp()

    handle_grid_update(app, ("processing", 1))

    assert app.data_manager.excel_data[1][STATUS_COL] == STATUS_PROCESSING
    assert app.grid_tree.seen == ["i1"]
    assert app.refresh_count == 1
    assert app.logger.debugs[-1].startswith("[_handle_grid_update] 1번 항목 업데이트 후:")


def test_handle_grid_update_completes_row_without_scroll():
    app = FakeApp()

    handle_grid_update(app, ("complete", 0, "2026/05/11", "3.500", STATUS_DONE))

    assert app.data_manager.excel_data[0][DATE_COL] == "2026/05/11"
    assert app.data_manager.excel_data[0][RATE_COL] == "3.500"
    assert app.data_manager.excel_data[0][STATUS_COL] == STATUS_DONE
    assert app.grid_tree.seen == []
    assert app.refresh_count == 1


def test_handle_grid_update_skips_scroll_when_tree_row_missing():
    app = FakeApp()
    app.grid_tree = FakeTree(children=("i0",))

    handle_grid_update(app, ("processing", 1))

    assert app.grid_tree.seen == []
    assert app.refresh_count == 1


def test_handle_grid_update_logs_bad_payload_without_raising():
    app = FakeApp()

    handle_grid_update(app, ("processing",))

    assert app.refresh_count == 0
    assert app.logger.errors == [
        "그리드 업데이트 중 오류: grid update payload requires update type and row index, 데이터: ('processing',)"
    ]


def test_legacy_app_grid_update_method_delegates(ocr_module, monkeypatch):
    app = object.__new__(ocr_module.CheckCaptureOCRApp)
    calls = []

    monkeypatch.setattr(ocr_module, "handle_grid_update", lambda actual_app, data: calls.append((actual_app, data)))

    app._handle_grid_update(("processing", 0))

    assert calls == [(app, ("processing", 0))]
