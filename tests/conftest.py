"""
Shared pytest fixtures and import guards for the MKV Subtitle Converter test suite.

The real ``config.Config`` is a singleton that reads/writes config files under the
user's data directory and installs gettext translations, so it is replaced by
a lightweight mock *before* any module under test is imported.

Heavy/optional dependencies (pytesseract, cv2, pysubs2, PIL) are stubbed out
so the pure-logic parts can be tested without a full application environment.
"""
import sys
import types
import logging
from pathlib import Path

# Make the project root importable (config.py, backend/, controller/ live there)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Mock config.Config BEFORE anything imports it
# ---------------------------------------------------------------------------
class _MockConfig:
    """Minimal stand-in for config.Config used during tests."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.logger = logging.getLogger("test")  # type: ignore[reportAttributeAccessIssue]
            cls._instance.translation = _MockTranslation()  # type: ignore[reportAttributeAccessIssue]
        return cls._instance

    def translate(self, text: str) -> str:
        return text

    def get_value(self, setting):
        return "en_US"

    def get_datadir(self) -> Path:
        return Path("/tmp/mkv-test-datadir")

    def get_resource_path(self, relative_path: str) -> str:
        return str(PROJECT_ROOT / relative_path)


class _MockTranslation:
    def gettext(self, text: str) -> str:
        return text

    def ngettext(self, singular: str, plural: str, n: int) -> str:
        return singular if n == 1 else plural


_config_module = types.ModuleType("config")
_config_module.Config = _MockConfig  # type: ignore[reportAttributeAccessIssue]
sys.modules["config"] = _config_module

# ---------------------------------------------------------------------------
# Stub heavy dependencies of backend.subconverter (only if missing)
# ---------------------------------------------------------------------------
try:
    import pytesseract  # type: ignore[reportMissingImports]
except ImportError:
    _pyt = types.ModuleType("pytesseract")
    _pyt.get_languages = lambda: ["eng"]  # type: ignore[reportAttributeAccessIssue]
    _pyt.image_to_string = lambda *a, **k: ""  # type: ignore[reportAttributeAccessIssue]
    sys.modules["pytesseract"] = _pyt

try:
    import cv2  # type: ignore[reportMissingImports]
except ImportError:
    _cv2 = types.ModuleType("cv2")
    _cv2.COLOR_BGR2HSV = 4  # type: ignore[reportAttributeAccessIssue]

    def _fake_cvt_color(*a, **k):
        return a[0][:, :, :3] if hasattr(a[0], "shape") else None

    _cv2.cvtColor = _fake_cvt_color  # type: ignore[reportAttributeAccessIssue]

    def _fake_inRange(img, low, high):
        import numpy  # type: ignore[reportMissingImports]
        return numpy.zeros(img.shape[:2], dtype=numpy.uint8)

    _cv2.inRange = _fake_inRange  # type: ignore[reportAttributeAccessIssue]
    sys.modules["cv2"] = _cv2

try:
    import pysubs2  # type: ignore[reportMissingImports]
except ImportError:
    _pysubs2 = types.ModuleType("pysubs2")
    _pysubs2.load = lambda *a, **k: None  # type: ignore[reportAttributeAccessIssue]
    sys.modules["pysubs2"] = _pysubs2

try:
    from PIL import Image  # type: ignore[reportMissingImports]
except ImportError:
    _pil = types.ModuleType("PIL")
    _pil_image = types.ModuleType("PIL.Image")
    _pil_image.fromarray = lambda *a, **k: None  # type: ignore[reportAttributeAccessIssue]
    _pil_image.NEAREST = 0  # type: ignore[reportAttributeAccessIssue]
    _pil.Image = _pil_image  # type: ignore[reportAttributeAccessIssue]
    sys.modules["PIL"] = _pil
    sys.modules["PIL.Image"] = _pil_image