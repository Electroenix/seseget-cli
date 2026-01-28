import argparse

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from seseget.metadata.comic import ComicMetaData
from seseget.metadata.comic.cbz import make_cbz_comic_info_xml
from seseget.utils.trace import logger


if __name__ == "__main__":
    paser = argparse.ArgumentParser()
    paser.add_argument("-f", "--format", default="", help="元数据文件对应格式，如 nfo / vsmeta / cbz / epub")
    paser.add_argument("-s", "--series", default="", help="")
    paser.add_argument("-t", "--title", default="", help="")
    paser.add_argument("-n", "--number", default="", help="")
    paser.add_argument("-c", "--creator", default="", help="")
    paser.add_argument("-p", "--publisher", default="", help="")
    paser.add_argument("-d", "--data", default="", help="")
    paser.add_argument("--description", default="", help="")
    paser.add_argument("-l", "--language", default="", help="")
    paser.add_argument("--tag", nargs="+", default="", help="")
    paser.add_argument("-o", "--outpath", default=".", help="输出目录")

    args = paser.parse_args()
    if args.format == "cbz":
        metadata = ComicMetaData()
        metadata.series = args.series
        metadata.title = args.title
        metadata.number = args.number
        metadata.creator = args.creator
        metadata.publisher = args.publisher
        metadata.year = args.data[:4]
        metadata.month = args.data[4:6]
        metadata.day = args.data[6:8]
        metadata.description = args.description
        metadata.language = args.language
        metadata.subjects = args.tag

        make_cbz_comic_info_xml(args.outpath, metadata)
    else:
        logger.error(f"invalid format: {args.format}")
