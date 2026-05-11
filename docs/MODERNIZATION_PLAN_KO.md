# CheckOCR2 현대화 실행 문서

작성일: 2026-05-11

## 목적

CheckOCR2는 현재 GUI 기능과 사용 편의성을 유지하면서 내부 구조, OCR 검증
체계, 패키징 안정성을 개선해야 한다. 목표는 화면을 새로 만드는 것이
아니라, 사용자가 매일 쓰는 Tkinter 흐름을 깨지 않고 유지보수성과 OCR 성능
개선 가능성을 확보하는 것이다.

## 반드시 유지할 사용자 경험

- 기존 실행 경로: `python check_capture_ocr.py`,
  `python Check_Capture_Excel_V6.1_배포.py`, `python -m checkocr2.main`.
- 기존 창 제목, 한국어 라벨, 메뉴, 툴바, 테마 선택, 로그 패널.
- 단축키: `F5`, `Esc`, `F1`, `Ctrl+S`, `Ctrl+L`, `Ctrl+O`, 그리드
  복사/붙여넣기/삭제, 셀 편집 Enter/Escape.
- Excel 파일 선택, 행 로드, 출력 폴더 자동 설정, `_updated.xlsx`
  내보내기.
- 클릭 지점, 전체 영역, 날짜 영역, 금리 영역 선택과 미리보기 오버레이.
- 상세 이미지 저장, KBP 스킵, OCR 업스케일, 프리셋 저장/적용/삭제.

이 항목을 건드리는 변경은 `docs/GUI_PARITY_CHECKLIST.md` 기준으로 수동
확인하거나 테스트를 추가해야 한다.

## 현재 진단

- 핵심 GUI 컨트롤러는 아직 `check_capture_ocr.py`에 남아 있지만, 설정,
  경로, Excel I/O, 테이블 로직, OCR 엔진 어댑터, 화면 자동화, 워크플로,
  런 리포트, 런타임 상태, 큐 디스패치, 메뉴/툴바, 일부 패널과 오버레이,
  데이터 매니저, 설정 UI 바인딩, 프리셋 컨트롤러는 `checkocr2/` 패키지로
  분리되었다.
- EasyOCR은 GUI 표시 후 백그라운드에서 초기화된다. OCR 준비 전에는 시작
  버튼과 `F5` 실행을 막는다.
- 현재 OCR 기본값은 동작 가능한 기준선이지 최적값으로 입증된 상태가
  아니다. 실제 crop fixture와 같은 입력의 라이브 비교가 아직 없기 때문에
  OCR 엔진 교체, 대기시간 축소, confidence threshold 기본값 변경은
  보류해야 한다.
- 고정 대기시간이 행별 처리시간을 크게 만든다. 단, 대기시간 축소는 정확도
  회귀가 없다는 근거가 있어야만 기본값으로 반영한다.

## 목표 구조

```text
Tk GUI -> App Controller -> Worker -> Workflow
Workflow -> ScreenAutomation -> Screenshot/Crop
Workflow -> ImageProcessing -> OcrEngine -> OcrText Parser
Workflow -> TableModel/DataManager -> ExcelIO -> RunReport
Worker -> typed queue events -> Tk GUI
```

원칙은 작은 단위 추출이다. 한 번에 전체 재작성하지 않고, 하나의 경계 또는
헬퍼를 옮긴 뒤 테스트와 GUI smoke로 검증한다.

## 병렬 작업 스트림

세부 운영 계획은 `docs/REIMPLEMENTATION_AGENT_PLAN_KO.md`를 기준으로 한다.

- 아키텍처 스트림: 남은 controller glue, 모듈 경계, 문서, 런처 호환성.
- OCR/성능 스트림: fixture 구축, benchmark matrix, run report 비교,
  대기시간 후보 실험.
- TDD 스트림: fake OCR, fake screen automation, queue event, GUI parity
  characterization test.
- 패키징 스트림: dependency pin, PyInstaller spec, package smoke, build
  metadata, 패키지 크기 축소.
