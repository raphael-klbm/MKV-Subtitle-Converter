"""
Unit tests for backend.srtchecker.check_srt.

check_srt fixes common OCR mistakes in SRT files:
  - replaces '|' with 'I' (OCR often confuses the two)
  - warns about double empty lines and empty subtitle entries
"""
import logging

import pytest

from backend import srtchecker


@pytest.fixture
def srt_file(tmp_path):
    """Helper: write given lines to a temp .srt file and return its path."""
    def _make(lines):
        path = tmp_path / "test.srt"
        path.write_text("".join(lines), encoding="utf8")
        return str(path)
    return _make


class TestCheckSrt:
    def test_replaces_pipe_with_i(self, srt_file):
        path = srt_file(["1\n00:00:01,000 --> 00:00:02,000\nH|II\n\n"])
        srtchecker.check_srt(path, silent=True)
        content = open(path, encoding="utf8").read()
        assert "H|II" not in content
        assert "HIII" in content

    def test_pipe_replacement_counts_all_occurrences(self, srt_file):
        path = srt_file(["1\n00:00:01,000 --> 00:00:02,000\n|||\n\n"])
        srtchecker.check_srt(path, silent=True)
        content = open(path, encoding="utf8").read()
        assert "III" in content

    def test_no_pipes_leaves_file_unchanged(self, srt_file):
        original = "1\n00:00:01,000 --> 00:00:02,000\nHello World\n\n"
        path = srt_file([original])
        srtchecker.check_srt(path, silent=True)
        assert open(path, encoding="utf8").read() == original

    def test_warns_on_double_empty_lines(self, srt_file, caplog):
        # lines 3 and 4 are both empty -> double empty line warning
        path = srt_file([
            "1\n",
            "00:00:01,000 --> 00:00:02,000\n",
            "Hello\n",
            "\n",
            "\n",
            "2\n",
            "00:00:03,000 --> 00:00:04,000\n",
            "World\n",
            "\n",
        ])
        with caplog.at_level(logging.WARNING):
            srtchecker.check_srt(path, silent=False)
        assert "Two empty lines" in caplog.text

    @pytest.mark.xfail(reason="BUG: srtchecker uses `index + 2` instead of `index + 1` (off-by-one), so the missing-text warning is never emitted", strict=True)
    def test_warns_on_missing_subtitle_text(self, srt_file, caplog):
        # When the bug is fixed, remove the xfail marker.
        # The expected correct behavior:
        path = srt_file([
            "1\n",
            "00:00:01,000 --> 00:00:02,000\n",
            "\n",
            "2\n",
            "00:00:03,000 --> 00:00:04,000\n",
            "World\n",
            "\n",
        ])
        with caplog.at_level(logging.WARNING):
            srtchecker.check_srt(path, silent=False)
        assert "No text for subtitle #1" in caplog.text

    def test_silent_mode_suppresses_all_logging(self, srt_file, caplog):
        path = srt_file([
            "1\n",
            "00:00:01,000 --> 00:00:02,000\n",
            "H|I\n",
            "\n",
            "\n",
        ])
        with caplog.at_level(logging.DEBUG):
            srtchecker.check_srt(path, silent=True)
        assert caplog.text == ""

    def test_empty_file_does_not_crash(self, srt_file):
        path = srt_file([""])
        srtchecker.check_srt(path, silent=True)  # should not raise
        assert open(path, encoding="utf8").read() == ""

    def test_multiple_pipe_replacements(self, srt_file):
        # The pipe '|' is replaced with 'I', so 'W|th' becomes 'WIth'
        path = srt_file([
            "1\n",
            "00:00:01,000 --> 00:00:02,000\n",
            "H|I\n",
            "\n",
            "2\n",
            "00:00:03,000 --> 00:00:04,000\n",
            "W|th\n",
            "\n",
        ])
        srtchecker.check_srt(path, silent=True)
        content = open(path, encoding="utf8").read()
        assert "H|I" not in content
        assert "HII" in content
        assert "W|th" not in content
        assert "WIth" in content  # | -> I, so W|th becomes WIth

    @pytest.mark.xfail(reason="BUG: srtchecker iterates `range(len(lines) - 1)` so the last line's pipes are never replaced", strict=True)
    def test_pipe_on_last_line_is_replaced(self, srt_file):
        # When the bug is fixed, remove the xfail marker and rename to
        # test_pipe_on_last_line_is_replaced. The expected correct behavior:
        path = srt_file(["1\n00:00:01,000 --> 00:00:02,000\nH|I\n"])
        srtchecker.check_srt(path, silent=True)
        content = open(path, encoding="utf8").read()
        assert "H|I" not in content
        assert "HII" in content