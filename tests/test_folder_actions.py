from __future__ import annotations

import subprocess

from checkocr2.ui import folder_actions


class FakeVar:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeLogger:
    def __init__(self):
        self.entries = []

    def info(self, message):
        self.entries.append(("info", message))

    def warning(self, message):
        self.entries.append(("warning", message))

    def error(self, message):
        self.entries.append(("error", message))


class FakeSettingsManager:
    def get_advanced(self, _key, default=None):
        return default


class FakeApp:
    def __init__(self, output_path=""):
        self.input_excel_path = FakeVar("")
        self.output_folder_path = FakeVar(output_path)
        self.logger = FakeLogger()
        self.settings_manager = FakeSettingsManager()

    def _clean_output_folder_path(self, path):
        return str(path).replace("\\", "/")


def test_browse_input_excel_sets_input_output_and_logs_parent_folder():
    app = FakeApp()
    calls = []

    def askopenfilename(**kwargs):
        calls.append(kwargs)
        return r"C:\input\source.xlsx"

    folder_actions.browse_input_excel(app, askopenfilename=askopenfilename)

    assert calls == [
        {"title": "엑셀 파일 선택", "filetypes": [("Excel files", "*.xlsx;*.xls")]}
    ]
    assert app.input_excel_path.get() == r"C:\input\source.xlsx"
    assert app.output_folder_path.get() == "C:/input"
    assert ("info", r"Excel 파일 선택됨: C:\input\source.xlsx") in app.logger.entries


def test_browse_output_folder_uses_initial_dir_sets_cleaned_path_and_warns_for_unc():
    app = FakeApp(r"\\server\share\old")
    messages = []
    calls = []

    def askdirectory(**kwargs):
        calls.append(kwargs)
        return r"\\server\share\new"

    folder_actions.browse_output_folder(
        app,
        askdirectory=askdirectory,
        initial_dir_func=lambda current: f"seed:{current}",
        showinfo=lambda title, message: messages.append(("info", title, message)),
        showerror=lambda title, message: messages.append(("error", title, message)),
    )

    assert calls == [
        {
            "title": "출력 폴더 선택",
            "initialdir": r"seed:\\server\share\old",
            "mustexist": False,
        }
    ]
    assert app.output_folder_path.get() == "//server/share/new"
    assert messages == []


def test_browse_output_folder_shows_network_notice_after_cleaning_unc_path():
    app = FakeApp()
    app._clean_output_folder_path = lambda path: path
    messages = []

    folder_actions.browse_output_folder(
        app,
        askdirectory=lambda **_kwargs: r"\\server\share\new",
        initial_dir_func=lambda _current: None,
        showinfo=lambda title, message: messages.append((title, message)),
        showerror=lambda title, message: messages.append(("error", title, message)),
    )

    assert app.output_folder_path.get() == r"\\server\share\new"
    assert messages and messages[0][0] == "네트워크 폴더 선택"


def test_open_output_folder_warns_when_output_path_is_blank():
    app = FakeApp("  ")
    messages = []

    folder_actions.open_output_folder(
        app,
        showwarning=lambda title, message: messages.append((title, message)),
    )

    assert messages == [("경고", "출력 폴더가 설정되지 않았습니다.")]


def test_open_output_folder_windows_creates_missing_local_folder_and_opens_it():
    app = FakeApp("C:/Output")
    created = []
    opened = []

    folder_actions.open_output_folder(
        app,
        system=lambda: "Windows",
        exists=lambda _path: False,
        makedirs=lambda path, *, exist_ok: created.append((path, exist_ok)),
        startfile=lambda path: opened.append(path),
        askyesno=lambda title, message: True,
        showwarning=lambda title, message: None,
        showerror=lambda title, message: None,
    )

    assert created == [(r"C:\Output", True)]
    assert opened == [r"C:\Output"]


def test_open_output_folder_windows_falls_back_to_explorer_when_startfile_fails():
    app = FakeApp(r"C:\Output")
    runs = []

    def startfile(_path):
        raise OSError("blocked")

    folder_actions.open_output_folder(
        app,
        system=lambda: "Windows",
        exists=lambda _path: True,
        startfile=startfile,
        run=lambda args, *, check, timeout: runs.append((args, check, timeout)),
        showwarning=lambda title, message: None,
        showerror=lambda title, message: None,
    )

    assert runs == [(["explorer", r"C:\Output"], True, 10)]


def test_open_output_folder_windows_unavailable_unc_warns_and_does_not_open():
    app = FakeApp(r"\\server\share\missing")
    messages = []
    opened = []

    folder_actions.open_output_folder(
        app,
        system=lambda: "Windows",
        exists=lambda _path: False,
        startfile=lambda path: opened.append(path),
        showwarning=lambda title, message: messages.append((title, message)),
        showerror=lambda title, message: None,
    )

    assert opened == []
    assert messages and messages[0][0] == "네트워크 오류"


def test_open_output_folder_posix_unc_converts_to_smb_url():
    app = FakeApp(r"\\server\share\folder")
    runs = []

    folder_actions.open_output_folder(
        app,
        system=lambda: "Darwin",
        run=lambda args, *, check, timeout: runs.append((args, check, timeout)),
        showerror=lambda title, message: None,
    )

    assert runs == [(["open", "smb://server/share/folder"], True, 10)]


def test_open_output_folder_reports_command_failure():
    app = FakeApp("/tmp/out")
    messages = []

    folder_actions.open_output_folder(
        app,
        system=lambda: "Darwin",
        run=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            subprocess.CalledProcessError(1, "open")
        ),
        showerror=lambda title, message: messages.append((title, message)),
    )

    assert messages
    assert messages[0][0] == "오류"
    assert "폴더 열기 명령어 실행 실패" in messages[0][1]


def test_legacy_app_folder_methods_delegate(ocr_module, monkeypatch):
    app = ocr_module.CheckCaptureOCRApp.__new__(ocr_module.CheckCaptureOCRApp)
    calls = []

    monkeypatch.setattr(
        ocr_module,
        "browse_input_excel_action",
        lambda app_ref: calls.append(("input", app_ref)),
    )
    monkeypatch.setattr(
        ocr_module,
        "browse_output_folder_action",
        lambda app_ref: calls.append(("browse_output", app_ref)),
    )
    monkeypatch.setattr(
        ocr_module,
        "open_output_folder_action",
        lambda app_ref: calls.append(("open_output", app_ref)),
    )

    app.browse_input_excel()
    app.browse_output_folder()
    app.open_output_folder()

    assert calls == [
        ("input", app),
        ("browse_output", app),
        ("open_output", app),
    ]
