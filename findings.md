# Startup Loading Optimization Findings

## Current Evidence

- The V7 package is OneDIR and approximately `1052.756 MB` with thousands of files, so first-run security scanning can be material.
- PaddleX official models are stored under `%USERPROFILE%\.paddlex\official_models` by default. `PADDLE_PDX_CACHE_HOME` can redirect this cache.
- Current OCR initialization starts after the Tk window is built and sets `RuntimeState.OCR_LOADING`.
- Current Paddle initialization immediately creates an EasyOCR English CPU blank fallback, which can load PyTorch/EasyOCR during startup even when Paddle succeeds.
- Existing package smoke validates `ocr_fallback_enabled=True` for Paddle real OCR ready, so tests and smoke validation need to distinguish enabled from loaded.
- After V7's default rate precision changed to 4, fixture audit integer aliases also need to accept `7 -> 7.0000`, not only `7 -> 7.000`.

## Implementation Constraints

- Preserve Korean UI labels and current operator workflow.
- Keep Paddle as default OCR engine.
- Keep EasyOCR as fallback/baseline, but lazy-load it.
- Avoid broad package profile changes until startup timing and fallback usage are measured.
