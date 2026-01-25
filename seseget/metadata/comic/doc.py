from ...config.config_manager import config
from ...utils.trace import SESE_PRINT
from . import ComicMetaData
from .cbz import make_cbz
from .epub import make_epub


def make_comic(save_dir: str, comic_title: str, image_path: str, metadata: ComicMetaData):
    comic_format = config["download"]["comic"]["format"]
    try:
        if "epub" in comic_format:
            make_epub(save_dir, comic_title, image_path, metadata)

        if "cbz" in comic_format:
            make_cbz(save_dir, comic_title, image_path, metadata)

    except Exception as e:
        raise
