from __future__ import annotations

from checkocr2.ui.start_validation import (
    ERROR,
    WARNING,
    validate_ocr_start,
)


def test_validate_ocr_start_blocks_empty_grid_first():
    result = validate_ocr_start(
        rows=[],
        output_dir_exists=lambda: False,
        ocr_initializing=True,
        ocr_ready=False,
    )

    assert result.is_valid is False
    assert result.severity == WARNING
    assert result.title == "경고"
    assert result.message == "처리할 데이터가 없습니다. Excel 파일을 로드하거나 데이터를 추가하세요."


def test_validate_ocr_start_does_not_probe_output_folder_for_empty_grid():
    def fail_if_called():
        raise AssertionError("output folder check should not run before row validation")

    result = validate_ocr_start(
        rows=[],
        output_dir_exists=fail_if_called,
        ocr_initializing=True,
        ocr_ready=False,
    )

    assert result.is_valid is False
    assert result.severity == WARNING


def test_validate_ocr_start_blocks_missing_output_folder():
    result = validate_ocr_start(
        rows=[{"code": "A001"}],
        output_dir_exists=lambda: False,
        ocr_initializing=False,
        ocr_ready=True,
    )

    assert result.is_valid is False
    assert result.severity == WARNING
    assert result.title == "경고"
    assert result.message == "유효한 Output 폴더를 지정하세요."


def test_validate_ocr_start_blocks_while_ocr_is_loading():
    result = validate_ocr_start(
        rows=[{"code": "A001"}],
        output_dir_exists=lambda: True,
        ocr_initializing=True,
        ocr_ready=False,
    )

    assert result.is_valid is False
    assert result.severity == WARNING
    assert result.title == "OCR 준비 중"
    assert result.message == "OCR 엔진을 초기화하고 있습니다. 잠시 후 다시 시작하세요."


def test_validate_ocr_start_blocks_when_ocr_failed_to_initialize():
    result = validate_ocr_start(
        rows=[{"code": "A001"}],
        output_dir_exists=lambda: True,
        ocr_initializing=False,
        ocr_ready=False,
    )

    assert result.is_valid is False
    assert result.severity == ERROR
    assert result.title == "오류"
    assert result.message == "OCR 엔진이 초기화되지 않았습니다. 프로그램을 재시작하거나 설정을 확인하세요."


def test_validate_ocr_start_accepts_ready_inputs():
    result = validate_ocr_start(
        rows=[{"code": "A001"}],
        output_dir_exists=lambda: True,
        ocr_initializing=False,
        ocr_ready=True,
    )

    assert result.is_valid is True
    assert result.severity is None
    assert result.title == ""
    assert result.message == ""
