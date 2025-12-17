
import os
from typing import List

from .config import SettingsArgs
from .vob_sub_pack import VobSubPack
from .idx import Idx
from .idx import IdxParagraph
from .vob_sub_merge_pack import VobSubMergedPack
from .utils import custom_timedelta
from .utils import is_subtitle_pack, is_private_stream1

PES_MAX_LENGTH = 2028

class VobSubParser:

    def __init__(self, is_pal: bool):
        self.is_pal = is_pal
        self.vob_sub_packs: list[VobSubPack] = []
        self.settings = SettingsArgs()

    def open_file(self, filename: str) -> None:
        with open(filename, mode='rb') as file:
            return file

    # /// <summary>
    # /// Can be used with e.g. MemoryStream or FileStream
    # /// </summary>
    # /// <param name="ms"></param>
    def open(self, ms: bytes):
        ms.Position = 0
        # var buffer = new byte[0x800] // 2048
        position = 0
        while (position < len(ms)):
            self.vob_sub_packs = []
            ms.seek(position, 0)
            buffer = ms.read(0x0800)
            if (is_subtitle_pack(buffer)):
                self.vob_sub_packs.append(VobSubPack(buffer, None))

            position += 0x800

    def open_sub_idx(self, vob_sub_filename: str,  idx_filename: str):
        self.vob_sub_packs = []
        if os.path.exists(idx_filename):
            idx = Idx(idx_filename)
            self.idx_palette = idx.palette
            self.idx_languages = idx.languages
            if len(idx.idx_paragraphs) > 0:
                with open(vob_sub_filename, mode='rb') as fs:
                    file = fs.read()
                    for p in idx.idx_paragraphs:
                        if p.file_position + 100 < len(file):
                            position = p.file_position
                            # fs.seek(p.file_position, 0)
                            buffer = file[position: position + 0x0800]
                            if is_subtitle_pack(buffer) or is_private_stream1(buffer, 0):
                                vsp = VobSubPack(buffer, p)
                                self.vob_sub_packs.append(vsp)
                                if is_private_stream1(buffer, 0):
                                    position += vsp.packetized_elementary_stream.lenght + 6
                                else:
                                    position += 0x800

                                current_sub_picture_stream_id = 0
                                if vsp.packetized_elementary_stream.sub_picture_stream_id != None:
                                    current_sub_picture_stream_id = vsp.packetized_elementary_stream.sub_picture_stream_id #.Value ?

                                while vsp.packetized_elementary_stream != None \
                                    and hasattr(vsp.packetized_elementary_stream, 'sub_picture_stream_id') \
                                    and (vsp.packetized_elementary_stream.lenght == PES_MAX_LENGTH \
                                        or current_sub_picture_stream_id != vsp.packetized_elementary_stream.sub_picture_stream_id) \
                                    and position < len(file):

                                    # fs.seek(position, 0)
                                    # buffer = fs.read(0x800)
                                    buffer = file[position: position + 0x0800]
                                    vsp = VobSubPack(buffer, p) # idx position?

                                    if vsp.packetized_elementary_stream is not None \
                                        and hasattr(vsp.packetized_elementary_stream, 'sub_picture_stream_id') \
                                        and current_sub_picture_stream_id == vsp.packetized_elementary_stream.sub_picture_stream_id:
                                        self.vob_sub_packs.append(vsp)

                                        if is_private_stream1(buffer, 0):
                                            position += vsp.packetized_elementary_stream.lenght + 6
                                        else:
                                            position += 0x800
                                    else:
                                        position += 0x800
                                        fs.seek(position, 0)
                return

        # // No valid idx file found - just open like vob file
        self.open_file(vob_sub_filename)

    def merge_vob_sub_packs(self) -> List[VobSubMergedPack]:
        """
        Demultiplex multiplexed packs together each stream_id at a time + removing bad packs + fixing displaytimes
        :return: List of complete packs each with a complete sub image
        """
        list_vob_sub_merge_pack: List[VobSubMergedPack] = []
        ms = bytearray()

        ticks_per_millisecond = 90.000
        if not self.is_pal:
            ticks_per_millisecond = 90.090 * (23.976 / 24)

        # get unique stream_ids
        unique_stream_ids = []
        for p in self.vob_sub_packs:
            if p.packetized_elementary_stream is not None \
                and hasattr(p.packetized_elementary_stream, "sub_picture_stream_id") \
                and p.packetized_elementary_stream.sub_picture_stream_id not in unique_stream_ids:

                unique_stream_ids.append(p.packetized_elementary_stream.sub_picture_stream_id)

        last_idx_paragraph: IdxParagraph = None
        for unique_stream_id in unique_stream_ids: # packets must be merged in stream_id order (so they don't get mixed)
            for p in self.vob_sub_packs:
                if (p.packetized_elementary_stream is not None  \
                    and hasattr(p.packetized_elementary_stream, "sub_picture_stream_id") \
                    and p.packetized_elementary_stream.sub_picture_stream_id == unique_stream_id):

                    if p.packetized_elementary_stream.presentation_timestamp_decode_timestamp_flags > 0:
                        if last_idx_paragraph is None or p.idx_line.file_position != last_idx_paragraph.file_position:
                            if len(ms) > 0:
                                list_vob_sub_merge_pack.append(VobSubMergedPack(ms, pts, stream_id, last_idx_paragraph))

                            ms = bytearray()
                            pts = custom_timedelta(milliseconds = float(p.packetized_elementary_stream.presentation_timestamp / ticks_per_millisecond)) # 90000F * 1000)); (PAL)
                            stream_id = p.packetized_elementary_stream.sub_picture_stream_id
                    last_idx_paragraph = p.idx_line
                    ms = p.packetized_elementary_stream.write_to_stream(ms)
            if len(ms) > 0:
                list_vob_sub_merge_pack.append(VobSubMergedPack(ms, pts, stream_id, last_idx_paragraph))
                ms = bytearray()

        # Remove any bad packs
        for i in range(len(list_vob_sub_merge_pack))[::-1]:
            pack = list_vob_sub_merge_pack[i]
            if pack.sub_picture == None \
                or pack.sub_picture.image_display_area.width <= 3 \
                or pack.sub_picture.image_display_area.height <= 2:

                list_vob_sub_merge_pack.pop(i)

            elif pack.end_time.total_seconds() - pack.start_time.total_seconds() < 0.1 \
                and pack.sub_picture.image_display_area.width <= 10 \
                and pack.sub_picture.image_display_area.height <= 10:

                list_vob_sub_merge_pack.pop(i)

        # Fix subs with no duration (completely normal) or negative duration or duration > 10 seconds
        for i in range(len(list_vob_sub_merge_pack)):
            pack = list_vob_sub_merge_pack[i]
            if pack.sub_picture.delay.total_milliseconds() > 0:
                pack.end_time = pack.start_time + pack.sub_picture.delay

            if pack.end_time < pack.start_time \
                or pack.end_time.total_milliseconds() - pack.start_time.total_milliseconds() \
                    > self.settings.general.subtitle_maximum_display_milliseconds:

                if i + 1 < len(list_vob_sub_merge_pack):

                    pack.end_time = custom_timedelta(
                        milliseconds=list_vob_sub_merge_pack[i + 1].start_time.total_milliseconds() \
                        - self.settings.general.minimum_milliseconds_between_lines
                    )

                    if pack.end_time.total_milliseconds() - pack.start_time.total_milliseconds() \
                        > self.settings.general.subtitle_maximum_display_milliseconds:

                        pack.end_time = custom_timedelta(milliseconds=pack.start_time.total_milliseconds() \
                            + self.settings.general.subtitle_maximum_display_milliseconds
                        )
                    else:
                        pack.end_time = custom_timedelta(milliseconds=pack.start_time.total_milliseconds() + 3000)
        return list_vob_sub_merge_pack
