"""
Unit tests for backend.vob.utils (MPEG-2 / VobSub low-level helpers).
"""
from datetime import timedelta

import pytest

from backend.vob.utils import (
    Mpeg2Header,
    Rectangle,
    custom_timedelta,
    get_endian,
    get_endian_word,
    is_mpeg2_pack_header,
    is_private_stream1,
    is_private_stream2,
    is_subtitle_pack,
)


class TestGetEndianWord:
    def test_reads_big_endian_word(self):
        buf = bytearray([0x12, 0x34, 0x56])
        assert get_endian_word(buf, 0) == 0x1234
        assert get_endian_word(buf, 1) == 0x3456

    def test_returns_zero_when_not_enough_bytes(self):
        buf = bytearray([0xAB])
        assert get_endian_word(buf, 0) == 0
        assert get_endian_word(buf, 1) == 0

    def test_empty_buffer_returns_zero(self):
        assert get_endian_word(bytearray(), 0) == 0

    def test_exact_two_bytes(self):
        buf = bytearray([0xFF, 0x00])
        assert get_endian_word(buf, 0) == 0xFF00


class TestGetEndian:
    def test_reads_multi_byte_value(self):
        buf = bytearray([0x01, 0x02, 0x03, 0x04])
        assert get_endian(buf, 0, 4) == 0x01020304
        assert get_endian(buf, 1, 3) == 0x020304

    def test_single_byte(self):
        buf = bytearray([0x7F])
        assert get_endian(buf, 0, 1) == 0x7F

    def test_returns_zero_for_empty_range(self):
        buf = bytearray([0xAB, 0xCD])
        # count=0 means no iteration, result stays 0
        assert get_endian(buf, 0, 0) == 0

    def test_index_out_of_range(self):
        buf = bytearray([0x01, 0x02])
        # accessing beyond buffer will raise IndexError
        with pytest.raises(IndexError):
            get_endian(buf, 2, 1)


class TestCustomTimedelta:
    def test_total_milliseconds(self):
        td = custom_timedelta(milliseconds=1234)
        assert td.total_milliseconds() == 1234

    def test_hours_minutes_seconds_milliseconds(self):
        # 1h 2m 3s 456ms
        td = custom_timedelta(hours=1, minutes=2, seconds=3, milliseconds=456)
        assert td.hours() == 1
        assert td.minutes() == 2
        assert td.seconds() == 3
        assert td.milliseconds() == 456

    def test_get_str_format(self):
        td = custom_timedelta(hours=1, minutes=20, seconds=52, milliseconds=412)
        assert td.get_str_format() == "01:20:52,412"

    def test_get_str_format_zero_padded(self):
        td = custom_timedelta(milliseconds=42)
        assert td.get_str_format() == "00:00:00,042"

    def test_plain_timedelta_methods_return_custom_timedelta(self, monkeypatch):
        # The metaclass wraps timedelta methods so they return custom_timedelta
        td = custom_timedelta(seconds=90)
        result = td + timedelta(seconds=1)
        assert isinstance(result, custom_timedelta)
        assert result.total_milliseconds() == 91000

    def test_negative_timedelta(self):
        # A negative timedelta produces unexpected formatting because
        # Python's // and % operators behave differently with negatives.
        # -5 seconds // 3600 = -1, (-5) % 3600 = 3595, so hours=-1,
        # minutes=59, seconds=55.
        td = custom_timedelta(seconds=-5)
        assert td.total_milliseconds() == -5000
        assert td.get_str_format() == "-1:59:55,000"

    def test_large_values(self):
        td = custom_timedelta(hours=99, minutes=59, seconds=59, milliseconds=999)
        assert td.hours() == 99
        assert td.minutes() == 59
        assert td.seconds() == 59
        assert td.milliseconds() == 999
        assert td.get_str_format() == "99:59:59,999"


class TestMpeg2Header:
    def test_parses_header_fields(self):
        # minimal 14-byte MPEG-2 pack header
        buf = bytearray(14)
        buf[0:4] = bytes([0x00, 0x00, 0x01, 0xBA])
        buf[3] = 0x44  # pack_identifier
        buf[10:13] = bytes([0x00, 0x00, 0x08])  # mux rate field
        buf[13] = 0b10100101  # stuffing length = 5
        header = Mpeg2Header(bytes(buf))
        assert header.start_code == 0x000001
        assert header.pack_identifier == 0x44
        assert header.pack_stuffing_length == 5

    def test_length_constant(self):
        assert Mpeg2Header.LENGTH == 14

    def test_program_mux_rate(self):
        buf = bytearray(14)
        buf[10:13] = bytes([0x01, 0xE8, 0x48])  # (0x01E848 >> 2)
        header = Mpeg2Header(bytes(buf))
        expected = 0x01E848 >> 2
        assert header.program_mux_rate == expected


