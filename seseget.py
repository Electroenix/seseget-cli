import argparse
from core.spiders import bika
from core.spiders import hanime
from core.spiders import wnacg
from core.spiders import bilibili
from core.spiders import youtube
from core.spiders import jm_comic
from core.config.settings import STATION
from core.utils.trace import *
from core.request.downloadtask import download_manager
from core.config import path


if __name__ == "__main__":
    # 日志配置
    setup_logger()
    # 创建系统目录
    path.mk_sys_dir()

    paser = argparse.ArgumentParser()
    paser.add_argument("urls", nargs="+", help="url列表，可接受多个url")
    paser.add_argument("-s", "--station", help="站点名，支持[bika/hanime/wnacg/bilibili/youtube/jmcomic]")
    paser.add_argument("-c", "--chapter", help="章节号，仅bika支持，指定下载章节号，多个章节请使用逗号分隔, 未指定章节则下载全部章节")

    args = paser.parse_args()
    urls = args.urls
    station = args.station

    for url in urls:
        if station == STATION["bika"]:
            chapter = []
            if args.chapter:
                chapter = args.chapter.split(",")
            bika_context = bika.create_context()
            bika.download(bika_context, url, chapter)
        elif station == STATION["hanime"]:
            hanime.download(url)
        elif station == STATION["wnacg"]:
            wnacg.download(url)
        elif station == STATION["bilibili"]:
            bilibili.download(url)
        elif station == STATION["youtube"]:
            youtube.download(url)
        elif station == STATION["jmcomic"]:
            jm_comic.download(url)
        else:
            SESE_PRINT(f"unknown station: {station}")

    download_manager.wait_finish()
