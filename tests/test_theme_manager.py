from __future__ import annotations

from checkocr2.ui import theme as theme_module
from checkocr2.ui.theme import ThemeManager


class FakeSettings:
    def __init__(self, theme_key: str = "modern_blue") -> None:
        self.theme_key = theme_key
        self.set_calls = []

    def get_advanced(self, key, default=None):
        return self.theme_key if key == "ui_theme" else default

    def set_advanced(self, key, value):
        self.set_calls.append((key, value))
        if key == "ui_theme":
            self.theme_key = value


class FakeLogger:
    def __init__(self) -> None:
        self.info_messages = []
        self.warning_messages = []

    def info(self, message):
        self.info_messages.append(message)

    def warning(self, message):
        self.warning_messages.append(message)


class FakeWidget:
    def __init__(self, exists: bool = True) -> None:
        self.exists = exists
        self.configure_calls = []

    def winfo_exists(self):
        return self.exists

    def configure(self, **kwargs):
        self.configure_calls.append(kwargs)


class FakeLogWidget(FakeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.tags = {}

    def tag_configure(self, tag, **kwargs):
        self.tags[tag] = kwargs


class FakeRoot:
    def __init__(self, theme_key: str = "modern_blue") -> None:
        self.settings_manager = FakeSettings(theme_key)
        self.logger = FakeLogger()
        self.configure_calls = []
        self.log_text_widget = FakeLogWidget()
        self.refresh_grid_tags_called = False

    def configure(self, **kwargs):
        self.configure_calls.append(kwargs)

    def refresh_grid_tags(self):
        self.refresh_grid_tags_called = True


class FakeStyle:
    instances = []

    def __init__(self) -> None:
        self.theme_uses = []
        self.configure_calls = []
        self.map_calls = []
        FakeStyle.instances.append(self)

    def theme_use(self, name):
        self.theme_uses.append(name)

    def configure(self, style_name, **kwargs):
        self.configure_calls.append((style_name, kwargs))

    def map(self, style_name, **kwargs):
        self.map_calls.append((style_name, kwargs))


def test_theme_manager_applies_widget_ttk_and_log_styles(monkeypatch):
    FakeStyle.instances.clear()
    monkeypatch.setattr(theme_module.ttk, "Style", FakeStyle)
    app = FakeRoot("green_nature")
    manager = ThemeManager(app)
    live_widget = FakeWidget()
    dead_widget = FakeWidget(exists=False)

    manager.register_widget(live_widget, {"bg": "primary", "fg": "white", "relief": "flat"})
    manager.register_widget(dead_widget, {"bg": "danger"})
    manager.apply_theme_to_all_widgets()

    assert manager.current_theme_key == "green_nature"
    assert app.configure_calls == [{"bg": manager.get_color("surface")}]
    assert live_widget.configure_calls == [
        {"bg": manager.get_color("primary"), "fg": manager.get_color("white"), "relief": "flat"}
    ]
    assert dead_widget not in manager.themed_widgets
    assert app.log_text_widget.tags["ERROR"] == {"foreground": manager.get_color("danger")}
    assert app.refresh_grid_tags_called is True
    assert FakeStyle.instances[0].theme_uses == ["clam"]
    configured_styles = [style_name for style_name, _kwargs in FakeStyle.instances[0].configure_calls]
    assert "Treeview" in configured_styles
    assert "TCombobox" in configured_styles


def test_theme_manager_changes_theme_and_preserves_legacy_export(ocr_module, monkeypatch):
    FakeStyle.instances.clear()
    monkeypatch.setattr(theme_module.ttk, "Style", FakeStyle)
    app = FakeRoot("modern_blue")
    manager = ThemeManager(app)

    manager.change_theme("dark_pro")
    manager.change_theme("missing_theme")

    assert ocr_module.ThemeManager.__module__ == "checkocr2.ui.theme"
    assert manager.current_theme_key == "dark_pro"
    assert app.settings_manager.set_calls == [("ui_theme", "dark_pro")]
    assert app.logger.info_messages[0].startswith("테마 변경됨:")
    assert app.logger.warning_messages == ["알 수 없는 테마 키: missing_theme"]
