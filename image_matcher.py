import os
import requests
from io import BytesIO
from PIL import Image
import imagehash
import config


class ImageMatcher:
    def __init__(self, log=print):
        self.log = log
        self.reference_hashes = []
        self._load_references()

    def _load_references(self):
        os.makedirs(config.REFERENCE_IMAGES_DIR, exist_ok=True)
        supported = ('.png', '.jpg', '.jpeg', '.webp', '.bmp')

        for filename in os.listdir(config.REFERENCE_IMAGES_DIR):
            if not filename.lower().endswith(supported):
                continue
            filepath = os.path.join(config.REFERENCE_IMAGES_DIR, filename)
            try:
                img = Image.open(filepath).convert('RGB')
                h = imagehash.phash(img)
                self.reference_hashes.append((filename, h))
                self.log(f"  [ref] Loaded: {filename}")
            except Exception as e:
                self.log(f"  [ref] Failed to load {filename}: {e}")

    def _fetch_image(self, url):
        url = (url
               .replace('_normal.', '_400x400.')
               .replace('_bigger.', '_400x400.')
               .replace('_mini.', '_400x400.'))
        try:
            resp = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0'
            })
            resp.raise_for_status()
            return Image.open(BytesIO(resp.content)).convert('RGB')
        except Exception:
            return None

    def is_match(self, image_url):
        """Returns (matched: bool, reference_filename: str|None)"""
        if not self.reference_hashes:
            return False, None

        img = self._fetch_image(image_url)
        if img is None:
            return False, None

        try:
            img_hash = imagehash.phash(img)
            for ref_name, ref_hash in self.reference_hashes:
                distance = img_hash - ref_hash
                if distance <= config.HASH_THRESHOLD:
                    return True, ref_name
        except Exception:
            pass

        return False, None
