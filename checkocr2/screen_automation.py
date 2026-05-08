"""Desktop automation adapter functions."""

from __future__ import annotations


def copy_text(text: str) -> None:
    import pyperclip

    pyperclip.copy(text)


def click(x: int, y: int, *, clicks: int = 1, interval: float = 0.1) -> None:
    import pyautogui

    pyautogui.click(x=x, y=y, clicks=clicks, interval=interval)


def hotkey(*keys: str) -> None:
    import pyautogui

    pyautogui.hotkey(*keys)


def screenshot(region: tuple[int, int, int, int]):
    import pyautogui

    return pyautogui.screenshot(region=region)
