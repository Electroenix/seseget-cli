import copy
import json
import core.config.path
from core.metadata.video import *
from core.request.fetcher import VideoFetcher, FetcherRegistry
from core.utils.trace import *
from core.request import seserequest as ssreq
from core.utils.file_utils import *
from core.request import seseytdlp


class YtbVideoInfo(VideoInfo):
    """Ytb视频信息"""

    def __init__(self):
        super().__init__()
        self.video_view = ""
        self.video_like = ""

    def print_info(self):
        SESE_PRINT(f"vid: {self.vid}")
        SESE_PRINT(f"标题: {self.metadata.title}")
        SESE_PRINT(f"简介: {self.metadata.describe}")
        SESE_PRINT(f"作者: {self.metadata.artist}")
        SESE_PRINT(f"日期: {self.metadata.public_time}")
        SESE_PRINT(f"标签: {self.metadata.tag_list}")
        SESE_PRINT(f"播放: {self.video_view}")
        SESE_PRINT(f"点赞: {self.video_like}")


@FetcherRegistry.register("youtube")
class YoutubeFetcher(VideoFetcher):
    site_dir = core.config.path.YOUTUBE_DATA_LOCAL_DIR + "/"
    GET_INFO_BY_HTML = 1

    @staticmethod
    def _get_video_info_by_html(video_url):
        """通过视频页面url请求youtube,获取视频信息"""
        vid = ""
        match = re.search(r'https?://www\.youtube\.com/watch\?v=([^/?]+)', video_url)
        if match:
            vid = match.group(1)

        # 发送请求获取网页html
        response = ssreq.request("GET", video_url)
        # PRINTLOG(response.text)

        # 解析视频信息
        info = re.findall('var ytInitialPlayerResponse = (.*?);var', response.text)[0]
        json_data = json.loads(info)

        # 提取视频信息
        video_title = json_data['videoDetails']['title']
        video_descript = json_data['videoDetails']['shortDescription']
        video_author = json_data['videoDetails']['author']
        video_cover = json_data['videoDetails']['thumbnail']['thumbnails'][-1]['url']
        video_thumbnail = json_data['videoDetails']['thumbnail']['thumbnails'][-1]['url']
        video_date = json_data['microformat']['playerMicroformatRenderer']['uploadDate']
        video_tags = [json_data['microformat']['playerMicroformatRenderer']['category'], json_data['microformat']['playerMicroformatRenderer']['ownerChannelName']]

        video_view = json_data['microformat']['playerMicroformatRenderer']['viewCount']  # 播放量

        # 元数据
        metadata = VideoMetaData()
        metadata.title = video_title
        metadata.sub_title = video_title
        metadata.describe = video_descript
        metadata.artist = video_author
        metadata.public_time = video_date[0:10]
        metadata.year = video_date[0:4]
        metadata.director = video_author
        metadata.tag_list = video_tags.copy()

        video_info = YtbVideoInfo()

        video_info.vid = vid
        video_info.name = video_title
        video_info.view_url = video_url
        video_info.cover_url = video_cover
        video_info.thumbnail_url = video_thumbnail
        video_info.metadata = metadata
        video_info.video_view = video_view

        return copy.deepcopy(video_info)

    @staticmethod
    def _get_video_info_by_yt_dlp(video_url):
        """通过yt_dlp请求视频信息"""
        vid = ""
        match = re.search(r'https?://www\.youtube\.com/watch\?v=([^/?]+)', video_url)
        if match:
            vid = match.group(1)

        info = seseytdlp.get_info(video_url)

        if not info:
            SESE_TRACE(LOG_ERROR, "video info is None!")
            return -1

        if "id" not in info:
            SESE_TRACE(LOG_ERROR, "video info is error!")
            return -1

        if info["id"] != vid:
            SESE_TRACE(LOG_ERROR, "video id not match!")
            return -1

        # 提取视频信息
        video_title = info["title"]
        video_descript = info["description"]
        video_author = info["uploader"]
        video_cover = info["thumbnail"]
        video_thumbnail = info["thumbnail"]
        video_date = f'{info["upload_date"][0:4]}-{info["upload_date"][4:6]}-{info["upload_date"][6:8]}'
        video_tags: list = info["categories"]
        video_tags.append(info["channel"])

        video_view = str(info["view_count"])  # 播放量
        video_like = str(info["like_count"])  # 点赞

        # 元数据
        metadata = VideoMetaData()
        metadata.title = video_title
        metadata.sub_title = video_title
        metadata.describe = video_descript
        metadata.artist = video_author
        metadata.public_time = video_date[0:10]
        metadata.year = video_date[0:4]
        metadata.director = video_author
        metadata.tag_list = video_tags.copy()

        video_info = YtbVideoInfo()

        video_info.vid = vid
        video_info.name = video_title
        video_info.view_url = video_url
        video_info.cover_url = video_cover
        video_info.thumbnail_url = video_thumbnail
        video_info.metadata = metadata
        video_info.video_view = video_view
        video_info.video_like = video_like

        return copy.deepcopy(video_info)

    def _fetch_info(self, url, **kwargs):
        if self.__class__.GET_INFO_BY_HTML:
            return self._get_video_info_by_html(url)
        else:
            return self._get_video_info_by_yt_dlp(url)

    def _download_resource(self, video_info: VideoInfo):
        video_path = video_info.video_dir + '/' + make_filename_valid('%s.mp4' % video_info.name)  # 视频保存路径

        ssreq.download_task(video_info.name,
                            seseytdlp.download_by_yt_dlp,
                            video_path, video_info.view_url)
