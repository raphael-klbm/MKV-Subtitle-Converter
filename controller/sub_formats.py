from enum import Enum

class SubtitleFileEndings(Enum):
    SRT  = 'srt'
    ASS  = 'ass'
    SSA  = 'ssa'
    SUB  = 'sub'
    JSON = 'json'
    MPL2 = 'mpl'
    TMP  = 'tmp'
    VTT  = 'vtt'

    def get_format(format: str):
        format = format.lower()
        for sub_ending in SubtitleFileEndings:
            if format in sub_ending.name.lower():
                return sub_ending
            
            if format in sub_ending.value.lower():
                return sub_ending
            
            if sub_ending.name.lower() in format:
                return sub_ending
            
            if sub_ending.value.lower() in format:
                return sub_ending
            
        raise ValueError(f'Unknwon file ending: {format}.')
    
class SubtitleFormats(Enum):
    SRT  = "SubRip Text (.srt)"
    ASS  = "Advanced SubStation Alpha (.ass)"
    SSA  = "SubStation Alpha (.ssa)"
    # SUB  = "MicroDVD (.sub)"  # Framerate must be specified when writing MicroDVD.
    # JSON = "JSON (.json)"  # not supported by pysubs2
    # MPL2 = "MPL2 (.mpl)"  # UnknownFileExtensionError: .mpl
    # TMP  = "TMP (.tmp)"  # UnknownFileExtensionError: .tmp
    VTT  = "VTT (.vtt)"

    def get_name(name: str):
        name = name.lower()
        for sub_format in SubtitleFormats:
            if name in sub_format.name.lower():
                return sub_format
            
            if name in sub_format.value.lower():
                return sub_format
            
            if sub_format.name.lower() in name:
                return sub_format
            
            if sub_format.value.lower() in name:
                return sub_format
            
        return ValueError(f'Unknwon subtitle format: {format}.')
    
    def get_file_ending(format) -> SubtitleFileEndings:
        match format.name.upper():
            case 'SRT':
                return SubtitleFileEndings.SRT
            case 'ASS':
                return SubtitleFileEndings.ASS
            case 'SSA':
                return SubtitleFileEndings.SSA
            case 'SUB':
                return SubtitleFileEndings.SUB
            case 'JSON':
                return SubtitleFileEndings.JSON
            case 'MPL2':
                return SubtitleFileEndings.MPL2
            case 'TMP':
                return SubtitleFileEndings.TMP
            case 'VTT':
                return SubtitleFileEndings.VTT
    