import argparse
import os

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from seseget.metadata.comic import ComicMetaData
from seseget.metadata.comic.cbz import make_cbz
from seseget.utils.file_utils import make_filename_valid

setup_logger()

if __name__ == "__main__":
    paser = argparse.ArgumentParser()
    paser.add_argument("-f", "--format", default="", help="漫画格式，如 cbz / epub")
    paser.add_argument("-s", "--series", default="", help="")
    paser.add_argument("-t", "--title", default="", help="")
    paser.add_argument("-n", "--number", default="", help="")
    paser.add_argument("-c", "--creator", default="", help="")
    paser.add_argument("-p", "--publisher", default="", help="")
    paser.add_argument("-d", "--data", default="", help="yyyyMMdd")
    paser.add_argument("--description", default="", help="")
    paser.add_argument("-l", "--language", default="", help="")
    paser.add_argument("--tag", nargs="+", default="", help="")
    paser.add_argument("-i", "--imagepath", default="", help="图片目录")
    paser.add_argument("-o", "--outpath", default=".", help="输出目录")

    args = paser.parse_args()
    if args.format == "cbz":
        metadata = ComicMetaData()
        metadata.series = args.series
        metadata.title = args.title if args.title else os.path.basename(args.imagepath)
        metadata.title = make_filename_valid(metadata.title)
        metadata.number = args.number
        metadata.creator = args.creator
        metadata.publisher = args.publisher
        if len(args.data) >= 8:
            metadata.year = args.data[:4]
            metadata.month = args.data[4:6]
            metadata.day = args.data[6:8]
        metadata.description = args.description
        metadata.language = args.language if args.language else "zh"
        metadata.subjects = args.tag

        print(f"title: {metadata.title}")
        print(f"imagepath: {args.imagepath}")
        if not os.path.exists(args.imagepath):
            print("目录不存在: {args.imagepath}")

        make_cbz(args.outpath, metadata.title, args.imagepath, metadata)
