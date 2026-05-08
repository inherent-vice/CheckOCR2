from __future__ import annotations

from types import SimpleNamespace

from checkocr2.ui.panels import grid_panel


class FakeWidget:
    created = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.pack_calls = []
        self.grid_calls = []
        self.grid_rowconfigure_calls = []
        self.grid_columnconfigure_calls = []
        self.__class__.created.append(self)

    def pack(self, **kwargs):
        self.pack_calls.append(kwargs)

    def grid(self, **kwargs):
        self.grid_calls.append(kwargs)

    def grid_rowconfigure(self, index, **kwargs):
        self.grid_rowconfigure_calls.append((index, kwargs))

    def grid_columnconfigure(self, index, **kwargs):
        self.grid_columnconfigure_calls.append((index, kwargs))


class FakeFrame(FakeWidget):
    created = []


class FakeButton(FakeWidget):
    created = []


class FakeLabel(FakeWidget):
    created = []


class FakeTreeview(FakeWidget):
    created = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.headings = []
        self.columns = []
        self.configure_calls = []
        self.bind_calls = []

    def heading(self, column, **kwargs):
        self.headings.append((column, kwargs))

    def column(self, column, **kwargs):
        self.columns.append((column, kwargs))

    def configure(self, **kwargs):
        self.configure_calls.append(kwargs)

    def bind(self, sequence, callback):
        self.bind_calls.append((sequence, callback))

    def yview(self, *args, **kwargs):
        return None

    def xview(self, *args, **kwargs):
        return None


class FakeScrollbar(FakeWidget):
    created = []

    def set(self, *args, **kwargs):
        return None


class FakeThemeManager:
    def __init__(self):
        self.registered = []

    def register_widget(self, widget, style_config):
        self.registered.append((widget, style_config))


class FakeApp:
    def __init__(self):
        self.theme_manager = FakeThemeManager()
        self.sections = []
        self.grid_tree = None
        self.grid_status_label = None
        self.grid_progress_label = None
        self.refresh_count = 0

    def _create_section_frame_styled(self, parent, title, fill_parent=False):
        section = FakeFrame(parent, title=title, fill_parent=fill_parent)
        self.sections.append((parent, title, fill_parent, section))
        return section

    def load_excel_to_grid(self):
        raise AssertionError("construction must not load Excel")

    def add_empty_row_ui(self):
        raise AssertionError("construction must not add rows")

    def paste_from_clipboard_ui(self):
        raise AssertionError("construction must not paste")

    def delete_selected_rows_ui(self):
        raise AssertionError("construction must not delete rows")

    def clear_all_data_ui(self):
        raise AssertionError("construction must not clear rows")

    def copy_selected_rows_ui(self):
        raise AssertionError("construction must not copy rows")

    def on_cell_double_click_ui(self, event):
        raise AssertionError("construction must not edit cells")

    def show_context_menu_ui(self, event):
        raise AssertionError("construction must not open context menu")

    def refresh_grid_tags(self):
        self.refresh_count += 1


def test_create_grid_panel_builds_tree_controls_and_status(monkeypatch):
    for widget_class in (FakeFrame, FakeButton, FakeLabel, FakeTreeview, FakeScrollbar):
        widget_class.created = []
    fake_tk = SimpleNamespace(Frame=FakeFrame, Button=FakeButton, Label=FakeLabel, YES=True)
    fake_ttk = SimpleNamespace(Treeview=FakeTreeview, Scrollbar=FakeScrollbar)
    monkeypatch.setattr(grid_panel, "tk", fake_tk)
    monkeypatch.setattr(grid_panel, "ttk", fake_ttk)
    app = FakeApp()
    parent = object()

    grid_panel.create_grid_panel(app, parent)

    assert app.sections[0][0:3] == (parent, "📊 Excel 데이터 그리드", True)
    assert [button.kwargs["text"] for button in FakeButton.created] == [
        "📁 Excel 로드",
        "➕ 행 추가",
        "📋 붙여넣기",
        "🗑️ 선택 삭제",
        "🧹 전체 삭제",
    ]
    assert [button.kwargs["command"] for button in FakeButton.created] == [
        app.load_excel_to_grid,
        app.add_empty_row_ui,
        app.paste_from_clipboard_ui,
        app.delete_selected_rows_ui,
        app.clear_all_data_ui,
    ]

    assert app.grid_tree is FakeTreeview.created[0]
    assert app.grid_tree.kwargs["columns"] == ("종목코드", "종목명", "날짜", "금리", "상태")
    assert app.grid_tree.kwargs["show"] == "headings"
    assert app.grid_tree.kwargs["style"] == "Treeview"
    assert [column for column, _kwargs in app.grid_tree.headings] == list(app.grid_tree.kwargs["columns"])
    assert app.grid_tree.columns[0] == (
        "종목코드",
        {"width": 95, "anchor": "center", "minwidth": 75, "stretch": True},
    )
    assert [sequence for sequence, _callback in app.grid_tree.bind_calls] == [
        "<Double-1>",
        "<Button-3>",
        "<Delete>",
        "<Control-c>",
        "<Control-v>",
    ]
    assert app.grid_tree.grid_calls[-1] == {"row": 0, "column": 0, "sticky": "nsew"}

    assert [label.kwargs["text"] for label in FakeLabel.created] == [
        "총 0행 | 완료: 0 | 대기: 0 | 오류: 0",
        "진행률: 0.0%",
    ]
    assert app.grid_status_label is FakeLabel.created[0]
    assert app.grid_progress_label is FakeLabel.created[1]
    assert app.refresh_count == 1
