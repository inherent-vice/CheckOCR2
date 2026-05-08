from __future__ import annotations

from checkocr2.ocr_engine import read_ocr_text


class FakeReader:
    def __init__(self):
        self.calls = []

    def readtext(self, image, detail=0, **kwargs):
        self.calls.append((image, detail, kwargs))
        return ["2026/05/08"]


def test_read_ocr_text_delegates_to_reader_with_detail():
    reader = FakeReader()

    result = read_ocr_text(reader, "image-array", detail=1)

    assert result == ["2026/05/08"]
    assert reader.calls == [("image-array", 1, {})]


def test_read_ocr_text_passes_allowlist_only_when_requested():
    reader = FakeReader()

    read_ocr_text(reader, "image-array", detail=0, allowlist="0123456789")

    assert reader.calls == [("image-array", 0, {"allowlist": "0123456789"})]
