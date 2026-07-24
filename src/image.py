from pathlib import Path
from math import gcd

from PIL import Image as PILImage

class Image:
    def __init__(self, path: Path):
        self.path = path
        self._image = PILImage.open(self.path)
    
    def crop_to_portrait(self) -> bool:
        width, height = self._image.size

        target_ratio = 2 / 3
        current_ratio = width / height

        if current_ratio <= target_ratio:
            return False

        target_width = round(height * target_ratio)

        self._image = self._image.crop(
            (0, 0, target_width, height)
        )

        self._image.save(self.path)
        
        return True
    
    def close(self):
        self._image.close()