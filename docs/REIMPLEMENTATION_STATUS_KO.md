# CheckOCR2 재구현 현황 문서

작성일: 2026-05-12

## 목적

이 문서는 CheckOCR2의 현재 구조 재구현 상태, 검증 기준, 남은 작업 순서를
한국어로 한 곳에 정리한다. 목표는 기존 Tkinter GUI와 업무 흐름을 유지하면서
OCR 정확도, 처리 속도, 패키징 안정성, 코드 유지보수성을 개선하는 것이다.

## 현재 기준선

- 실행 경로는 `python check_capture_ocr.py`,
  `python Check_Capture_Excel_V6.1_배포.py`, `python -m checkocr2.main`을
  모두 유지한다.
- `Check_Capture_Excel_V6.1_배포.py`는 기존 바로가기와 배포 습관을 위한
  호환 런처이고, 실제 개발 기준은 `check_capture_ocr.py`와 `checkocr2/`
  패키지다.
- 사용자 설정은 저장소가 아니라 `%APPDATA%\CheckOCR2\settings.json`에
  저장한다. 저장소에는 `settings.example.json`만 유지한다.
  기존 GUI 호환 adapter는 `checkocr2/settings_compat.py`에 있다.
- EasyOCR는 GUI가 먼저 표시된 뒤 백그라운드에서 초기화된다. OCR 준비 전에는
  시작 버튼과 `F5` 실행을 막는다.
- 최신 기록 기준 검증은 `ruff`, `pytest` 416개, `compileall`, OCR benchmark
  dry-run, matrix dry-run, source GUI smoke, clean PyInstaller build, real OCR
  package smoke를 통과했다.
- 최신 기록 기준 source/package smoke는 최소 창 크기 `1000x600`과 clean
  GUI exit을 검사한다. 확인된 창 크기는 `1216x889`이고, 최신 패키지는 약
  `596.405 MB`, real package smoke startup은 `4.641`초다.

## 반드시 유지할 GUI 동작

- 기존 창 제목, 아이콘, 메뉴, 툴바, 테마 선택, 로그 패널.
- 단축키: `F5`, `Esc`, `F1`, `Ctrl+S`, `Ctrl+L`, `Ctrl+O`.
- 그리드 행 추가/삭제/초기화, 복사/붙여넣기, 셀 편집 Enter/Escape.
- Excel 파일 선택, 행 로드, 출력 폴더 자동 설정, `_updated.xlsx` export.
- 클릭 지점, 전체/날짜/금리 영역 선택, 영역 미리보기 오버레이.
- 상세 이미지 저장, KBP skip, OCR 업스케일, 프리셋 저장/적용/삭제.
- OCR 시작/중지, 행별 상태 갱신, 최종 export, run report 생성.

이 항목을 건드리는 변경은 `docs/GUI_PARITY_CHECKLIST.md` 기준으로 수동
확인 또는 자동 테스트 증거를 남긴다. 현재 체크리스트에는 세 Python
entrypoint와 built EXE의 dated 자동 launch/package 증거, `1000x600` 최소
창 크기 증거, clean GUI exit 증거가 기록되어 있다.

## 분리 완료된 주요 구조

`check_capture_ocr.py`는 아직 Tk shell과 일부 controller glue를 갖고 있지만,
다음 경계는 `checkocr2/` 패키지로 분리되어 있다.

- 설정/경로/Excel: `settings.py`, `settings_compat.py`, `paths.py`,
  `excel_io.py`, `data_manager.py`.
