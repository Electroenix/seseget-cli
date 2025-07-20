import os
import sys
import shutil
import threading
import zipfile

from core.config.path import BASE_DIR
from core.utils.trace import *
from core.config.config_manager import config
from core.utils.file_utils import make_filename_valid
from core.utils.subprocess_utils import exec_cmd
from core.metadata.comic import ComicInfo, ComicMetaData, update_epub_metadate, make_cbz_comic_info_xml
from core.metadata.video import VideoInfo, VideoMetaData
from core.metadata.vsmeta import *
from core.metadata.nfo import *

kcc_c2e_path = BASE_DIR / "core/thirdparty/kcc/kcc-c2e.py"  # kcc_c2e转换工具路径
kcc_lock = threading.Lock()  # 避免KCC运行时冲突


def make_video_metadata_file(save_dir, video_name, metadata: VideoMetaData):
    metadata_file = config["download"]["video"]["metadata_file"]

    if metadata_file["nfo"]:
        nfo_path = save_dir + '/' + make_filename_valid('%s.nfo' % video_name)  # nfo文件保存路径
        make_nfo_file(nfo_path, metadata)

    if metadata_file["vsmeta"]:
        vsmeta_path = save_dir + '/' + make_filename_valid('%s.mp4.vsmeta' % video_name)  # vsmeta文件保存路径
        make_vsmeta_file(vsmeta_path, metadata)


def make_source_info_file(save_dir, resource_info):
    """创建保存下载资源的来源信息的文件"""
    if config["download"]["save_source_info"]:
        content = ""
        if isinstance(resource_info, VideoInfo):
            content = content + 'video url: %s\r\n' % resource_info.view_url
            content = content + 'thumbnail url: %s\r\n' % resource_info.thumbnail_url
            content = content + 'cover url: %s\r\n' % resource_info.cover_url
            content = content + 'download url: %s\r\n' % resource_info.download_url
        elif isinstance(resource_info, ComicInfo):
            content = "comic url: %s\r\n" % resource_info.view_url
        elif isinstance(resource_info, str):
            content = resource_info
        else:
            SESE_TRACE(LOG_WARNING, "Invalid resource_info!")
            return

        with open(save_dir + '/' + 'source.txt', 'wb') as f:
            f.write(content.encode())


def make_cbz(save_dir: str, comic_title: str, image_path: str, metadata: ComicMetaData):
    """
    下载的漫画图片合成CBZ文件
    Args:
        save_dir: 漫画保存的目录路径
        comic_title: 漫画名，基于此名字创建文件名
        image_path: 图片文件夹路径
        metadata: 漫画元数据对象

    """
    file_name = save_dir + "/" + comic_title + ".cbz"
    SESE_PRINT("打包图片为CBZ格式...")

    make_cbz_comic_info_xml(image_path, metadata)
    with zipfile.ZipFile(file_name, "w") as cbz:
        for root, dirs, files in os.walk(image_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, image_path)
                cbz.write(file_path, arcname)

    SESE_PRINT("打包完成, 漫画保存在%s" % file_name)


def make_epub(save_dir: str, comic_title: str, image_path: str, metadata: ComicMetaData):
    """
    下载的漫画图片合成EPUB电子书文件
    Args:
        save_dir: 漫画保存的目录路径
        comic_title: 漫画名，基于此名字创建文件名
        image_path: 图片文件夹路径
        metadata: 漫画元数据对象

    """
    file_name = save_dir + "/" + comic_title + ".epub"
    SESE_PRINT("kcc-c2e开始转换epub...")

    with kcc_lock:
        # 调用kcc-c2e转换图片为epub格式
        exec_cmd([sys.executable, kcc_c2e_path, image_path, "-t", make_filename_valid(metadata.title),
                  "-f", "KFX", "-o", file_name, "-m", "--forcecolor", "-n"])

    # 更新epub中的metadata
    update_epub_metadate(file_name, file_name, metadata)
    SESE_PRINT("转换完成, 漫画保存在%s" % file_name)


def make_comic(save_dir: str, comic_title: str, image_path: str, metadata: ComicMetaData):
    comic_format = config["download"]["comic"]["format"]
    try:
        if comic_format.lower() == "epub".lower():
            make_epub(save_dir, comic_title, image_path, metadata)
        elif comic_format.lower() == "cbz".lower():
            make_cbz(save_dir, comic_title, image_path, metadata)
        else:
            raise ValueError(f"Invalid comic format: {comic_format}! Please check your config.")

    except Exception as e:
        raise

    finally:
        # 删除图片文件夹
        if not config["download"]["comic"]["leave_images"]:
            shutil.rmtree(image_path)
            SESE_PRINT('已删除图片缓存')
