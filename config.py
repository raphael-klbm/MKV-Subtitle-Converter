__version__ = "v1.4.1"

import configparser
from enum import Enum
import gettext
import os
from babel import Locale
import sys
from pathlib import Path
import logging
from datetime import datetime
from controller.sub_formats import SubtitleFormats
import darkdetect

class Config:
    class Settings(Enum):
        CHECK_FOR_UPDATES = 'bUpdates'
        LANGUAGE = 'sLanguage'
        FIRST_START = 'bFirstStart'
        THEME = 'sTheme'

    
    config = None
    _new_config = None

    def __new__(cls, *args, **kwargs):
        if not cls.config:
            cls.config = super(Config, cls).__new__(cls, *args, **kwargs)
            cls.config._initialize_config()
        return cls.config

    def _initialize_config(self):
        self.config_path = str(self.get_datadir() / 'config.ini')
        self.config = configparser.ConfigParser()
        self.config.read(self.config_path)
        self.create_default_config()
        self._new_config.read(self.config_path)
        self.save_config()

        self.logger = self.create_logger()

        language: str = self.get_value(self.Settings.LANGUAGE) # get the language set in the config
        self.translation = gettext.translation('messages', self.get_resource_path('languages'), [language, 'en_US'], fallback=True)
        self.translation.install()
        
    def create_default_config(self):
        settings = {}
        settings[self.Settings.CHECK_FOR_UPDATES] = True
        settings[self.Settings.LANGUAGE] = 'en_US'
        settings[self.Settings.FIRST_START] = True
        settings[self.Settings.THEME] = 'Light'

        self.save_settings(settings)


    def check_for_updates(self):        
        if self.get_value(self.Settings.FIRST_START):
            return False
        
        return self.get_value(self.Settings.CHECK_FOR_UPDATES)

    def save_settings(self, settings: dict[Settings]):

        # Make changes to the config without saving the file
        if self._new_config is None:
            self._new_config = configparser.ConfigParser()
            self._new_config.optionxform = str
            self._new_config.read(self.config_path)

        if not os.path.exists(self.config_path):
            for setting in self.Settings:
                section = self._get_section(setting)
                if not self._new_config.has_section(section):
                    self._new_config.add_section(section)
                self._new_config.set(section, setting.value, self._convert_value_to_config_value(setting, settings[setting]))
        else:
            # check if there are any changes
            if all(self.get_value(setting) == settings[setting] for setting in settings):
                return
        
        for setting in settings:
            section = self._get_section(setting)
            value = self._convert_value_to_config_value(setting, settings[setting])
            self._new_config.set(section, setting.value, value)

    def save_config(self):
        # Return if there are no changes
        if self._new_config is None:
            return
        
        # Save the config file with all the new changes
        with open(self.config_path, 'w') as configfile:
            self._new_config.write(configfile, False)

        # read the new config
        # TODO: just do _initialize_config() but there is currently a bug
        self.config = configparser.ConfigParser()
        self.config.read(self.config_path)

        language: str = self.get_value(self.Settings.LANGUAGE) # get the language set in the config
        self.translation = gettext.translation('messages', self.get_resource_path('languages'), [language, 'en_US'], fallback=True)
        self.translation.install()

        self._new_config = None

    def _convert_value_to_config_value(self, setting: Settings, value) -> str:
        match setting.value[0]:
            case 'b':
                return '1' if value else '0'
            case 's':
                return str(value)
            
    def _get_section(self, setting: Settings):
        config = {
            'General': ['bUpdates', 'sLanguage', 'sTheme'],
            'Misc': ['bFirstStart']
        }

        for section, settings in config.items():
            if setting.value in settings:
                return section
            
    def get_value(self, setting: Settings):
        value = self.config.get(self._get_section(setting), setting.value)

        match setting.value[0]:
            case 'b':
                return value == '1'
            case 's':
                return value

    def get_version(self):
        return __version__
    
    def translate(self, text: str):
        return self.translation.gettext(text)
    
    def get_language(self):
        lang_code = self.get_value(self.Settings.LANGUAGE)
        return Locale.parse(lang_code).get_display_name()
    
    def get_languages(self):
        lang_codes = [code.name for code in os.scandir(self.get_resource_path('languages')) if code.is_dir()]
        languages = [Locale.parse(code).get_display_name() for code in lang_codes]

        return languages

    def convert_language_to_code(self, language: str):
        if language.strip() == '':
            return 'en_US'
        
        lang_codes = [code.name for code in os.scandir(self.get_resource_path('languages')) if code.is_dir()]
        languages = [Locale.parse(code).get_display_name() for code in lang_codes]
        return lang_codes[languages.index(language)]
    
    def get_datadir(self) -> Path:
        """
        Returns a parent directory path
        where persistent application data can be stored.

        # Linux: ~/.local/share/MKV Subtitle Converter
        # macOS: ~/Library/Application Support/MKV Subtitle Converter
        # Windows: C:/Users/<USER>/AppData/Roaming/MKV Subtitle Converter
        """

        if sys.platform.startswith("win"):
            path = Path(os.getenv("LOCALAPPDATA"))
        elif sys.platform.startswith("darwin"):
            path = Path("~/Library/Application Support")
        else:
            # linux
            path = Path(os.path.expanduser(os.getenv("XDG_DATA_HOME", "~/.local/share")))

        path = path / "MKV Subtitle Converter"
        path.mkdir(parents=True, exist_ok=True)

        return path
    
    def get_resource_path(self, relative_path: str) -> str:
        """
        Get the absolute path to a resource file.
        It searches in common locations for development, installation, and packaging.
        """
        # Path for PyInstaller bundles
        if hasattr(sys, '_MEIPASS'):
            base_path = getattr(sys, '_MEIPASS')
            path = os.path.join(base_path, relative_path)
            if os.path.exists(path):
                return path

        # Path for local development (running from project root)
        # Assumes the script is run from the project root directory.
        path = os.path.join(os.path.dirname(__file__), relative_path)
        if os.path.exists(path):
            self.logger.debug(f"Found resource file (local): {path}")
            return path

        # Path for installation via pip/venv
        path = os.path.join(sys.prefix, "share", "mkv-subtitle-converter", relative_path)
        if os.path.exists(path):
            self.logger.debug(f"Found resource file (pip/venv): {path}")
            return path

        # Path for system-wide installation (e.g., Debian package)
        path = os.path.join("/usr/share/mkv-subtitle-converter", relative_path)
        if os.path.exists(path):
            self.logger.debug(f"Found resource file (system-wide): {path}")
            return path

        raise FileNotFoundError(f"Resource file not found: {relative_path}")
    
    def create_logger(self):
        self.logger = logging.getLogger(__name__)
        date = datetime.now().strftime('%Y-%m-%d %H.%M.%S')
        logs_dir = Path(self.get_datadir() / 'logs')
        # logs_dir = Path('logs')
        logs_dir.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(filename=str(logs_dir / f'{date}.log'), level=logging.DEBUG, format='[%(levelname)s] %(asctime)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        # logging.getLogger().addHandler(logging.StreamHandler())  # print logs to console
        self.logger.debug(f'Program started at {date}.')

        return self.logger
    
    def get_allowed_sub_formats(self) -> list[str]:
        return [sub_format.value for sub_format in SubtitleFormats]
    
    def get_theme(self):
        theme = self.get_value(self.Settings.THEME)

        if theme == 'Auto':
            theme = 'Dark' if darkdetect.isDark() else 'Light'

        return theme.lower()
