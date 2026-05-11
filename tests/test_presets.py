from types import SimpleNamespace

from checkocr2.ui import presets


class FakeCombo:
    def __init__(self, selected=""):
        self.selected = selected
        self.items = {}
        self.current_calls = []
        self.set_calls = []

    def __bool__(self):
        return True

    def __setitem__(self, key, value):
        self.items[key] = value

    def get(self):
        return self.selected

    def current(self, index):
        self.current_calls.append(index)

    def set(self, value):
        self.set_calls.append(value)
        self.selected = value


class FakeEntry:
    def __init__(self, value):
        self.value = value
        self.delete_calls = []
        self.insert_calls = []

    def __bool__(self):
        return True

    def get(self):
        return self.value

    def delete(self, start, end):
        self.delete_calls.append((start, end))

    def insert(self, index, value):
        self.insert_calls.append((index, value))
        self.value = value


class FakeSettingsManager:
    def __init__(self):
        self.preset_names = []
        self.applied = {}
        self.saved = []
        self.deleted = []

    def get_preset_names(self):
        return self.preset_names

    def apply_preset(self, name):
        return self.applied.get(name)

    def save_preset(self, name, settings):
        self.saved.append((name, settings))

    def delete_preset(self, name):
        self.deleted.append(name)


class FakeLogger:
    def __init__(self):
        self.infos = []

    def info(self, message):
        self.infos.append(message)


def make_app():
    app = SimpleNamespace(
        preset_combo=FakeCombo(),
        preset_name_entry=FakeEntry("Preset A"),
        settings_manager=FakeSettingsManager(),
        logger=FakeLogger(),
        applied_settings=[],
        updated_presets=0,
    )
    app.get_current_ui_settings = lambda: {"click_point": (1, 2)}
    app.apply_settings_to_ui = lambda settings: app.applied_settings.append(settings)
    app.update_preset_combo = lambda: setattr(
        app, "updated_presets", app.updated_presets + 1
    )
    return app


def capture_messages(monkeypatch, *, askyesno=True, askstring=None):
    messages = {"info": [], "warning": [], "askyesno": [], "askstring": []}
    monkeypatch.setattr(
        presets.messagebox,
        "showinfo",
        lambda *args, **kwargs: messages["info"].append((args, kwargs)),
    )
    monkeypatch.setattr(
        presets.messagebox,
        "showwarning",
        lambda *args, **kwargs: messages["warning"].append((args, kwargs)),
    )
    monkeypatch.setattr(
        presets.messagebox,
        "askyesno",
        lambda *args, **kwargs: messages["askyesno"].append((args, kwargs)) or askyesno,
    )
    monkeypatch.setattr(
        presets.simpledialog,
        "askstring",
        lambda *args, **kwargs: messages["askstring"].append((args, kwargs))
        or askstring,
    )
    return messages


def test_update_preset_combo_selects_first_or_clears_empty_values():
    app = make_app()
    app.settings_manager.preset_names = ["fast", "safe"]

    presets.update_preset_combo(app)

    assert app.preset_combo.items["values"] == ["fast", "safe"]
    assert app.preset_combo.current_calls == [0]

    app.settings_manager.preset_names = []
    presets.update_preset_combo(app)

    assert app.preset_combo.items["values"] == []
    assert app.preset_combo.set_calls == [""]


def test_apply_selected_preset_updates_ui_and_logs(monkeypatch):
    messages = capture_messages(monkeypatch)
    app = make_app()
    app.preset_combo.selected = "fast"
    app.settings_manager.applied["fast"] = {"click_point": (10, 20)}

    presets.apply_selected_preset(app)

    assert app.applied_settings == [{"click_point": (10, 20)}]
    assert messages["info"][0][0] == ("정보", "프리셋 'fast'이 적용되었습니다.")
    assert app.logger.infos == ["프리셋 'fast' 적용됨."]


def test_save_current_as_preset_rejects_placeholder_or_blank_names(monkeypatch):
    messages = capture_messages(monkeypatch)
    app = make_app()
    app.preset_name_entry = FakeEntry("새 프리셋 이름")

    presets.save_current_as_preset(app)

    assert app.settings_manager.saved == []
    assert messages["warning"][0][0] == ("경고", "유효한 프리셋 이름을 입력해주세요.")


def test_save_current_as_preset_saves_entry_name_and_resets_entry(monkeypatch):
    messages = capture_messages(monkeypatch)
    app = make_app()

    presets.save_current_as_preset(app)

    assert app.settings_manager.saved == [("Preset A", {"click_point": (1, 2)})]
    assert app.updated_presets == 1
    assert app.preset_name_entry.delete_calls == [(0, "end")]
    assert app.preset_name_entry.insert_calls == [(0, "새 프리셋 이름")]
    assert messages["info"][0][0] == ("완료", "'Preset A' 프리셋이 저장되었습니다.")
    assert app.logger.infos == ["프리셋 'Preset A' 저장됨."]


def test_save_current_as_preset_uses_dialog_when_entry_is_absent(monkeypatch):
    messages = capture_messages(monkeypatch, askstring="Dialog Preset")
    app = make_app()
    delattr(app, "preset_name_entry")

    presets.save_current_as_preset(app)

    assert messages["askstring"][0][0] == ("프리셋 저장", "프리셋 이름을 입력하세요:")
    assert messages["askstring"][0][1] == {"parent": app}
    assert app.settings_manager.saved == [("Dialog Preset", {"click_point": (1, 2)})]


def test_delete_selected_preset_warns_for_empty_selection(monkeypatch):
    messages = capture_messages(monkeypatch)
    app = make_app()
    app.preset_combo.selected = ""

    presets.delete_selected_preset(app)

    assert app.settings_manager.deleted == []
    assert messages["warning"][0][0] == ("경고", "삭제할 프리셋을 선택해주세요.")


def test_delete_selected_preset_honors_confirmation(monkeypatch):
    messages = capture_messages(monkeypatch, askyesno=False)
    app = make_app()
    app.preset_combo.selected = "fast"

    presets.delete_selected_preset(app)

    assert app.settings_manager.deleted == []
    assert app.updated_presets == 0
    assert messages["askyesno"][0][0] == (
        "확인",
        "프리셋 'fast'을(를) 삭제하시겠습니까?",
    )

    capture_messages(monkeypatch, askyesno=True)
    presets.delete_selected_preset(app)

    assert app.settings_manager.deleted == ["fast"]
    assert app.updated_presets == 1
    assert app.logger.infos == ["프리셋 'fast' 삭제됨."]


def test_legacy_preset_methods_delegate_to_preset_helpers(ocr_module, monkeypatch):
    capture_messages(monkeypatch)
    app = object.__new__(ocr_module.CheckCaptureOCRApp)
    fake = make_app()
    app.__dict__.update(fake.__dict__)
    del app.__dict__["update_preset_combo"]

    app.settings_manager.preset_names = ["fast"]
    app.update_preset_combo()
    assert app.preset_combo.current_calls == [0]

    app.settings_manager.applied["fast"] = {"click_point": (10, 20)}
    app.preset_combo.selected = "fast"
    app.apply_selected_preset()
    assert app.applied_settings == [{"click_point": (10, 20)}]

    app.save_current_as_preset()
    assert app.settings_manager.saved == [("Preset A", {"click_point": (1, 2)})]

    app.delete_selected_preset()
    assert app.settings_manager.deleted == ["fast"]
