# source: https://github.com/EzraBC/pgsreader

import numpy as np
from PIL import Image
import cv2

class ImageMaker:

    def __init__(self, brighness_diff: float):
        self.brightness_diff = 255 * brighness_diff


    def read_rle_bytes(self, ods_bytes):

        pixels = []
        line_builder = []

        i = 0
        while i < len(ods_bytes):
            if ods_bytes[i]:
                incr = 1
                color = ods_bytes[i]
                length = 1
            else:
                check = ods_bytes[i+1]
                if check == 0:
                    incr = 2
                    color = 0
                    length = 0
                    pixels.append(line_builder)
                    line_builder = []
                elif check < 64:
                    incr = 2
                    color = 0
                    length = check
                elif check < 128:
                    incr = 3
                    color = 0
                    length = ((check - 64) << 8) + ods_bytes[i + 2]
                elif check < 192:
                    incr = 3
                    color = ods_bytes[min(i+2, len(ods_bytes)-1)]
                    length = check - 128
                else:
                    incr = 4
                    color = ods_bytes[i+3]
                    length = ((check - 192) << 8) + ods_bytes[i + 2]
            line_builder.extend([color]*length)
            i += incr

        # if line_builder:
        #     logging.error("RLE data ended before end of line was reached.")
        #     raise Exception("RLE data ended before end of line was reached.")

        return pixels
                            
    def ycbcr2rgb(self, ar):
        xform = np.array([[1, 0, 1.402], [1, -0.34414, -.71414], [1, 1.772, 0]]).T
        rgb = ar.astype(np.single)
        # Subtracting 128 from R & G channels
        rgb[:,[1,2]] -= 128
        rgb = rgb.dot(xform)
        np.clip(rgb, 0, 255, out=rgb)
        return np.uint8(rgb)

    def px_rgb_a(self, ods, pds, swap):
        px = self.read_rle_bytes(ods.img_data)
        px = np.array([[255]*(ods.width - len(l)) + l for l in px], dtype=np.uint8)
        
        # Extract the YCbCrA palette data, swapping channels if requested.
        if swap:
            ycbcr = np.array([(entry.Y, entry.Cb, entry.Cr) for entry in pds.palette])
        else:
            ycbcr = np.array([(entry.Y, entry.Cr, entry.Cb) for entry in pds.palette])
        
        rgb = self.ycbcr2rgb(ycbcr)
        
        # Separate the Alpha channel from the YCbCr palette data
        a = [entry.Alpha for entry in pds.palette]
        a = np.array([[a[x] for x in l] for l in px], dtype=np.uint8)

        return px, rgb, a

    def make_image(self, ods, pds, swap=False) -> np.ndarray:
        px, rgb, a = self.px_rgb_a(ods, pds, swap)
        
        rgb_img = rgb[px]
        rgba_img = np.dstack((rgb_img, a))  # combine RGB and A channels
        # img = Image.fromarray(rgba_img, mode='RGBA')

        return rgba_img