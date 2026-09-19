from backend.ocr.ocr_backend import OCRBackend
import tesserocr
from config import Config

class TesserOCRBackend(OCRBackend):
    def __init__(self, language_path, language: str):
        super().__init__()
        self.lang_path = language_path
        path = language_path if language_path else None
        self.ocr_api = tesserocr.PyTessBaseAPI(path=path, lang=language)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.ocr_api.End()

    def __del__(self):
        self.ocr_api.End()

    def extract_text(self, image):
        self.ocr_api.SetImage(image)
        return self.ocr_api.GetUTF8Text()

    @classmethod
    def get_languages(cls, language_path: str = '') -> list[str]:
        path = language_path if language_path else None

        if not path:
            config = Config()
            config.logger.warning("No language path provided for TesserOCRBackend.get_languages(). Using no path instead.")

        return tesserocr.get_languages(path)[1] if path else tesserocr.get_languages()[1]