- OCR/이미지/자동화: `ocr_engine.py`, `ocr_reader_lifecycle.py`,
  `ocr_runtime_options.py`, `ocr_text.py`, `ocr_field_analysis.py`,
  `ocr_field_extraction.py`, `ocr_pair_processing.py`, `image_processing.py`,
  `screen_automation.py`, `capture_adapter.py`.
  `ocr_reader_lifecycle.py`는 EasyOCR 초기화, fallback, 기존 설정 reset,
  치명적 초기화 실패 queue 메시지를 담당한다.
  `ocr_runtime_options.py`는 `ocr_detail_level`과 필드별 confidence 기준값
  조회를 담당한다.
  `image_processing.py`는 임시 날짜/금리 crop 삭제 조건과 삭제 로그도
  담당한다.
  `ocr_field_analysis.py`는 날짜/금리 OCR 값 판정과 기존 debug log 문구를
  담당한다.
  `ocr_field_extraction.py`는 단일 필드 OCR의 이미지 로드, 업스케일,
  EasyOCR 호출, confidence gate, 파싱, cleanup, timing/confidence 기록을
  담당한다.
  `ocr_pair_processing.py`는 날짜/금리 이미지 쌍의 단일 행 OCR 호출 순서,
  누락 이미지 skip, 부분 실패 결과 보존, 기존 한국어 오류 로그를 담당한다.
  `image_processing.py`는 crop 검증, 재사용 가능한 이미지 소스 처리, 업스케일
  크기/변경 상태 계산을 담당한다.
- 워크플로/상태/리포트: `workflow.py`, `workflow_event_bridge.py`,
  `workflow_legacy_adapters.py`, `workflow_run_setup.py`, `worker.py`,
  `workflow_report_finalization.py`, `work_controller.py`, `runtime_state.py`,
  `run_report.py`, `events.py`, `table_model.py`.
  `models.py`의 `OcrRow.from_dict()`는 이제 구체적인 `dict`뿐 아니라
  `Mapping[str, Any]`를 받아 workflow row snapshot의 타입 계약과 맞춘다.
- UI action/helper: 메뉴, 툴바, 패널, 공통 section frame, 대화상자, 오버레이,
  queue dispatch,
  runtime status, settings, preset, folder, coordinate, grid, log, keyboard,
  lifecycle, window geometry, OCR initialization/run/stop, options,
  completion/export helpers.
- 패키징: build metadata, release preflight, package smoke, OpenCV headless
  검증, PyInstaller build gate.

## OCR 정확도와 속도 판단

현재 EasyOCR CPU 기본값은 "동작하는 기준선"이지 "최선으로 입증된 값"은
아니다. OCR 정확도와 속도를 바꾸려면 실제 crop fixture와 같은 입력 live
비교가 먼저 필요하다.

열려 있는 하드 게이트:

- `tests\fixtures\ocr_crops\ground_truth.csv`가 아직 없다.
- `scripts\audit_ocr_fixtures.py`는 현재 `ready_for_baseline=false` 상태다.
- 같은 Excel 입력 기준 최소 10행 baseline/candidate live run report 비교가
  아직 없다.
- 따라서 wait-time 단축, OCR 엔진 교체, confidence threshold, allowlist,
  preprocessing 기본값 변경은 아직 승격하면 안 된다.

채택 조건:

- 날짜/금리 정규화 정확도 회귀 없음.
- 기대값이 있는 필드의 blank 증가 없음.
- false positive 증가 없음.
- 실패 행 증가 없음.
- fixture coverage 유지.
- P95 OCR 또는 live row 처리시간이 의미 있게 개선됨. 속도 변경은 기본
  기준으로 최소 10% 개선을 요구한다.

## 다음 구현 순서

1. 실제 날짜/금리 crop을 수집하고 `ground_truth_draft.csv`를 수동 검토한다.
2. 검토된 파일만 `ground_truth.csv`로 승격한다.
3. `scripts\audit_ocr_fixtures.py`를 통과시킨다.
4. 현재 EasyOCR baseline과 matrix 결과를 `.analysis_tmp/`에 기록한다.
5. `detail=1`, field allowlist, confidence threshold, preprocessing,
   wait-time 후보를 기본값 변경 없이 실험한다.
6. 같은 입력 최소 10행의 baseline/candidate run report를 비교한다.
7. `scripts\check_ocr_evidence_bundle.py`로 audit, benchmark, matrix, live
   comparison artifact가 dry-run/zero-case/not-ready/coverage-changed/rejected
   live 상태가 아닌지 확인한다. 선택 후보 matrix는
   `--require-no-matrix-regressions`로 더 엄격하게 검사한다.
