from backend.ocr.ocr_backend import OCRBackend
import tesserocr

class TesserOCRBackend(OCRBackend):
    def __init__(self, language_path, lang: str):
        super().__init__()
        self.lang_path = language_path
        self.ocr_api = tesserocr.PyTessBaseAPI(path=language_path, lang=lang)

    def __exit__(self, exc_type, exc, tb):
        self.ocr_api.End()

    def extract_text(self, image):
        self.ocr_api.SetImage(image)
        return self.ocr_api.GetUTF8Text()

    def get_languages(self):
        return tesserocr.get_languages(self.lang_path)[1]