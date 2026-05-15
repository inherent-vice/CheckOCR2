# CheckOCR2 V7 시작 로딩 최적화 계획

작성일: 2026-05-15  
대상: `dist/CheckCaptureOCR_V7.0/CheckCaptureOCR_V7.0.exe`, PaddleOCR 3.5.0 / PP-OCRv5 운영 배포

## 결론

다른 PC의 최초 실행 지연은 정상적인 캐시 생성 비용이 포함되어 있지만, 현재 구조는 개선 여지가 크다. 우선순위는 다음과 같다.

1. EasyOCR fallback을 시작 시점에 같이 초기화하지 말고 lazy-load로 전환한다.
2. Paddle/PaddleX 모델 캐시를 운영 배포 전에 준비하거나 패키지 안에 포함한다.
3. 첫 실행이 오래 걸릴 수 있음을 명확히 보여주는 로딩 화면을 추가한다.
4. 시작 시간을 계측해 cold run과 warm run을 분리해서 관리한다.

GUI 기능, 단축키, 엑셀 입출력, OCR 결과 포맷은 변경하지 않는다.

## 현재 시작 흐름

현재 앱은 `checkocr2/app.py`에서 Tk 화면을 만든 뒤 `after(100, start_ocr_initialization_async)`로 OCR 초기화를 시작한다. `checkocr2/ui/ocr_initialization_actions.py`는 상태를 `OCR_LOADING`으로 바꾸고 백그라운드 스레드에서 `OCRWorkflowManager.initialize_ocr()`를 호출한다.

기본 OCR 엔진은 `settings.py`의 `ocr_engine=paddle`이다. Paddle 경로는 `checkocr2/ocr_paddle_engine.py`에서 `TextRecognition` 기반으로 `korean_PP-OCRv5_mobile_rec`을 사용한다. Paddle 초기화가 끝나면 `ocr_reader_lifecycle.py`에서 EasyOCR English CPU fallback도 즉시 생성한다.

현재 패키지는 OneDIR 기준 약 `1052.756 MB`, `4953`개 파일이다. 이 PC의 PaddleX 모델 캐시는 `C:\Users\leeho22\.paddlex\official_models`에 약 `191.16 MB`로 존재한다. 새 PC는 이 캐시가 없으므로 다운로드, 압축 해제, 모델 파일 생성, Windows Defender/보안 프로그램 스캔이 최초 실행에 몰린다.

## 병목 원인

### 1. PaddleX 공식 모델 캐시 미존재

PaddleX 기본 캐시는 `%USERPROFILE%\.paddlex`이며 환경변수 `PADDLE_PDX_CACHE_HOME`으로 바꿀 수 있다. 모델이 없으면 PaddleX가 `official_models` 아래로 공식 모델을 내려받는다. 사내망, 프록시, 백신, 느린 디스크에서는 이 단계가 가장 큰 지연 원인이 된다.

### 2. EasyOCR fallback 즉시 초기화

현재 Paddle reader 생성 후 `add_easyocr_blank_fallback()`가 바로 EasyOCR reader를 만든다. EasyOCR는 PyTorch를 로드하고 자체 모델 캐시도 사용할 수 있어 첫 실행 시간을 늘린다. 실제 30일치 검증에서 Paddle이 화면값 기준 100%였으므로, fallback은 “항상 준비”보다 “필요할 때만 준비”가 더 맞다.

### 3. 대형 OneDIR 패키지 파일 스캔

Paddle, PaddleOCR, PaddleX, EasyOCR, Torch, Torchvision, SciPy, OpenCV 계열이 함께 들어간다. 새 PC나 네트워크 드라이브 실행에서는 보안 프로그램이 수천 개 파일을 검사하면서 창 표시 또는 OCR 준비가 늦어질 수 있다.

### 4. 사용자 피드백 부족

현재 버튼 텍스트는 `OCR 준비 중` 수준이다. 첫 실행이 30초 이상 걸리면 사용자는 멈춘 것으로 판단할 수 있다. 실제로는 모델 다운로드/캐시 준비가 진행 중일 수 있으므로 별도 로딩 화면이 필요하다.

## 목표 지표

| 구분 | 목표 |
| --- | --- |
| Warm run, 캐시 존재 | 창 표시 5초 이내, OCR Ready 10초 이내 |
| Cold run, 로컬 모델 포함 | 창 표시 5초 이내, OCR Ready 30초 이내 |
| Cold run, 모델 다운로드 필요 | 로딩 화면 5초 이내 표시, OCR Ready 180초 이내 |
| 정상 실행 후 재실행 | 모델 다운로드 재시도 없음 |
| OCR 품질 | 기존 30일 화면값 기준 100% 결과 유지 |
| GUI | 기존 업무 흐름, 버튼, 한글 라벨, 엑셀 포맷 유지 |