- 리뷰 스트림: 보안, 예외 처리, silent failure, 회귀 위험 검토.

각 스트림은 쓰기 범위를 분리하고, 변경 파일과 검증 명령을 보고한 뒤
통합한다.

## OCR 정확도와 속도 개선 게이트

OCR 관련 기본값을 바꾸기 전에 먼저 fixture와 비교 리포트를 만들어야 한다.

```powershell
python scripts\audit_ocr_fixtures.py --output-json .analysis_tmp\ocr_fixture_audit.json
python scripts\benchmark_ocr.py --output-json .analysis_tmp\easyocr_baseline.json
python scripts\benchmark_ocr_matrix.py --allowlist-modes none,field --output-json .analysis_tmp\ocr_benchmark_matrix_allowlist.json
```

대기시간 또는 라이브 처리속도 후보는 같은 Excel 입력으로 최소 10개 행을
기준선/후보 각각 실행한 뒤 비교한다.

```powershell
python scripts\compare_run_reports.py .analysis_tmp\baseline_run_report.json .analysis_tmp\candidate_run_report.json --require-p95-improvement --min-p95-improvement-percent 10 --output-json .analysis_tmp\live_ocr_compare.json
```

채택 조건:

- 날짜/금리 normalized output 정확도 회귀 없음.
- 빈 값, false positive, 실패 행 증가 없음.
- fixture coverage 유지.
- P95 OCR 또는 행 처리시간이 최소 10% 개선되거나, 패키징 변경이면 사전
  선언한 크기 절감 기준을 만족.
- 같은 조건으로 3회 연속 fixture 실행에서 안정적이어야 함.

## 구현 순서

1. 실제 날짜/금리 crop fixture와 `ground_truth.csv`를 만든다.
2. fixture audit를 통과시킨다.
3. 현재 EasyOCR 기준선과 matrix 결과를 `.analysis_tmp/`에 기록한다.
4. field allowlist, `detail=1`, confidence threshold, preprocessing,
   wait-time 후보를 기본값 변경 없이 실험한다.
5. 같은 입력 10행 라이브 run report를 비교한다.
6. 정확도 회귀가 없는 후보만 기본값 승격 대상으로 삼는다.
7. 남은 controller/UI glue를 작은 단위로 계속 추출한다.
8. 패키징 크기 축소는 한 변경마다 clean build와 package smoke를 통과시킨다.

## 기본 검증 명령

구조 변경 후 최소 게이트:

```powershell
python -m ruff check .
python -m pytest --basetemp $env:TEMP\checkocr2-pytest
python -m compileall checkocr2 scripts check_capture_ocr.py Check_Capture_Excel_V6.1_배포.py
python scripts\benchmark_ocr.py --dry-run --allow-empty-fixture
python scripts\benchmark_ocr_matrix.py --dry-run --allow-empty-fixture --allowlist-modes none,field
```

패키징 영향이 있으면 clean release venv에서 PyInstaller 빌드와 real OCR
package smoke까지 실행한다.

## 현재 남은 핵심 과제

- 실제 OCR fixture가 없어서 정확도/속도 최적화 결론을 낼 수 없다.
- 같은 입력 10행 라이브 비교가 없어서 wait-time 기본값을 줄일 수 없다.
- `check_capture_ocr.py`에는 아직 일부 Tk controller glue가 남아 있다.
- 패키지 크기 최적화는 package smoke와 함께 작은 단위로 계속 진행해야 한다.

## 운영 원칙

- GUI 기능과 편의성은 그대로 둔다.
- OCR 성능 주장은 benchmark와 run report로만 확정한다.
- production Excel, screenshot, crop fixture, 개인 설정 파일은 커밋하지 않는다.
- 실패를 숨기는 broad exception은 adapter 또는 top-level safety boundary에만
  남기고, 나머지는 typed error로 좁힌다.
- 문서와 테스트를 함께 갱신해 다음 작업자가 같은 판단을 반복하지 않게 한다.
