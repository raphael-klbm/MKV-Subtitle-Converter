
from enum import Enum
from typing import List
import numpy as np

from .utils import get_endian_word, Rectangle
from .utils import custom_timedelta as timedelta
from .custom_color import CustomColor as Color

class SubPicture:
# Subtitle Picture - see http:#www.mpucoder.com/DVD/spu.html for more info
# http://sam.zoy.org/writings/dvd/subtitles/

    class DisplayControlCommand(Enum):
        ForcedStartDisplay = 0
        StartDisplay = 1
        StopDisplay = 2
        SetColor = 3
        SetContrast = 4
        SetDisplayArea = 5
        SetPixelDataAddress = 6
        ChangeColorAndContrast = 7
        End = 0xFF

    def __init__(
        self, data: bytes,
        start_display_control_sequence_table_address: int = None,
        pixel_data_address_offset: int = 0
    ):
        """
        For SP packet with DVD sub pictures
        :param: data: bytes content of the sub pack
        :param: start_display_control_sequence_table_address: Adress of the first control sequence in data
        :param: pixel_data_address_offset: Bitmap pixel data address offset
        """
        self._data = data
        self.forced = False
        self.delay = timedelta()
        self.sub_picture_data_size = get_endian_word(self._data, 0)
        self._pixel_data_address_offset = pixel_data_address_offset
        if start_display_control_sequence_table_address is None and pixel_data_address_offset is None:
            self._start_display_control_sequence_table_address = start_display_control_sequence_table_address
        else:
            self._start_display_control_sequence_table_address = get_endian_word(self._data, 2)
            self.sub_picture_data_size = len(self._data)
        self.parse_display_control_commands(False, None, None, False, False)

    def get_bitmap(
        self,
        color_lookup_table: List[Color],
        background: Color,
        pattern: Color,
        emphasis1: Color,
        emphasis2: Color,
        use_custom_colors: bool,
        crop: bool = True
    ) -> np.ndarray:
        """
        Generates the current subtitle image
        :param: color_lookup_table: The Color LookUp Table (CLUT), if null then only the four colors are used (should contain 16 elements if not null)
        :param: background: Background color
        :param: pattern: Color
        :param: emphasis1: Color
        :param: emphasis2: Color
        :param: use_custom_colors: Use custom colors instead of lookup table
        :param: crop: Crop result image

        :return: Subtitle image
        """
        four_colors = [background, pattern, emphasis1, emphasis2]
        return self.parse_display_control_commands(True, color_lookup_table, four_colors, use_custom_colors, crop)

    def parse_display_control_commands(
        self,
        create_bitmap: bool,
        color_look_up_table: List[Color],
        four_colors: List[Color],
        use_custom_colors: bool,
        crop: bool
    ) -> np.ndarray:
        self.image_display_area = Rectangle()
        bmp = None
        display_control_sequence_table_addresses = []
        image_top_field_data_address = 0
        image_bottom_field_data_address = 0
        bitmap_generated = False
        largest_delay = -999999
        display_control_sequence_table_address = self._start_display_control_sequence_table_address - self._pixel_data_address_offset
        last_display_control_sequence_table_address = 0
        display_control_sequence_table_addresses.append(display_control_sequence_table_address)
        command_index = 0
        while (display_control_sequence_table_address > last_display_control_sequence_table_address
            and display_control_sequence_table_address + 1 < len(self._data) and command_index < len(self._data)):

            delay_before_execute = get_endian_word(self._data, display_control_sequence_table_address + self._pixel_data_address_offset)
            command_index = display_control_sequence_table_address + 4 + self._pixel_data_address_offset
            if (command_index >= len(self._data)):
                break ## invalid index

            command = self._data[command_index]
            number_of_commands = 0
            while command != SubPicture.DisplayControlCommand.End.value and number_of_commands < 1000 and command_index < len(self._data):
                number_of_commands += 1
                if command == SubPicture.DisplayControlCommand.ForcedStartDisplay.value: # 0
                    self.forced = True
                    command_index+=1
                elif command == SubPicture.DisplayControlCommand.StartDisplay.value: # 1
                    command_index+=1
                elif command == SubPicture.DisplayControlCommand.StopDisplay.value: # 2
                    self.delay = timedelta(milliseconds=(delay_before_execute << 10) / 90.0)
                    if create_bitmap and self.delay.total_milliseconds() > largest_delay: # in case of more than one images, just use the one with the largest display time
                        largest_delay = self.delay.total_milliseconds()
                        # bmp?.Dispose() # Release the image memory
                        bmp = self.generate_bitmap(self.image_display_area, image_top_field_data_address, image_bottom_field_data_address, four_colors, crop)
                        bitmap_generated = True
                    command_index+=1
                elif command == SubPicture.DisplayControlCommand.SetColor.value: # 3
                    if color_look_up_table != None and len(four_colors) == 4:
                        imageColor = [self._data[command_index + 1], self._data[command_index + 2]]
                        if not use_custom_colors:
                            four_colors = SubPicture.set_color(four_colors, 3, imageColor[0] >> 4, color_look_up_table)
                            four_colors = SubPicture.set_color(four_colors, 2, imageColor[0] & 0b00001111, color_look_up_table)
                            four_colors = SubPicture.set_color(four_colors, 1, imageColor[1] >> 4, color_look_up_table)
                            four_colors = SubPicture.set_color(four_colors, 0, imageColor[1] & 0b00001111, color_look_up_table)
                    command_index += 3
                elif command == SubPicture.DisplayControlCommand.SetContrast.value: # 4
                    if color_look_up_table != None and len(four_colors) == 4:
                        imageContrast = [self._data[command_index + 1], self._data[command_index + 2]]
                        if imageContrast[0] + imageContrast[1] > 0:
                            four_colors = SubPicture.set_transparency(four_colors, 3, (imageContrast[0] & 0xF0) >> 4)
                            four_colors = SubPicture.set_transparency(four_colors, 2, imageContrast[0] & 0b00001111)
                            four_colors = SubPicture.set_transparency(four_colors, 1, (imageContrast[1] & 0xF0) >> 4)
                            four_colors = SubPicture.set_transparency(four_colors, 0, imageContrast[1] & 0b00001111)
                    command_index += 3
                elif command == SubPicture.DisplayControlCommand.SetDisplayArea.value: # 5
                    if len(self._data) > command_index + 6 and self.image_display_area.width == 0 and self.image_display_area.height == 0:
                        starting_x = (self._data[command_index + 1] << 8 | self._data[command_index + 2]) >> 4
                        ending_x = (self._data[command_index + 2] & 0b00001111) << 8 | self._data[command_index + 3]
                        starting_y = (self._data[command_index + 4] << 8 | self._data[command_index + 5]) >> 4
                        ending_y = (self._data[command_index + 5] & 0b00001111) << 8 | self._data[command_index + 6]
                        self.image_display_area = Rectangle(starting_x, starting_y, ending_x - starting_x +1, ending_y - starting_y+1)
                    command_index += 7
                elif command == SubPicture.DisplayControlCommand.SetPixelDataAddress.value: # 6
                    image_top_field_data_address = get_endian_word(self._data, command_index + 1) + self._pixel_data_address_offset
                    image_bottom_field_data_address = get_endian_word(self._data, command_index + 3) + self._pixel_data_address_offset
                    command_index += 5
                elif command == SubPicture.DisplayControlCommand.ChangeColorAndContrast.value: # 7
                    command_index += 1
                    #int parameterAreaSize = (int)Helper.GetEndian(_data, command_index, 2)
                    if command_index + 1 < len(self._data):
                        parameter_area_size = self._data[command_index + 1] # this should be enough??? (no larger than 255 bytes)
                        if (color_look_up_table is not None):
                            # TODO: Set four_colors
                            pass
                        command_index += parameter_area_size
                    else:
                        command_index+=1
                else:
                    command_index+=1
                if command_index >= len(self._data): # in case of bad files...
                    break

                command = self._data[command_index]

            last_display_control_sequence_table_address = display_control_sequence_table_address
            if self._pixel_data_address_offset == -4:
                display_control_sequence_table_address = get_endian_word(self._data, command_index + 3)
            else:
                display_control_sequence_table_address = get_endian_word(self._data, display_control_sequence_table_address + 2)
        if create_bitmap and not bitmap_generated: # StopDisplay not needed (delay will be zero - should be just before start of next subtitle)
            bmp = self.generate_bitmap(self.image_display_area, image_top_field_data_address, image_bottom_field_data_address, four_colors, crop)

        return bmp

    @staticmethod
    def set_color(
        four_colors: List[Color],
        four_color_index: int,
        clut_index: int,
        color_look_up_table: List[Color]
    ) -> None:

        if clut_index >= 0 and clut_index < len(color_look_up_table) and four_color_index >= 0:
            four_colors[four_color_index] = color_look_up_table[clut_index]
        return four_colors

    @staticmethod
    def set_transparency(
        four_colors: List[Color],
        four_color_index: int,
        alpha: int
    ):
        # alpha: 0x0 = transparent, 0xF = opaque (in C# 0 is fully transparent, and 255 is fully opaque so we have to multiply by 17)
        if (four_color_index >= 0):
            # four_colors[four_color_index] = Color(rgba=(alpha * 17, four_colors[four_color_index].red, four_colors[four_color_index].green, four_colors[four_color_index].blue))
            four_colors[four_color_index] = Color(rgb=(four_colors[four_color_index].red, four_colors[four_color_index].green, four_colors[four_color_index].blue))
        return four_colors

    def generate_bitmap(
        self,
        image_display_area: Rectangle,
        image_top_field_data_address: int,
        image_bottom_field_data_address: int,
        four_colors: List[Color],
        crop: bool
    ) -> np.ndarray:
        if image_display_area.width <= 0 and image_display_area.height <= 0:
            return np.zeros([1, 1])

        img = np.zeros([image_display_area.height, image_display_area.width, 3])
        # initialize the bg color
        img = img + list(four_colors[0].rgb)

        img = self.generate_fast_bitmap(self._data, img, 0, image_top_field_data_address, four_colors, 2)
        img = self.generate_fast_bitmap(self._data, img, 1, image_bottom_field_data_address, four_colors, 2)
        cropped = self.crop_bitmap_and_unlock(img, four_colors[0], crop)

        return cropped

    @staticmethod
    def crop_bitmap_and_unlock(
        img: np.ndarray,
        background_color: Color,
        crop: bool
    ) -> np.ndarray:
        y = 0
        c: Color = background_color
        background_argb = list(background_color.rgb)
        min_x = 0
        max_x = 0
        min_y = 0
        max_y = 0

        img_heigt = img.shape[0]
        img_width = img.shape[1]

        if crop:
            # Crop top
            while y < img_heigt and SubPicture.is_background_color(c, background_argb):
                c = img[y, 0]
                if SubPicture.is_background_color(c, background_argb):
                    for x in range(1, img_width):
                        c = img[y, x]
                        if c != background_argb:
                            break
                if SubPicture.is_background_color(c, background_argb):
                    y+=1
            min_y = y
            if (min_y > 3):
                min_y -= 3
            else:
                min_y = 0

            # Crop left
            x = 0
            c = background_color
            while x < img_width and SubPicture.is_background_color(c, background_argb):
                for y in range(min_y, img_heigt):
                    c = img[y, x]
                    if not SubPicture.is_background_color(c, background_argb):
                        break
                if SubPicture.is_background_color(c, background_argb):
                    x+=1
            min_x = x
            if (min_x > 3):
                min_x -= 3
            else:
                min_x -= 0

            # Crop bottom
            y = img_heigt - 1
            c = background_color
            while y > min_y and SubPicture.is_background_color(c, background_argb):
                c = img[y, 0]
                if SubPicture.is_background_color(c, background_argb):
                    for x in range(1, img_width):
                        c = img[y, x]
                        if not SubPicture.is_background_color(c, background_argb):
                            break
                if SubPicture.is_background_color(c, background_argb):
                    y-=1
            max_y = y + 7
            if max_y >= img_heigt:
                max_y = img_heigt - 1

            # Crop right
            x = img_width - 1
            c = background_color
            while x > min_x and SubPicture.is_background_color(c, background_argb):
                for y in range(min_y, img_heigt):
                    c = img[y, x]
                    if not SubPicture.is_background_color(c, background_argb):
                        break
                if SubPicture.is_background_color(c, background_argb):
                    x-=1
            max_x = x + 7
            if max_x >= img_width:
                max_x = img_width - 1

        if img_width > 1 and img_heigt > 1 and max_x - min_x > 0 and max_y - min_y > 0:
            imgCrop = img[min_y:max_y, min_x:max_x]
            return imgCrop
        return img

    @staticmethod
    def is_background_color(c: Color, background_argb: int) -> bool:
        return c == background_argb

    @staticmethod
    def generate_fast_bitmap(
        data: bytes,
        img: np.ndarray,
        startY: int,
        data_address: int,
        four_colors: List[Color],
        addY: int
    ) -> None:
        index = 0
        only_half = False
        y = startY
        x = 0
        color_zero_value = four_colors[0].hex
        img_heigt = img.shape[0]
        img_width = img.shape[1]
        while y < img_heigt and data_address + index + 2 < len(data):
            sup_index, run_length, color, only_half, rest_of_line = SubPicture.decode_rle(data_address + index, data, only_half)
            index += sup_index
            if rest_of_line:
                run_length = img_width - x

            c: Color = four_colors[color] # set color via the four colors
            for i in range(run_length):
                if x >= img_width - 1:
                    if y < img_heigt and x < img_width and c != four_colors[0]:
                        img[y, x] = list(c.rgb)

                    if only_half:
                        only_half = False
                        index+=1
                    x = 0
                    y += addY
                    break
                if y < img_heigt and c.hex != color_zero_value:
                    img[y, x] = list(c.rgb)
                x+=1
        return img

    @staticmethod
    def decode_rle(
        index: int,
        data: bytes,
        only_half: bool
    ) -> int:
        #Value      Bits   n=length, c=color
        #1-3        4      nncc               (half a byte)
        #4-15       8      00nnnncc           (one byte)
        #16-63     12      0000nnnnnncc       (one and a half byte)
        #64-255    16      000000nnnnnnnncc   (two bytes)
        # When reaching EndOfLine, index is byte aligned (skip 4 bits if necessary)
        rest_of_line = False
        b1 = data[index]
        b2 = data[index + 1]

        if only_half:
            b3 = data[index + 2]
            b1 = ((b1 & 0b00001111) << 4) | ((b2 & 0b11110000) >> 4)
            b2 = ((b2 & 0b00001111) << 4) | ((b3 & 0b11110000) >> 4)

        if b1 >> 2 == 0:
            run_length = (b1 << 6) | (b2 >> 2)
            color = b2 & 0b00000011
            if run_length == 0:
                # rest of line + skip 4 bits if Only half
                rest_of_line = True
                if only_half:
                    only_half = False
                    return 3, run_length, color, only_half, rest_of_line
            return 2, run_length, color, only_half, rest_of_line

        if b1 >> 4 == 0:
            run_length = (b1 << 2) | (b2 >> 6)
            color = (b2 & 0b00110000) >> 4
            if only_half:
                only_half = False
                return 2, run_length, color, only_half, rest_of_line
            only_half = True
            return 1, run_length, color, only_half, rest_of_line

        if b1 >> 6 == 0:
            run_length = b1 >> 2
            color = b1 & 0b00000011
            return 1, run_length, color, only_half, rest_of_line

        run_length = b1 >> 6
        color = (b1 & 0b00110000) >> 4

        if only_half:
            only_half = False
            return 1, run_length, color, only_half, rest_of_line
        only_half = True
        return 0, run_length, color, only_half, rest_of_line