## 구현 계획

### Phase 0. 시작 시간 계측 추가

시작 병목을 추측하지 않도록 계측부터 넣는다.

- `checkocr2/startup_trace.py` 추가
- 마일스톤 기록: process start, Tk created, UI built, OCR init requested, Paddle import start/end, model cache check, reader ready, fallback state, Ready
- `%APPDATA%\CheckOCR2\logs\startup_trace.jsonl`에 cold/warm 여부와 소요 시간 기록
- `scripts/measure_startup.py`로 source/package fast/real 시작 시간을 자동 측정

검증:

```powershell
python scripts\measure_startup.py --entrypoint "python check_capture_ocr.py"
python scripts\measure_startup.py --entrypoint "dist\CheckCaptureOCR_V7.0\CheckCaptureOCR_V7.0.exe" --isolated-appdata
```

### Phase 1. 로딩 화면 설계 및 구현

Tk 메인 화면은 그대로 유지하되, OCR 준비 중에는 최상단 overlay 또는 splash-style Toplevel을 표시한다.

표시 내용:

- 제목: `OCR 모델 준비 중`
- 본문: 최초 실행이면 `최초 1회는 모델 캐시 생성으로 시간이 걸릴 수 있습니다.`
- 진행 단계: `앱 시작`, `설정 로드`, `PaddleOCR 로드`, `모델 캐시 확인`, `OCR 준비 완료`
- elapsed seconds
- 취소 버튼은 두지 않는다. OCR 초기화를 중간 취소하면 상태 복구가 더 복잡해진다.
- 닫기 버튼은 앱 종료로 동작한다.

동작 원칙:

- Excel 파일 선택, 좌표 설정 화면은 보이되 OCR 시작 버튼만 비활성화한다.
- `RuntimeState.OCR_LOADING`과 연결해 Ready가 되면 자동으로 overlay를 닫는다.
- 오류 시 overlay를 오류 상태로 바꾸고 로그 위치를 안내한다.

대상 파일:

- `checkocr2/ui/loading_overlay.py`
- `checkocr2/ui/ocr_initialization_actions.py`
- `checkocr2/ui/runtime_status_actions.py`
- `tests/test_loading_overlay.py`
- `tests/test_async_ocr_initialization.py`

### Phase 2. EasyOCR fallback lazy-load

`BlankFallbackOcrReader`를 즉시 fallback reader를 받는 구조에서 factory 기반으로 바꾼다.

제안 구조:

- `LazyBlankFallbackOcrReader(primary, fallback_factory)`
- Paddle 결과가 비어 있을 때만 `fallback_factory()` 실행
- fallback 생성 시간과 fallback count를 startup/run report에 기록
- 기본 설정은 `fallback_enabled=True`, `fallback_init_mode=lazy`

운영 효과:

- 첫 실행에서 EasyOCR/PyTorch 모델 초기화 비용 제거
- Paddle 정상 케이스에서는 fallback이 한 번도 로드되지 않음
- 문제가 생기면 fallback은 여전히 사용 가능

검증:

- source/package real smoke에서 `actual_ocr_engine=paddle`
- 시작 직후 `fallback_loaded=false`
- 강제 blank reader 테스트에서만 fallback 생성
- 30일 OCR fixture 결과 변화 없음

### Phase 3. Paddle 모델 캐시 전략

두 가지 배포 방식을 지원한다.

#### A. 사전 캐시 워밍 방식

배포 전에 대상 PC에서 한 번 실행하거나 별도 워밍 스크립트를 실행한다.

```powershell
dist\CheckCaptureOCR_V7.0\CheckCaptureOCR_V7.0.exe --warm-ocr-cache
```

또는:

```powershell
python scripts\warm_paddle_cache.py --models korean_PP-OCRv5_mobile_rec
```

효과:

- 패키지 크기 증가는 없다.
- PC별 최초 1회 작업은 필요하다.

#### B. 모델 포함 패키지 방식

빌드 시 필요한 공식 모델만 포함한다.

대상 모델:

- `korean_PP-OCRv5_mobile_rec`
- 필요 시 `en_PP-OCRv5_mobile_rec`

구현 방향:

