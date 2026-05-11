from __future__ import annotations

from checkocr2.ui import log_actions


class FakeLogTextWidget:
    def __init__(self, *, exists=True, tags=("INFO", "WARNING", "ERROR")):
        self.exists = exists
        self.tags = tags
        self.config_calls = []
        self.inserts = []
        self.seen = []

    def winfo_exists(self):
        return self.exists

    def config(self, **kwargs):
        self.config_calls.append(kwargs)

    def tag_names(self):
        return self.tags

    def insert(self, position, text, tag):
        self.inserts.append((position, text, tag))

    def see(self, position):
        self.seen.append(position)


class FakeApp:
    def __init__(self, widget):
        self.log_text_widget = widget


def test_append_log_text_writes_message_with_existing_level_tag():
    widget = FakeLogTextWidget()
    app = FakeApp(widget)

    log_actions.append_log_text(app, "hello", "warning")

    assert widget.config_calls == [{"state": "normal"}, {"state": "disabled"}]
    assert widget.inserts == [("end", "hello\n", "WARNING")]
    assert widget.seen == ["end"]


def test_append_log_text_falls_back_to_info_for_unknown_tag():
    widget = FakeLogTextWidget(tags=("INFO",))
    app = FakeApp(widget)

    log_actions.append_log_text(app, "hello", "debug")

    assert widget.inserts == [("end", "hello\n", "INFO")]


def test_append_log_text_noops_when_widget_missing_or_destroyed():
    missing_app = FakeApp(None)
    destroyed_widget = FakeLogTextWidget(exists=False)

    log_actions.append_log_text(missing_app, "missing")
    log_actions.append_log_text(FakeApp(destroyed_widget), "destroyed")

    assert destroyed_widget.config_calls == []
    assert destroyed_widget.inserts == []


def test_legacy_app_log_update_method_delegates(ocr_module, monkeypatch):
    app = object.__new__(ocr_module.CheckCaptureOCRApp)
    calls = []

    monkeypatch.setattr(ocr_module, "append_log_text", lambda actual_app, message, level: calls.append((actual_app, message, level)))

    app._update_log_text_widget("hello", "ERROR")

    assert calls == [(app, "hello", "ERROR")]
