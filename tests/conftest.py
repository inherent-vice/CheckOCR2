from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _blocked(*args, **kwargs):
    raise AssertionError("GUI, OCR, and desktop automation calls are disabled in tests")


def _install_tkinter_stub() -> None:
    tkinter = types.ModuleType("tkinter")

    class BlockedTk:
        def __init__(self, *args, **kwargs):
            _blocked(*args, **kwargs)

    tkinter.Tk = BlockedTk
    tkinter.Toplevel = BlockedTk
    tkinter.Canvas = BlockedTk
    tkinter.Menu = BlockedTk
    tkinter.StringVar = BlockedTk
    tkinter.IntVar = BlockedTk
    tkinter.DoubleVar = BlockedTk
    tkinter.BooleanVar = BlockedTk
    tkinter.BOTH = "both"

    for child_name in ("filedialog", "messagebox", "simpledialog", "ttk"):
        child = types.ModuleType(f"tkinter.{child_name}")
        if child_name == "messagebox":
            child.showinfo = _blocked
            child.showerror = _blocked
            child.askyesno = _blocked
        if child_name == "simpledialog":
            child.askstring = _blocked
        setattr(tkinter, child_name, child)
        sys.modules[f"tkinter.{child_name}"] = child

    sys.modules["tkinter"] = tkinter


def _install_easyocr_stub() -> None:
    easyocr = types.ModuleType("easyocr")

    class Reader:
        def __init__(self, *args, **kwargs):
            _blocked(*args, **kwargs)

    easyocr.Reader = Reader
    sys.modules["easyocr"] = easyocr


def _install_desktop_automation_stubs() -> None:
    pyautogui = types.ModuleType("pyautogui")
    pyautogui.click = _blocked
    pyautogui.hotkey = _blocked
    pyautogui.screenshot = _blocked
    sys.modules["pyautogui"] = pyautogui

    pyperclip = types.ModuleType("pyperclip")
    pyperclip.copy = _blocked
    sys.modules["pyperclip"] = pyperclip


def _install_pillow_imagetk_stub() -> None:
    sys.modules["PIL.ImageTk"] = types.ModuleType("PIL.ImageTk")


@pytest.fixture(scope="session")
def ocr_module():
    _install_tkinter_stub()
    _install_easyocr_stub()
    _install_desktop_automation_stubs()
    _install_pillow_imagetk_stub()
    sys.modules.pop("check_capture_ocr", None)
    return importlib.import_module("check_capture_ocr")
