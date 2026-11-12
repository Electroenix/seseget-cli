"""漫画成品打包。
"""

import os
from typing import Callable

from ...config.config_manager import config
from ...metadata.comic import ComicMetaData
from ...utils.trace import logger
from .cbz import write_cbz
from .epub import write_epub

# 漫画打包函数签名：save_dir, comic_title, image_path, metadata
ComicPackager = Callable[[str, str, str, ComicMetaData], None]

# 按配置中记录的格式名分发；新增格式时在此注册即可
COMIC_PACKAGERS: dict[str, ComicPackager] = {
    "epub": write_epub,
    "cbz": write_cbz,
}


def register_comic_packager(format_name: str, packager: ComicPackager) -> None:
    """注册新的漫画成品格式。

    Args:
        format_name: 配置中使用的格式名，如 ``cbz``。
        packager: 接收 ``(save_dir, comic_title, image_path, metadata)``
            的打包函数。
    """
    if format_name in COMIC_PACKAGERS:
        raise ValueError(f"漫画格式已注册: {format_name}")
    COMIC_PACKAGERS[format_name] = packager


def _configured_formats() -> list[str]:
    comic_format = config["download"]["comic"]["format"]
    return [name for name in COMIC_PACKAGERS if name in comic_format]


def comic_output_paths(save_dir: str, comic_title: str) -> list[str]:
    """返回当前配置下漫画成品的候选路径。"""
    return [
        os.path.join(save_dir, f"{comic_title}.{format_name}")
        for format_name in _configured_formats()
    ]


def comic_missing_formats(save_dir: str, comic_title: str) -> list[str]:
    """返回尚未生成的漫画成品格式。"""
    return [
        format_name
        for format_name in _configured_formats()
        if not os.path.exists(os.path.join(save_dir, f"{comic_title}.{format_name}"))
    ]


def package_comic(save_dir: str, comic_title: str, image_path: str, metadata: ComicMetaData):
    """按配置把图片目录打包为一种或多种漫画格式；已存在的格式不覆盖。"""
    missing = comic_missing_formats(save_dir, comic_title)
    if not missing:
        logger.warning(
            "漫画成品已存在，跳过打包: %s",
            ", ".join(comic_output_paths(save_dir, comic_title)),
        )
        return

    for format_name in missing:
        COMIC_PACKAGERS[format_name](save_dir, comic_title, image_path, metadata)
