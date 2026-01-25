from ...config.config_manager import config
from ...utils.file_utils import make_filename_valid
from .vsmeta import make_vsmeta_file
from .nfo import make_nfo_file
from . import VideoMetaData


def make_video_metadata_file(save_dir, video_name, metadata: VideoMetaData):
    metadata_file = config["download"]["video"]["metadata_file"]

    if "nfo" in metadata_file:
        nfo_path = save_dir + '/' + make_filename_valid('%s.nfo' % video_name)  # nfo文件保存路径
        make_nfo_file(nfo_path, metadata)

    if "vsmeta" in metadata_file:
        vsmeta_path = save_dir + '/' + make_filename_valid('%s.mp4.vsmeta' % video_name)  # vsmeta文件保存路径
        make_vsmeta_file(vsmeta_path, metadata)
