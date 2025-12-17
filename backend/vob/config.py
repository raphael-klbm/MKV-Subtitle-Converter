from dataclasses import dataclass
from dataclasses import field

# Default settings found in SubTitle
@dataclass
class SettingsArgs:
    @dataclass
    class GeneralArgs:
        minimum_milliseconds_between_lines: int = 24
        subtitle_maximum_display_milliseconds: int = 8 * 1000

    general: GeneralArgs = field(default_factory=GeneralArgs)
