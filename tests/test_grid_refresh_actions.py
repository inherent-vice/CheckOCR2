from __future__ import annotations

from checkocr2.models import (
    CODE_COL,
    DATE_COL,
    NAME_COL,
    RATE_COL,
    STATUS_COL,
    STATUS_DONE,
    STATUS_ERROR_PROCESSING,
    STATUS_WAITING,
)
from checkocr2.ui import grid_refresh_actions


class FakeTree:
    def __init__(self, children=("old0", "old1")):
        self.children = list(children)
        self.deleted = []
        self.inserted = []

    def get_children(self):
        return tuple(self.children)

    def delete(self, item):
        self.deleted.append(item)

    def insert(self, parent, index, *, values, tags):
        self.inserted.append((parent, index, values, tags))


class FakeLabel:
    def __init__(self):
        self.config_calls = []

    def config(self, **kwargs):
        self.config_calls.append(kwargs)


class FakeDataManager:
    def __init__(self):
        self.current_processing_index = 1
        self.excel_data = [
            {
                CODE_COL: "A001",
                NAME_COL: "Alpha",
                DATE_COL: "2026/05/11",
                RATE_COL: "3.500",
                STATUS_COL: STATUS_DONE,
            },
            {
                CODE_COL: "B002",
                NAME_COL: "Beta",
                DATE_COL: "",
                RATE_COL: "",
                STATUS_COL: STATUS_WAITING,
            },
            {
                CODE_COL: "C003",
                NAME_COL: "Gamma",
                DATE_COL: "",
                RATE_COL: "",
                STATUS_COL: STATUS_ERROR_PROCESSING,
            },
        ]


class FakeWorkController:
    is_running = True


class FakeApp:
    def __init__(self):
        self.grid_tree = FakeTree()
        self.data_manager = FakeDataManager()
        self.work_controller = FakeWorkController()
        self.grid_status_label = FakeLabel()
        self.grid_progress_label = FakeLabel()
        self.status_refresh_count = 0

    def update_grid_status_labels(self):
        self.status_refresh_count += 1


def test_refresh_grid_rebuilds_tree_rows_and_refreshes_status():
    app = FakeApp()

    grid_refresh_actions.refresh_grid(app)

    assert app.grid_tree.deleted == ["old0", "old1"]
    assert app.grid_tree.inserted == [
        ("", "end", ("A001", "Alpha", "2026/05/11", "3.500", STATUS_DONE), ("completed",)),
        ("", "end", ("B002", "Beta", "", "", STATUS_WAITING), ("processing",)),
        ("", "end", ("C003", "Gamma", "", "", STATUS_ERROR_PROCESSING), ("error",)),
    ]
    assert app.status_refresh_count == 1


def test_refresh_grid_noops_without_grid_tree():
    app = FakeApp()
    app.grid_tree = None

    grid_refresh_actions.refresh_grid(app)

    assert app.status_refresh_count == 0


def test_update_grid_status_labels_writes_current_summary_and_progress():
    app = FakeApp()

    grid_refresh_actions.update_grid_status_labels(app)

    assert app.grid_status_label.config_calls == [{"text": "총 3행 | 완료: 1 | 대기: 1 | 오류: 1"}]
    assert app.grid_progress_label.config_calls == [{"text": "진행률: 33.3%"}]


def test_update_grid_status_labels_noops_without_status_label():
    app = FakeApp()
    del app.grid_status_label

    grid_refresh_actions.update_grid_status_labels(app)

    assert app.grid_progress_label.config_calls == []


def test_update_grid_status_labels_allows_missing_progress_label():
    app = FakeApp()
    del app.grid_progress_label

    grid_refresh_actions.update_grid_status_labels(app)

    assert app.grid_status_label.config_calls == [{"text": "총 3행 | 완료: 1 | 대기: 1 | 오류: 1"}]


def test_legacy_app_grid_refresh_methods_delegate(ocr_module, monkeypatch):
    app = object.__new__(ocr_module.CheckCaptureOCRApp)
    calls = []

    monkeypatch.setattr(ocr_module, "refresh_grid_action", lambda actual_app: calls.append(("refresh", actual_app)))
    monkeypatch.setattr(
        ocr_module,
        "update_grid_status_labels_action",
        lambda actual_app: calls.append(("status", actual_app)),
    )

    app.refresh_grid_ui()
    app.update_grid_status_labels()

    assert calls == [("refresh", app), ("status", app)]
