# CheckOCR2 실사용 데이터 기반 최종화 계획

작성일: 2026-05-13

## 결론

최종 OCR 후보는 최신 PaddleOCR 3.x 계열의 PP-OCRv5로 잡는다. 다만 GUI
기능과 일일 업무 결과를 유지해야 하므로 EasyOCR은 기준선으로 남기고,
실사용 데이터 benchmark, repeatability, live smoke, package smoke가 모두
통과한 뒤에만 PaddleOCR을 기본 엔진으로 승격한다.

공식 확인 기준:

- PyPI `paddleocr` 최신 배포: 3.5.0, 2026-04-21 업로드
  (`https://pypi.org/project/paddleocr/`).
- GitHub `PaddlePaddle/PaddleOCR` 최신 릴리스: v3.5.0, 2026-04-21
  (`https://github.com/PaddlePaddle/PaddleOCR/releases`).
- PaddleOCR 3.x 문서: 기본 OCR 파이프라인은 PP-OCRv5이며, 2.x API와
  호환되지 않는 변경이 있다
  (`https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html`).
- PP-OCRv5 문서: 다국어 인식, Korean 포함, PP-OCRv3 대비 정확도 개선을
  명시한다
  (`https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.en.md`).

## 실사용 데이터 기준선

운영 데이터 위치:

```text
\\10.10.10.11\파생상품평가본부\B.SWAP평가팀\8_엑셀수동일일평가\CouponCheck\CHECK
```

확인된 구조:

- 루트: `List_CouponCheck_(YYYYMMDD).xlsx` 원본 workbook.
- 루트: `List_CouponCheck_(YYYYMMDD)_updated.xlsx` 기존 OCR 결과 workbook.
- 일자 폴더: `List_CouponCheck_(YYYYMMDD)\종목코드.png` 전체 영역 이미지.
- 최근 샘플 PNG 개수: 2026-05-13 69개, 2026-05-12 79개, 2026-05-11
  110개.
- 최근 샘플 이미지 크기: 884x496, 747x428, 691x425 등 일자별 차이가 있다.
- 최근 샘플에는 `_date.png`, `_rate.png` crop 파일이 없었다.
- 2026-05-13 원본 workbook은 `종목코드, 종목명, 날짜, 표면금리`, 기존 결과
  workbook은 `종목코드, 종목명, 날짜, 금리, 상태` 형태다.

## 작업 원칙

- 네트워크 원본에는 쓰지 않는다. 모든 검증은 `.analysis_tmp/real_data/...`
  로컬 복사본에서 수행한다.
- 원본 workbook, 결과 workbook, PNG 폴더는 SHA256 manifest로 묶는다.
- `_updated.xlsx`의 날짜/금리는 fixture 초안 값으로만 사용하고, 승격 전
  audit에서 blank, 비정규화 값, 중복, 누락 이미지를 거부한다.
- GUI 기능, 버튼, 단축키, 파일 선택, 출력 형식, 한국어 문구는 유지한다.

## Phase 1: 실데이터 수집 자동화

1. `scripts/inventory_couponcheck_real_data.py`를 추가해 일자별 workbook,
   `_updated.xlsx`, PNG 개수, 이미지 크기 분포, 누락 짝을 JSON으로 기록한다.
2. `scripts/prepare_real_data_workspace.py`를 추가해 선택 일자 원본을
   `.analysis_tmp/real_data/YYYYMMDD/`로 복사하고 manifest를 만든다.
3. 최근 10영업일을 기본 release 후보군으로 삼고, 최소 500개 row 또는
   1,000개 date/rate crop을 확보한다.

## Phase 2: Fixture 생성

1. 우선 기존 GUI를 로컬 복사 workbook에 대해 실행해 `*_date.png`,
   `*_rate.png` crop과 run report를 다시 생성한다.
2. 과거 전체 영역 `종목코드.png`만 활용해야 하는 경우,
   `scripts/extract_crops_from_full_images.py`를 추가해 이미지 크기별 ROI
   template을 적용한다.
