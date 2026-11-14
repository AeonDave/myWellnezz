"""Download a logo image and render it as ASCII art for the dashboard header."""

from io import BytesIO

import httpx
from PIL import Image

from mywellnezz.api.client import ApiError, get_client

ASCII_CHARS = ['B', 'S', '8', 'P', 'o', 'd', 'u', '*', '+', ';', ':', ',', '.', ' ']


class AsciiArt:
    def __init__(self):
        self.max_height = 40
        self.max_width = 80
        self.ascii_chars = list(ASCII_CHARS)

    async def generate(self, url: str) -> str | None:
        """Download the image and return the ASCII art; ``None`` on failure."""
        client = await get_client()
        try:
            response = await client.get(url, headers={'User-Agent': 'myWellnezz'})
            response.raise_for_status()
            with Image.open(BytesIO(response.content)) as image:
                return self._convert(image)
        except (ApiError, httpx.HTTPError, OSError, ValueError):
            return None

    def _convert(self, image: Image.Image) -> str:
        if image.width > image.height:
            w = min(self.max_width, image.width)
            h = max(1, int(image.height * self.max_width / image.width))
        else:
            h = min(self.max_height, image.height)
            w = max(1, int(image.width * self.max_height / image.height))
        image = image.resize((w, h), Image.Resampling.LANCZOS)
        gray = image.convert('L')
        rows = []
        for i in range(h):
            row = []
            for j in range(w):
                pixel = int(gray.getpixel((j, i)))
                if i == 0 and j == 0 and pixel <= 5:
                    self.ascii_chars.reverse()
                row.append(self.ascii_chars[pixel * (len(self.ascii_chars) - 1) // 255])
            rows.append(''.join(row))
        return '\n'.join(r for r in rows if r.strip())