8. 정확도 회귀가 없고 속도 또는 패키지 크기 이득이 있는 후보만 채택한다.
9. 남은 controller/UI glue는 작은 단위로 계속 분리하고 매번 smoke를 돌린다.
10. 패키지 크기 최적화는 한 번에 하나의 dependency/PyInstaller 변경만 적용한다.

## 검증 명령

구조 변경 기본 게이트:

```powershell
python -m ruff check .
python -m pytest --basetemp $env:TEMP\checkocr2-pytest
python -m compileall checkocr2 scripts check_capture_ocr.py Check_Capture_Excel_V6.1_배포.py
python scripts\benchmark_ocr.py --dry-run --allow-empty-fixture
python scripts\benchmark_ocr_matrix.py --dry-run --allow-empty-fixture --allowlist-modes none,field
python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --min-window-width 1000 --min-window-height 600 --require-clean-exit
```

OCR 후보 검증:

```powershell
python scripts\audit_ocr_fixtures.py --output-json .analysis_tmp\ocr_fixture_audit.json
python scripts\benchmark_ocr.py --output-json .analysis_tmp\easyocr_baseline.json
python scripts\benchmark_ocr_matrix.py --allowlist-modes none,field --output-json .analysis_tmp\ocr_benchmark_matrix_allowlist.json
python scripts\compare_run_reports.py .analysis_tmp\baseline_run_report.json .analysis_tmp\candidate_run_report.json --require-p95-improvement --min-p95-improvement-percent 10 --output-json .analysis_tmp\live_ocr_compare.json
python scripts\check_ocr_evidence_bundle.py --audit-json .analysis_tmp\ocr_fixture_audit.json --benchmark-json .analysis_tmp\easyocr_baseline.json --matrix-json .analysis_tmp\ocr_benchmark_matrix_allowlist.json --live-comparison-json .analysis_tmp\live_ocr_compare.json --require-live-comparison --output-json .analysis_tmp\ocr_evidence_bundle.json
```

패키지 영향 변경 게이트:

```powershell
$env:PYTHONNOUSERSITE='1'; .\.analysis_tmp\package_venv\Scripts\python.exe -m PyInstaller build_app.spec --noconfirm --clean
python scripts\package_smoke.py dist\CheckCaptureOCR_V6.1\CheckCaptureOCR_V6.1.exe --timeout 45 --require-package-metadata --require-ocr-ready --require-settings-file --isolated-appdata --ocr-ready-mode real --ocr-ready-timeout 180 --max-package-size-mb 650 --max-startup-seconds 5 --min-window-width 1000 --min-window-height 600 --require-clean-exit
```

## 커밋과 보안 규칙

- `DESIGN.md`, `.analysis_tmp/`, `settings.json`, crop fixture, 생산 Excel,
  screenshot, run report JSON은 명시 요청이 없으면 stage하지 않는다.
- commit은 하나의 경계만 포함한다. 예: `refactor: extract grid actions`,
  `test: add OCR fixture audit`, `docs: document reimplementation status`.
- OCR crop과 run report에는 좌표, 화면 내용, OCR 원문이 들어갈 수 있으므로
  기본적으로 ignored/local evidence로만 다룬다.
- 외부 OCR, telemetry, cloud 서비스는 명시 승인 없이는 추가하지 않는다.

## 관련 문서

- `docs/REIMPLEMENTATION_EXECUTION_GUIDE.md`: 다음 작업자가 따라야 할 실행 규칙.
- `docs/REIMPLEMENTATION_HANDOFF.md`: 최신 검증 상태와 남은 게이트.
- `docs/OCR_FIXTURE_WORKFLOW.md`: crop fixture 준비와 수동 검토 절차.
- `docs/OCR_BENCHMARK_PLAN.md`: OCR benchmark와 matrix 판단 기준.
- `docs/GUI_PARITY_CHECKLIST.md`: UI 변경 전후 수동 parity 체크리스트.
