from typing import Callable

from ...config.config_manager import config
from ...metadata.video import VideoMetaData
from .nfo import write_nfo
from .vsmeta import write_vsmeta

# 视频元数据 writer 签名：save_dir, video_name, metadata
VideoMetadataWriter = Callable[[str, str, VideoMetaData], None]

VIDEO_METADATA_WRITERS: dict[str, VideoMetadataWriter] = {
    "nfo": write_nfo,
    "vsmeta": write_vsmeta,
}


def register_video_metadata_writer(format_name: str, writer: VideoMetadataWriter) -> None:
    """注册新的视频元数据格式。

    Args:
        format_name: 配置中使用的格式名，如 ``nfo``。
        writer: 接收 ``(save_dir, video_name, metadata)`` 的写文件函数，
            writer 自行负责最终文件名与后缀。
    """
    if format_name in VIDEO_METADATA_WRITERS:
        raise ValueError(f"视频元数据格式已注册: {format_name}")
    VIDEO_METADATA_WRITERS[format_name] = writer


def make_video_metadata_file(save_dir: str, video_name: str, metadata: VideoMetaData):
    """按注册表与配置生成视频元数据文件。"""
    metadata_file = config["download"]["video"]["metadata_file"]

    for format_name, writer in VIDEO_METADATA_WRITERS.items():
        if format_name in metadata_file:
            writer(save_dir, video_name, metadata)
