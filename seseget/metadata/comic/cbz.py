import os
import zipfile

from . import ComicMetaData
from ...utils.trace import SESE_TRACE, LOG_WARNING, SESE_PRINT


# 翻页方向: YesAndRightToLeft - 右至左    No - 左至右
MANGA_DIRECTION = "No"


def make_cbz_comic_info_xml(output_dir, metadata: ComicMetaData):
    output_path = output_dir + "/" + "ComicInfo.xml"

    with open(output_path, "w", encoding='utf-8') as f:
        f.write(f"""\
<?xml version='1.0' encoding='UTF-8'?>
<ComicInfo xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">""")

        # 系列
        if metadata.series:
            f.write(f"""
  <Series>{metadata.series}</Series>""")

        # 标题
        if metadata.title:
            f.write(f"""
  <Title>{metadata.title}</Title>""")

        # 编号
        if metadata.number:
            f.write(f"""
  <Number>{metadata.number}</Number>""")

        # 作者
        if metadata.creator:
            f.write(f"""
  <Writer>{metadata.creator}</Writer>""")

        # 简介
        if metadata.description:
            f.write(f"""
  <Summary>{metadata.description}</Summary>""")

        # 发布时间: 年
        if metadata.year:
            f.write(f"""
  <Year>{metadata.year}</Year>""")

        # 发布时间: 月
        if metadata.month:
            f.write(f"""
  <Month>{metadata.month}</Month>""")

        # 发布时间: 日
        if metadata.day:
            f.write(f"""
  <Day>{metadata.day}</Day>""")

        # 语言
        if metadata.language:
            f.write(f"""
  <LanguageISO>{metadata.language}</LanguageISO>""")

        # 标签
        if metadata.subjects:
            f.write(f"""
  <Tags>{",".join(metadata.subjects)}</Tags>""")

        # 翻页方向
        f.write(f"""
  <Manga>{MANGA_DIRECTION}</Manga>
</ComicInfo>""")


def make_cbz(save_dir: str, comic_title: str, image_path: str, metadata: ComicMetaData):
    """
    下载的漫画图片合成CBZ文件
    Args:
        save_dir: 漫画保存的目录路径
        comic_title: 漫画名，基于此名字创建文件名
        image_path: 图片文件夹路径
        metadata: 漫画元数据对象

    """
    file_name = save_dir + "/" + comic_title + ".cbz"
    SESE_PRINT("打包图片为CBZ格式...")

    make_cbz_comic_info_xml(image_path, metadata)
    with zipfile.ZipFile(file_name, "w") as cbz:
        for root, dirs, files in os.walk(image_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, image_path)
                cbz.write(file_path, arcname)

    SESE_PRINT("打包完成, 漫画保存在%s" % file_name)
