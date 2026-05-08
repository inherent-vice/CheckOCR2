from __future__ import annotations

from types import SimpleNamespace

from checkocr2.ui.panels import options_panel


class FakeWidget:
    created = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.pack_calls = []
        self.__class__.created.append(self)

    def pack(self, **kwargs):
        self.pack_calls.append(kwargs)


class FakeFrame(FakeWidget):
    created = []


class FakeCheckbutton(FakeWidget):
    created = []


class FakeLabel(FakeWidget):
    created = []


class FakeCombobox(FakeWidget):
    created = []


class FakeVar:
    def __init__(self, value=None):
        self.value = value
        self.set_calls = []

    def set(self, value):
        self.value = value
        self.set_calls.append(value)


class FakeThemeManager:
    def __init__(self):
        self.registered = []

    def register_widget(self, widget, style_config):
        self.registered.append((widget, style_config))


class FakeSettingsManager:
    def __init__(self):
        self.values = {
            "skip_kbp_code": False,
            "upscaling_enabled": False,
            "upscaling_factor": 3.0,
            "upscaling_method": "BICUBIC",
        }
        self.calls = []

    def get_advanced(self, key, default=None):
        self.calls.append((key, default))
        return self.values.get(key, default)


class FakeApp:
    def __init__(self):
        self.theme_manager = FakeThemeManager()
        self.settings_manager = FakeSettingsManager()
        self.sections = []
        self.save_detail_images = FakeVar(True)
        self.skip_kbp_var = None
        self.enable_upscaling = FakeVar(True)
        self.upscaling_factor = FakeVar(2.0)
        self.upscaling_method = FakeVar("LANCZOS")
        self.enable_upscaling_cb = None
        self.upscaling_details_frame = None
        self.factor_combo = None
        self.method_combo = None
        self.saved_advanced = 0
        self.toggle_count = 0

    def _create_section_frame_styled(self, parent, title, fill_parent=False):
        section = FakeFrame(parent, title=title, fill_parent=fill_parent)
        self.sections.append((parent, title, fill_parent, section))
        return section

    def save_advanced_ui_to_settings(self):
        self.saved_advanced += 1

    def on_upscaling_toggle(self):
        self.toggle_count += 1


def test_create_options_panel_builds_option_controls(monkeypatch):
    for widget_class in (FakeFrame, FakeCheckbutton, FakeLabel, FakeCombobox):
        widget_class.created = []
    fake_tk = SimpleNamespace(
        Frame=FakeFrame,
        Checkbutton=FakeCheckbutton,
        Label=FakeLabel,
        BooleanVar=FakeVar,
    )
    fake_ttk = SimpleNamespace(Combobox=FakeCombobox)
    monkeypatch.setattr(options_panel, "tk", fake_tk)
    monkeypatch.setattr(options_panel, "ttk", fake_ttk)
    app = FakeApp()
    parent = object()

    options_panel.create_options_panel(app, parent)

    assert app.sections[0][0:3] == (parent, "⚙️ 옵션 설정", False)
    assert app.skip_kbp_var.value is False
    assert app.enable_upscaling.set_calls == [False]
    assert app.upscaling_factor.set_calls == [3.0]
    assert app.upscaling_method.set_calls == ["BICUBIC"]
    assert app.toggle_count == 1
    assert app.saved_advanced == 0

    assert [button.kwargs["text"] for button in FakeCheckbutton.created] == [
        "상세 이미지 저장 (영역별 개별 파일)",
        "'KBP' 코드 건너뛰기 (빈 값으로 완료 처리)",
        "🔍 OCR 업스케일링 활성화 (인식률 향상)",
    ]
    assert FakeCheckbutton.created[0].kwargs["variable"] is app.save_detail_images
    assert FakeCheckbutton.created[1].kwargs["variable"] is app.skip_kbp_var
    assert FakeCheckbutton.created[1].kwargs["command"] == app.save_advanced_ui_to_settings
    assert FakeCheckbutton.created[2].kwargs["variable"] is app.enable_upscaling
    assert FakeCheckbutton.created[2].kwargs["command"] == app.on_upscaling_toggle

    assert app.factor_combo.kwargs["textvariable"] is app.upscaling_factor
    assert app.factor_combo.kwargs["values"] == [1.5, 2.0, 2.5, 3.0, 4.0]
    assert app.factor_combo.kwargs["state"] == "readonly"
    assert app.method_combo.kwargs["textvariable"] is app.upscaling_method
    assert app.method_combo.kwargs["values"] == ["LANCZOS", "BICUBIC", "BILINEAR"]
    assert app.method_combo.kwargs["state"] == "readonly"
    assert app.upscaling_details_frame.pack_calls[-1] == {"fill": "x", "padx": (20, 0)}

    assert app.settings_manager.calls == [
        ("skip_kbp_code", True),
        ("upscaling_enabled", True),
        ("upscaling_factor", 2.0),
        ("upscaling_method", "LANCZOS"),
    ]
