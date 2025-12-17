from dataclasses import dataclass
from datetime import timedelta
from functools import wraps


def get_endian_word(buffer: bytearray, index: int) -> int:
    """
    Get two bytes word stored in endian order
    :param: buffer: bytearray
    :param: index: index in byte array

    """
    if (index + 1 < len(buffer)):
        return (buffer[index] << 8) | buffer[index + 1]

    return 0

def get_endian(buffer: bytearray, index: int, count: int):
    result = 0
    for i in range(count):
        result = (result << 8) + buffer[index + i]

    return result


def wrapper(method):
    @wraps(method)
    def wrapped(*args, **kwargs):
        r = method(*args, **kwargs)
        if isinstance(r, timedelta):
            return custom_timedelta(seconds=r.total_seconds())
        else:
            return r
    return wrapped

class TimeDeltaMetaClass(type):
    def __new__(meta, classname, bases, class_dict):
        class_ = super().__new__(meta, classname, bases, class_dict)
        new_class_dict = {}
        for attribute_name in dir(class_):
            if attribute_name in ['__init__', '__new__', '__class__', '__dict__']:
                continue
            # if hasattr(attribute, '__call__'):
            # if type(attribute) == FunctionType:
                # attribute = wrapper(attribute)
            attribute = getattr(class_, attribute_name)
            setattr(class_, attribute_name,  wrapper(attribute))
            # new_class_dict[attributeName] = attribute
        # return super().__new__(meta, classname, bases, new_class_dict)
        return class_
class custom_timedelta(timedelta, metaclass=TimeDeltaMetaClass):
    def total_milliseconds(self) -> float:
        """Total milliseconds in the duration."""
        return self / timedelta(milliseconds=1)

    def hours(self) -> int:
        seconds =  self.total_seconds()
        return int(seconds // 3600)

    def minutes(self) -> int:
        seconds =  self.total_seconds()
        return int((seconds % 3600) // 60)

    def seconds(self) -> int:
        seconds =  self.total_seconds()
        return int(seconds % 60)

    def milliseconds(self) -> int:
        milliseconds = self.total_milliseconds()
        return int(milliseconds % 1000)

    def get_str_format(self):
        # 01:20:52,412
        return "{:02d}:{:02d}:{:02d},{:03d}".format(self.hours(), self.minutes(), self.seconds(), self.milliseconds())


class Mpeg2Header:
    #  <summary>
    #  http://www.mpucoder.com/DVD/packhdr.html
    #  </summary>
    LENGHT = 14

    def __init__(self, buffer: bytes):

        self.start_code = get_endian(buffer, 0, 3)
        self.pack_identifier = buffer[3]
        self.program_mux_rate = get_endian(buffer, 10, 3) >> 2
        self.pack_stuffing_length = buffer[13] & 0b00000111

@dataclass
class Rectangle:
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0



def is_mpeg2_pack_header(buffer: bytearray) -> bool:
    return len(buffer) >= 4 \
            and buffer[0] == 0 \
            and buffer[1] == 0 \
            and buffer[2] == 1 \
            and buffer[3] == 0xba; # 0xba == 186 - MPEG-2 Pack Header

def is_private_stream1(buffer: bytearray, index: int) -> bool:
    return len(buffer) >= index + 4 \
            and buffer[index + 0] == 0 \
            and buffer[index + 1] == 0 \
            and buffer[index + 2] == 1 \
            and buffer[index + 3] == 0xbd; # 0xbd == 189 - MPEG-2 Private stream 1 (non MPEG audio, subpictures)

def is_private_stream2(buffer: bytearray, index: int) -> bool:
    return len(buffer) >= index + 4 \
            and buffer[index + 0] == 0 \
            and buffer[index + 1] == 0 \
            and buffer[index + 2] == 1 \
            and buffer[index + 3] == 0xbf; # 0xbf == 191 - MPEG-2 Private stream 2

def is_subtitle_pack(buffer: bytearray) -> bool:
    if is_mpeg2_pack_header(buffer) and is_private_stream1(buffer, Mpeg2Header.LENGHT):
        pesHeader_data_length = buffer[Mpeg2Header.LENGHT + 8]
        streamId = buffer[Mpeg2Header.LENGHT + 8 + 1 + pesHeader_data_length]

        return streamId >= 0x20 and streamId <= 0x3f # Subtitle IDs allowed (or x3f to x40?)
    return False