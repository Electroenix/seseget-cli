import argparse

from core.config import init
from core.config import settings
from core.request.downloadtask import download_manager
from core.request.fetcher import FetcherRegistry

FetcherRegistry.discover(settings.SITE_FETCHERS_PACKAGE)
if __name__ == "__main__":
    paser = argparse.ArgumentParser()
    paser.add_argument("url", nargs="+", default="", help="url，可接受多个url")
    paser.add_argument("-s", "--site", default="", help="站点名，支持[bika/hanime/wnacg/bilibili/youtube/jmcomic]")
    paser.add_argument("-c", "--chapter", default="", help="章节号，仅bika支持，指定下载章节号，多个章节请使用逗号分隔, 未指定章节则下载全部章节")
    paser.add_argument("--no-download", default=False, action="store_true", help="不下载资源，仅显示资源信息")

    args = paser.parse_args()
    urls = args.url
    site = args.site
    no_download = args.no_download

    for url in urls:
        fetcher = FetcherRegistry.get_fetcher(site)
        if site == "bika":
            chapter = args.chapter.split(",") if args.chapter else []
            fetcher.download(url, chapter_id_list=chapter, no_download=no_download)
        else:
            fetcher.download(url, no_download=no_download)

    download_manager.wait_finish()
