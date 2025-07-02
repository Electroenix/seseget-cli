import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
print("BASE_DIR:", BASE_DIR)

# 配置文件路径
config_path = BASE_DIR / "conf/conf.json"
default_config_path = BASE_DIR / "conf/default_conf.json"

# 下载资源路径
data_path = BASE_DIR / "data"

# 哔咔资源路径
bika_data_local_path = str(data_path) + "/bika"

# Hanime.me资源路径
hanime_data_local_path = str(data_path) + "/hanime"

# 绅士漫画资源路径
wnacg_data_local_path = str(data_path) + "/wnacg"

# bilibili资源路径
bili_data_local_path = str(data_path) + "/bilibili"

# youtube资源路径
youtube_data_local_path = str(data_path) + "/youtube"

# jmcomic资源路径
jmcomic_data_local_path = str(data_path) + "/jmcomic"


# 创建目录
def mk_sys_dir():
    # 下载资源目录
    if not os.path.exists(data_path):
        os.mkdir(data_path)

    # 哔咔
    if not os.path.exists(bika_data_local_path):
        os.mkdir(bika_data_local_path)

    # Hanime.me
    if not os.path.exists(hanime_data_local_path):
        os.mkdir(hanime_data_local_path)

    # 绅士漫画
    if not os.path.exists(wnacg_data_local_path):
        os.mkdir(wnacg_data_local_path)

    # 哔哩哔哩
    if not os.path.exists(bili_data_local_path):
        os.mkdir(bili_data_local_path)

    # 油管
    if not os.path.exists(youtube_data_local_path):
        os.mkdir(youtube_data_local_path)

    # 禁漫
    if not os.path.exists(jmcomic_data_local_path):
        os.mkdir(jmcomic_data_local_path)