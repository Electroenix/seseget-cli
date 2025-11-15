from collections import OrderedDict

from core.utils.trace import SESE_PRINT


class VideoMetaData:
    """视频元数据"""
    title = ""  # 标题
    sub_title = ""  # 标语
    year = ""  # 年份
    public_time = ""  # 发布日期
    tag_list = []  # 类型
    artist = ""  # 作者
    director = ""  # 导演
    describe = ""  # 摘要
    back_ground_path = ""  # 背景图片路径


# 视频信息
class VideoInfo:
    def __init__(self):
        self.vid = ""
        self.name = ""              # 视频标题
        self.view_url = ""          # 网页地址
        self.download_url = ""      # 下载地址
        self.cover_url = ""         # 封面地址
        self.thumbnail_url = ""     # 缩略图地址
        self.metadata = VideoMetaData()     # 元数据
        self.series_info = []       # 系列视频信息
        self.video_dir = ""         # 本地保存目录

    def print_info(self):
        SESE_PRINT(f"---------------------------------")
        SESE_PRINT(f"标题: {self.name}")
        SESE_PRINT(f"作者: {self.metadata.artist}")
        SESE_PRINT(f"标签: {self.metadata.tag_list}")
        SESE_PRINT(f"简介: {self.metadata.describe}")
        SESE_PRINT(f"---------------------------------")


class VideoInfoCache:
    def __init__(self, max_size=10):
        self.cache = OrderedDict()  # 核心缓存容器
        self.max_size = max_size  # 最大缓存数量

    def get_video_info(self, vid):
        """ 获取视频信息（自动缓存） """
        if vid in self.cache:
            # 命中缓存：移动元素到末尾表示最近使用
            self.cache.move_to_end(vid)
            #PRINTLOG(f"缓存命中 vid: {vid}")
            return self.cache[vid]

        # 缓存未命中
        return None

    def update_cache(self, vid, video_info):
        """ 更新缓存并执行淘汰策略 """
        self.cache[vid] = video_info
        if len(self.cache) > self.max_size:
            # 移除最久未使用的条目
            oldest_vid, _ = self.cache.popitem(last=False)
            #PRINTLOG(f"移除过期缓存 vid: {oldest_vid}")
        #PRINTLOG("当前缓存:", list(self.cache.keys()))