- `build_app.spec`에 선택 모델 디렉터리만 datas로 추가
- `checkocr2/ocr_paddle_engine.py`에서 `model_dir`을 우선 사용
- 패키지 내부 모델은 읽기 전용으로 두고, lock/temp/function cache는 `%LOCALAPPDATA%\CheckOCR2\paddlex_cache`를 사용
- `PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True`를 package runtime에서 설정해 불필요한 host connectivity check를 줄인다.

효과:

- 인터넷 없는 PC의 최초 실행 안정성 향상
- 패키지 크기는 약 100-250MB 증가 가능
- 다운로드 지연은 제거되지만 모델 로드 시간은 남는다.

### Phase 4. 패키지 슬림화 검토

V7은 Paddle과 EasyOCR/Torch를 함께 담고 있어 크다. Lazy fallback 후 실제 운영에서 fallback 사용이 0이면 `paddle-only` 배포 프로필을 추가할 수 있다.

프로필:

- `paddle-full`: Paddle + lazy EasyOCR fallback, 현재 안정성 우선
- `paddle-only`: Paddle만 포함, 가장 빠른 시작/작은 패키지 후보
- `diagnostic`: EasyOCR baseline 포함, 검증/비상용

`paddle-only`는 fallback 제거가 사용자-visible 안전망 변화이므로 별도 승인 후 적용한다.

### Phase 5. 운영 배포 절차

운영 배포는 다음 절차로 표준화한다.

1. 로컬 디스크에 `CheckCaptureOCR_V7.0` 폴더 전체 복사
2. 네트워크 드라이브에서 직접 실행하지 않기
3. 최초 1회 실행 또는 `--warm-ocr-cache` 실행
4. Ready 상태 확인
5. 동일 PC 재실행 시간이 목표 범위인지 확인
6. 실패 시 `%APPDATA%\CheckOCR2\logs\startup_trace.jsonl`과 `ocr_app.log` 수집

## 검증 게이트

필수 검증:

```powershell
python -m ruff check .
python -m compileall checkocr2 scripts check_capture_ocr.py Check_Capture_Excel_V6.1_배포.py
python -m pytest --basetemp $env:TEMP\checkocr2-startup-opt
python scripts\source_gui_smoke.py --entrypoint "python check_capture_ocr.py" --isolated-appdata --require-ready --ocr-ready-mode real --require-settings-file --min-window-width 1000 --min-window-height 600 --require-clean-exit
python scripts\package_smoke.py dist\CheckCaptureOCR_V7.0\CheckCaptureOCR_V7.0.exe --timeout 90 --require-package-metadata --paddle-package --require-ocr-ready --ocr-ready-mode real --require-settings-file --isolated-appdata --min-window-width 1000 --min-window-height 600 --require-clean-exit --ocr-ready-timeout 180
```

성능 검증:

- warm run 3회 반복 p50/p95 기록
- isolated `PADDLE_PDX_CACHE_HOME`으로 cold run 시뮬레이션
- 모델 포함 패키지와 사전 캐시 방식 비교
- Windows Defender 실시간 검사 ON/OFF 환경 차이 기록

OCR 검증:

- 30일 reviewed fixture 재실행
- live smoke copied workbook 재실행
- fallback lazy-load 전후 output workbook 비교

## 리스크와 중단 규칙

- Paddle 정확도 또는 엑셀 출력이 바뀌면 최적화 중단
- 로딩 화면이 기존 조작 흐름을 막으면 overlay 범위를 축소
- 모델 포함 패키지가 보안 정책이나 파일 크기 제한을 넘으면 사전 캐시 워밍 방식으로 전환
- `paddle-only` 프로필은 fallback 제거 승인이 없으면 기본 배포로 승격하지 않음
- 네트워크 생산 폴더에는 쓰지 않음

## 권장 실행 순서

1. Phase 0 계측 추가
2. Phase 1 로딩 화면 추가
3. Phase 2 EasyOCR lazy fallback 적용
4. cold/warm 시작 시간 비교
5. 필요 시 Phase 3 모델 포함 또는 워밍 스크립트 적용
6. 패키지 재빌드 및 real package smoke
7. 운영 배포 가이드 업데이트

가장 먼저 할 작업은 Phase 1이 아니라 Phase 0이다. 로딩 화면은 사용자 체감 문제를 해결하지만, 실제 병목 제거 여부는 계측 없이는 판단할 수 없다. 다만 Phase 0과 Phase 1은 같은 PR/커밋으로 묶어도 된다.
