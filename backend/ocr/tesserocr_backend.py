from backend.ocr.ocr_backend import OCRBackend
import tesserocr

class TesserOCRBackend(OCRBackend):
    def __init__(self, language_path, language: str):
        super().__init__()
        self.lang_path = language_path
        print(f"Initializing TesserOCRBackend with language_path: '{language_path}' and language: '{language}'")
        self.ocr_api = tesserocr.PyTessBaseAPI(path=language_path, lang=language)

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
        return tesserocr.get_languages(language_path)[1]
