"""
Unit tests for backend.helper (language code conversion and diff parsing).
"""
import logging

import pytest

from backend import helper


class TestConvertLanguage:
    """convert_language: ISO 639-2/B -> ISO 639-2/T mapping used for OCR."""

    @pytest.mark.parametrize("b_code, t_code", [
        ("alb", "sqi"),
        ("arm", "hye"),
        ("baq", "eus"),
        ("bur", "mya"),
        ("chi", "zho"),
        ("cze", "ces"),
        ("dut", "nld"),
        ("fre", "fra"),
        ("geo", "kat"),
        ("ger", "deu"),
        ("gre", "ell"),
        ("ice", "isl"),
        ("mac", "mkd"),
        ("may", "msa"),
        ("mao", "mri"),
        ("per", "fas"),
        ("rum", "ron"),
        ("slo", "slk"),
        ("tib", "bod"),
        ("wel", "cym"),
    ])
    def test_b_to_t_conversion(self, b_code, t_code):
        assert helper.convert_language(b_code) == t_code

    def test_already_t_code_is_unchanged(self):
        # T codes (and any code not in the B->T table) pass through as-is
        assert helper.convert_language("sqi") == "sqi"
        assert helper.convert_language("eng") == "eng"
        assert helper.convert_language("deu") == "deu"

    def test_unknown_code_is_unchanged(self):
        assert helper.convert_language("xyz") == "xyz"
        assert helper.convert_language("gde") == "gde"  # not in mapping


class TestDiffLangsFromText:
    """diff_langs_from_text: parses 'old->new' lines into a dict."""

    def test_empty_string_returns_empty_dict(self):
        assert helper.diff_langs_from_text("") == {}

    def test_single_mapping(self):
        # 'ger' is a B code, so it is converted to its T code 'deu'
        result = helper.diff_langs_from_text("ger->eng")
        assert result == {"deu": "eng"}

    def test_whitespace_is_stripped(self):
        result = helper.diff_langs_from_text("  ger  ->  eng  ")
        assert result == {"deu": "eng"}

    def test_multiple_lines(self):
        text = "ger->eng\nfre->ita\nchi->jpn"
        result = helper.diff_langs_from_text(text)
        assert result == {"deu": "eng", "fra": "ita", "zho": "jpn"}

    def test_blank_lines_are_skipped(self):
        text = "ger->eng\n\n\nfre->ita\n"
        result = helper.diff_langs_from_text(text)
        assert result == {"deu": "eng", "fra": "ita"}

    def test_b_codes_are_converted_on_both_sides(self, caplog):
        # 'ger' (B) -> 'deu' (T), 'fre' (B) -> 'fra' (T)
        with caplog.at_level(logging.INFO):
            result = helper.diff_langs_from_text("ger->fre")
        assert result == {"deu": "fra"}
        assert 'Changed "ger" to "deu"' in caplog.text
        assert 'Changed "fre" to "fra"' in caplog.text

    def test_invalid_line_without_arrow_is_skipped(self, caplog):
        with caplog.at_level(logging.ERROR):
            result = helper.diff_langs_from_text("ger eng")
        assert result == {}
        assert "Invalid input" in caplog.text

    def test_invalid_line_with_multiple_arrows_is_skipped(self, caplog):
        with caplog.at_level(logging.ERROR):
            result = helper.diff_langs_from_text("ger->eng->ita")
        assert result == {}
        assert "Invalid input" in caplog.text

    def test_later_mapping_wins_for_same_source(self):
        # 'ger' (B) -> 'deu', and since 'fre' is also B->'fra', both sides
        # of the second mapping get converted.
        result = helper.diff_langs_from_text("ger->eng\ngde->fre")
        # 'gde' is not a known B code, stays as-is; 'fre' -> 'fra'
        assert result["gde"] == "fra"
        assert result["deu"] == "eng"