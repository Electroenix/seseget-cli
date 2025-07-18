import sys
import shutil
import threading

from core.config.path import BASE_DIR
from core.utils.trace import *
from core.config.config_manager import config
from core.utils.file_utils import make_filename_valid
from core.utils.subprocess_utils import exec_cmd
from core.metadata.comic import ComicInfo, ComicMetaData, update_metadate
from core.metadata.video import VideoInfo

kcc_c2e_path = BASE_DIR / "core/thirdparty/kcc/kcc-c2e.py"  # kcc_c2e转换工具路径
kcc_lock = threading.Lock()  # 避免KCC运行时冲突


def create_source_info_file(save_dir, resource_info):
    """创建保存下载资源的来源信息的文件"""
    if config["download"]["save_resource_info"]:
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


def comic_to_epub(file_name: str, image_path: str, metadata: ComicMetaData):
    """
    下载的漫画图片合成EPUB电子书文件
    Args:
        file_name: 合成的EPUB文件名，如”xxxx.epub“
        image_path: 图片文件夹路径
        metadata: 漫画元数据对象

    """
    SESE_PRINT("kcc-c2e开始转换epub...")

    with kcc_lock:
        # 调用kcc-c2e转换图片为epub格式
        exec_cmd([sys.executable, kcc_c2e_path, image_path, "-t", make_filename_valid(metadata.title),
                  "-f", "KFX", "-o", file_name, "-m", "--forcecolor", "-n"])

    # 更新epub中的metadata
    update_metadate(file_name, file_name, metadata)
    SESE_PRINT("转换完成, 漫画保存在%s" % file_name)

    # 删除图片文件夹
    if not config["download"]["comic"]["leave_images"]:
        shutil.rmtree(image_path)
        SESE_PRINT('已删除图片缓存')