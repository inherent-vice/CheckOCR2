from __future__ import annotations

from types import SimpleNamespace

from checkocr2.ui import menu


class FakeMenu:
    created = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.cascades = []
        self.commands = []
        self.separator_count = 0
        self.__class__.created.append(self)

    def add_cascade(self, **kwargs):
        self.cascades.append(kwargs)

    def add_command(self, **kwargs):
        self.commands.append(kwargs)

    def add_separator(self):
        self.separator_count += 1


class FakeApp:
    def __init__(self):
        self.config_calls = []

    def config(self, **kwargs):
        self.config_calls.append(kwargs)

    def load_excel_to_grid(self):
        raise AssertionError("construction must not load Excel")

    def browse_input_excel(self):
        raise AssertionError("construction must not browse Excel")

    def browse_output_folder(self):
        raise AssertionError("construction must not browse output")

    def open_output_folder(self):
        raise AssertionError("construction must not open output")

    def quit_app(self):
        raise AssertionError("construction must not quit")

    def quick_save_settings(self):
        raise AssertionError("construction must not save settings")

    def load_last_settings(self):
        raise AssertionError("construction must not load settings")

    def show_area_preview(self):
        raise AssertionError("construction must not preview")

    def handle_f5_key(self):
        raise AssertionError("construction must not run OCR")

    def stop_processing_ui_initiated(self):
        raise AssertionError("construction must not stop OCR")

    def show_shortcuts(self):
        raise AssertionError("construction must not show shortcuts")

    def show_about(self):
        raise AssertionError("construction must not show about")


def test_create_menu_builds_expected_menu_commands(monkeypatch):
    FakeMenu.created = []
    monkeypatch.setattr(menu, "tk", SimpleNamespace(Menu=FakeMenu))
    app = FakeApp()

    menu.create_menu(app)

    menubar, file_menu, settings_menu, preview_menu, run_menu, help_menu = FakeMenu.created
    assert app.config_calls == [{"menu": menubar}]
    assert [cascade["label"] for cascade in menubar.cascades] == [
        "파일",
        "설정",
        "미리보기",
        "실행",
        "도움말",
    ]
    assert [cascade["menu"] for cascade in menubar.cascades] == [
        file_menu,
        settings_menu,
        preview_menu,
        run_menu,
        help_menu,
    ]
    assert all(menu_obj.kwargs == {"tearoff": 0} for menu_obj in FakeMenu.created[1:])

    assert [command["label"] for command in file_menu.commands] == [
        "Excel 파일 로드 (Ctrl+O)",
        "Excel 파일 선택",
        "출력 폴더 선택",
        "출력 폴더 열기",
        "종료 (Alt+F4)",
    ]
    assert [command["command"] for command in file_menu.commands] == [
        app.load_excel_to_grid,
        app.browse_input_excel,
        app.browse_output_folder,
        app.open_output_folder,
        app.quit_app,
    ]
    assert file_menu.separator_count == 1
    assert file_menu.commands[0]["accelerator"] == "Ctrl+O"
    assert file_menu.commands[-1]["accelerator"] == "Alt+F4"

    assert [command["label"] for command in settings_menu.commands] == [
        "현재 설정 저장 (Ctrl+S)",
        "마지막 설정 불러오기 (Ctrl+L)",
    ]
    assert [command["command"] for command in settings_menu.commands] == [
        app.quick_save_settings,
        app.load_last_settings,
    ]
    assert settings_menu.separator_count == 1

    assert preview_menu.commands == [
        {"label": "전체 영역 미리보기", "command": app.show_area_preview}
    ]
    assert [command["command"] for command in run_menu.commands] == [
        app.handle_f5_key,
        app.stop_processing_ui_initiated,
    ]
    assert [command["accelerator"] for command in run_menu.commands] == ["F5", "Esc"]
    assert [command["command"] for command in help_menu.commands] == [
        app.show_shortcuts,
        app.show_about,
    ]
