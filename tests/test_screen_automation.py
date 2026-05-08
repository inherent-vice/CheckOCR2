from __future__ import annotations

import sys
import types

from checkocr2 import screen_automation


def test_screen_automation_delegates_to_desktop_libraries(monkeypatch):
    calls = []
    pyperclip = types.SimpleNamespace(copy=lambda text: calls.append(("copy", text)))
    pyautogui = types.SimpleNamespace(
        click=lambda **kwargs: calls.append(("click", kwargs)),
        hotkey=lambda *keys: calls.append(("hotkey", keys)),
        screenshot=lambda **kwargs: ("image", kwargs),
    )
    monkeypatch.setitem(sys.modules, "pyperclip", pyperclip)
    monkeypatch.setitem(sys.modules, "pyautogui", pyautogui)

    screen_automation.copy_text("A001")
    screen_automation.click(1, 2, clicks=2, interval=0.3)
    screen_automation.hotkey("ctrl", "v")
    image = screen_automation.screenshot((1, 2, 3, 4))

    assert calls == [
        ("copy", "A001"),
        ("click", {"x": 1, "y": 2, "clicks": 2, "interval": 0.3}),
        ("hotkey", ("ctrl", "v")),
    ]
    assert image == ("image", {"region": (1, 2, 3, 4)})
