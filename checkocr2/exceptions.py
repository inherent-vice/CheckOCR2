"""Application-specific exception hierarchy."""


class CheckOCRError(Exception):
    """Base exception for CheckOCR2 failures."""


class SettingsError(CheckOCRError):
    """Raised when settings cannot be loaded, saved, or migrated."""


class ExcelIOError(CheckOCRError):
    """Raised when Excel input or output fails."""


class OCREngineError(CheckOCRError):
    """Raised when the OCR engine cannot initialize or process an image."""


class ScreenAutomationError(CheckOCRError):
    """Raised when screen automation or screenshot capture fails."""


class FolderOpenError(CheckOCRError):
    """Raised when an output folder cannot be opened."""
