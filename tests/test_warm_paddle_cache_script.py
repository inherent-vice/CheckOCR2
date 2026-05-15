from __future__ import annotations

import os

from scripts.warm_paddle_cache import language_for_model, warm_paddle_cache


def test_language_for_model_uses_korean_for_korean_models():
    assert language_for_model("korean_PP-OCRv5_mobile_rec") == ["ko", "en"]
    assert language_for_model("PP-OCRv5_mobile_rec") == ["en"]


def test_warm_paddle_cache_sets_model_env_and_restores_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("PADDLE_PDX_CACHE_HOME", str(tmp_path / "existing-cache"))
    monkeypatch.setenv("CHECKOCR2_PADDLE_REC_MODEL", "existing-model")
    calls = []

    class Reader:
        def __init__(self):
            self.reader = self
            self.closed = False

        def close(self):
            self.closed = True

    def reader_factory(languages, *, gpu=False):
        calls.append(
            {
                "languages": languages,
                "gpu": gpu,
                "model": os.environ["CHECKOCR2_PADDLE_REC_MODEL"],
                "cache": os.environ["PADDLE_PDX_CACHE_HOME"],
            }
        )
        return Reader()

    report = warm_paddle_cache(
        ["korean_PP-OCRv5_mobile_rec"],
        cache_dir=tmp_path / "new-cache",
        reader_factory=reader_factory,
    )

    assert report["status"] == "ok"
    assert calls == [
        {
            "languages": ["ko", "en"],
            "gpu": False,
            "model": "korean_PP-OCRv5_mobile_rec",
            "cache": str(tmp_path / "new-cache"),
        }
    ]
    assert os.environ["PADDLE_PDX_CACHE_HOME"] == str(tmp_path / "existing-cache")
    assert os.environ["CHECKOCR2_PADDLE_REC_MODEL"] == "existing-model"


def test_warm_paddle_cache_dry_run_does_not_create_reader(tmp_path):
    report = warm_paddle_cache(
        ["korean_PP-OCRv5_mobile_rec"],
        cache_dir=tmp_path,
        dry_run=True,
        reader_factory=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError),
    )

    assert report["status"] == "ok"
    assert report["dry_run"] is True
    assert report["warmed"] == []
