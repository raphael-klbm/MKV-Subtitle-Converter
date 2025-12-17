
from dataclasses import dataclass
from datetime import datetime
from typing import List
import re

from .custom_color import CustomColor as Color
from .utils import custom_timedelta as timedelta


@dataclass
class IdxParagraph:
    start_time: datetime
    file_position: int


class Idx:

    def __init__(self, file_name: str):
        self.idx_paragraphs: List[IdxParagraph] = []
        self.palette: List[str] = [] #Colour
        self.languages: List[str] = []
        self.time_code_line_pattern = re.compile("^timestamp: \d+:\d+:\d+:\d+, filepos: [\dabcdefABCDEF]+$")

        with open(file_name) as file:
            lines = file.readlines()

        self.process_file(lines)


    def process_file(self, lines: List[str]):
        language_index = 0
        for line in lines:
            line = line.strip('\n')
            if self.time_code_line_pattern.search(line) is not None:
                p: IdxParagraph = self.get_time_code_and_file_position(line)
                if p is not None:
                    self.idx_paragraphs.append(p)

            elif line.startswith("palette:") and len(line) > 10:
                s =  line.strip('palette:').split(',')
                colors = [c.strip(' ') for c in s]
                for hex_str in colors:
                    self.palette.append(self.hex_to_color(hex_str))

            elif line.startswith("id:") and len(line) > 4:
                # id: en, index: 1
                # id: es, index: 2
                self.language_index = line[-2].strip(' ')
                self.two_letter_language_id = line.split(',')[0][-3:].strip(' ')
                # parts = line.split(new[] { ':', ',', ' ' }, StringSplitOptions.RemoveEmptyEntries);
                # if parts.Length > 1:
                    # string twoLetterLanguageId = parts[1];
                    # string languageName = DvdSubtitleLanguage.GetLocalLanguageName(twoLetterLanguageId);
                    # if (parts.Length > 3 && parts[2].Equals("index", StringComparison.OrdinalIgnoreCase))
                    # {
                    #     int index;
                    #     if (int.TryParse(parts[3], out index))
                    #     {
                    #         languageIndex = index;
                    #     }
                    # }
                    # # Use U+200E (LEFT-TO-RIGHT MARK) to support right-to-left scripts
                    # Languages.Add(string.Format("{0} \x200E(0x{1:x})", languageName, languageIndex + 32));
                    # languageIndex++;


    def hex_to_color(self, hex_str: str):
        hex_str = hex_str.strip('#').strip()
        if (len(hex_str) == 6):
            r = int(hex_str[0: 2], 16) / 255
            g = int(hex_str[2: 4], 16) / 255
            b = int(hex_str[4: 6], 16) / 255
            return Color(rgb=(r, g, b))

        elif (len(hex_str) == 8):
            a = int(hex_str[0: 2], 16)
            r = int(hex_str[2: 4], 16)
            g = int(hex_str[4: 6], 16)
            b = int(hex_str[6: 8], 16)
            return Color(rgba=(r, g, b, a))
        return Color("red")


    def get_time_code_and_file_position(self, line: str) -> IdxParagraph:
        # timestamp: 00:00:01:401, filepos: 000000000
        timestamp, filepos = line.split(',')
        timestamp = timestamp[-12:]
        filepos = int(filepos[-9:], 16)
        if (len(timestamp.split(':')) == 4):
            hours, minutes, seconds, milliseconds = [int(o) for o in timestamp.split(':')]
            return IdxParagraph(timedelta(hours=hours, minutes=minutes, seconds=seconds, milliseconds=milliseconds), filepos)
        return None