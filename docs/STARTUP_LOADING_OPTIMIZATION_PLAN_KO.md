# CheckOCR2 V7 시작 로딩 최적화 계획

작성일: 2026-05-15  
대상: `CheckCaptureOCR_V7.0`, PaddleOCR 3.5.0 / PP-OCRv5 운영 배포

## 결론

다른 PC에서 첫 실행이 느린 주된 이유는 Paddle/PaddleX 모델 캐시 생성, 대형 OneDIR 패키지 파일 스캔, 그리고 기존 EasyOCR fallback의 즉시 초기화 비용이다. GUI 기능과 업무 흐름은 유지하고, 다음 네 가지를 적용한다.

1. 시작 단계별 시간을 JSONL로 기록한다.
2. OCR 준비 중에는 별도 로딩 화면을 표시한다.
3. EasyOCR fallback은 Paddle 결과가 비어 있을 때만 지연 로드한다.
4. Paddle 모델 캐시를 사전 생성하거나 선택적으로 패키지에 포함할 수 있게 한다.

## 현재 병목

- Tk 화면은 빠르게 뜨지만 OCR 초기화가 백그라운드에서 오래 걸리면 사용자는 멈춘 것으로 오해할 수 있다.
- PaddleX 모델이 없으면 `%USERPROFILE%\.paddlex\official_models` 아래에 모델을 다운로드하고 캐시를 만든다.
- 기존 구조는 Paddle reader 생성 직후 EasyOCR English CPU fallback도 함께 만들었기 때문에 PyTorch/EasyOCR 로딩 비용이 시작 시간에 섞였다.
- OneDIR 패키지는 파일 수가 많아 새 PC에서 보안 프로그램의 최초 스캔 영향을 받을 수 있다.

## 구현 단계

### Phase 0. 시작 추적

`checkocr2/startup_trace.py`를 추가해 process start 기준 elapsed time을 기록한다. 기록 위치는 `%APPDATA%\CheckOCR2\logs\startup_trace.jsonl`이며, 주요 이벤트는 Tk 초기화, UI 구성 완료, OCR 초기화 요청, Paddle import, 모델 캐시 확인, reader 준비, runtime state 변경이다.

측정 스크립트:

```powershell
python scripts\measure_startup.py --entrypoint "python check_capture_ocr.py" --isolated-appdata
python scripts\measure_startup.py --entrypoint "dist\CheckCaptureOCR_V7.0\CheckCaptureOCR_V7.0.exe" --isolated-appdata
```

### Phase 1. 로딩 화면

`RuntimeState.OCR_LOADING` 동안 `checkocr2/ui/loading_overlay.py`의 Toplevel overlay를 띄운다. 문구는 `OCR 모델 준비 중`으로 고정하고, 최초 실행 시 모델 캐시 생성으로 시간이 걸릴 수 있음을 안내한다. Ready가 되면 자동으로 닫히고, Error 상태에서는 실패 메시지를 남긴다.

### Phase 2. EasyOCR 지연 fallback

`BlankFallbackOcrReader`는 fallback reader 객체 대신 factory도 받을 수 있다. Paddle OCR 결과가 비어 있을 때만 EasyOCR English CPU를 생성한다. smoke 상태 JSON에는 `ocr_fallback_enabled`, `ocr_fallback_loaded`, `ocr_fallback_load_count`, `ocr_fallback_init_ms`를 기록해 “fallback 가능”과 “실제로 로드됨”을 구분한다.

### Phase 3. Paddle 캐시 준비

`scripts/warm_paddle_cache.py`로 배포 전 또는 사용자 PC 최초 실행 전에 Paddle 모델 캐시를 만들 수 있다.

```powershell
python scripts\warm_paddle_cache.py --models korean_PP-OCRv5_mobile_rec
```

패키지 빌드 시 `CHECKOCR2_PACKAGE_PADDLE_MODELS`를 지정하면 로컬 PaddleX 공식 모델 캐시에서 필요한 모델 폴더만 OneDIR에 포함한다. 포함된 모델은 `CHECKOCR2_PADDLE_MODEL_ROOT`를 통해 우선 사용한다.

## 운영 기준

- Warm run: 창 표시 5초 이내, OCR Ready 10초 이내를 목표로 한다.
- Cold run with bundled/cache-ready model: OCR Ready 30초 이내를 목표로 한다.
- Cold run requiring download/cache: 로딩 화면 5초 이내 표시, OCR Ready 180초 이내를 목표로 한다.
- OCR 출력, Excel 컬럼, 파일명, 단축키, 한국어 GUI 라벨은 변경하지 않는다.
- 금리 기본 자리수는 V7 기준 4자리로 유지한다.

## 검증 게이트

필수 검증:

```powershell
python -m ruff check .
python -m compileall checkocr2 scripts check_capture_ocr.py Check_Capture_Excel_V6.1_배포.py
python -m pytest --basetemp $env:TEMP\checkocr2-startup-opt
python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --ocr-ready-mode real --require-settings-file --min-window-width 1000 --min-window-height 600 --require-clean-exit
python scripts\source_gui_smoke.py --entrypoint "python Check_Capture_Excel_V6.1_배포.py" --isolated-appdata --require-ready --ocr-ready-mode real --require-settings-file --min-window-width 1000 --min-window-height 600 --require-clean-exit
python -m PyInstaller build_app.spec
python scripts\package_smoke.py dist\CheckCaptureOCR_V7.0\CheckCaptureOCR_V7.0.exe --timeout 90 --require-package-metadata --paddle-package --require-ocr-ready --ocr-ready-mode real --ocr-ready-timeout 180 --require-settings-file --isolated-appdata --min-window-width 1000 --min-window-height 600 --require-clean-exit
```

추가 성능 검증:

```powershell
python scripts\measure_startup.py --entrypoint "python check_capture_ocr.py" --repeat 3 --isolated-appdata --output-json .analysis_tmp\source_startup_measure.json
python scripts\measure_startup.py --entrypoint "dist\CheckCaptureOCR_V7.0\CheckCaptureOCR_V7.0.exe" --repeat 3 --isolated-appdata --output-json .analysis_tmp\package_startup_measure.json
```

## 중단 규칙

- Paddle 정확도나 Excel 결과가 바뀌면 기본 엔진 승격 또는 배포를 중단한다.
- 생산 네트워크 폴더에는 쓰지 않는다.
- production workbook, screenshot, OCR crop, raw OCR report는 커밋하지 않는다.
- 모델 포함 패키지가 사내 보안 정책이나 배포 크기 제한을 넘으면 사전 캐시 방식으로 전환한다.
- `paddle-only` 패키지는 EasyOCR fallback 제거 승인을 받은 뒤 별도 프로파일로 진행한다.
