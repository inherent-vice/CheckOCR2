from types import SimpleNamespace

from checkocr2.exceptions import SettingsError
from checkocr2.ui import settings_actions


class FakeVar:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeSettingsManager:
    def __init__(self, current_settings=None):
        self.current_settings = current_settings
        self.data = {"advanced": {"existing": "keep"}}
        self.saved_current_settings = None
        self.get_error = None
        self.save_error = None
        self.default_advanced = {"ui_theme": "modern_blue", "skip_kbp_code": True}
        self.advanced_theme = "modern_dark"

    def get_current_settings(self):
        if self.get_error:
            raise self.get_error
        return self.current_settings

    def save_current_settings(self, settings):
        if self.save_error:
            raise self.save_error
        self.saved_current_settings = settings

    def _get_default_advanced_settings(self):
        return self.default_advanced

    def get_advanced(self, key, default=None):
        if key == "ui_theme":
            return self.advanced_theme
        return self.data["advanced"].get(key, default)


class FakeLogger:
    def __init__(self):
        self.infos = []
        self.errors = []

    def info(self, message):
        self.infos.append(message)

    def error(self, message):
        self.errors.append(message)


class FakeThemeManager:
    def __init__(self):
        self.changed_themes = []

    def change_theme(self, theme):
        self.changed_themes.append(theme)


def make_app(current_settings=None):
    app = SimpleNamespace(
        input_excel_path=FakeVar("old.xlsx"),
        output_folder_path=FakeVar("old_out"),
        settings_manager=FakeSettingsManager(current_settings=current_settings),
        logger=FakeLogger(),
        theme_manager=FakeThemeManager(),
        applied_settings=[],
        preset_updates=0,
        advanced_saves=0,
    )

    def apply_settings_to_ui(settings):
        app.applied_settings.append(settings)

    def update_preset_combo():
        app.preset_updates += 1

    def save_advanced_ui_to_settings():
        app.advanced_saves += 1

    app.apply_settings_to_ui = apply_settings_to_ui
    app.update_preset_combo = update_preset_combo
    app.save_advanced_ui_to_settings = save_advanced_ui_to_settings
    return app


def make_legacy_app(ocr_module):
    app = object.__new__(ocr_module.CheckCaptureOCRApp)
    app.__dict__.update(make_app().__dict__)
    return app


def test_load_last_settings_applies_saved_current_settings():
    settings = {
        "click_point": (1, 2),
        "input_excel_path": "input.xlsx",
        "output_folder_path": "out",
    }
    app = make_app(current_settings=settings)

    settings_actions.load_last_settings(app)

    assert app.applied_settings == [settings]
    assert app.input_excel_path.get() == "input.xlsx"
    assert app.output_folder_path.get() == "out"
    assert app.preset_updates == 1
    assert app.theme_manager.changed_themes == ["modern_dark"]
    assert app.logger.infos == ["마지막 설정이 성공적으로 불러와졌습니다."]


def test_load_last_settings_uses_defaults_when_no_current_settings():
    app = make_app(current_settings=None)

    settings_actions.load_last_settings(app)

    assert app.applied_settings == []
    assert app.input_excel_path.get() == "old.xlsx"
    assert app.output_folder_path.get() == "old_out"
    assert (
        app.settings_manager.data["advanced"] == app.settings_manager.default_advanced
    )
    assert app.preset_updates == 1
    assert app.theme_manager.changed_themes == ["modern_dark"]
    assert app.logger.infos == ["저장된 현재 설정이 없습니다. 기본값을 사용합니다."]


def test_load_last_settings_logs_expected_errors_without_raising():
    app = make_app()
    app.settings_manager.get_error = SettingsError("bad settings")

    settings_actions.load_last_settings(app)

    assert app.logger.errors == ["설정 불러오기 실패: bad settings"]
    assert app.preset_updates == 0
    assert app.theme_manager.changed_themes == []


def test_quick_save_settings_persists_current_settings_and_advanced_values(monkeypatch):
    app = make_app()
    sentinel_settings = {"input_excel_path": "input.xlsx"}
    monkeypatch.setattr(
        settings_actions,
        "build_current_settings",
        lambda received_app: sentinel_settings,
    )

    settings_actions.quick_save_settings(app)

    assert app.settings_manager.saved_current_settings is sentinel_settings
    assert app.advanced_saves == 1
    assert app.logger.infos == ["현재 설정이 저장되었습니다."]


def test_quick_save_settings_reports_save_errors(monkeypatch):
    app = make_app()
    app.settings_manager.save_error = OSError("locked")
    messagebox_errors = []
    monkeypatch.setattr(
        settings_actions, "build_current_settings", lambda received_app: {"x": 1}
    )
    monkeypatch.setattr(
        settings_actions.messagebox,
        "showerror",
        lambda title, message: messagebox_errors.append((title, message)),
    )

    settings_actions.quick_save_settings(app)

    assert app.advanced_saves == 0
    assert app.logger.errors == ["설정 저장 실패: locked"]
    assert messagebox_errors == [("오류", "설정 저장 중 오류가 발생했습니다: locked")]


def test_legacy_app_settings_actions_delegate_to_extracted_helpers(
    ocr_module, monkeypatch
):
    app = make_legacy_app(ocr_module)
    calls = []

    monkeypatch.setattr(
        ocr_module,
        "load_last_settings_action",
        lambda received_app: calls.append(("load", received_app)),
    )
    monkeypatch.setattr(
        ocr_module,
        "quick_save_settings_action",
        lambda received_app: calls.append(("save", received_app)),
    )

    app.load_last_settings()
    app.quick_save_settings()

    assert calls == [("load", app), ("save", app)]
