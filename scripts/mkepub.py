import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from seseget.metadata.comic import ComicMetaData
from seseget.metadata.comic.epub import EpubGenerator

if __name__ == "__main__":
    metadata = ComicMetaData()
    metadata.series = "系列"  # 系列名
    metadata.title = "标题"  # 章节名
    metadata.number = "章节号"  # 章节号
    metadata.creator = "作者"  # 作者
    metadata.publisher = "出版商"  # 出版商
    metadata.year = "26"  # 发布日期: 年
    metadata.month = "01"  # 发布日期: 月
    metadata.day = "24"  # 发布日期: 日
    metadata.description = "剧情简介"  # 剧情简介
    metadata.language = "ja"  # 语言
    metadata.subjects = ["标签1", "标签2", "标签3"]  # 标签
    IMAGE_DIR = ""

    paser = argparse.ArgumentParser()
    paser.add_argument("-i", "--input", default="", help="漫画图片目录")
    paser.add_argument("-o", "--output", default="", help="EPUB输出目录")

    args = paser.parse_args()
    epub = EpubGenerator(
        output_dir=args.output,
        image_dir=args.input,
        metadata=metadata
    )

    epub.generate()
