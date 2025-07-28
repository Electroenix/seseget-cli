import argparse

from core.config import init
from core.config import settings
from core.request.downloadtask import download_manager
from core.request.fetcher import FetcherRegistry

FetcherRegistry.discover(settings.SITE_FETCHERS_PACKAGE)
if __name__ == "__main__":
    paser = argparse.ArgumentParser()
    paser.add_argument("url", nargs="+", help="url，可接受多个url")
    paser.add_argument("-s", "--site", help="站点名，支持[bika/hanime/wnacg/bilibili/youtube/jmcomic]")
    paser.add_argument("-c", "--chapter", help="章节号，仅bika支持，指定下载章节号，多个章节请使用逗号分隔, 未指定章节则下载全部章节")

    args = paser.parse_args()
    urls = args.url
    site = args.site

    for url in urls:
        fetcher = FetcherRegistry.get_fetcher(site)
        if site == "bika":
            chapter = None
            if args.chapter:
                chapter = args.chapter.split(",")
            fetcher.download(url, chapter_id_list=chapter)
        else:
            fetcher.download(url)

    download_manager.wait_finish()
