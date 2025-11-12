import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 配置文件路径
CONFIG_DIR = BASE_DIR / "conf"
CONFIG_PATH = str(CONFIG_DIR) + "/conf.yaml"
DEFAULT_CONFIG_PATH = BASE_DIR / "core/config/default_conf.yaml"

# 下载资源路径
DATA_DIR = str(BASE_DIR / "data")


# 创建目录
def mk_sys_dir():
    # 配置文件目录
    if not os.path.exists(CONFIG_DIR):
        os.mkdir(CONFIG_DIR)

    # 下载资源目录
    if not os.path.exists(DATA_DIR):
        os.mkdir(DATA_DIR)
