
class ComicMetaData:
    """comic元数据，以EPUB文件中元数据的标签命名"""
    def __init__(self):
        self.series = ""    # 系列名
        self.title = ""     # 章节名
        self.number = ""    # 章节号
        self.creator = ""   # 作者
        self.publisher = ""     # 出版商
        self.year = ""      # 发布日期: 年
        self.month = ""      # 发布日期: 月
        self.day = ""       # 发布日期: 日
        self.description = ""   # 剧情简介
        self.language = ""  # 语言
        self.subjects = []  # 标签