class TestRectangle:
    def test_defaults_are_zero(self):
        r = Rectangle()
        assert (r.x, r.y, r.width, r.height) == (0, 0, 0, 0)

    def test_values(self):
        r = Rectangle(x=1, y=2, width=3, height=4)
        assert (r.x, r.y, r.width, r.height) == (1, 2, 3, 4)

    def test_negative_values(self):
        r = Rectangle(x=-1, y=-2, width=3, height=4)
        assert (r.x, r.y) == (-1, -2)


class TestIsMpeg2PackHeader:
    def test_valid_header(self):
        buf = bytearray([0x00, 0x00, 0x01, 0xBA, 0x00])
        assert is_mpeg2_pack_header(buf) is True

    def test_wrong_start_code(self):
        buf = bytearray([0x00, 0x00, 0x02, 0xBA, 0x00])
        assert is_mpeg2_pack_header(buf) is False

    def test_wrong_pack_identifier(self):
        buf = bytearray([0x00, 0x00, 0x01, 0xBD, 0x00])
        assert is_mpeg2_pack_header(buf) is False

    def test_too_short_buffer(self):
        assert is_mpeg2_pack_header(bytearray([0x00, 0x00, 0x01])) is False
        assert is_mpeg2_pack_header(bytearray()) is False


class TestIsPrivateStream:
    def test_private_stream1(self):
        buf = bytearray(8)
        buf[2:6] = bytes([0x00, 0x00, 0x01, 0xBD])
        assert is_private_stream1(buf, 2) is True
        assert is_private_stream1(buf, 0) is False

    def test_private_stream2(self):
        buf = bytearray(8)
        buf[2:6] = bytes([0x00, 0x00, 0x01, 0xBF])
        assert is_private_stream2(buf, 2) is True
        assert is_private_stream1(buf, 2) is False

    def test_out_of_range_index_is_false(self):
        buf = bytearray([0x00, 0x00, 0x01, 0xBD])
        assert is_private_stream1(buf, 1) is False
        assert is_private_stream2(buf, 1) is False

    def test_private_stream1_correct_byte(self):
        buffer = bytearray([
            0x00, 0x00, 0x01, 0xBA,  # MPEG-2 Pack Header
            0x00, 0x00, 0x01, 0xBD   # Private Stream 1
        ])
        assert is_private_stream1(buffer, 4) is True
        assert is_private_stream2(buffer, 4) is False


class TestIsSubtitlePack:
    def test_valid_subtitle_pack(self):
        # MPEG-2 pack header + private stream 1 at offset 14,
        # PES header with length 0 and stream id 0x20 (subtitle range)
        buf = bytearray(14 + 8 + 1 + 1)
        buf[0:4] = bytes([0x00, 0x00, 0x01, 0xBA])
        buf[14:18] = bytes([0x00, 0x00, 0x01, 0xBD])
        buf[14 + 8] = 0x00  # pesHeader_data_length
        buf[14 + 8 + 1 + 0] = 0x20  # stream id in subtitle range
        assert is_subtitle_pack(buf) is True

    def test_non_subtitle_stream_id(self):
        buf = bytearray(14 + 8 + 1 + 1)
        buf[0:4] = bytes([0x00, 0x00, 0x01, 0xBA])
        buf[14:18] = bytes([0x00, 0x00, 0x01, 0xBD])
        buf[14 + 8] = 0x00
        buf[14 + 8 + 1 + 0] = 0xC0  # audio stream id, not subtitle
        assert is_subtitle_pack(buf) is False

    def test_not_a_pack_header(self):
        assert is_subtitle_pack(bytearray(32)) is False

    def test_stream_id_0x3f_is_valid(self):
        # Upper bound of subtitle range
        buf = bytearray(14 + 8 + 1 + 1)
        buf[0:4] = bytes([0x00, 0x00, 0x01, 0xBA])
        buf[14:18] = bytes([0x00, 0x00, 0x01, 0xBD])
        buf[14 + 8] = 0x00
        buf[14 + 8 + 1 + 0] = 0x3F
        assert is_subtitle_pack(buf) is True