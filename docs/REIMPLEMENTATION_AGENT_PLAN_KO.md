# CheckOCR2 병렬 에이전트 재구현 계획

작성일: 2026-05-11

## 목적

현재 GUI 기능과 사용 편의성은 유지하면서 CheckOCR2의 OCR 정확도, 처리 속도,
패키징 안정성, 코드 구조를 단계적으로 개선한다. 화면을 새로 설계하는 작업이
아니라, 기존 Tkinter 조작 흐름을 보존한 상태에서 내부 경계를 테스트 가능한
패키지 모듈로 옮기는 작업이다.

## 현재 기준선

- 실행 경로는 `python check_capture_ocr.py`,
  `python Check_Capture_Excel_V6.1_배포.py`, `python -m checkocr2.main`을
  모두 유지한다.
- `checkocr2/`에는 설정, 경로, Excel I/O, OCR 텍스트 정규화, OCR 엔진
  어댑터, 화면 자동화, 캡처 어댑터, 워크플로, 런 리포트, 런타임 상태,
  큐 디스패치, 주요 UI action/helper가 분리되어 있다.
- 최신 소스 게이트는 `ruff`, `pytest` 249개, `compileall`, OCR benchmark
  dry-run, matrix dry-run, canonical source GUI smoke까지 통과했다.
- 최신 패키지 게이트는 clean PyInstaller build와 real OCR package smoke를
  통과했으며, 패키지 크기는 약 `596.382 MB`, 시작 시간은 `1.765`초다.
- 아직 실제 OCR crop fixture와 같은 입력 10행 라이브 비교가 없으므로 OCR
  기본값, wait-time, 엔진 교체는 기본값으로 승격하지 않는다.

## 반드시 보존할 GUI 계약

- 기존 창 제목, 한국어 라벨, 메뉴, 툴바, 로그 패널, 테마 선택.
- `F5`, `Esc`, `F1`, `Ctrl+S`, `Ctrl+L`, `Ctrl+O` 및 그리드 편집 단축키.
- Excel 로드, 출력 폴더 자동 설정, `_updated.xlsx` export, run report 생성.
- 클릭 지점, 전체/날짜/금리 영역 선택, 미리보기 오버레이, 프리셋 관리.
- OCR 시작/중지, KBP skip, 상세 이미지 저장, 업스케일 옵션.

변경이 이 항목을 건드리면 `docs/GUI_PARITY_CHECKLIST.md`에 수동 증거를
남기거나 자동화 테스트를 추가한다.

## 병렬 에이전트 작업 분할

| 스트림 | 책임 | 주요 산출물 |
| --- | --- | --- |
| 아키텍처 | 남은 `check_capture_ocr.py` controller glue 분리, 모듈 경계 유지 | 작은 refactor PR, `docs/ARCHITECTURE.md` 갱신 |
| OCR/성능 | fixture 구축, benchmark matrix, 같은 입력 live 비교 | `.analysis_tmp/*` 리포트, 후보별 정확도/속도 판단 |
| TDD/품질 | fake OCR/screen/Tk 기반 characterization test 확대 | `tests/test_*.py`, GUI parity 회귀 테스트 |
| UI parity | 실제 GUI smoke, 체크리스트 증거, 단축키/대화상자 검증 | `docs/GUI_PARITY_CHECKLIST.md` 날짜별 증거 |
| 패키징 | dependency pin, PyInstaller spec, package smoke, 크기 최적화 | clean build, package smoke 결과 |
| 리뷰/안전성 | broad exception, silent failure, 보안/개인정보 커밋 위험 검토 | 리뷰 결과와 수정 커밋 |

각 에이전트는 쓰기 범위를 분리한다. 통합 담당자는 한 번에 하나의 slice만
merge하고 전체 게이트를 다시 실행한다.

## 구현 순서

1. 실제 날짜/금리 crop fixture를 만들고 `ground_truth.csv`를 수동 검수한다.
2. `scripts\audit_ocr_fixtures.py`로 fixture 품질 게이트를 통과시킨다.
3. 현재 EasyOCR 기준선과 matrix 결과를 저장한다.
4. `detail=1`, field allowlist, confidence threshold, preprocessing,
   wait-time 후보를 기본값 변경 없이 실험한다.
5. 같은 입력 최소 10행의 baseline/candidate run report를 비교한다.
6. 정확도 회귀가 없고 P95 처리시간 또는 패키지 크기가 의미 있게 개선된
   후보만 기본값 승격 대상으로 삼는다.
7. 남은 controller/UI glue를 작은 단위로 계속 추출한다.
8. 패키징 크기 최적화는 한 변경마다 clean build와 package smoke를 통과시킨다.

## 검증 명령

```powershell
python -m ruff check .
python -m pytest --basetemp $env:TEMP\checkocr2-pytest
python -m compileall checkocr2 scripts check_capture_ocr.py Check_Capture_Excel_V6.1_배포.py
python scripts\benchmark_ocr.py --dry-run --allow-empty-fixture
python scripts\benchmark_ocr_matrix.py --dry-run --allow-empty-fixture --allowlist-modes none,field
python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file
```

OCR 기본값 또는 속도 후보는 추가로 아래 게이트를 통과해야 한다.

```powershell
python scripts\audit_ocr_fixtures.py --output-json .analysis_tmp\ocr_fixture_audit.json
python scripts\compare_run_reports.py .analysis_tmp\baseline_run_report.json .analysis_tmp\candidate_run_report.json --require-p95-improvement --min-p95-improvement-percent 10 --output-json .analysis_tmp\live_ocr_compare.json
```

## 현재 열린 게이트

- `tests\fixtures\ocr_crops\ground_truth.csv`가 아직 없어 fixture audit는
  `not_ready`가 정상 상태다.
- 같은 입력 10행 live OCR 비교가 아직 없다.
- `docs/GUI_PARITY_CHECKLIST.md`는 전체 자동화 green gate가 아니라 수동
  체크리스트다.
- package-affecting 변경은 clean PyInstaller build와 real OCR package smoke가
  필요하다.
