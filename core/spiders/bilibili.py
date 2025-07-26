import copy
import json
from bs4 import BeautifulSoup
import core.config.path
from core.metadata.video import *
from core.request.fetcher import VideoFetcher, FetcherRegistry
from core.utils.trace import *
from core.request import seserequest as ssreq
from core.utils.file_utils import *
from core.config.config_manager import config
from core.utils.file_process import make_source_info_file, make_video_metadata_file


# 视频信息
class BiliVideoInfo(VideoInfo):
    def __init__(self):
        super().__init__()
        self.video_download_url = ""
        self.audio_download_url = ""
        self.video_view = ""
        self.video_like = ""
        self.video_coin = ""
        self.video_fav = ""
        self.video_share = ""


@FetcherRegistry.register("bilibili")
class BilibiliFetcher(VideoFetcher):
    station_dir = core.config.path.bili_data_local_path + "/"
    headers = {
        "Referer": "",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Cookie": f"{config['bilibili']['cookie']}"
    }

    # 通过视频页面url请求bilibili,获取视频信息和下载地址
    def get_info(self, url, **kwargs):
        vid = ""
        match = re.search(r'https?://www\.bilibili\.com/video/([^/?]+)', url)
        if match:
            vid = match.group(1)

        # 发送请求获取网页html
        response = ssreq.request("GET", url, headers=self.headers)
        video_soup = BeautifulSoup(response.text, 'html.parser')

        # 关键元素
        viewbox_report = video_soup.find("div", attrs={"id": "viewbox_report"})
        view_text = viewbox_report.find("div", attrs={"class": "view-text"})
        arc_toolbar_report = video_soup.find("div", attrs={"id": "arc_toolbar_report"})
        video_like_info = arc_toolbar_report.find("span", attrs={"class": "video-like-info"})
        video_coin_info = arc_toolbar_report.find("span", attrs={"class": "video-coin-info"})
        video_fav_info = arc_toolbar_report.find("span", attrs={"class": "video-fav-info"})
        video_share_info = arc_toolbar_report.find("span", attrs={"class": "video-share-info"})
        v_desc = video_soup.find("div", attrs={"id": "v_desc"})

        # 提取视频信息
        video_title = viewbox_report.find("h1").text
        video_descript = v_desc.find("span").text
        video_author = video_soup.find("meta", attrs={"itemprop": "author"}).attrs["content"]
        video_cover = "https:" + video_soup.find("meta", attrs={"itemprop": "image"}).attrs["content"].split("@")[0]
        video_thumbnail = "https:" + video_soup.find("meta", attrs={"itemprop": "thumbnailUrl"}).attrs["content"].split("@")[0]
        video_date = video_soup.find("meta", attrs={"itemprop": "uploadDate"}).attrs["content"]
        video_tags_element = video_soup.find_all("div", attrs={"class": "tag not-btn-tag"})

        video_tags = []
        for e in video_tags_element:
            video_tags.append(e.text)

        video_view = view_text.text  # 播放量
        video_like = video_like_info.text  # 点赞
        video_coin = video_coin_info.text  # 投币
        video_fav = video_fav_info.text  # 收藏
        video_share = video_share_info.text  # 转发

        SESE_PRINT(f"BV号: {vid}")
        SESE_PRINT(f"标题: {video_title}")
        SESE_PRINT(f"简介: {video_descript}")
        SESE_PRINT(f"up主: {video_author}")
        SESE_PRINT(f"日期: {video_date}")
        SESE_PRINT(f"标签: {video_tags}")
        SESE_PRINT(f"播放: {video_view}")
        SESE_PRINT(f"点赞: {video_like}")
        SESE_PRINT(f"投币: {video_coin}")
        SESE_PRINT(f"收藏: {video_fav}")
        SESE_PRINT(f"转发: {video_share}")

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

        # 解析视频信息
        info = re.findall('window.__playinfo__=(.*?)</script>', response.text)[0]
        json_data = json.loads(info)

        # 提取视频链接和音频链接
        video_download_url = json_data['data']['dash']['video'][0]['baseUrl']
        audio_download_url = json_data['data']['dash']['audio'][0]['baseUrl']

        video_info = BiliVideoInfo()

        video_info.vid = vid
        video_info.name = video_title
        video_info.view_url = url
        video_info.cover_url = video_cover
        video_info.thumbnail_url = video_thumbnail
        video_info.metadata = metadata
        video_info.video_download_url = video_download_url
        video_info.audio_download_url = audio_download_url
        video_info.video_view = video_view
        video_info.video_like = video_like
        video_info.video_coin = video_coin
        video_info.video_fav = video_fav
        video_info.video_share = video_share

        return copy.deepcopy(video_info)

    def _start_download(self, video_info: VideoInfo):
        if not isinstance(video_info, BiliVideoInfo):
            raise TypeError(f"video_info类型({type(video_info)})错误！不是BiliVideoInfo")

        video_path = video_info.video_dir + '/' + make_filename_valid('%s.mp4' % video_info.name)  # 视频保存路径
        self.headers["Referer"] = video_info.view_url

        # 创建下载任务
        ssreq.download_task(video_info.name,
                            ssreq.download_mp4_by_merge_video_audio,
                            video_path, video_info.audio_download_url,
                            video_info.video_download_url,
                            self.headers.copy())

    def _make_source_info_file(self, video_info: VideoInfo):
        if not isinstance(video_info, BiliVideoInfo):
            raise TypeError(f"video_info类型({type(video_info)})错误！不是BiliVideoInfo")

        source_info = 'video url: %s\r\n' % video_info.view_url
        source_info = source_info + 'thumbnail url: %s\r\n' % video_info.thumbnail_url
        source_info = source_info + 'cover url: %s\r\n' % video_info.cover_url
        source_info = source_info + 'video download url: %s\r\n' % video_info.video_download_url
        source_info = source_info + 'audio download url: %s\r\n' % video_info.audio_download_url
        make_source_info_file(video_info.video_dir, source_info)
