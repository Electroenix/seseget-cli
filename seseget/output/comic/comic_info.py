"""ComicInfo.xml 元数据序列化。
"""

from xml.sax.saxutils import escape

from ...metadata.comic import ComicMetaData


# 翻页方向: YesAndRightToLeft - 右至左    No - 左至右
MANGA_DIRECTION = "No"


def _escape(value) -> str:
    return escape(str(value))


def write_comic_info_xml(output_dir: str, metadata: ComicMetaData):
    output_path = output_dir + "/" + "ComicInfo.xml"

    with open(output_path, "w", encoding='utf-8') as f:
        f.write("""\
<?xml version='1.0' encoding='UTF-8'?>
<ComicInfo xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">""")

        # 系列
        if metadata.series:
            f.write(f"""
  <Series>{_escape(metadata.series)}</Series>""")

        # 标题
        if metadata.title:
            f.write(f"""
  <Title>{_escape(metadata.title)}</Title>""")

        # 编号
        if metadata.number:
            f.write(f"""
  <Number>{_escape(metadata.number)}</Number>""")

        # 作者
        if metadata.creator:
            f.write(f"""
  <Writer>{_escape(metadata.creator)}</Writer>""")

        # 简介
        if metadata.description:
            f.write(f"""
  <Summary>{_escape(metadata.description)}</Summary>""")

        # 发布时间: 年
        if metadata.year:
            f.write(f"""
  <Year>{_escape(metadata.year)}</Year>""")

        # 发布时间: 月
        if metadata.month:
            f.write(f"""
  <Month>{_escape(metadata.month)}</Month>""")

        # 发布时间: 日
        if metadata.day:
            f.write(f"""
  <Day>{_escape(metadata.day)}</Day>""")

        # 语言
        if metadata.language:
            f.write(f"""
  <LanguageISO>{_escape(metadata.language)}</LanguageISO>""")

        # 标签
        if metadata.subjects:
            f.write(f"""
  <Tags>{",".join(_escape(s) for s in metadata.subjects)}</Tags>""")

        # 翻页方向
        f.write(f"""
  <Manga>{MANGA_DIRECTION}</Manga>
</ComicInfo>""")
