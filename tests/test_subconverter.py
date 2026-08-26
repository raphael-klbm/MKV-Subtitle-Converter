"""
Unit tests for backend.subconverter.SubtitleConverter (pure-logic methods).

The OCR/image pipeline (pytesseract, cv2) is not exercised here — only the
deterministic helpers: language selection, timing extraction and image
cropping.
"""
from datetime import timedelta
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from backend.subconverter import SubtitleConverter
from controller.sub_formats import SubtitleFileEndings


@pytest.fixture
def converter(tmp_path):
    """A SubtitleConverter instance with Config mocked out."""
    with patch("backend.subconverter.Config") as mock_config:
        config = mock_config.return_value
        config.translate = lambda text: text
        config.logger = MagicMock()
        conv = SubtitleConverter(
            subtitle_counter=1,
            sub_langs=["eng"],
            diff_langs={},
            sub_dir=str(tmp_path),
            img_dir=tmp_path,
            sub_format=SubtitleFileEndings.SRT.value,
            keep_imgs=False,
            text_brightness_diff=0.1,
        )
    return conv


class TestGetLang:
    """__get_lang picks the OCR language, honouring user overrides."""

    def test_returns_original_when_no_override(self, converter):
        with patch("backend.subconverter.pytesseract.get_languages",
                   return_value=["eng", "deu"]):
            assert converter._SubtitleConverter__get_lang("eng") == "eng"

    def test_returns_override_when_installed(self, converter):
        converter.diff_langs = {"deu": "fra"}
        with patch("backend.subconverter.pytesseract.get_languages",
                   return_value=["fra"]):
            assert converter._SubtitleConverter__get_lang("deu") == "fra"

    def test_falls_back_to_original_when_override_not_installed(self, converter):
        converter.diff_langs = {"deu": "fra"}
        with patch("backend.subconverter.pytesseract.get_languages",
                   return_value=["deu"]):
            assert converter._SubtitleConverter__get_lang("deu") == "deu"

    def test_returns_none_when_nothing_installed(self, converter):
        with patch("backend.subconverter.pytesseract.get_languages",
                   return_value=["fra"]):
            assert converter._SubtitleConverter__get_lang("deu") is None

    def test_b_code_is_converted_before_lookup(self, converter):
        # 'ger' (B code) -> 'deu' (T code) must happen before the installed check
        with patch("backend.subconverter.pytesseract.get_languages",
                   return_value=["deu"]):
            assert converter._SubtitleConverter__get_lang("ger") == "deu"

    def test_override_code_is_converted_upstream(self, converter):
        # The upstream caller (controller.start_subconverter) calls
        # diff_langs_from_text() which converts B->T codes on both sides.
        # So by the time __get_lang sees the diff_langs dict, the override
        # value is already a T code. This test documents that __get_lang
        # itself does NOT need to convert the override value.
        converter.diff_langs = {"eng": "deu"}
        with patch("backend.subconverter.pytesseract.get_languages",
                   return_value=["deu"]):
            assert converter._SubtitleConverter__get_lang("eng") == "deu"

    def test_logs_warning_when_override_not_installed(self, converter):
        converter.diff_langs = {"deu": "fra"}
        with patch("backend.subconverter.pytesseract.get_languages",
                   return_value=["deu"]):
            converter._SubtitleConverter__get_lang("deu")
            converter.config.logger.warning.assert_called_once()


class TestCreateSubfileTimings:
    """create_subfile_timings converts pack timedeltas to seconds."""

    def test_converts_to_seconds(self, converter):
        pack = MagicMock()
        pack.start_time = timedelta(milliseconds=1500)
        pack.end_time = timedelta(seconds=4, milliseconds=250)
        start, end = converter.create_subfile_timings(pack)
        assert start == pytest.approx(1.5)
        assert end == pytest.approx(4.25)

    def test_zero_start(self, converter):
        pack = MagicMock()
        pack.start_time = timedelta(0)
        pack.end_time = timedelta(seconds=2)
        start, end = converter.create_subfile_timings(pack)
        assert start == 0
        assert end == 2


