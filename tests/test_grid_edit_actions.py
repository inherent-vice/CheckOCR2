from __future__ import annotations

from checkocr2.ui import grid_edit_actions


class FakeEntry:
    created = []

    def __init__(self, parent, *, font):
        self.parent = parent
        self.font = font
        self.exists = True
        self.place_calls = []
        self.insert_calls = []
        self.bindings = []
        self.focused = False
        self.selected_ranges = []
        self.value = ""
        self.destroy_count = 0
        self.__class__.created.append(self)

    def winfo_exists(self):
        return self.exists

    def destroy(self):
        self.exists = False
        self.destroy_count += 1

    def place(self, **kwargs):
        self.place_calls.append(kwargs)

    def insert(self, index, value):
        self.insert_calls.append((index, value))
        self.value = value

    def focus_set(self):
        self.focused = True

    def select_range(self, start, end):
        self.selected_ranges.append((start, end))

    def bind(self, sequence, callback):
        self.bindings.append((sequence, callback))

    def get(self):
        return self.value


class FakeTree:
    def __init__(self):
        self.columns = ("code", "name", "date")
        self.row_id = "row0"
        self.column_id = "#2"
        self.row_index = 0
        self.bbox_result = (11, 22, 133, 24)

    def identify_row(self, y):
        self.seen_y = y
        return self.row_id

    def identify_column(self, x):
        self.seen_x = x
        return self.column_id

    def __getitem__(self, key):
        if key != "columns":
            raise KeyError(key)
        return self.columns

    def index(self, item_id):
        assert item_id == self.row_id
        return self.row_index

    def bbox(self, item_id, column_id):
        assert item_id == self.row_id
        assert column_id == self.column_id
        return self.bbox_result


class FakeThemeManager:
    def __init__(self):
        self.registered = []
        self.apply_count = 0

    def register_widget(self, widget, style_config):
        self.registered.append((widget, style_config))

    def apply_theme_to_all_widgets(self):
        self.apply_count += 1


class FakeDataManager:
    def __init__(self):
        self.excel_data = [{"code": "A001", "name": "Alpha", "date": "2026/05/11"}]
        self.update_result = True
        self.updates = []

    def update_grid_cell_data(self, row_index, col_name, new_value):
        self.updates.append((row_index, col_name, new_value))
        if self.update_result:
            self.excel_data[row_index][col_name] = new_value
        return self.update_result


class FakeApp:
    def __init__(self):
        self.grid_tree = FakeTree()
        self.theme_manager = FakeThemeManager()
        self.data_manager = FakeDataManager()
        self.refresh_count = 0

    def refresh_grid_ui(self):
        self.refresh_count += 1

    def _save_cell_edit(self, row_index, col_name):
        self.save_call = (row_index, col_name)

    def _cancel_cell_edit(self):
        self.cancel_call = True

    def _save_cell_edit_on_focus_out(self, row_index, col_name):
        self.focus_out_call = (row_index, col_name)


class FakeEvent:
    x = 20
    y = 30


def test_on_cell_double_click_creates_entry_and_binds_legacy_edit_events(monkeypatch):
    FakeEntry.created = []
    monkeypatch.setattr(grid_edit_actions.tk, "Entry", FakeEntry)
    monkeypatch.setattr(grid_edit_actions.tk, "END", "end")
    app = FakeApp()

    grid_edit_actions.on_cell_double_click(app, FakeEvent())

    entry = FakeEntry.created[0]
    assert app._editing_cell_entry is entry
    assert entry.parent is app.grid_tree
    assert entry.font == ("Segoe UI", 9)
    assert app.theme_manager.registered == [
        (
            entry,
            {"bg": "white", "fg": "on_surface", "insertbackground": "on_surface", "relief": "solid", "bd": 1},
        )
    ]
    assert app.theme_manager.apply_count == 1
    assert entry.place_calls == [{"x": 11, "y": 22, "width": 133, "height": 24}]
    assert entry.insert_calls == [(0, "Alpha")]
    assert entry.focused is True
    assert entry.selected_ranges == [(0, "end")]
    assert [sequence for sequence, _callback in entry.bindings] == [
        "<Return>",
        "<KP_Enter>",
        "<Escape>",
        "<FocusOut>",
    ]
    assert app._current_edit_info == {"row_index": 0, "col_name": "name"}

    entry.bindings[0][1](object())
    entry.bindings[2][1](object())
    entry.bindings[3][1](object())

    assert app.save_call == (0, "name")
    assert app.cancel_call is True
    assert app.focus_out_call == (0, "name")


