from __future__ import annotations

from argparse import Namespace

from scripts import measure_startup


def test_is_exe_entrypoint_accepts_single_quoted_exe_path():
    assert measure_startup.is_exe_entrypoint('"dist\\CheckCaptureOCR_V7\\CheckCaptureOCR_V7.exe"')
    assert not measure_startup.is_exe_entrypoint("python check_capture_ocr.py")


def test_run_measurement_uses_source_gui_smoke(monkeypatch):
    calls = []

    def fake_source_smoke(entrypoint, **kwargs):
        calls.append((entrypoint, kwargs))
        return 0, {"ready": True}

    monkeypatch.setattr(measure_startup.source_gui_smoke, "run_source_gui_smoke", fake_source_smoke)
    args = Namespace(
        entrypoint="python check_capture_ocr.py",
        repeat=2,
        timeout=10.0,
        ocr_ready_timeout=20.0,
        ocr_ready_mode="real",
        isolated_appdata=True,
    )

    report = measure_startup.run_measurement(args)

    assert report["status"] == "ok"
    assert len(report["runs"]) == 2
    assert calls[0][0] == "python check_capture_ocr.py"
    assert calls[0][1]["require_ready"] is True
    assert calls[0][1]["ocr_ready_timeout_seconds"] == 20.0
    assert calls[0][1]["ocr_ready_mode"] == "real"


def test_run_measurement_uses_package_smoke_for_exe(monkeypatch, tmp_path):
    calls = []

    def fake_package_smoke(exe_path, **kwargs):
        calls.append((exe_path, kwargs))
        return 0, {"ready": True}

    monkeypatch.setattr(measure_startup.package_smoke, "run_package_smoke", fake_package_smoke)
    exe_path = tmp_path / "CheckCaptureOCR_V7.exe"
    args = Namespace(
        entrypoint=f'"{exe_path}"',
        repeat=1,
        timeout=10.0,
        ocr_ready_timeout=20.0,
        ocr_ready_mode="fast",
        isolated_appdata=True,
    )

    report = measure_startup.run_measurement(args)

    assert report["status"] == "ok"
    assert calls[0][0] == exe_path
    assert calls[0][1]["paddle_package"] is True
    assert calls[0][1]["ocr_ready_mode"] == "fast"
