# MKV-Subtitle-Converter

This program extracts all PGS subtitles (i.e .sup files) in a MKV file, converts them to text based subtitles (e.g. .srt, .ass, ...) using OCR and replace the old PGS subtitles with the newly created subtitle files. It also allows you to edit the subtitles before replacing them. \
Using text based subtitles instead of PGS subtitles is useful because they can be edited and are supported by more players.

## Requirements

- The program needs [Tesseract](https://github.com/tesseract-ocr/tesseract) to be installed to use OCR. If you use Windows, you also need to add the `Tesseract-OCR` folder to your PATH.
- To extract and replace the subtitles and create the new video file the program also needs [ffmpeg](https://www.ffmpeg.org/download.html).
- To extract and replace the subtitles of a DVD the program also needs [mkvextract](https://mkvtoolnix.download/).

## Tips

- For better OCR results you should download the language models for the languages of the subtitles. You can download them [here](https://tesseract-ocr.github.io/tessdoc/Data-Files.html). Simply put them in the `tessdata` folder.
- If a subtitle uses letters of a different language, e.g., an english subtitles uses letters like ä, ö or ü, using the german language model instead of the english model because the german model contains all letters that the english one has, plus these special letters. This can be done by entering the language codes like this after checking the sixth checkbox: `old -> new`. In this example it would be `eng -> ger`.
- You can select MKV files from different directories, just select the MKV files you want to use and browse to another directory to select the next files.
- If you do not want a subtitle in your new MKV file, you can delete the corresponding new file when editing them before muxing the new MKV file.

If you want to build the program yourself, you can run the command in the `build.txt` file.
