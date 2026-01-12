from threading import Thread
import backend.helper as subhelper
import os
import pytesseract
import backend.pgs.pgsreader as pgsreader
from backend.pgs.imagemaker import ImageMaker
from tqdm import tqdm
from pysrt import SubRipFile, SubRipItem, SubRipTime
import backend.srtchecker as srtchecker
import pysubs2
from controller.sub_formats import SubtitleFileEndings
from config import Config
from backend.vob.vob_sub_parser import VobSubParser
from backend.vob.vob_sub_merge_pack import VobSubMergedPack
from pathlib import Path
import numpy as np
from PIL import Image
from datetime import timedelta


class SubtitleConverter:
    def __init__(self, subtitle_counter: int, sub_langs: list, diff_langs: dict, sub_dir: str, img_dir: str, sub_format: SubtitleFileEndings, keep_imgs: bool, text_brightness_diff: float):
        self.subtitle_counter = subtitle_counter
        self.subtitle_languages = sub_langs
        self.diff_langs = diff_langs
        self.sub_dir = sub_dir
        self.img_dir = img_dir
        self.format = sub_format
        self.keep_imgs = keep_imgs
        self.text_brightness_diff = text_brightness_diff

        self.continue_flag = None
        self.config = Config()
        self.translate = self.config.translate

    def convert_subtitles(self): # convert PGS subtitles to SRT subtitles
        thread_pool = []

        if self.continue_flag is False:
            return

        for id in range(self.subtitle_counter):

            # get language to use in subtitle
            lang_code = self.subtitle_languages[id]
            language = self.__get_lang(lang_code)

            if os.path.exists(os.path.join(self.sub_dir, f'{id}.sup')):
                thread = Thread(name=f"Convert subtitle #{id}", target=self.__convert_sup_to_srt, args=(language, id))
                thread.start()
                thread_pool.append(thread)
            elif os.path.exists(os.path.join(self.sub_dir, f'{id}.sub')):
                thread = Thread(name=f"Convert subtitle #{id}", target=self.__convert_sub_to_srt, args=(language, id))
                thread.start()
                thread_pool.append(thread)

        for thread in thread_pool:
            thread.join()

        if pgsreader.exit_code != 0:
            self.config.logger.error(f'Error while converting subtitle #{id}. See messages before for more information.')
            raise Exception(self.translate("Error while converting subtitle #{id}. See logs for more info.").format(id=id))
            # TODO Print error message by exit code, therefore check which warnings trigger exceptions

        # no multithreading here because it's already fast enough
        if self.format != SubtitleFileEndings.SRT.value:
            for id in range(self.subtitle_counter):
                new_sub = pysubs2.load(os.path.join(self.sub_dir, f'{id}.srt'))
                open(os.path.join(self.sub_dir, f'{id}.{self.format}'), 'w').close()
                new_sub.save(os.path.join(self.sub_dir, f'{id}.{self.format}'))

    def __get_lang(self, lang_code: str) -> str | None:

        lang_code = subhelper.convert_language(lang_code)
        new_lang = self.diff_langs.get(lang_code) # check if user wants to use a different language

        if new_lang is  not None:
            if new_lang in pytesseract.get_languages():
                return new_lang
            else:
                self.config.logger.warning(f'Language "{new_lang}" is not installed, using "{lang_code}" instead.')

        if lang_code in pytesseract.get_languages(): # when user doesn't want to change language or changed language is not installed
            return lang_code
        else:
            self.config.logger.warning(f'Language "{lang_code}" is not installed, using English instead.')
            return None

    def __convert_sup_to_srt(self, lang:str, track_id: int):
        srt_file = os.path.join(self.sub_dir, f'{track_id}.srt')
        pgs_file = os.path.join(self.sub_dir, f'{track_id}.sup')

        # extracted subtitle was already srt
        if (not os.path.exists(pgs_file)) and os.path.exists(srt_file):
            return 

        open(srt_file, "w").close() # create empty SRT file

        pgs = pgsreader.PGSReader(pgs_file)
        srt = SubRipFile()
        
        if self.keep_imgs:
            track_img_dir = self.img_dir / str(track_id)
            track_img_dir.mkdir(parents=True, exist_ok=True)

        # loading DisplaySets
        all_sets = [ds for ds in tqdm(pgs.iter_displaysets(), unit=" ds")]

        if pgsreader.exit_code != 0:
            return
        
        if self.continue_flag is False:
            return

        # building SRT file from DisplaySets
        sub_text = ""
        sub_start = 0
        sub_index = 0
        im = ImageMaker(self.text_brightness_diff)
        progress_bar = tqdm(all_sets, unit=" ds")
        for ds in progress_bar:
            if ds.has_image:
                pds = ds.pds[0] # get Palette Definition Segment
                ods = ds.ods[0] # get Object Definition Segment
                img = im.make_image(ods, pds)

                # TODO add exit code check for ImageMaker
                
                if self.keep_imgs:
                    img.save(os.path.join(track_img_dir, f"{sub_index}.jpg"))
                
                sub_text = pytesseract.image_to_string(img, lang)
                sub_start = ods.presentation_timestamp
            else:
                start_time = SubRipTime(milliseconds=int(sub_start))
                end_time = SubRipTime(milliseconds=int(ds.end[0].presentation_timestamp))
                srt.append(SubRipItem(sub_index, start_time, end_time, sub_text))
                sub_index += 1

        self.config.logger.debug(f'Finished converting subtitle #{track_id} in {int(progress_bar.format_dict["elapsed"])}s.')
        srt.save(srt_file) # save as SRT file

        # remove \f and new double empty lines from file
        # with open(srt_file, "r") as file:
        #     content = file.read()

        # content = content.replace("\f", "\n")
        # content = re.sub(r'\n\s*\n', '\n\n', content)

        # with open(srt_file, "w") as file:
        #     file.write(content)

        srtchecker.check_srt(srt_file, True) # check SRT file for common OCR mistakes


    def process_pack(self, pack: VobSubMergedPack, palette: list[str]) -> tuple[Path, Image.Image]:
        img = self.extract_subtitle_image_from_pack(pack, palette)
        img = Image.fromarray((img * 255).astype('uint8'), 'RGBA')
        img = img.convert('RGB')

        scale = 1
        padding = 25
        
        img = img.resize((img.width*scale, img.height*scale), Image.NEAREST)

        # add padding to image so text is not at the edge to improve OCR
        width, height = img.size
        new_width = width + 2*padding
        new_height = height + 2*padding

        new_img = Image.new(img.mode, (new_width, new_height), (0, 0, 0))
        new_img.paste(img, (padding, padding))
        img = new_img

        subfile_text = self.create_subfile_text(pack)
        return subfile_text, img

    def create_subfile_text(self, pack: VobSubMergedPack):
        # result = f"{pack_id + 1}\n" + \
        #     f"{pack.start_time.get_str_format()} --> {pack.end_time.get_str_format()}\n" + \
        #     f"{image_path}\n\n"
        # print(result)

        result = (pack.start_time / timedelta(seconds=1), pack.end_time / timedelta(seconds=1))
        return result


    def extract_subtitle_image_from_pack(self, pack: VobSubMergedPack, palette: list[str]) -> np.ndarray :
        pack.palette = palette
        img = pack.get_bitmap()
        # Resize image to make sure we don't keep large empty space
        # if more pixels are 1 instead of 0, use img < 1 instead of img > 0 to find the area with content
        if np.mean(img) > 0.5:
            x, y, _ = np.where(img < 1)
        else:
            x, y, _ = np.where(img > 0)
        img = img[max(np.min(x), 0):np.max(x), max(np.min(y), 0): np.max(y)]
        return img

    
    def __convert_sub_to_srt(self, lang:str, track_id: int):
        sub_file = os.path.join(self.sub_dir, f'{track_id}.sub')
        idx_file = os.path.join(self.sub_dir, f'{track_id}.idx')
        srt_file = os.path.join(self.sub_dir, f'{track_id}.srt')

        # extracted subtitle was already srt
        if (not os.path.exists(sub_file)) and os.path.exists(srt_file):
            return

        open(srt_file, "w").close() # create empty SRT file

        vob_sub_parser = VobSubParser(True)
        srt = SubRipFile()
        
        if self.keep_imgs:
            track_img_dir = self.img_dir / str(track_id)
            track_img_dir.mkdir(parents=True, exist_ok=True)

        vob_sub_parser.open_sub_idx(str(sub_file), str(idx_file))
        _vob_sub_merged_pack_list = vob_sub_parser.merge_vob_sub_packs()
        _palette = vob_sub_parser.idx_palette
        
        if self.continue_flag is False:
            return

        # building SRT file from DisplaySets
        sub_text = ""
        sub_start = 0
        sub_index = 0

        for pack in tqdm(_vob_sub_merged_pack_list):
            subfile_text, img = self.process_pack(pack, _palette)
            sub_start, sub_end = subfile_text
            
            if self.keep_imgs:
                img.save(os.path.join(track_img_dir, f"{sub_index}.jpg"))
            
            sub_text = pytesseract.image_to_string(img, lang)
            start_time = SubRipTime(seconds=sub_start)
            end_time = SubRipTime(seconds=sub_end)
            srt.append(SubRipItem(sub_index, start_time, end_time, sub_text))
            sub_index += 1

        # self.config.logger.debug(f'Finished converting subtitle #{track_id} in {int(progress_bar.format_dict["elapsed"])}s.')
        srt.save(srt_file) # save as SRT file

        # remove \f and new double empty lines from file
        # with open(srt_file, "r") as file:
        #     content = file.read()

        # content = content.replace("\f", "\n")
        # content = re.sub(r'\n\s*\n', '\n\n', content)

        # with open(srt_file, "w") as file:
        #     file.write(content)

        srtchecker.check_srt(srt_file, True) # check SRT file for common OCR mistakes
