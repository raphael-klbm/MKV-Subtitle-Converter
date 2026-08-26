"""
Unit tests for backend.subextractor.SubExtractor (pure-logic methods only).

The ffprobe/ffmpeg extraction pipeline is not exercised here — only the
deterministic helpers: subtitle duration calculation and ffmpeg/mkvextract
output parsing.
"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from backend.subextractor import SubExtractor


@pytest.fixture
def extractor(tmp_path):
    """A SubExtractor instance with Config mocked out."""
    with patch("backend.subextractor.Config"):
        ext = SubExtractor(
            file_path="/fake/path.mkv",
            sub_dir=tmp_path,
        )
    return ext


class TestCalculateSubtitleDuration:
    """calculate_subtitle_duration extracts the duration from a subtitle stream dict."""

    def test_duration_from_tags(self, extractor):
        # NOTE: The source code strips milliseconds (splits on '.', takes [0]),
        # so "00:00:05.500" becomes "00:00:05" -> 5.0 seconds.
        start = datetime(1900, 1, 1)
        subtitle = {
            "tags": {
                "DURATION": "00:00:05.500",
            }
        }
        duration = extractor.calculate_subtitle_duration(start, subtitle)
        assert duration == 5.0

    def test_duration_with_comma_separator(self, extractor):
        # Some matroska files use comma as millisecond separator.
        # The code splits on '.' first (5.0 -> "00:01:30,250" -> "00:01:30,250"),
        # then on ',' (also strips): "00:01:30" -> 90.0 seconds.
        start = datetime(1900, 1, 1)
        subtitle = {
            "tags": {
                "DURATION": "00:01:30,250",
            }
        }
        duration = extractor.calculate_subtitle_duration(start, subtitle)
        assert duration == 90.0

    def test_no_tags_returns_zero(self, extractor):
        start = datetime(1900, 1, 1)
        subtitle = {}
        duration = extractor.calculate_subtitle_duration(start, subtitle)
        assert duration == 0.0

    def test_no_duration_tag_returns_zero(self, extractor):
        start = datetime(1900, 1, 1)
        subtitle = {"tags": {"LANGUAGE": "eng"}}
        duration = extractor.calculate_subtitle_duration(start, subtitle)
        assert duration == 0.0

    def test_duration_key_is_case_insensitive(self, extractor):
        start = datetime(1900, 1, 1)
        subtitle = {
            "tags": {
                "duration": "00:00:02.000",
            }
        }
        duration = extractor.calculate_subtitle_duration(start, subtitle)
        assert duration == 2.0

    def test_long_duration(self, extractor):
        start = datetime(1900, 1, 1)
        subtitle = {
            "tags": {
                "DURATION": "01:23:45.678",
            }
        }
        duration = extractor.calculate_subtitle_duration(start, subtitle)
        assert duration == 5025.0  # milliseconds stripped, so just 01:23:45

    def test_duration_without_milliseconds(self, extractor):
        start = datetime(1900, 1, 1)
        subtitle = {
            "tags": {
                "DURATION": "00:00:10",
            }
        }
        # No dot or comma, so split returns single element
        duration = extractor.calculate_subtitle_duration(start, subtitle)
        assert duration == 10.0


class TestGetSecondsProgressFromFfmpegOutput:
    """__get_seconds_progress_from_ffmpeg_output parses time= lines."""

    def test_parses_time_value(self, extractor):
        # NOTE: The source code strips milliseconds (splits on '.', takes [0]),
        # so "00:01:30.500" yields "00:01:30" -> 90.0 seconds.
        line = "frame=  123 fps=0.0 q=0.0 size=    1024kB time=00:01:30.500 bitrate=   0.0kbits/s speed=N/A"
        result = extractor._SubExtractor__get_seconds_progress_from_ffmpeg_output(line)
        assert result == 90.0

    def test_no_time_returns_minus_one(self, extractor):
        result = extractor._SubExtractor__get_seconds_progress_from_ffmpeg_output(
            "frame=  123 fps=0.0"
        )
        assert result == -1.0

    def test_na_time_returns_minus_one(self, extractor):
        line = "time=N/A bitrate=N/A"
        result = extractor._SubExtractor__get_seconds_progress_from_ffmpeg_output(line)
        assert result == -1.0

    def test_negative_time_becomes_zero(self, extractor):
        line = "time=-00:00:05.000 bitrate=0.0"
        result = extractor._SubExtractor__get_seconds_progress_from_ffmpeg_output(line)
        assert result == 0.0

    def test_zero_time(self, extractor):
        line = "time=00:00:00.000 bitrate=0.0"
        result = extractor._SubExtractor__get_seconds_progress_from_ffmpeg_output(line)
        assert result == 0.0

    def test_empty_line_returns_minus_one(self, extractor):
        result = extractor._SubExtractor__get_seconds_progress_from_ffmpeg_output("")
        assert result == -1.0

    def test_strips_whitespace(self, extractor):
        line = "  time=00:00:10.000 bitrate=0.0  "
        result = extractor._SubExtractor__get_seconds_progress_from_ffmpeg_output(line)
        assert result == 10.0

    def test_time_value_without_bitrate(self, extractor):
        line = "duration=N/A, time=00:00:05.000, "
        # The split logic splits on "time=" then " bitrate=" — if bitrate=
        # isn't present, the second split just takes the rest of the string
        result = extractor._SubExtractor__get_seconds_progress_from_ffmpeg_output(line)
        assert result == 5.0


class TestGetProgressFromMkvextractOutput:
    """__get_progress_from_mkvextract_output parses percentage lines."""

    def test_parses_percentage(self, extractor):
        line = "Progress: 42%"
        result = extractor._SubExtractor__get_progress_from_mkvextract_output(line)
        assert result == pytest.approx(42.0)

    def test_zero_percent(self, extractor):
        line = "Progress: 0%"
        result = extractor._SubExtractor__get_progress_from_mkvextract_output(line)
        assert result == 0.0

    def test_hundred_percent(self, extractor):
        line = "Progress: 100%"
        result = extractor._SubExtractor__get_progress_from_mkvextract_output(line)
        assert result == 100.0

    def test_no_colon_returns_minus_one(self, extractor):
        result = extractor._SubExtractor__get_progress_from_mkvextract_output(
            "No progress here"
        )
        assert result == -1.0

    def test_na_value_returns_minus_one(self, extractor):
        line = "Progress: N/A"
        result = extractor._SubExtractor__get_progress_from_mkvextract_output(line)
        assert result == -1.0

    @pytest.mark.xfail(reason="BUG: __get_progress_from_mkvextract_output copies ffmpeg null-time logic (sets `00:00:00.000`) instead of returning 0.0", strict=True)
    def test_negative_value_returns_zero(self, extractor):
        # When the bug is fixed, remove the xfail marker.
        # The expected correct behavior: negative progress should return 0.0.
        line = "Progress: -5%"
        result = extractor._SubExtractor__get_progress_from_mkvextract_output(line)
        assert result == 0.0

    def test_empty_line_returns_minus_one(self, extractor):
        result = extractor._SubExtractor__get_progress_from_mkvextract_output("")
        assert result == -1.0

    def test_non_percent_format(self, extractor):
        line = "Something: 42"
        # no "%" in the line, so split on "%" returns the whole string
        # after the last split
        result = extractor._SubExtractor__get_progress_from_mkvextract_output(line)
        assert result == 42.0