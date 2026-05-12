from __future__ import annotations

from pathlib import Path

from checkocr2.workflow_run_setup import prepare_workflow_run


def make_ui_settings():
    return {
        "delays": {"paste": 0.25, "loading": 1.5},
        "click_point": (10, 20),
        "all_area": (1, 2, 3, 4),
        "date_area": (5, 6, 7, 8),
        "rate_area": (9, 10, 11, 12),
    }


def test_prepare_workflow_run_uses_input_excel_stem_for_detail_folder(tmp_path):
    created = []
    input_path = r"C:\input\sample.xlsx"

    setup = prepare_workflow_run(
        make_ui_settings(),
        str(tmp_path),
        input_path,
        total_items=3,
        save_detail_images=True,
        makedirs=lambda path, *, exist_ok: created.append((path, exist_ok)),
    )

    assert setup.input_excel_file == input_path
    assert setup.save_folder == str(tmp_path / "sample")
    assert setup.report_path == tmp_path / "sample_run_report.json"
    assert setup.report["input_excel_path"] == input_path
    assert setup.report["output_dir"] == str(tmp_path)
    assert setup.report["summary"]["total_items"] == 3
    assert setup.report["options"]["save_detail_images"] is True
    assert created == [(str(tmp_path / "sample"), True)]


def test_prepare_workflow_run_uses_default_detail_folder_without_input(tmp_path):
    setup = prepare_workflow_run(
        make_ui_settings(),
        str(tmp_path),
        "",
        total_items=0,
        save_detail_images=False,
    )

    assert setup.input_excel_file == ""
    assert setup.save_folder == str(tmp_path / "ocr_images")
    assert setup.report_path == tmp_path / "ocr_results_run_report.json"
    assert setup.report["input_excel_path"] == ""
    assert setup.report["summary"]["total_items"] == 0
    assert setup.report["options"]["save_detail_images"] is False
    assert Path(setup.save_folder).is_dir()


def test_prepare_workflow_run_copies_delays_and_coordinate_mapping(tmp_path):
    ui_settings = make_ui_settings()

    setup = prepare_workflow_run(
        ui_settings,
        str(tmp_path),
        "",
        total_items=1,
        save_detail_images=True,
    )

    assert setup.paste_delay == 0.25
    assert setup.load_delay == 1.5
    assert setup.coords == {
        "click": ui_settings["click_point"],
        "all": ui_settings["all_area"],
        "date": ui_settings["date_area"],
        "rate": ui_settings["rate_area"],
    }
    assert set(setup.coords) == {"click", "all", "date", "rate"}
