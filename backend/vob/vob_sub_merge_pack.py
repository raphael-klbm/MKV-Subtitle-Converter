
from typing import Tuple

import numpy as np

from .idx import IdxParagraph
from .sub_picture import SubPicture
from .utils import timedelta as timedelta
from .custom_color import CustomColor as Color

class VobSubMergedPack: #IBinaryParagraphWithPosition
    def __init__(self, sub_picture_data: bytearray, presentation_time_stamp: timedelta, stream_id: int, idx_line: IdxParagraph):
        self.sub_picture = SubPicture(sub_picture_data)
        self.end_time = timedelta()
        self.start_time = presentation_time_stamp
        self.stream_id = stream_id
        self.idx_line = idx_line
        self.palette  = None

    def is_forced(self):
        return self.sub_picture.forced

    def get_bitmap(self) -> np.ndarray:
        return self.sub_picture.get_bitmap(self.palette, Color("red"), Color("black"), Color("white"), Color("black"), False, True)
        # return self.sub_picture.get_bitmap(self.palette, Color.Transparent, Color("black"), Color("white"), Color("black"), False, True)

    def get_screen_size(self) -> Tuple:
        return (720, 480)

    def get_position(self) -> Tuple:
        return self.sub_picture.image_display_area.x, self.sub_picture.image_display_area.y
