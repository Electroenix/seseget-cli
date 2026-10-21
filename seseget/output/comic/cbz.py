import os
import zipfile

from ...metadata.comic import ComicMetaData
from .comic_info import write_comic_info_xml
from ...utils.trace import logger


def write_cbz(save_dir: str, comic_title: str, image_path: str, metadata: ComicMetaData):
    """将下载的漫画图片打包为 CBZ 文件。

    Args:
        save_dir: 漫画保存的目录路径
        comic_title: 漫画名，基于此名字创建文件名
        image_path: 图片文件夹路径
        metadata: 漫画元数据对象
    """
    file_name = save_dir + "/" + comic_title + ".cbz"
    logger.info("打包图片为CBZ格式...")

    write_comic_info_xml(image_path, metadata)
    with zipfile.ZipFile(file_name, "w") as cbz:
        for root, dirs, files in os.walk(image_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, image_path)
                cbz.write(file_path, arcname)

    logger.info("打包完成, 漫画保存在%s" % file_name)