3. crop 초안은 `tests/fixtures/ocr_crops/ground_truth_draft.csv`로 만들고,
   사람이 확인한 뒤 `scripts/promote_ocr_fixtures.py`로 `ground_truth.csv`를
   승격한다.
4. `scripts/audit_ocr_fixtures.py` 통과 전에는 benchmark 결과를 기준선으로
   인정하지 않는다.

## Phase 3: PaddleOCR 엔진 도입

1. `checkocr2/ocr_engine.py`를 EasyOCR 전용 함수에서 `OcrEngine` protocol
   기반으로 확장한다.
2. `checkocr2/ocr_paddle_engine.py`를 추가한다.
3. 후보 설정:
   - `paddleocr==3.5.0`
   - PP-OCRv5
   - `use_doc_orientation_classify=False`
   - `use_doc_unwarping=False`
   - `use_textline_orientation=False`
   - CPU 기본, GPU는 별도 측정
   - `paddle_static` 우선
4. PaddleOCR 결과의 `rec_texts`, `rec_scores`를 기존 `raw_text`,
   `confidence` 구조로 변환해 run report와 benchmark format을 유지한다.
5. EasyOCR `allowlist`와 동일하지 않은 옵션은 별도 Paddle 후보군으로
   분리해 비교한다.

## Phase 4: Benchmark와 승격 기준

필수 산출물:

아래 `--engine`, `--engines` 옵션은 Phase 3에서 benchmark harness에 추가할
신규 옵션이다.

```powershell
python scripts\audit_ocr_fixtures.py --output-json .analysis_tmp\ocr_fixture_audit.json
python scripts\benchmark_ocr.py --engine easyocr --output-json .analysis_tmp\easyocr_baseline.json
python scripts\benchmark_ocr.py --engine paddle --output-json .analysis_tmp\paddle_baseline.json
python scripts\benchmark_ocr_matrix.py --engines easyocr,paddle --output-json .analysis_tmp\ocr_engine_matrix.json
python scripts\check_ocr_repeatability.py --benchmark-json .analysis_tmp\paddle_repeat_1.json .analysis_tmp\paddle_repeat_2.json .analysis_tmp\paddle_repeat_3.json --output-json .analysis_tmp\ocr_repeatability.json
```

승격 기준:

- date/rate 각각 EasyOCR 기준선보다 exact accuracy가 낮아지면 실패.
- expected nonempty 값에서 blank가 발생하면 실패.
- 최근 10영업일 fixture coverage가 줄어들면 실패.
- 3회 반복 결과에서 exact accuracy, blank, false positive가 흔들리면 실패.
- 평균 속도만 보지 않고 p95 latency와 row-level total time을 함께 본다.

## Phase 5: Live Smoke와 패키징

1. `scripts/prepare_live_smoke_workspace.py`로 1-2 row 로컬 복사본 smoke를
   만든다.
2. 같은 입력 10 row를 EasyOCR/Paddle 각각 실행해
   `scripts/compare_run_reports.py`로 날짜, 금리, 상태, timing을 비교한다.
3. Paddle 승격 후 `python check_capture_ocr.py`,
   `python Check_Capture_Excel_V6.1_배포.py`, `python -m checkocr2.main`을 모두
   smoke-test한다.
4. PyInstaller build 후 package metadata, package size, OCR ready, clean exit를
   `scripts/package_smoke.py`로 검증한다.
5. Paddle dependency와 model cache는 패키지에 모두 넣을지, `%APPDATA%`에
   사전 설치할지 package size와 오프라인 실행성으로 결정한다.

## 완료 정의

- 실사용 데이터 기반 fixture audit 통과.
- EasyOCR baseline, Paddle baseline, matrix, repeatability 통과.
- copied workbook live smoke 통과.
- 동일 입력 live comparison에서 사용자-visible 결과 regression 없음.
- PaddleOCR 기본 엔진 승격 후 GUI parity checklist 통과.
- source/package smoke 통과.
- 최종 evidence bundle이 `accepted=true`를 반환.
