import os
import shutil
from config import Config
from controller.jobs import Jobs
from controller.sub_formats import SubtitleFormats, SubtitleFileEndings
import time
import subprocess
from backend.subextractor import SubExtractor
from backend.subconverter import SubtitleConverter
from pathlib import Path

class SubMain:

    def __init__(self, files: list = [], edit_flag: bool = False, keep_imgs: bool = False, keep_old_mkvs: bool = False, keep_old_subs: bool = False, keep_new_subs: bool = False, diff_langs: dict = {}, sub_format: SubtitleFormats = SubtitleFormats.SRT, text_brightness_diff: float = 0.1, shared_dict: dict = None):
        
        self.file_paths = files
        self.edit_flag = edit_flag
        self.keep_imgs = keep_imgs
        self.keep_old_mkvs = keep_old_mkvs
        self.keep_old_subs = keep_old_subs
        self.keep_new_subs = keep_new_subs
        self.diff_langs = diff_langs
        self.format = SubtitleFileEndings.get_format(sub_format.name).value
        self.text_brightness_diff = text_brightness_diff
        self.shared_dict = shared_dict

        self.config = Config()
        self.translate = self.config.translate

        self.shared_dict['finished_files_counter'] = 0
        self.shared_dict['files_with_error_counter'] = 0
        self.shared_dict['current_job'] = Jobs.IDLE

        self.shared_dict['error_code'] = 0
        self.shared_dict['error_message'] = ''

    # estimate new file size based on size of new subtitles
    def calc_size(self) -> int:
        file_size = os.path.getsize(self.file_path)
        new_size = file_size
        for track_id in range(self.subtitle_counter):
            path = os.path.join(self.sub_dir, str(track_id)) # path to subtitle file without extension

            new_size -= os.path.getsize(f"{path}.sup")

            if os.path.exists(f"{path}.{self.format}"):
                new_size += os.path.getsize(f"{path}.{self.format}")

        return new_size

    def mux_file(self):
        if self.shared_dict.get('continue_flag', None) is False:
            return

        self.config.logger.info(f'Muxing file {self.file_name}.')
        new_file_dir = os.path.dirname(self.file_path)
        new_file_path = Path(new_file_dir) / f"{self.file_name} (1).mkv"

        self.shared_dict['current_job'] = Jobs.MUXING

        ffmpeg_cmd = [
            "ffmpeg",
            "-i", self.file_path,
            "-y"
        ]

        # add new subtitles as inputs
        for track_id in range(self.subtitle_counter):
            sub_path = os.path.join(self.sub_dir, f"{track_id}.{self.format}")
            ffmpeg_cmd += ["-i", sub_path]

        # add video and audio streams to new file
        ffmpeg_cmd += ["-map", "0:v", "-map", "0:a"]

        # add new subtitles to the new file
        for i in range(self.subtitle_counter):
            ffmpeg_cmd += ["-map", f"{i + 1}:0"]

        # add metadata for new subtitles
        for i in range(self.subtitle_counter):
            lang = self.subtitle_languages[i]
            ffmpeg_cmd += ["-metadata:s:s:" + str(i), f"language={lang}"]

        # copy the codecs of video, audio and subtitle streams
        ffmpeg_cmd += ["-c", "copy", new_file_path]


        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        for line in iter(process.stderr.readline, ''):
            if "Timestamps are unset in a packet" in line:
                self.config.logger.warning(line + ". This may lead to a decreased playback performance.")

        process.wait()

    # remove file that may not exist anymore without throwing an error
    def silent_remove(self, file: str):
        try:
            os.remove(file)
        except OSError:
            pass

    def clean(self):
        new_file_dir = os.path.dirname(self.file_path)
        new_file_path = os.path.join(new_file_dir, f"{self.file_name} (1).mkv")

        self.config.logger.info("Cleaning up.")

        if not (self.keep_old_subs or self.keep_new_subs):
            if not self.keep_imgs:
                shutil.rmtree(self.img_dir.parent)
            else:
                shutil.rmtree(self.sub_dir)
        elif not self.keep_old_subs:
            for track_id in range(self.subtitle_counter):
                self.silent_remove(os.path.join(self.sub_dir, f'{track_id}.sup'))
        elif not self.keep_new_subs:
            for track_id in range(self.subtitle_counter):
                self.silent_remove(os.path.join(self.sub_dir, f'{track_id}.srt'))
                self.silent_remove(os.path.join(self.sub_dir, f'{track_id}.{self.format}'))

        if not self.keep_old_mkvs:
            os.remove(self.file_path)
            os.rename(new_file_path, self.file_path)

    def convert(self):
        self.shared_dict['continue_flag'] = None
        
        for self.file_path in self.file_paths:
            self.file_name = os.path.splitext(os.path.basename(self.file_path))[0]
            
            try:
                self.config.logger.info(f'Processing {self.file_name}.')

                main_dir_path = self.config.get_datadir() / 'subtitles' / self.file_name
                self.img_dir = main_dir_path / 'images'
                self.sub_dir = main_dir_path / 'subtitles'

                self.shared_dict['current_job'] = Jobs.EXTRACT
                self.config.logger.debug(f'Starting to extract subtitles.')

                extractor = SubExtractor(self.file_path, self.sub_dir)
                extractor.start()

                self.subtitle_counter = extractor.subtitle_counter
                self.subtitle_languages = extractor.subtitle_languages

                self.config.logger.debug(f'Finished extracting subtitles.')

                # skip title if no PGS subtitles were found
                if self.subtitle_counter == 0:
                    self.config.logger.info("No subtitles found.")
                    continue

                self.config.logger.debug(f'Starting to convert subtitles.')
                self.shared_dict['current_job'] = Jobs.CONVERT

                converter = SubtitleConverter(self.subtitle_counter, self.subtitle_languages, self.diff_langs, self.sub_dir, self.img_dir, self.format, self.keep_imgs, self.text_brightness_diff)
                converter.convert_subtitles()
                self.config.logger.debug(f'Finished converting subtitles.')

                self.shared_dict['edit_flag'] = self.edit_flag
                self.shared_dict['sub_dir'] = self.sub_dir

                if self.edit_flag:
                    self.config.logger.debug(f'Pause for editing subtitles in {self.sub_dir}.')
                    if os.name == "nt":
                        os.system(f"explorer.exe \"{os.path.join(os.getcwd(), self.sub_dir)}\"")
                    
                    while self.shared_dict.get('edit_flag', False) is not False:
                        time.sleep(1)

                    self.config.logger.debug(f'Continue after pausing for subtitle editing.')
                
                self.mux_file()
                self.clean()

                self.config.logger.info(f'Finished {self.file_name}.')
                self.shared_dict['finished_files_counter'] += 1
            except Exception as e:
                self.shared_dict['files_with_error_counter'] += 1
                self.shared_dict['error_code'] = 2
                self.shared_dict['error_message'] = self.translate('Error while processing {file_name}: {error}').format(file_name=self.file_name, error=e)
                self.config.logger.error(f'Error while processing {self.file_name}: {e}')

                # wait for user input to continue
                while self.shared_dict.get('continue_flag', None) is None:
                    time.sleep(1)

                if self.shared_dict.get('continue_flag', None):
                    self.config.logger.debug("Continuing with the next file after error.")
                    self.clean()
                else:
                    self.config.logger.debug("Exiting program after error.")
                    self.clean()
                    break

        self.shared_dict['current_job'] = Jobs.FINISHED
    
# ----------------FOR THE CONTROLLER----------------
    def set_continue_flag(self, flag: bool):
        self.shared_dict['continue_flag'] = flag
        self.reset_error_code()
    
    def reset_error_code(self):
        self.shared_dict['error_code'] = 0
        self.shared_dict['error_message'] = ''