def test_on_cell_double_click_destroys_existing_entry_before_new_edit(monkeypatch):
    FakeEntry.created = []
    monkeypatch.setattr(grid_edit_actions.tk, "Entry", FakeEntry)
    monkeypatch.setattr(grid_edit_actions.tk, "END", "end")
    app = FakeApp()
    existing = FakeEntry(app.grid_tree, font=("old", 1))
    app._editing_cell_entry = existing

    grid_edit_actions.on_cell_double_click(app, FakeEvent())

    assert existing.destroy_count == 1
    assert app._editing_cell_entry is FakeEntry.created[-1]


def test_on_cell_double_click_noops_for_invalid_grid_targets(monkeypatch):
    FakeEntry.created = []
    monkeypatch.setattr(grid_edit_actions.tk, "Entry", FakeEntry)
    app = FakeApp()

    app.grid_tree.row_id = ""
    grid_edit_actions.on_cell_double_click(app, FakeEvent())

    app.grid_tree.row_id = "row0"
    app.grid_tree.column_id = ""
    grid_edit_actions.on_cell_double_click(app, FakeEvent())

    assert FakeEntry.created == []
    assert not hasattr(app, "_editing_cell_entry")


def test_save_cell_edit_updates_data_refreshes_and_clears_edit_state():
    app = FakeApp()
    entry = FakeEntry(app.grid_tree, font=("Segoe UI", 9))
    entry.value = "Beta"
    app._editing_cell_entry = entry
    app._current_edit_info = {"row_index": 0, "col_name": "name"}

    result = grid_edit_actions.save_cell_edit(app, 0, "name")

    assert result == "break"
    assert entry.destroy_count == 1
    assert not hasattr(app, "_editing_cell_entry")
    assert not hasattr(app, "_current_edit_info")
    assert app.data_manager.updates == [(0, "name", "Beta")]
    assert app.refresh_count == 1


def test_save_cell_edit_preserves_current_edit_info_when_update_rejected():
    app = FakeApp()
    app.data_manager.update_result = False
    entry = FakeEntry(app.grid_tree, font=("Segoe UI", 9))
    entry.value = "Beta"
    app._editing_cell_entry = entry
    app._current_edit_info = {"row_index": 0, "col_name": "name"}

    result = grid_edit_actions.save_cell_edit(app, 0, "name")

    assert result == "break"
    assert app.refresh_count == 0
    assert app._current_edit_info == {"row_index": 0, "col_name": "name"}


def test_focus_out_saves_only_when_entry_still_exists(monkeypatch):
    app = FakeApp()
    entry = FakeEntry(app.grid_tree, font=("Segoe UI", 9))
    app._editing_cell_entry = entry
    calls = []
    monkeypatch.setattr(app, "_save_cell_edit", lambda row_index, col_name: calls.append((row_index, col_name)))

    grid_edit_actions.save_cell_edit_on_focus_out(app, 0, "name")
    entry.exists = False
    grid_edit_actions.save_cell_edit_on_focus_out(app, 0, "name")

    assert calls == [(0, "name")]


def test_cancel_cell_edit_destroys_entry_clears_state_and_returns_break():
    app = FakeApp()
    entry = FakeEntry(app.grid_tree, font=("Segoe UI", 9))
    app._editing_cell_entry = entry
    app._current_edit_info = {"row_index": 0, "col_name": "name"}

    result = grid_edit_actions.cancel_cell_edit(app)

    assert result == "break"
    assert entry.destroy_count == 1
    assert not hasattr(app, "_editing_cell_entry")
    assert not hasattr(app, "_current_edit_info")


def test_legacy_app_grid_edit_methods_delegate(ocr_module, monkeypatch):
    app = object.__new__(ocr_module.CheckCaptureOCRApp)
    event = object()
    calls = []

    monkeypatch.setattr(ocr_module, "on_cell_double_click", lambda actual_app, actual_event: calls.append(("open", actual_app, actual_event)))
    monkeypatch.setattr(
        ocr_module,
        "save_cell_edit_on_focus_out",
        lambda actual_app, row_index, col_name: calls.append(("focus_out", actual_app, row_index, col_name)),
    )
    monkeypatch.setattr(
        ocr_module,
        "save_cell_edit",
        lambda actual_app, row_index, col_name: calls.append(("save", actual_app, row_index, col_name)) or "break",
    )
    monkeypatch.setattr(
        ocr_module,
        "cancel_cell_edit",
        lambda actual_app: calls.append(("cancel", actual_app)) or "break",
    )

    app.on_cell_double_click_ui(event)
    focus_out_result = app._save_cell_edit_on_focus_out(1, "name")
    save_result = app._save_cell_edit(1, "name")
    cancel_result = app._cancel_cell_edit()

    assert focus_out_result is None
    assert save_result == "break"
    assert cancel_result == "break"
    assert calls == [
        ("open", app, event),
        ("focus_out", app, 1, "name"),
        ("save", app, 1, "name"),
        ("cancel", app),
    ]
