from __future__ import annotations

import tkinter as tk

import pytest

from checkocr2.models import CODE_COL, NAME_COL, RATE_COL, STATUS_COL, STATUS_WAITING
from checkocr2.ui import grid_actions


class FakeTree:
    def __init__(self, items=None, selected=None):
        self.items = list(items or [])
        self.selected = tuple(selected or ())
        self.seen = []

    def get_children(self):
        return tuple(self.items)

    def see(self, item):
        self.seen.append(item)

    def selection(self):
        return self.selected

    def index(self, item):
        return self.items.index(item)


class FakeDataManager:
    def __init__(self):
        self.excel_data = []
        self.added = 0
        self.paste_result = 0
        self.deleted = []
        self.cleared = False

    def add_empty_row_data(self):
        self.added += 1

    def paste_from_clipboard_data(self, content):
        self.pasted_content = content
        return self.paste_result

    def delete_rows_data(self, indices):
        self.deleted.append(list(indices))

    def clear_all_data_internal(self):
        self.cleared = True


class FakeLogger:
    def __init__(self):
        self.messages = []

    def info(self, message):
        self.messages.append(message)


class FakeMessageBox:
    def __init__(self, *, askyesno=True):
        self.askyesno_result = askyesno
        self.calls = []

    def showinfo(self, *args, **kwargs):
        self.calls.append(("info", args, kwargs))

    def showwarning(self, *args, **kwargs):
        self.calls.append(("warning", args, kwargs))

    def showerror(self, *args, **kwargs):
        self.calls.append(("error", args, kwargs))

    def askyesno(self, *args, **kwargs):
        self.calls.append(("askyesno", args, kwargs))
        return self.askyesno_result


class FakeApp:
    def __init__(self):
        self.data_manager = FakeDataManager()
        self.grid_tree = FakeTree(["i0", "i1"], selected=["i0", "i1"])
        self.logger = FakeLogger()
        self.refresh_count = 0
        self.clipboard = ""
        self.clipboard_get_value = "A001\tAlpha"

    def refresh_grid_ui(self):
        self.refresh_count += 1

    def clipboard_get(self):
        return self.clipboard_get_value

    def clipboard_clear(self):
        self.clipboard = ""

    def clipboard_append(self, text):
        self.clipboard += text


@pytest.fixture
def fake_messagebox(monkeypatch):
    box = FakeMessageBox()
    monkeypatch.setattr(grid_actions, "messagebox", box)
    return box


def test_add_empty_row_refreshes_and_scrolls_to_last_row():
    app = FakeApp()

    grid_actions.add_empty_row(app)

    assert app.data_manager.added == 1
    assert app.refresh_count == 1
    assert app.grid_tree.seen == ["i1"]


def test_paste_from_clipboard_refreshes_reports_and_scrolls(fake_messagebox):
    app = FakeApp()
    app.data_manager.paste_result = 2

    grid_actions.paste_from_clipboard(app)

    assert app.data_manager.pasted_content == "A001\tAlpha"
    assert app.refresh_count == 1
    assert app.grid_tree.seen == ["i1"]
    assert fake_messagebox.calls[0][0] == "info"
    assert fake_messagebox.calls[0][1][0:2] == ("성공", "2행을 추가했습니다.")
    assert fake_messagebox.calls[0][2]["parent"] is app


def test_paste_from_clipboard_warns_for_no_added_rows(fake_messagebox):
    app = FakeApp()
    app.data_manager.paste_result = 0

    grid_actions.paste_from_clipboard(app)

    assert app.refresh_count == 0
    assert fake_messagebox.calls[0][0] == "warning"
    assert fake_messagebox.calls[0][1] == (
        "경고",
        "붙여넣을 유효한 데이터가 없습니다 (탭으로 구분된 데이터 필요).",
    )


def test_paste_from_clipboard_reports_tcl_clipboard_error(fake_messagebox):
    app = FakeApp()
    app.clipboard_get = lambda: (_ for _ in ()).throw(tk.TclError("empty"))

    grid_actions.paste_from_clipboard(app)

    assert fake_messagebox.calls[0][0] == "error"
    assert fake_messagebox.calls[0][1] == ("오류", "클립보드에 텍스트 데이터가 없습니다.")


def test_delete_selected_rows_respects_confirmation(monkeypatch):
    app = FakeApp()
    box = FakeMessageBox(askyesno=False)
    monkeypatch.setattr(grid_actions, "messagebox", box)

    grid_actions.delete_selected_rows(app)

    assert app.data_manager.deleted == []
    assert app.refresh_count == 0
    assert box.calls[0][1] == ("확인", "2개의 행을 삭제하시겠습니까?")

    box.askyesno_result = True
    grid_actions.delete_selected_rows(app)

    assert app.data_manager.deleted == [[0, 1]]
    assert app.refresh_count == 1


def test_delete_selected_rows_uses_selection_confirmed_before_dialog(monkeypatch):
    app = FakeApp()

    class ChangingMessageBox(FakeMessageBox):
        def askyesno(self, *args, **kwargs):
            app.grid_tree.selected = ("i1",)
            return super().askyesno(*args, **kwargs)

    monkeypatch.setattr(grid_actions, "messagebox", ChangingMessageBox())

    grid_actions.delete_selected_rows(app)

    assert app.data_manager.deleted == [[0, 1]]


def test_clear_all_data_prompts_only_when_rows_exist(monkeypatch):
    app = FakeApp()
    app.data_manager.excel_data = [{CODE_COL: "A001"}]
    box = FakeMessageBox(askyesno=False)
    monkeypatch.setattr(grid_actions, "messagebox", box)

    grid_actions.clear_all_data(app)

    assert app.data_manager.cleared is False
    assert box.calls[0][1] == (
        "확인",
        "모든 데이터를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.",
    )

    app.data_manager.excel_data = []
    grid_actions.clear_all_data(app)

    assert app.data_manager.cleared is True
    assert app.refresh_count == 1


def test_copy_selected_rows_and_rates_write_clipboard(fake_messagebox):
    app = FakeApp()
    app.data_manager.excel_data = [
        {CODE_COL: "A001", NAME_COL: "Alpha", RATE_COL: "3.500", STATUS_COL: STATUS_WAITING},
        {CODE_COL: "B002", NAME_COL: "Beta", RATE_COL: "", STATUS_COL: STATUS_WAITING},
    ]

    grid_actions.copy_selected_rows(app)

    assert app.clipboard.startswith("A001\tAlpha")
    assert "B002\tBeta" in app.clipboard
    assert app.logger.messages[-1] == "2개 행이 클립보드에 복사되었습니다."

    app.clipboard = ""
    grid_actions.copy_selected_rates(app)

    assert app.clipboard == "3.500\n"
    assert app.logger.messages[-1] == "선택된 2개 행의 금리가 클립보드에 복사되었습니다."


def test_copy_selected_rates_warns_when_no_selection(fake_messagebox):
    app = FakeApp()
    app.grid_tree = FakeTree(["i0"], selected=[])

    grid_actions.copy_selected_rates(app)

    assert fake_messagebox.calls[0][0] == "warning"
    assert fake_messagebox.calls[0][1] == ("경고", "복사할 행을 선택해주세요.")
