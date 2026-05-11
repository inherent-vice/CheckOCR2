# CheckOCR2 현대화 실행 문서

작성일: 2026-05-11

## 목적

CheckOCR2의 현재 Tkinter GUI 기능과 사용 흐름은 유지하면서 내부 구조,
OCR 검증 체계, 패키징 안정성을 개선한다. 목표는 화면을 새로 설계하는
것이 아니라, 기존 사용자가 매일 쓰는 OCR/Excel 작업을 깨지 않으면서
성능 개선과 유지보수가 가능한 구조를 만드는 것이다.

## 반드시 유지할 사용자 경험

- 실행 경로: `python check_capture_ocr.py`,
  `python Check_Capture_Excel_V6.1_배포.py`, `python -m checkocr2.main`.
- 기존 창 제목, 아이콘, 메뉴, 툴바, 테마 선택, 로그 패널.
- 단축키: `F5`, `Esc`, `F1`, `Ctrl+S`, `Ctrl+L`, `Ctrl+O`, 그리드
  복사/붙여넣기/삭제, 셀 편집 Enter/Escape.
- Excel 파일 선택, 행 로드, 출력 폴더 자동 설정, `_updated.xlsx` 내보내기.
- 클릭 지점, 전체 영역, 날짜 영역, 금리 영역 선택과 미리보기 오버레이.
- 상세 이미지 저장, KBP 스킵, OCR 업스케일, 프리셋 저장/적용/삭제.

이 항목을 건드리는 변경은 `docs/GUI_PARITY_CHECKLIST.md` 기준으로 수동
확인 또는 자동 테스트 증거를 남긴 뒤 진행한다.

## 현재 진단

- `check_capture_ocr.py`는 아직 Tk 컨트롤러 역할을 일부 갖고 있지만,
  설정, 경로, Excel I/O, 테이블 로직, OCR 엔진 경계, 화면 자동화,
  캡처 어댑터, 워크플로, 런 리포트, 런타임 상태, 작업 컨트롤러,
  메뉴/툴바, 패널, 대화상자, 그리드 액션, 로그 액션 등은
  `checkocr2/` 패키지로 분리되어 있다.
- EasyOCR는 GUI 표시 후 백그라운드에서 초기화된다. OCR 준비 전에는
  시작 버튼과 `F5` 실행이 막힌다.
- 현재 OCR 기본값은 동작 가능한 기준선이지 최적값으로 입증된 상태가
  아니다. 실제 crop fixture와 동일 입력 10행 live 비교가 없으므로 OCR
  엔진, 대기시간, confidence threshold 기본값은 아직 바꾸면 안 된다.
- 고정 대기시간이 행당 처리시간에 큰 영향을 준다. 다만 줄이려면
  정확도 회귀가 없다는 fixture/live 증거가 먼저 필요하다.

## 목표 구조

```text
Tk GUI -> App Controller -> Worker -> Workflow
Workflow -> ScreenAutomation -> Screenshot/Crop
Workflow -> ImageProcessing -> OcrEngine -> OcrText Parser
Workflow -> TableModel/DataManager -> ExcelIO -> RunReport
Worker -> typed queue events -> Tk GUI
```

원칙은 작은 단위 추출이다. 한 번에 전체를 재작성하지 않고, 하나의 경계나
헬퍼를 분리한 뒤 테스트와 GUI smoke로 검증한다.

## OCR 정확도와 속도 게이트

OCR 관련 기본값을 바꾸기 전에 먼저 fixture와 비교 리포트를 만든다.

```powershell
python scripts\audit_ocr_fixtures.py --output-json .analysis_tmp\ocr_fixture_audit.json
python scripts\benchmark_ocr.py --output-json .analysis_tmp\easyocr_baseline.json
python scripts\benchmark_ocr_matrix.py --allowlist-modes none,field --output-json .analysis_tmp\ocr_benchmark_matrix_allowlist.json
```

대기시간이나 live 처리속도 후보는 같은 Excel 입력으로 최소 10행을 baseline과
candidate 각각 실행한 뒤 비교한다.

```powershell
python scripts\compare_run_reports.py .analysis_tmp\baseline_run_report.json .analysis_tmp\candidate_run_report.json --require-p95-improvement --min-p95-improvement-percent 10 --output-json .analysis_tmp\live_ocr_compare.json
```

채택 조건은 날짜/금리 정규화 정확도 회귀 없음, 빈 값 증가 없음, false
positive 증가 없음, 실패 행 증가 없음, fixture coverage 유지, 그리고 P95
처리시간 최소 10% 개선이다. 패키징 변경은 사전에 정한 크기 감소 기준 또는
최소 25 MB 감소가 있어야 한다.

## 구현 순서

1. 실제 날짜/금리 crop fixture와 수동 검증된 `ground_truth.csv`를 만든다.
2. fixture audit를 통과시킨다.
3. 현재 EasyOCR baseline과 matrix 결과를 `.analysis_tmp/`에 기록한다.
4. `detail=1`, field allowlist, confidence threshold, preprocessing,
   wait-time 후보를 기본값 변경 없이 실험한다.
5. 같은 입력 10행 live run report를 비교한다.
6. 정확도 회귀가 없는 후보만 기본값 승격 대상으로 올린다.
7. 남은 controller/UI glue를 작은 단위로 계속 추출한다.
8. 패키지 크기 축소는 변경마다 clean build와 package smoke를 통과시킨다.

## 기본 검증 명령

구조 변경 후 최소 게이트:

```powershell
python -m ruff check .
python -m pytest --basetemp $env:TEMP\checkocr2-pytest
python -m compileall checkocr2 scripts check_capture_ocr.py Check_Capture_Excel_V6.1_배포.py
python scripts\benchmark_ocr.py --dry-run --allow-empty-fixture
python scripts\benchmark_ocr_matrix.py --dry-run --allow-empty-fixture --allowlist-modes none,field
python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file
```

패키지에 영향이 있으면 clean release venv에서 PyInstaller build와 real OCR
package smoke까지 실행한다.

## 현재 남은 핵심 과제

- 실제 OCR fixture가 없어 정확도와 속도 최적화를 결론낼 수 없다.
- 동일 입력 10행 live 비교가 없어 wait-time 기본값을 줄일 수 없다.
- `check_capture_ocr.py`에는 일부 Tk controller glue가 남아 있다.
- 패키지 크기 최적화는 package smoke와 함께 작은 단위로 계속 진행해야 한다.

## 운영 원칙

- GUI 기능과 사용 흐름은 그대로 둔다.
- OCR 성능 주장은 benchmark와 run report로만 확정한다.
- production Excel, screenshot, crop fixture, 개인 설정 파일은 커밋하지 않는다.
- 실패를 숨기는 broad exception은 adapter 또는 top-level safety boundary에만
  남기고, 나머지는 typed error로 좁힌다.
- 문서는 테스트와 함께 갱신해 다음 작업자가 같은 판단을 반복하지 않게 한다.
