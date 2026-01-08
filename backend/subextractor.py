import os
from threading import Thread
import json
import subprocess
from datetime import datetime
from pathlib import Path
from config import Config
import time


class SubExtractor:
    def __init__(self, file_path: str, sub_dir: Path):
        self.file_path = file_path
        self.config = Config()
        self.continue_flag = None
        self.sub_dir = sub_dir
        self.subtitle_counter = 0
        self.probe = None
        self.subtitle_languages = []

    def start(self):
        self.__extract_metadata()
        self.__extract_sup_subtitles()
        self.__extract_sub_subtitles()
        self.__extract_srt_subtitles()

    def __extract_metadata(self):
        self.probe = os.popen(f"ffprobe \"{self.file_path}\" -of json -show_entries format:stream").read()
        self.probe = json.loads(self.probe)

        self.subtitle_languages = []
        metadata_file = str(Path(self.config.get_datadir(), "metadata.txt"))

        command = [
            "ffmpeg", "-i", self.file_path,
            "-map", "0:s?", "-c", "copy", "-y",
            "-f", "ffmetadata", metadata_file
        ]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, text=True)

        for line in iter(process.stderr.readline, ''):
            passed_time = self.__get_seconds_progress_from_ffmpeg_output(line)
            if passed_time > 0:
                process.communicate('q')
                break

        time.sleep(1)

        with open(metadata_file, "r") as file:
            metadata = file.read()
            metadata = metadata.splitlines()
            languages = [line for line in metadata if "language" in line]
            self.subtitle_languages = [line.split("=")[1] for line in languages]
        os.remove(metadata_file)

    def __get_seconds_progress_from_ffmpeg_output(self, line: str) -> float:
        start_time = datetime(1900, 1, 1)
        line = line.strip()

        if "time=" in line:
            line = line.split("time=")[1]
            line = line.split(" bitrate=")[0]
            line = line.strip()
            
            if 'N/A' in line:
                return -1
            if line.startswith('-'):
                line = "00:00:00.000"
            
            subtitle_time = line.split('.')[0]
            subtitle_time = datetime.strptime(subtitle_time, "%H:%M:%S")
            subtitle_time = subtitle_time - start_time
            
            return subtitle_time.total_seconds()
        
        return -1
    

    def __get_progress_from_mkvextract_output(self, line: str) -> float:
        line = line.strip()

        if ":" in line:
            line = line.split(":")[1]
            line = line.split("%")[0]
            line = line.strip()
            
            if 'N/A' in line:
                return -1
            if line.startswith('-'):
                line = "00:00:00.000"
            
            return float(line)
        
        return -1


    # helper function for threading
    def __extract(self, file_id: int, track_id: int, file_ending: str, times: list[int], finished: list[bool]):
        file_path = Path(self.sub_dir, f"{file_id}.{file_ending}")
        
        if file_ending in ['sup', 'srt']:
            command = [
                "ffmpeg",
                "-y",
                "-i", self.file_path,
                "-map", f"0:s:{track_id}",
                "-c", "copy",
                str(file_path)
            ]

        elif file_ending == 'sub':
            command = [
                'mkvextract',
                'tracks',
                self.file_path,
                f'{track_id}:{str(file_path)}'
            ]

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        for line in iter(process.stderr.readline, ''):
            if file_ending == 'sup':
                times[file_id] = self.__get_seconds_progress_from_ffmpeg_output(line)
            elif file_ending == 'sub':
                # TODO: instead of percentage put time in list
                times[file_id] = self.__get_progress_from_mkvextract_output(line)

        process.wait()
        finished[file_id] = True


    def calculate_subtitle_duration(self, start_time: datetime, subtitle: dict) -> float:
        if 'tags' in subtitle and any('duration' in key.lower() for key in subtitle['tags']):
            subtitle_time_key = [key for key in subtitle['tags'] if 'duration' in key.lower()][0]
            subtitle_time = subtitle['tags'][subtitle_time_key]
            subtitle_time = subtitle_time.split('.')[0]  # remove milliseconds
            subtitle_time = subtitle_time.split(',')[0]  # remove milliseconds (if comma is used instead of dot)
            subtitle_time = datetime.strptime(subtitle_time, "%H:%M:%S")
            subtitle_time = subtitle_time - start_time
            subtitle_time = subtitle_time.total_seconds()
        else:
            subtitle_time = 0.0
            
        return subtitle_time


    def __extract_sup_subtitles(self) -> list[int]:
        thread_pool = []

        if self.continue_flag is False:
            return

        subtitle_streams = [stream for stream in self.probe['streams'] if stream['codec_name'] == 'hdmv_pgs_subtitle']
        total_time = 0
        current_times = []
        finished = []
        start_time = datetime(1900, 1, 1)

        if not os.path.exists(self.sub_dir):
            self.sub_dir.mkdir(parents=True, exist_ok=True)
            
        for i, subtitle in enumerate(subtitle_streams):

            # calculate total timelength of subtitles
            subtitle_time = self.calculate_subtitle_duration(start_time, subtitle)
            total_time += subtitle_time

            self.subtitle_counter += 1

            # skip if subtitle already exists
            if os.path.exists(str(self.sub_dir / f'{self.subtitle_counter - 1}.sup')):
                continue
            
            current_times.append(0)
            thread = Thread(name=f"Extract subtitle #{i}", target=self.__extract, args=(i, i, 'sup', current_times, finished))
            finished.append(False)
            thread.start()
            thread_pool.append(thread)

        for thread in thread_pool:
            thread.join()


    def __extract_sub_subtitles(self) -> list[int]:
        thread_pool = []

        if self.continue_flag is False:
            return

        subtitle_streams = [stream for stream in self.probe['streams'] if stream['codec_name'] == 'dvd_subtitle']
        total_time = 0
        current_times = []
        finished = []
        start_time = datetime(1900, 1, 1)

        if not os.path.exists(self.sub_dir):
            self.sub_dir.mkdir(parents=True, exist_ok=True)

        for i, subtitle in enumerate(subtitle_streams):
            index = subtitle['index']

            # calculate total timelength of subtitles
            subtitle_time = self.calculate_subtitle_duration(start_time, subtitle)
            total_time += subtitle_time

            self.subtitle_counter += 1

            # skip if subtitle already exists
            if os.path.exists(str(self.sub_dir / f'{index}.sub')):
                continue
            
            current_times.append(0)
            # TODO: Fix IndexError
            thread = Thread(name=f"Extract subtitle #{i}", target=self.__extract, args=(i, index, 'sub', current_times, finished))
            finished.append(False)
            thread.start()
            thread_pool.append(thread)

        for thread in thread_pool:
            thread.join()


    def __extract_srt_subtitles(self) -> list[int]:
        thread_pool = []

        if self.continue_flag is False:
            return

        subtitle_streams = [stream for stream in self.probe['streams'] if stream['codec_name'] == 'subrip']
        total_time = 0
        current_times = []
        finished = []
        start_time = datetime(1900, 1, 1)

        if not os.path.exists(self.sub_dir):
            self.sub_dir.mkdir(parents=True, exist_ok=True)
            
        for i, subtitle in enumerate(subtitle_streams):

            # calculate total timelength of subtitles
            subtitle_time = self.calculate_subtitle_duration(start_time, subtitle)
            total_time += subtitle_time

            self.subtitle_counter += 1

            # skip if subtitle already exists
            if os.path.exists(str(self.sub_dir / f'{self.subtitle_counter - 1}.srt')):
                continue
            
            current_times.append(0)
            thread = Thread(name=f"Extract subtitle #{i}", target=self.__extract, args=(i, i, 'srt', current_times, finished))
            finished.append(False)
            thread.start()
            thread_pool.append(thread)

        for thread in thread_pool:
            thread.join()
