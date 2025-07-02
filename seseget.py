import argparse
from core.spiders import bika
from core.spiders import hanime
from core.spiders import wnacg
from core.spiders import bilibili
from core.spiders import youtube
from core.spiders import jmcomic
from core.config.settings import STATION
from core.utils.trace import *
from core.request.downloadtask import download_manager


# import core.utils.output_redirector  # noqa 重定向输出

# 日志配置
from core.utils import trace
trace.setup_logger()

# 创建系统目录
from core.config import path
path.mk_sys_dir()

if __name__ == "__main__":
    paser = argparse.ArgumentParser()
    paser.add_argument("url", help="source url")
    paser.add_argument("-o", "--output", help="下载目录")
    paser.add_argument("-s", "--station", help="站点名，支持[bika/hanime/wnacg/bilibili/youtube/jmcomic]")
    paser.add_argument("-c", "--chapter", help="章节号，仅bika支持，设置下载章节号，支持多个章节，使用逗号分隔", default="1")

    args = paser.parse_args()
    url = args.url
    station = args.station

    if station == STATION["哔咔"]:
        chapter = args.chapter.split(",")
        bika_context = bika.create_context()
        bika.download(bika_context, url, chapter)
    elif station == STATION["Hanime"]:
        hanime.download(url)
    elif station == STATION["绅士漫画"]:
        wnacg.download(url)
    elif station == STATION["bilibili"]:
        bilibili.download(url)
    elif station == STATION["Youtube"]:
        youtube.download(url)
    elif station == STATION["jmcomic"]:
        jmcomic.download(url)
    else:
        SESE_PRINT("unknown station: ", station)

    download_manager.wait_finish()
