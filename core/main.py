import argparse
import signal
import time

from core.config import settings
from core.request.downloadtask import download_manager
from core.request.fetcher import FetcherRegistry
from core.request.seserequest import ss_session
from core.utils.trace import *


def process_worker():
    def handle_signal(signum, frame):
        SESE_PRINT("exiting...")
        # 终止所有线程
        download_manager.shutdown()
        # 关闭所有连接
        ss_session.close_all()
        exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    FetcherRegistry.discover(settings.SITE_FETCHERS_PACKAGE)

    paser = argparse.ArgumentParser()
    paser.add_argument("url", nargs="+", default="", help="url，可接受多个url")
    paser.add_argument("-s", "--site", default="", help="站点名，支持[bika/hanime/wnacg/bilibili/youtube/jmcomic]")
    paser.add_argument("-c", "--chapter", default="", help="章节号，指定漫画下载章节号，多个章节请使用逗号分隔, 未指定章节则下载全部章节")
    paser.add_argument("--no-download", default=False, action="store_true", help="不下载资源，仅显示资源信息")

    args = paser.parse_args()
    urls = args.url
    site = args.site
    no_download = args.no_download

    for url in urls:
        fetcher = FetcherRegistry.get_fetcher(site)
        SESE_TRACE(LOG_DEBUG, f"获取到Fetcher[{fetcher}]")
        if site == "bika" or \
           site == "jmcomic":
            chapter = [int(c) for c in (args.chapter.split(",") if args.chapter else [])]
            fetcher.download(url, chapter_id_list=chapter, no_download=no_download)
        else:
            fetcher.download(url, no_download=no_download)

    while not download_manager.all_done():
        time.sleep(1)
