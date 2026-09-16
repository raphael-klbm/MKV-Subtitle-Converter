from backend.ocr.ocr_backend import OCRBackend
import pytesseract

class PytesseractBackend(OCRBackend):
    def __init__(self, language_path, language: str):
        super().__init__()
        self.lang_path = language_path
        self.language = language
        print(f"Using pytesseract backend")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass

    def extract_text(self, image):
        return pytesseract.image_to_string(image, lang=self.language)

    def get_languages(self):
        return pytesseract.get_languages()