# CheckOCR2 병렬 에이전트 재구현 계획

작성일: 2026-05-11

## 목적

현재 GUI 기능과 사용 편의성을 유지하면서 CheckOCR2의 OCR 정확도, 처리
속도, 패키징 안정성, 코드 구조를 단계적으로 개선한다. 이 계획은 화면
리디자인이 아니라 기존 Tkinter 운영 흐름을 보존한 구조 재구현 계획이다.

## 현재 기준선

- 실행 경로는 `python check_capture_ocr.py`,
  `python Check_Capture_Excel_V6.1_배포.py`, `python -m checkocr2.main` 모두
  유지한다.
- `checkocr2/`에는 설정, 경로, Excel I/O, OCR 텍스트 정규화, OCR 엔진
  어댑터, 단일 필드 OCR 추출, 날짜/금리 OCR pair 처리, 화면 자동화,
  캡처 어댑터, 워크플로, 런 리포트, 테이블 모델, 런타임 상태, 작업
  컨트롤러, OCR 초기화 포함 주요 UI action/helper가 분리되어 있다.
- 최근 model seam은 `OcrRow.from_dict()` 입력을 `Mapping[str, Any]`로 넓혀
  legacy grid dict와 workflow row snapshot 타입을 함께 지원한다.
- 최신 기록 기준 검증은 `ruff`, `pytest` 435개, `compileall`, OCR benchmark
  dry-run, matrix dry-run, source GUI smoke, clean PyInstaller build, real OCR
  package smoke를 통과했다.
- 최신 기록 기준 source/package smoke는 최소 창 크기 `1000x600`과 clean
  GUI exit을 검사한다. 확인된 창 크기는 `1044x788`이고, 최신 패키지 크기는
  약 `596.408 MB`, strict package smoke startup은 `3.704`초다.
- 실제 OCR crop fixture와 동일 입력 10행 live 비교가 아직 없으므로 OCR
  기본값, wait-time, OCR 엔진 교체는 기본값으로 승격하지 않는다.

## 보존해야 할 GUI 계약

- 기존 창 제목, 아이콘, 메뉴, 툴바, 로그 패널, 테마 선택.
- `F5`, `Esc`, `F1`, `Ctrl+S`, `Ctrl+L`, `Ctrl+O` 및 그리드 편집 단축키.
- Excel 로드, 출력 폴더 자동 설정, `_updated.xlsx` export, run report 생성.
- Excel 빈 셀과 NaN 값은 grid 표시, 복사, export에서 빈 문자열로 유지.
- 클릭 지점, 전체/날짜/금리 영역 선택, 미리보기 오버레이, 프리셋 관리.
- OCR 시작/중지, KBP skip, 상세 이미지 저장, 업스케일 옵션.

변경이 이 계약을 건드리면 `docs/GUI_PARITY_CHECKLIST.md`에 수동 증거를
남기거나 자동 테스트를 추가한다. 현재 체크리스트에는 최소 창 크기
`1000x600`, clean GUI exit, 메뉴/툴바/단축키/source icon helper 자동 검증
증거와 파일/폴더/Excel/grid 자동 검증 증거가 포함되어 있다.

## 병렬 작업 스트림

| 스트림 | 책임 | 산출물 |
| --- | --- | --- |
| 아키텍처 | 남은 `check_capture_ocr.py` controller glue 분리, module boundary 정리 | 작은 refactor commit, `docs/ARCHITECTURE.md` 갱신 |
| OCR/성능 | fixture 구축, benchmark matrix, 동일 입력 live 비교, wait 후보 검증 | `.analysis_tmp/*` 리포트, 정확도/속도 판정 |
| TDD/검증 | fake OCR/screen/Tk 기반 characterization test 확장 | `tests/test_*.py`, GUI parity 테스트 |
| UI parity | 실제 GUI smoke, 체크리스트 증거, 단축키/대화상자 검증 | `docs/GUI_PARITY_CHECKLIST.md` dated evidence |
| 패키징 | dependency pin, PyInstaller spec, package smoke, build metadata, 크기 축소 | clean build, package smoke 결과 |
| 리뷰/안전성 | broad exception, silent failure, 보안/개인정보 커밋 위험 검토 | 리뷰 결과와 수정 commit |

각 에이전트는 파일 소유 범위를 분리한다. 통합 담당자는 한 번에 하나의
slice만 merge하고 전체 게이트를 다시 실행한다.

## 구현 순서

1. 실제 날짜/금리 crop fixture를 만들고 `ground_truth.csv`를 수동 검증한다.
2. `scripts\audit_ocr_fixtures.py`로 fixture 준비 상태를 통과시킨다.
3. 현재 EasyOCR baseline과 matrix 결과를 기록한다.
4. `detail=1`, field allowlist, confidence threshold, preprocessing,
   wait-time 후보를 기본값 변경 없이 실험한다.
5. 같은 입력 최소 10행의 baseline/candidate run report를 비교한다.
6. `scripts\check_ocr_evidence_bundle.py`로 not-ready, dry-run, zero-case,
   coverage-changed, rejected live-comparison artifact를 fail-closed로
   차단한다. 선택 후보 matrix는 `--require-no-matrix-regressions`로 더
   엄격하게 검사한다.
7. 정확도 회귀가 없고 P95 처리시간 또는 패키지 크기가 의미 있게 개선된
   후보만 기본값 승격 대상으로 올린다.
8. 남은 controller/UI glue를 작은 단위로 계속 추출한다.
9. 패키지 크기 최적화는 변경마다 clean build와 real package smoke를 통과시킨다.

## 검증 명령

기본 구조 변경 게이트:

```powershell
python -m ruff check .
python -m pytest --basetemp $env:TEMP\checkocr2-pytest
python -m compileall checkocr2 scripts check_capture_ocr.py Check_Capture_Excel_V6.1_배포.py
python scripts\benchmark_ocr.py --dry-run --allow-empty-fixture
python scripts\benchmark_ocr_matrix.py --dry-run --allow-empty-fixture --allowlist-modes none,field
python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --require-settings-file --min-window-width 1000 --min-window-height 600 --require-clean-exit
```

OCR 후보 또는 속도 후보 검증:

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

## 현재 열려 있는 게이트

- `tests\fixtures\ocr_crops\ground_truth.csv`가 아직 없어 fixture audit는 준비
  전 상태다.
- 동일 입력 10행 live OCR 비교가 아직 없다.
- `docs/GUI_PARITY_CHECKLIST.md`는 세 Python entrypoint와 built EXE의 dated
  자동 launch/package 증거를 기록하지만, 전체 자동 green gate는 아니다.
- package-affecting 변경은 항상 clean PyInstaller build와 real OCR package smoke가
  필요하다.

## 커밋 규칙

- `DESIGN.md`, `.analysis_tmp/`, `settings.json`, crop fixture, 생산 Excel,
  screenshot, run report JSON은 명시적 요청이 없으면 stage하지 않는다.
- commit은 하나의 boundary만 포함한다. 예: `refactor: extract settings actions`,
  `test: add OCR fixture audit`, `docs: document reimplementation plan`.
- push 전에는 `git status --short`, `git diff --cached --check`, 관련 검증
  명령 결과를 확인한다.
