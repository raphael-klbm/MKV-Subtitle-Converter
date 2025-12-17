from .utils import get_endian, get_endian_word, Mpeg2Header

# http://www.mpucoder.com/DVD/pes-hdr.html
class PacketizedElementaryStream:
    HEADER_LENGHT: int = 6

    def __init__(self, buffer: bytearray, index: int):
        self.buffer = buffer
        self.start_code = get_endian(buffer, index, 3)
        self.stream_id = buffer[index + 3]
        self.lenght = get_endian_word(buffer, index + 4)

        self.scrambling_control = (buffer[index + 6] >> 4) & 0b00000011
        self.priority = buffer[index + 6] & 0b00001000
        self.data_alignment_indicator = buffer[index + 6] & 0b00000100
        self.copyright = buffer[index + 6] & 0b00000010
        self.original_or_copy = buffer[index + 6] & 0b00000001
        self.presentation_timestamp_decode_timestamp_flags = buffer[index + 7] >> 6
        self.elementary_stream_clock_reference_flag = buffer[index + 7] & 0b00100000
        self.es_rate_flag = buffer[index + 7] & 0b00010000
        self.dsm_trick_mode_flag = buffer[index + 7] & 0b00001000
        self.additional_copy_info_flag = buffer[index + 7] & 0b00000100
        self.crc_flag = buffer[index + 7] & 0b00001000
        self.extension_flag = buffer[index + 7] & 0b00000010

        self.header_data_length = buffer[index + 8]

        if self.stream_id == 0xBD:
            id = buffer[index + 9 + self.header_data_length]
            if id >= 0x20 and id <= 0x40: # x3f 0r x40 ?
                self.sub_picture_stream_id = id

        temp_index = index + 9
        if self.presentation_timestamp_decode_timestamp_flags == 0b00000010 or \
            self.presentation_timestamp_decode_timestamp_flags == 0b00000011:

            self.presentation_timestamp = buffer[temp_index + 4] >> 1 #ulong
            self.presentation_timestamp += buffer[temp_index + 3] << 7
            self.presentation_timestamp += (buffer[temp_index + 2] & 0b11111110) << 14
            self.presentation_timestamp += buffer[temp_index + 1] << 22
            self.presentation_timestamp += (buffer[temp_index + 0] & 0b00001110) << 29

            temp_index += 5
        if self.presentation_timestamp_decode_timestamp_flags == 0b00000011:
            self.decode_timestamp = buffer[temp_index + 4] >> 1
            self.decode_timestamp += buffer[temp_index + 3] << 7
            self.decode_timestamp += (buffer[temp_index + 2] & 0b11111110) << 14
            self.decode_timestamp += buffer[temp_index + 1] << 22
            self.decode_timestamp += (buffer[temp_index + 0] & 0b00001110) << 29

        data_index = index + self.header_data_length + 24 - Mpeg2Header.LENGHT

        data_size = self.lenght - (4 + self.header_data_length)

        if data_size < 0 or (data_size + data_index > len(buffer)): #// to fix bad subs...
            self.data_size = len(buffer) - data_index
            if (self.data_size < 0):
                return

        self._data_buffer = buffer[data_index:data_index+data_size]

    def write_to_stream(self, stream: bytes):
        return stream + self._data_buffer
