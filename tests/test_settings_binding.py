from types import SimpleNamespace

from checkocr2.ui.settings_binding import (
    apply_ui_settings,
    build_current_settings,
    collect_ui_settings,
    save_advanced_settings,
)


class FakeVar:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeSettingsManager:
    def __init__(self):
        self.data = {"advanced": {"existing": "keep"}}
        self.advanced_values = {}
        self.current_settings = None
        self.saved = False
        self.save_error = None

    def save_current_settings(self, settings):
        self.current_settings = settings

    def set_advanced(self, key, value):
        self.advanced_values[key] = value

    def save_settings(self):
        if self.save_error:
            raise self.save_error
        self.saved = True


class FakeLogger:
    def __init__(self):
        self.infos = []
        self.errors = []

    def info(self, message):
        self.infos.append(message)

    def error(self, message):
        self.errors.append(message)


def make_app():
    return SimpleNamespace(
        click_x=FakeVar(340),
        click_y=FakeVar(165),
        allarea_x1=FakeVar(15),
        allarea_y1=FakeVar(200),
        allarea_x2=FakeVar(1845),
        allarea_y2=FakeVar(870),
        datearea_x1=FakeVar(826),
        datearea_y1=FakeVar(88),
        datearea_x2=FakeVar(1064),
        datearea_y2=FakeVar(127),
        ratearea_x1=FakeVar(1069),
        ratearea_y1=FakeVar(89),
        ratearea_x2=FakeVar(1326),
        ratearea_y2=FakeVar(126),
        paste_delay=FakeVar(0.5),
        loading_delay=FakeVar(2.5),
        save_detail_images=FakeVar(True),
        skip_kbp_var=FakeVar(True),
        rate_decimal_places=FakeVar(3),
        enable_upscaling=FakeVar(True),
        upscaling_factor=FakeVar(2.0),
        upscaling_method=FakeVar("LANCZOS"),
        input_excel_path=FakeVar("input.xlsx"),
        output_folder_path=FakeVar("out"),
        settings_manager=FakeSettingsManager(),
        logger=FakeLogger(),
    )


def make_legacy_app(ocr_module):
    app = object.__new__(ocr_module.CheckCaptureOCRApp)
    app.__dict__.update(make_app().__dict__)
    return app


def test_collect_ui_settings_preserves_legacy_payload_shape():
    app = make_app()
    app.click_x.set(11)
    app.ratearea_x2.set(44)
    app.save_detail_images.set(False)
    app.skip_kbp_var.set(False)
    app.upscaling_factor.set(3.0)

    assert collect_ui_settings(app) == {
        "click_point": (11, 165),
        "all_area": (15, 200, 1845, 870),
        "date_area": (826, 88, 1064, 127),
        "rate_area": (1069, 89, 44, 126),
        "delays": {"paste": 0.5, "loading": 2.5},
        "save_detail_images": False,
        "skip_kbp_code": False,
        "rate_decimal_places": 3,
        "upscaling": {"enabled": True, "factor": 3.0, "method": "LANCZOS"},
    }


def test_build_current_settings_includes_input_and_output_paths():
    app = make_app()

    current = build_current_settings(app)

    assert current["input_excel_path"] == "input.xlsx"
    assert current["output_folder_path"] == "out"
    assert current["click_point"] == (340, 165)


def test_apply_ui_settings_writes_vars_and_advanced_settings():
    app = make_app()

    apply_ui_settings(
        app,
        {
            "click_point": (1, 2),
            "all_area": (3, 4, 5, 6),
            "date_area": (7, 8, 9, 10),
            "rate_area": (11, 12, 13, 14),
            "delays": {"paste": 1.25, "loading": 4.5},
            "save_detail_images": False,
            "skip_kbp_code": False,
            "rate_decimal_places": 4,
            "upscaling": {"enabled": False, "factor": 1.5, "method": "BICUBIC"},
            "advanced": {"ui_theme": "modern_dark"},
        },
    )

    assert (app.click_x.get(), app.click_y.get()) == (1, 2)
    assert (app.allarea_x1.get(), app.allarea_y1.get(), app.allarea_x2.get(), app.allarea_y2.get()) == (3, 4, 5, 6)
    assert (app.datearea_x1.get(), app.datearea_y1.get(), app.datearea_x2.get(), app.datearea_y2.get()) == (
        7,
        8,
        9,
        10,
    )
    assert (app.ratearea_x1.get(), app.ratearea_y1.get(), app.ratearea_x2.get(), app.ratearea_y2.get()) == (
        11,
        12,
        13,
        14,
    )
    assert app.paste_delay.get() == 1.25
    assert app.loading_delay.get() == 4.5
    assert app.save_detail_images.get() is False
    assert app.skip_kbp_var.get() is False
    assert app.rate_decimal_places.get() == 4
    assert app.enable_upscaling.get() is False
    assert app.upscaling_factor.get() == 1.5
    assert app.upscaling_method.get() == "BICUBIC"
    assert app.settings_manager.data["advanced"] == {"existing": "keep", "ui_theme": "modern_dark"}


