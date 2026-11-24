from backend.ocr.ocr_backend import OCRBackend
import io
from openai import OpenAI
import base64
from config import Config

class LLMBackend(OCRBackend):
    def __init__(self, language_path, language: str):
        super().__init__()
        self.lang_path = language_path
        self.language = language
        self.config = Config()

        self.client = OpenAI(
            base_url = self.config.get_value(self.config.Settings.OPENAI_API_BASE_URL),
            api_key = self.config.get_value(self.config.Settings.OPENAI_API_KEY),
        )

        self.prompt = """Transcribe all text in the image exactly as it appears.
                        Rules:
                        - Keep the original language. Do not translate, correct or summarize.
                        - Preserve the line breaks exactly: every visual line of text in the image
                        is one line in your output.
                        - Wrap italic text in <i>...</i>. Wrap bold text in <b>...</b>.
                        - Keep punctuation, dashes (e.g. dialogue dashes) and ellipses as they are.
                        - Output only the transcribed text, without comments, code fences or quotes."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.client.close()

    def extract_text(self, image):
        buf = io.BytesIO()
        image.save(buf, format="WEBP")
        b64 = base64.b64encode(buf.getvalue()).decode()

        response = self.client.chat.completions.create(
            model=self.config.get_value(self.config.Settings.OPENAI_MODEL),
            temperature=0,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": self.prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/{"WEBP".lower()};base64,{b64}"}},
                ],
            }],
        )
        return response.choices[0].message.content

    @classmethod
    def get_languages(cls, language_path: str = '') -> list[str]:
        return []