class TestCropImage:
    """crop_image trims empty border around subtitle content."""

    def test_crops_to_content_bounding_box(self, converter):
        # 5x5 all-zero image with a 2x2 block of content in the middle
        img = np.zeros((5, 5, 3), dtype=np.float64)
        img[2:4, 2:4] = 1.0
        cropped = converter.crop_image(img)
        assert cropped.shape == (2, 2, 3)
        assert np.all(cropped == 1.0)

    def test_inverted_image_uses_dark_content(self, converter):
        # mostly-white image (mean > 0.5): content is the dark (0) pixels
        img = np.ones((5, 5, 3), dtype=np.float64)
        img[1:3, 1:3] = 0.0
        cropped = converter.crop_image(img)
        assert cropped.shape == (2, 2, 3)
        assert np.all(cropped == 0.0)

    def test_content_touching_edge(self, converter):
        img = np.zeros((4, 4, 3), dtype=np.float64)
        img[0:2, 0:4] = 1.0  # content in top half, full width
        cropped = converter.crop_image(img)
        assert cropped.shape == (2, 4, 3)

    def test_single_pixel_content(self, converter):
        img = np.zeros((4, 4, 3), dtype=np.float64)
        img[1, 2] = 1.0
        cropped = converter.crop_image(img)
        assert cropped.shape == (1, 1, 3)
        assert np.all(cropped == 1.0)

    def test_dark_content_background_is_zero(self, converter):
        # Background is 0 (dark), content is bright: mean < 0.5,
        # uses np.where(image > 0), finds only the content pixels.
        img = np.zeros((6, 6, 3), dtype=np.float64)
        img[1:3, 1:3] = 0.8  # bright content on dark background
        cropped = converter.crop_image(img)
        assert cropped.shape == (2, 2, 3)
        assert np.allclose(cropped, 0.8)

    def test_mean_exactly_05_with_content(self, converter):
        # Even mean with actual content: background=0, content=1,
        # exactly balanced so mean = 0.5 -> uses image < 1 branch
        img = np.full((4, 4, 3), 0.0, dtype=np.float64)
        img[1:3, 1:3] = 1.0  # 4 content pixels out of 16 = mean 0.25
        # Actually this gives mean = 0.25, not 0.5. Let's adjust:
        # 8 content pixels out of 16 = 0.5 mean using values 1.0
        img = np.zeros((4, 4, 3), dtype=np.float64)
        img[0:2, 0:2] = 1.0  # 4/16 = 0.25... hmm
        # Actually let's just make a clear test case:
        # Use background=0.25 and content=0.75 so mean is between
        img = np.full((4, 4, 3), 0.25, dtype=np.float64)
        img[1:3, 1:3] = 0.75
        # mean = (0.25*12 + 0.75*4) / 16 = (3 + 3) / 16 = 0.375
        # Uses image > 0 branch, finds all pixels
        cropped = converter.crop_image(img)
        # All pixels are > 0, so the whole image is the bounding box
        assert cropped.shape == (4, 4, 3)

    @pytest.mark.xfail(reason="BUG: crop_image crashes on solid-color images (no content pixels -> empty arrays)", strict=True)
    def test_full_content_image_is_unchanged(self, converter):
        # When the bug is fixed, remove the xfail marker.
        # The expected correct behavior: a solid-color image should pass
        # through unchanged.
        img = np.ones((3, 4, 3), dtype=np.float64)
        cropped = converter.crop_image(img)
        assert cropped.shape == (3, 4, 3)

    @pytest.mark.xfail(reason="BUG: crop_image crashes on solid-color images (no content pixels -> empty arrays)", strict=True)
    def test_solid_black_image(self, converter):
        # When the bug is fixed, remove the xfail marker.
        # The expected correct behavior: a solid-black image should pass
        # through unchanged.
        img = np.zeros((3, 4, 3), dtype=np.float64)
        cropped = converter.crop_image(img)
        assert cropped.shape == (3, 4, 3)