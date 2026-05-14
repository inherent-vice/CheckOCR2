from __future__ import annotations

from pathlib import Path

from checkocr2 import launcher_bootstrap


def test_ensure_repo_venv_noops_inside_repo_venv(monkeypatch):
    repo_python = Path(__file__).resolve().parents[1] / ".venv" / "Scripts" / "python.exe"
    calls: list[tuple[str, list[str]]] = []

    monkeypatch.setattr(launcher_bootstrap.sys, "executable", str(repo_python))
    monkeypatch.setattr(launcher_bootstrap.sys, "argv", ["check_capture_ocr.py"])
    monkeypatch.setattr(launcher_bootstrap.os, "execv", lambda path, args: calls.append((path, args)))

    launcher_bootstrap.ensure_repo_venv()

    assert calls == []


def test_ensure_repo_venv_reexecs_when_not_using_repo_python(monkeypatch):
    repo_python = Path(__file__).resolve().parents[1] / ".venv" / "Scripts" / "python.exe"
    calls: list[tuple[str, list[str]]] = []

    monkeypatch.setattr(launcher_bootstrap.sys, "executable", r"C:\Windows\System32\python.exe")
    monkeypatch.setattr(launcher_bootstrap.sys, "argv", ["check_capture_ocr.py", "--foo"])
    monkeypatch.setattr(launcher_bootstrap.os, "execv", lambda path, args: calls.append((path, args)))

    launcher_bootstrap.ensure_repo_venv()

    assert calls == [(str(repo_python), [str(repo_python), "check_capture_ocr.py", "--foo"])]
