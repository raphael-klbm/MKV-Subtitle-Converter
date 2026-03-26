# Source: https://github.com/vincrichard/VobSub-ML-OCR

from typing import Tuple
import numpy as np
from PIL import ImageColor

from .idx import IdxParagraph
from .sub_picture import SubPicture
from .utils import timedelta as timedelta

class VobSubMergedPack: #IBinaryParagraphWithPosition
    def __init__(self, sub_picture_data: bytearray, presentation_time_stamp: timedelta, stream_id: int, idx_line: IdxParagraph, video_size: Tuple[int, int] = (720, 576)):
        self.sub_picture = SubPicture(sub_picture_data)
        self.end_time = timedelta()
        self.start_time = presentation_time_stamp
        self.stream_id = stream_id
        self.idx_line = idx_line
        self.video_size = video_size
        self.palette  = None

    def is_forced(self):
        return self.sub_picture.forced

    def get_bitmap(self) -> np.ndarray:
        sub_bitmap = self.sub_picture.get_bitmap(self.palette, ImageColor.getrgb("red"), ImageColor.getrgb("black"), ImageColor.getrgb("white"), ImageColor.getrgb("black"), False)

        screen_width, screen_height = self.video_size
        full_bitmap = np.zeros((screen_height, screen_width, 4), dtype=sub_bitmap.dtype)

        x, y = self.get_position()
        h, w = sub_bitmap.shape[:2]

        dst_x0 = max(x, 0)
        dst_y0 = max(y, 0)
        dst_x1 = min(x + w, screen_width)
        dst_y1 = min(y + h, screen_height)

        if dst_x1 > dst_x0 and dst_y1 > dst_y0:
            src_x0 = dst_x0 - x
            src_y0 = dst_y0 - y
            src_x1 = src_x0 + (dst_x1 - dst_x0)
            src_y1 = src_y0 + (dst_y1 - dst_y0)
            full_bitmap[dst_y0:dst_y1, dst_x0:dst_x1] = sub_bitmap[src_y0:src_y1, src_x0:src_x1]

        return full_bitmap
        # return self.sub_picture.get_bitmap(self.palette, Color.Transparent, Color("black"), Color("white"), Color("black"), False)

    def get_position(self) -> Tuple:
        return self.sub_picture.image_display_area.x, self.sub_picture.image_display_area.y