def test_apply_ui_settings_uses_existing_legacy_defaults_for_partial_payloads():
    app = make_app()
    app.paste_delay.set(9.9)
    app.loading_delay.set(9.9)
    app.save_detail_images.set(False)
    app.skip_kbp_var.set(False)
    app.rate_decimal_places.set(9)
    app.enable_upscaling.set(False)
    app.upscaling_factor.set(9.9)
    app.upscaling_method.set("NEAREST")

    apply_ui_settings(app, {"click_point": (1, 2)})

    assert (app.click_x.get(), app.click_y.get()) == (1, 2)
    assert (app.allarea_x1.get(), app.allarea_y1.get(), app.allarea_x2.get(), app.allarea_y2.get()) == (
        15,
        200,
        1845,
        870,
    )
    assert app.paste_delay.get() == 0.5
    assert app.loading_delay.get() == 2.5
    assert app.save_detail_images.get() is True
    assert app.skip_kbp_var.get() is True
    assert app.rate_decimal_places.get() == 3
    assert app.enable_upscaling.get() is True
    assert app.upscaling_factor.get() == 2.0
    assert app.upscaling_method.get() == "LANCZOS"


def test_save_advanced_settings_persists_expected_keys_and_logs_success():
    app = make_app()
    app.skip_kbp_var.set(False)
    app.rate_decimal_places.set(4)
    app.enable_upscaling.set(False)
    app.upscaling_factor.set(1.5)
    app.upscaling_method.set("BICUBIC")

    save_advanced_settings(app)

    assert app.settings_manager.advanced_values == {
        "skip_kbp_code": False,
        "rate_decimal_places": 4,
        "upscaling_enabled": False,
        "upscaling_factor": 1.5,
        "upscaling_method": "BICUBIC",
    }
    assert app.settings_manager.saved is True
    assert app.logger.infos == ["고급 설정이 저장되었습니다."]


def test_save_advanced_settings_logs_save_errors_without_raising():
    app = make_app()
    app.settings_manager.save_error = OSError("locked")

    save_advanced_settings(app)

    assert app.logger.errors == ["고급 설정 저장 실패: locked"]


def test_legacy_app_settings_methods_delegate_to_settings_binding(ocr_module):
    app = make_legacy_app(ocr_module)

    assert app.get_current_ui_settings()["click_point"] == (340, 165)

    app.apply_settings_to_ui(
        {
            "click_point": (1, 2),
            "delays": {"paste": 1.0, "loading": 2.0},
            "save_detail_images": False,
            "skip_kbp_code": False,
            "upscaling": {"enabled": False, "factor": 1.5, "method": "BICUBIC"},
        }
    )
    assert app.get_current_ui_settings()["click_point"] == (1, 2)
    assert app.get_current_ui_settings()["delays"] == {"paste": 1.0, "loading": 2.0}

    app.save_advanced_ui_to_settings()
    assert app.settings_manager.advanced_values["skip_kbp_code"] is False
    assert app.settings_manager.advanced_values["rate_decimal_places"] == 3

    app.quick_save_settings()
    assert app.settings_manager.current_settings["input_excel_path"] == "input.xlsx"
    assert app.settings_manager.current_settings["output_folder_path"] == "out"
    assert app.settings_manager.current_settings["upscaling"]["method"] == "BICUBIC"
    assert app.logger.infos[-1] == "현재 설정이 저장되었습니다."
