# CheckOCR2 재구현 문서 인덱스

작성일: 2026-05-12

## 목적

이 문서는 현재 재구현 작업을 이어받을 때 먼저 읽을 문서와 남은 게이트를
한 곳에 묶는다. 기준은 기존 Tkinter GUI와 업무 흐름을 그대로 유지하면서
내부 구조, OCR 검증 체계, 패키징 안정성을 개선하는 것이다.

## 먼저 볼 문서

- `docs/REIMPLEMENTATION_STATUS_KO.md`: 한국어 현황 요약, 보존할 GUI 동작,
  OCR 정확도와 속도 판단 기준.
- `docs/REIMPLEMENTATION_EXECUTION_GUIDE.md`: 다음 구현자가 따라야 할 실행
  규칙, safe slice, 검증 명령, commit checklist.
- `docs/REIMPLEMENTATION_HANDOFF.md`: 최신 구조 변경, 검증 결과, 남은 작업
  이력.
- `docs/REIMPLEMENTATION_COMPLETION_AUDIT.md`: 전체 목표 완료 여부를 판정하는
  hard gate. 현재 상태는 `not complete`다.
- `docs/GUI_PARITY_CHECKLIST.md`: 메뉴, 툴바, 단축키, 파일/폴더, grid,
  좌표, 옵션, 로그, workflow 요약의 parity 증거.

## 현재 상태

- `check_capture_ocr.py`는 호환 런처이고, Tk shell은 `checkocr2/app.py`가
  소유한다.
- `OCRWorkflowManager`는 `checkocr2/ocr_workflow_manager.py`에 있고,
  실행 조립은 `checkocr2/workflow_execution.py`로 분리되었다.
- OCR run setup, event bridge, legacy adapters, report finalization은 각각
  package module로 분리되어 focused pytest 증거가 있다.
- 최신 기록 기준 source/package smoke는 `1044x788` 창, clean exit,
  isolated settings, strict package smoke startup `1.109s`, package size
  `596.409 MB`를 확인했다.

## 남은 hard gate

- `tests\fixtures\ocr_crops\ground_truth.csv`가 없어 real OCR fixture audit가
  아직 준비 전이다.
- audited fixture 기반 EasyOCR baseline과 matrix 결과가 없다.
- 같은 입력 최소 10행 baseline/candidate live run report 비교가 없다.
- 따라서 OCR 기본값, wait-time, confidence threshold, preprocessing,
  OCR engine 교체는 아직 승격하지 않는다.

## 다음 작업 순서

1. 현재 구조 변경은 `ruff`, focused pytest, full pytest, `compileall`,
   source GUI smoke 순서로 검증한다.
2. OCR 성능 변경 전에는 crop fixture를 만들고
   `scripts\check_ocr_evidence_bundle.py --require-live-comparison`을 통과시킨다.
3. controller/UI glue extraction은 한 번에 하나의 module boundary만 이동한다.
4. 패키지 영향 변경은 clean PyInstaller build와 real package smoke를 다시
   통과시킨다.
