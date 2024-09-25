from io import BytesIO
from typing import Optional

import colorama
from PIL import Image

from modules.http_calls import raw_get
from modules.useragent import fake_ua_android


class AsciiArt:
    def __init__(self):
        self.max_height = 40
        self.max_width = 80
        self.ascii_chars = ["B", "S", "8", "P", "o", "d", "u", "*", "+", ";", ":", ",", ".", " "]
        self.art: Optional[str] = None

    def print_art(self):
        print(self.art)

    def generate_ascii(self, url: str):
        headers = {"User-Agent": fake_ua_android()}
        r = raw_get(url, headers)
        image = Image.open(BytesIO(r))
        return self._convert_to_ascii_art(image)

    def _convert_to_ascii_art(self, image: Image):
        self.art = ''
        if image.width > image.height:
            w = min(self.max_width, image.width)
            h = int(image.height * self.max_height / image.width)
        else:
            h = min(self.max_height, image.height)
            w = int(image.width * self.max_width / image.height)
        image = image.resize((w, h), Image.Resampling.LANCZOS)
        gray = image.convert('L')
        ascii_img = []
        for i in range(h):
            ascii_row = []
            for j in range(w):
                if i == 0 and j == 0 and int(gray.getpixel((j, i))) <= 5:
                    self.ascii_chars.reverse()
                ascii_row.append(self.ascii_chars[int(gray.getpixel((j, i)) * (len(self.ascii_chars) - 1) / 255)])
            ascii_img.append(ascii_row)
        for row in ascii_img:
            n_row = ''.join(row)
            if n_row.strip():
                self.art += f'{colorama.Fore.LIGHTBLACK_EX}{n_row}' + '\n'
        self.art += colorama.Style.RESET_ALL
