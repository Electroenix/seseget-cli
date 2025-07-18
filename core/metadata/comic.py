import os
import argparse
import zipfile
from lxml import etree
from lxml.etree import QName
from tempfile import TemporaryDirectory
from core.utils.trace import *


class ComicMetaData:
    """comic元数据，以EPUB文件中元数据的标签命名"""
    def __init__(self):
        self.title = ""
        self.creator = ""
        self.publisher = ""
        self.date = ""
        self.description = ""
        self.language = ""
        self.subjects = []


class ChapterInfo:
    """漫画章节信息，存储章节名，章节号以及漫画元数据"""
    def __init__(self):
        self.title = ""
        self.id = 0
        self.metadata = ComicMetaData()

    def print_info(self):
        print("ChapterInfo:")
        print("\ttitle: ", end="")
        print(self.title)
        print("\tid: ", end="")
        print(self.id)
        print("\tmetadata.title: ", end="")
        print(self.metadata.title)
        print("\tmetadata.language: ", end="")
        print(self.metadata.language)
        print("\tmetadata.creator: ", end="")
        print(self.metadata.creator)
        print("\tmetadata.subjects: ", end="")
        print(self.metadata.subjects)
        print("\tmetadata.description: ", end="")
        print(self.metadata.description)

    
class ComicInfo:
    """完整的整部漫画的信息，包含系列名，作者，以及全部章节信息"""
    def __init__(self):
        self.view_url = ""
        self.cid = ""
        self.cover = ""
        self.series_title = ""  # 系列名
        self.author = ""  # 作者
        self.genres = []  # 标签
        self.description = ""
        self.chapter_list: list[ChapterInfo] = []  # 漫画列表，可能有多个章节，以列表形式存储

    def print_info(self):
        print("ComicInfo:")
        print("\tview_url: ", end="")
        print(self.view_url)
        print("\tcid: ", end="")
        print(self.cid)
        print("\tseries_title: ", end="")
        print(self.series_title)
        print("\tauthor: ", end="")
        print(self.author)
        print("\tgenres: ", end="")
        print(self.genres)
        print("\tchapter_list: ", end="")
        print(self.chapter_list)


# 更新epub文件中的metadata
def update_metadate(epub_path, output_path, metadata: ComicMetaData):
    with TemporaryDirectory() as extract_path:
        try:
            with zipfile.ZipFile(epub_path, 'r') as zf:
                zf.extractall(extract_path)

            opf_path = os.path.join(extract_path, "OEBPS", "content.opf")
            parser = etree.XMLParser(remove_blank_text=True)
            opf_tree = etree.parse(opf_path, parser)
            root_elem = opf_tree.getroot()

            # namespace
            nsmap = root_elem.nsmap
            ns = {
                'opf': 'http://www.idpf.org/2007/opf',
                'dc': 'http://purl.org/dc/elements/1.1/'
            }
            if None in nsmap:
                ns[None] = nsmap[None]

            metadata_dc = {
                "title": metadata.title,
                "creator": metadata.creator,
                "description": metadata.description,
                "language": metadata.language,
                "subject": metadata.subjects
            }

            metadata_elem = root_elem.find("opf:metadata", ns)
            for tag, value in metadata_dc.items():
                if value is None:
                    continue

                # 查找并删除已存在元素
                elem_list = metadata_elem.findall(f'dc:{tag}', ns)
                for elem in elem_list:
                    metadata_elem.remove(elem)

                tag_value_list = value if isinstance(value, list) else [value]

                for tag_value in tag_value_list:
                    elem = etree.SubElement(metadata_elem, QName(ns['dc'], tag))
                    elem.text = tag_value

            opf_tree.write(opf_path, encoding='utf-8', xml_declaration=True, pretty_print=True)

            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as new_zf:
                for root, _, files in os.walk(extract_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, extract_path)
                        new_zf.write(file_path, arcname)

        except Exception as e:
            SESE_TRACE(LOG_ERROR, f"更新EPUB元数据失败, info:{e}")
            if os.path.exists(output_path):
                os.remove(output_path)
            raise


if __name__ == "__main__":
    paser = argparse.ArgumentParser()
    paser.add_argument("file", help="epub file path")
    paser.add_argument("-o", "--output", help="output file path")
    paser.add_argument("-t", "--title", help="comic title")
    paser.add_argument("-a", "--author", help="comic author")
    paser.add_argument("-d", "--describe", help="comic describe")
    paser.add_argument("-l", "--language", help="comic language")
    paser.add_argument("-s", "--subjects", help="comic subject/tags, split with \",\"")

    args = paser.parse_args()

    comic_meta = ComicMetaData()
    comic_meta.title = args.title
    comic_meta.creator = args.author
    comic_meta.description = args.describe
    comic_meta.language = args.language
    comic_meta.subjects = args.subjects.split(",")
    output_file = args.output
    file_path = args.file

    if not output_file:
        output_file = "test.epub"

    print("input file: %s" % file_path)
    print("output file: %s" % output_file)
    print("title: %s" % comic_meta.title)
    print("author: %s" % comic_meta.creator)
    print("description: %s" % comic_meta.description)
    print("language: %s" % comic_meta.language)
    print("subjects: ", end="")
    for s in comic_meta.subjects:
        print("[%s], " % s, end="")
    print()

    update_metadate(file_path, output_file, comic_meta)
