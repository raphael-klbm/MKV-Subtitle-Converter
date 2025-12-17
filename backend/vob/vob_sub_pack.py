
from .idx import IdxParagraph
from .packetized_elementary_strem import PacketizedElementaryStream
from .utils import is_mpeg2_pack_header, is_private_stream1, Mpeg2Header

class VobSubPack:
        packetized_elementary_stream: PacketizedElementaryStream
        mpeg_2_header: Mpeg2Header

        def __init__(self, buffer: bytes, idx_line: IdxParagraph):
            self._buffer = buffer
            self.idx_line = idx_line

            if (is_mpeg2_pack_header(buffer)):

                self.mpeg_2_header = Mpeg2Header(buffer)
                self.packetized_elementary_stream = PacketizedElementaryStream(buffer, self.mpeg_2_header.LENGHT)

            elif (is_private_stream1(buffer, 0)):

                self.packetized_elementary_stream = PacketizedElementaryStream(buffer, 0)
