"""
Unit tests for controller.sub_formats (subtitle format/ending enums).
"""
import pytest

from controller.sub_formats import SubtitleFileEndings, SubtitleFormats


class TestSubtitleFileEndings:
    def test_values(self):
        assert SubtitleFileEndings.SRT.value == "srt"
        assert SubtitleFileEndings.ASS.value == "ass"
        assert SubtitleFileEndings.SSA.value == "ssa"
        assert SubtitleFileEndings.SUB.value == "sub"
        assert SubtitleFileEndings.JSON.value == "json"
        assert SubtitleFileEndings.MPL2.value == "mpl"
        assert SubtitleFileEndings.TMP.value == "tmp"
        assert SubtitleFileEndings.VTT.value == "vtt"

    def test_get_format_by_value(self):
        assert SubtitleFileEndings.get_format("srt") is SubtitleFileEndings.SRT
        assert SubtitleFileEndings.get_format("ass") is SubtitleFileEndings.ASS

    def test_get_format_is_case_insensitive(self):
        assert SubtitleFileEndings.get_format("SRT") is SubtitleFileEndings.SRT
        assert SubtitleFileEndings.get_format("Ass") is SubtitleFileEndings.ASS

    def test_get_format_by_name_substring(self):
        assert SubtitleFileEndings.get_format("sub") is SubtitleFileEndings.SUB
        assert SubtitleFileEndings.get_format("json") is SubtitleFileEndings.JSON

    def test_get_format_by_value_substring(self):
        # 'srt' matches via value substring
        assert SubtitleFileEndings.get_format("srt") is SubtitleFileEndings.SRT

    def test_get_format_unknown_returns_value_error(self):
        with pytest.raises(ValueError):
            SubtitleFileEndings.get_format("xyz")

    def test_get_format_full_filename(self):
        # 'subtitle.srt' contains 'srt' as a substring of its value
        assert SubtitleFileEndings.get_format("subtitle.srt") is SubtitleFileEndings.SRT

    def test_get_format_handle_nonexistent_name(self):
        with pytest.raises(ValueError):
            SubtitleFileEndings.get_format("nonexistent")

    def test_get_format_wrong_type_as_arg(self):
        # The function expects a string; passing an int shouldn't crash
        # (it will call .lower() on the int, which raises AttributeError)
        with pytest.raises(AttributeError):
            SubtitleFileEndings.get_format(123)  # type: ignore[arg-type]


class TestSubtitleFormats:
    def test_values_are_display_names(self):
        assert SubtitleFormats.SRT.value == "SubRip Text (.srt)"
        assert SubtitleFormats.ASS.value == "Advanced SubStation Alpha (.ass)"
        assert SubtitleFormats.SSA.value == "SubStation Alpha (.ssa)"
        assert SubtitleFormats.VTT.value == "VTT (.vtt)"

    def test_get_name_by_name(self):
        assert SubtitleFormats.get_name("srt") is SubtitleFormats.SRT
        assert SubtitleFormats.get_name("ass") is SubtitleFormats.ASS

    def test_get_name_by_value_substring(self):
        assert SubtitleFormats.get_name("subrip") is SubtitleFormats.SRT

    def test_get_name_case_insensitive(self):
        assert SubtitleFormats.get_name("SRT") is SubtitleFormats.SRT

    def test_get_name_unknown_returns_value_error(self):
        result = SubtitleFormats.get_name("xyz")
        assert isinstance(result, ValueError)

    def test_get_file_ending_mapping(self):
        assert SubtitleFormats.SRT.get_file_ending() is SubtitleFileEndings.SRT
        assert SubtitleFormats.ASS.get_file_ending() is SubtitleFileEndings.ASS
        assert SubtitleFormats.SSA.get_file_ending() is SubtitleFileEndings.SSA
        assert SubtitleFormats.VTT.get_file_ending() is SubtitleFileEndings.VTT

    def test_writable_formats_are_pysubs2_supported(self):
        # Only formats pysubs2 can write are exposed as SubtitleFormats
        names = {f.name for f in SubtitleFormats}
        assert names == {"SRT", "ASS", "SSA", "VTT"}