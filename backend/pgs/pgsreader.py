# source: https://github.com/EzraBC/pgsreader

#!/usr/bin/env python3
from os.path import split as pathsplit
from collections import namedtuple
import logging

# Segments
PDS = int('0x14', base=16) # Palette Definition Segment, 0x14
ODS = int('0x15', base=16) # Object Definition Segment, 0x15
PCS = int('0x16', base=16) # Presentation Composition Segment, 0x16
WDS = int('0x17', base=16) # Window Definition Segment, 0x17
END = int('0x80', base=16) # End of Display Set Segment, 0x80

exit_code = 0

# Named tuple access for static PDS palettes 
Palette = namedtuple('Palette', "Y Cr Cb Alpha")

class InvalidSegmentError(Exception):
    '''Raised when a segment does not match PGS specification'''


class PGSReader:

    def __init__(self, filepath):
        self.filedir, self.file = pathsplit(filepath) 
        with open(filepath, 'rb') as f:
            self.bytes = f.read()
            

    def make_segment(self, bytes_):
        cls = SEGMENT_TYPE[bytes_[10]]
        return cls(bytes_) # can return any segment, but cls is no segment

    def iter_segments(self):
        index = 0
        while index < len(self.bytes):
            size = 13 + int(self.bytes[index + 11:index + 13].hex(), 16)
            yield self.make_segment(self.bytes[index:index + size])
            index += size

    def iter_displaysets(self):
        ds = []
        for s in self.iter_segments():
            ds.append(s)
            if s.type == 'END':
                yield DisplaySet(ds)
                ds = []

    @property
    def segments(self):
        if not hasattr(self, '_segments'):
            self._segments = list(self.iter_segments())
        return self._segments

    @property
    def displaysets(self):
        if not hasattr(self, '_displaysets'):
            self._displaysets = list(self.iter_displaysets())
        return self._displaysets


class BaseSegment:

    SEGMENT = {
        PDS: 'PDS', 
        ODS: 'ODS', 
        PCS: 'PCS', 
        WDS: 'WDS', 
        END: 'END'
    }
    
    def __init__(self, bytes_):
        self.bytes = bytes_
        if bytes_[:2] != b'PG': # magic number (0x5047)
            logging.error('Invalid segment magic number.')
            raise InvalidSegmentError
        self.pts = int(bytes_[2:6].hex(), base=16)/90 # presentation timestamp (90kHz clock)
        self.dts = int(bytes_[6:10].hex(), base=16)/90 # decoding timestamp (90kHz clock) # can be ignored because it should always be 0.
        self.type = self.SEGMENT[bytes_[10]] # segment type
        self.size = int(bytes_[11:13].hex(), base=16) # segment size
        self.data = bytes_[13:] # segment data

        # if self.dts != 0:
        #     logging.warning('Decoding timestamp (DTS) not 0.')

    def __len__(self):
        return self.size

    @property
    def presentation_timestamp(self): return self.pts

    @property
    def decoding_timestamp(self): return self.dts

    @property
    def segment_type(self): return self.type


class PresentationCompositionSegment(BaseSegment):
    pass


class WindowDefinitionSegment(BaseSegment):
    pass

class PaletteDefinitionSegment(BaseSegment):

    def __init__(self, bytes_):
        BaseSegment.__init__(self, bytes_)
        self.palette_id = self.data[0]
        self.version = self.data[1]
        self.palette = [Palette(0, 0, 0, 0)]*256
        # Slice from byte 2 til end of segment. Divide by 5 to determine number of palette entries
        # Iterate entries. Explode the 5 bytes into namedtuple Palette. Must be exploded
        for entry in range(len(self.data[2:])//5):
            i = 2 + entry*5
            self.palette[self.data[i]] = Palette(*self.data[i+1:i+5])


class ObjectDefinitionSegment(BaseSegment):

    SEQUENCE = {
        int('0x40', base=16): 'Last',
        int('0x80', base=16): 'First',
        int('0xc0', base=16): 'First and last'
    }
    
    def __init__(self, bytes_):
        global exit_code
        
        BaseSegment.__init__(self, bytes_)
        self.id = int(self.data[0:2].hex(), base=16)
        self.version = self.data[2]
        self.in_sequence = self.SEQUENCE[self.data[3]]
        self.data_len = int(self.data[4:7].hex(), base=16)
        self.width = int(self.data[7:9].hex(), base=16)
        self.height = int(self.data[9:11].hex(), base=16)
        self.img_data = self.data[11:]
        # if len(self.img_data) != self.data_len - 4:
        #     logging.error("Image data length asserted does not match the "
        #                   "length found.")
        #     exit_code = 3
        #     err_msg = "Image data length asserted does not match the length found."


class EndSegment(BaseSegment):
    pass


class DisplaySet:

    def __init__(self, segments):
        self.segments = segments
        self.segment_types = [s.type for s in segments]
        self.has_image = 'ODS' in self.segment_types


SEGMENT_TYPE = {
    PDS: PaletteDefinitionSegment,
    ODS: ObjectDefinitionSegment,
    PCS: PresentationCompositionSegment,
    WDS: WindowDefinitionSegment,
    END: EndSegment
}
        
def segment_by_type_getter(type_):
    def f(self):
        return [s for s in self.segments if s.type == type_]
    return f

for type_ in BaseSegment.SEGMENT.values():
    setattr(DisplaySet, type_.lower(), property(segment_by_type_getter(type_)))