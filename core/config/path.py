import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 配置文件路径
CONFIG_DIR = BASE_DIR / "conf"
CONFIG_PATH = str(CONFIG_DIR) + "/conf.yaml"
DEFAULT_CONFIG_PATH = BASE_DIR / "core/config/default_conf.yaml"

# 下载资源路径
DATA_DIR = BASE_DIR / "data"

# 哔咔资源路径
BIKA_DATA_LOCAL_DIR = str(DATA_DIR) + "/bika"

# Hanime.me资源路径
HANIME_DATA_LOCAL_DIR = str(DATA_DIR) + "/hanime"

# 绅士漫画资源路径
WNACG_DATA_LOCAL_DIR = str(DATA_DIR) + "/wnacg"

# bilibili资源路径
BILI_DATA_LOCAL_DIR = str(DATA_DIR) + "/bilibili"

# youtube资源路径
YOUTUBE_DATA_LOCAL_DIR = str(DATA_DIR) + "/youtube"

# jmcomic资源路径
JMCOMIC_DATA_LOCAL_DIR = str(DATA_DIR) + "/jmcomic"


# 创建目录
def mk_sys_dir():
    # 配置文件目录
    if not os.path.exists(CONFIG_DIR):
        os.mkdir(CONFIG_DIR)

    # 下载资源目录
    if not os.path.exists(DATA_DIR):
        os.mkdir(DATA_DIR)

    # 哔咔
    if not os.path.exists(BIKA_DATA_LOCAL_DIR):
        os.mkdir(BIKA_DATA_LOCAL_DIR)

    # Hanime.me
    if not os.path.exists(HANIME_DATA_LOCAL_DIR):
        os.mkdir(HANIME_DATA_LOCAL_DIR)

    # 绅士漫画
    if not os.path.exists(WNACG_DATA_LOCAL_DIR):
        os.mkdir(WNACG_DATA_LOCAL_DIR)

    # 哔哩哔哩
    if not os.path.exists(BILI_DATA_LOCAL_DIR):
        os.mkdir(BILI_DATA_LOCAL_DIR)

    # 油管
    if not os.path.exists(YOUTUBE_DATA_LOCAL_DIR):
        os.mkdir(YOUTUBE_DATA_LOCAL_DIR)

    # 禁漫
    if not os.path.exists(JMCOMIC_DATA_LOCAL_DIR):
        os.mkdir(JMCOMIC_DATA_LOCAL_DIR)
