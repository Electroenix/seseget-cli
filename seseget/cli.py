import argparse
import asyncio
import signal

from .request.downloadtask import download_manager
from .request.fetcher import FetcherRegistry
from .request.requests import session_manager
from .utils.trace import logger


async def process_worker_async():
    def handle_signal(signum, frame):
        logger.debug("收到退出信号")
        asyncio.ensure_future(cleanup())

    async def cleanup():
        logger.info("cleaning...")
        await download_manager.shutdown()
        await session_manager.close_all()
        logger.info("clean OK, Exit!")

    signal.signal(signal.SIGINT, handle_signal)

    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="+", default="", help="url，可接受多个url")
    parser.add_argument("-s", "--site", default="", help=f"站点名，支持{FetcherRegistry.list_sites()}")
    parser.add_argument("-c", "--chapter", default="", help="章节号，指定漫画下载章节号，多个章节请使用逗号分隔, 未指定章节则下载全部章节")
    parser.add_argument("--no-download", default=False, action="store_true", help="不下载资源，仅显示资源信息")

    args = parser.parse_args()
    urls = args.url
    site = args.site
    no_download = args.no_download

    for url in urls:
        fetcher = FetcherRegistry.get_fetcher(site)
        logger.debug(f"获取到Fetcher[{fetcher}]")
        if site in ("bika", "jmcomic"):
            chapter = [int(c) for c in (args.chapter.split(",") if args.chapter else [])]
            await fetcher.download(url, chapter_id_list=chapter, no_download=no_download)
        else:
            await fetcher.download(url, no_download=no_download)

    await download_manager.wait_all()
    await session_manager.close_all()


def main():
    try:
        asyncio.run(process_worker_async())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
