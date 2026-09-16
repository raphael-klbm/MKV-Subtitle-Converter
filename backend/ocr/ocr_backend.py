import abc
from PIL import Image

class OCRBackend(abc.ABC):
    def __init__(self):
        super().__init__()

    @abc.abstractmethod
    def __enter__(self):
        return self

    @abc.abstractmethod
    def __exit__(self, exc_type, exc, tb):
        pass
    
    @abc.abstractmethod
    def extract_text(self, image: Image.Image) -> str:
        pass

    @abc.abstractmethod
    def get_languages(self):
        pass

