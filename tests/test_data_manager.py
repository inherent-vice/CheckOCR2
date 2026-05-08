from __future__ import annotations

import logging
import queue

import pandas as pd

CODE = "\uc885\ubaa9\ucf54\ub4dc"
NAME = "\uc885\ubaa9\uba85"
DATE = "\ub0a0\uc9dc"
RATE = "\uae08\ub9ac"
STATUS = "\uc0c1\ud0dc"
WAITING = "\ub300\uae30 \uc911"
DONE = "\uc644\ub8cc"
STOPPED = "\uc911\ub2e8\ub428"


def make_data_manager(ocr_module):
    events = queue.Queue()
    manager = ocr_module.DataManager(
        app_ref=None,
        logger=logging.getLogger("tests.data_manager"),
        message_queue=events,
    )
    return manager, events


def test_load_excel_to_grid_accepts_english_code_and_name_columns(ocr_module, tmp_path):
    workbook_path = tmp_path / "input.xlsx"
    pd.DataFrame(
        [
            {"code": "A001", "name": "Alpha"},
            {"code": "B002", "name": "Beta"},
        ],
    ).to_excel(workbook_path, index=False)

    manager, _events = make_data_manager(ocr_module)

    assert manager.load_excel_to_grid_data(workbook_path) == 2
    assert manager.excel_data == [
        {CODE: "A001", NAME: "Alpha", DATE: "", RATE: "", STATUS: WAITING},
        {CODE: "B002", NAME: "Beta", DATE: "", RATE: "", STATUS: WAITING},
    ]


def test_export_grid_to_excel_writes_updated_workbook(ocr_module, tmp_path):
    manager, events = make_data_manager(ocr_module)
    manager.excel_data = [
        {CODE: "A001", NAME: "Alpha", DATE: "2024/05/01", RATE: "3.500", STATUS: DONE},
        {CODE: "B002", NAME: "Beta", DATE: "", RATE: "", STATUS: STOPPED},
    ]

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    manager.export_grid_to_excel_data(output_dir, str(tmp_path / "source.xlsx"))

    exported_path = output_dir / "source_updated.xlsx"
    assert exported_path.exists()
    exported = pd.read_excel(exported_path, dtype=str).fillna("")

    assert list(exported.columns) == [CODE, NAME, DATE, RATE, STATUS]
    assert exported.to_dict("records") == [
        {CODE: "A001", NAME: "Alpha", DATE: "2024/05/01", RATE: "3.500", STATUS: DONE},
        {CODE: "B002", NAME: "Beta", DATE: "", RATE: "", STATUS: ""},
    ]
    assert any(event[0] == "log" and event[2] == "SUCCESS" for event in list(events.queue))
