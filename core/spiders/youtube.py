import copy
import json
import core.config.path
from core.metadata.video import *
from core.metadata.vsmeta import *
from core.metadata.nfo import *
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


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}

save_path = core.config.path.youtube_data_local_path + "/"
video_info_cache = VideoInfoCache(10)


def _get_video_info_by_html(video_url):
    """通过视频页面url请求youtube,获取视频信息"""
    vid = ""
    match = re.search(r'https?://www\.youtube\.com/watch\?v=([^/?]+)', video_url)
    if match:
        vid = match.group(1)

    # 发送请求获取网页html
    response = ssreq.request("GET", video_url, headers=headers)
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

    SESE_PRINT(f"vid: {vid}")
    SESE_PRINT(f"标题: {video_title}")
    SESE_PRINT(f"简介: {video_descript}")
    SESE_PRINT(f"作者: {video_author}")
    SESE_PRINT(f"日期: {video_date}")
    SESE_PRINT(f"标签: {video_tags}")
    SESE_PRINT(f"播放: {video_view}")

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
    video_info.cover_url = video_cover
    video_info.thumbnail_url = video_thumbnail
    video_info.metadata = metadata
    video_info.video_view = video_view

    return copy.deepcopy(video_info)


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

    SESE_PRINT(f"vid: {vid}")
    SESE_PRINT(f"标题: {video_title}")
    SESE_PRINT(f"简介: {video_descript}")
    SESE_PRINT(f"作者: {video_author}")
    SESE_PRINT(f"日期: {video_date}")
    SESE_PRINT(f"标签: {video_tags}")
    SESE_PRINT(f"播放: {video_view}")
    SESE_PRINT(f"点赞: {video_like}")

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
    video_info.cover_url = video_cover
    video_info.thumbnail_url = video_thumbnail
    video_info.metadata = metadata
    video_info.video_view = video_view
    video_info.video_like = video_like

    return copy.deepcopy(video_info)


def get_video_info(video_url):
    """获取视频信息"""
    GET_INFO_BY_HTML = 1
    if GET_INFO_BY_HTML:
        return _get_video_info_by_html(video_url)
    else:
        return _get_video_info_by_yt_dlp(video_url)


def download(url):
    video_url_list = url.split(',')
    for video_url in video_url_list:
        # 请求url获取视频信息和下载地址
        video_info = get_video_info(video_url)

        video_name = video_info.name
        video_thumbnail_url = video_info.thumbnail_url
        cover_url = video_info.cover_url
        metadata = video_info.metadata

        SESE_PRINT('video name: %s' % video_name)
        SESE_PRINT('thumbnail url: %s' % video_thumbnail_url)
        SESE_PRINT('cover url: %s' % cover_url)

        # 创建下载目录
        middle_dir = save_path + '%s' % make_filename_valid(metadata.artist)  # 中间目录，主要用来分类同一个作者的作品
        download_dir = '%s/%s' % (middle_dir, make_filename_valid(video_name))  # 下载目录，以视频名命名

        # 如果目录已经存在，生成不同的目录名，避免视频名相同导致被覆盖
        download_dir = make_diff_dir_name(download_dir)

        if not os.path.exists(save_path):
            os.mkdir(save_path)
        if not os.path.exists(middle_dir):
            os.mkdir(middle_dir)
        if not os.path.exists(download_dir):
            os.mkdir(download_dir)

        poster_path = download_dir + '/' + 'poster.jpg'  # 封面图保存路径
        fanart_path = download_dir + '/' + 'fanart.jpg'  # 背景图保存路径
        video_path = download_dir + '/' + make_filename_valid('%s.mp4' % video_name)  # 视频保存路径
        vsmeta_path = download_dir + '/' + make_filename_valid('%s.mp4.vsmeta' % video_name)  # vsmeta文件保存路径
        nfo_path = download_dir + '/' + make_filename_valid('%s.nfo' % video_name)  # nfo文件保存路径

        # 创建下载任务
        ssreq.download_task(video_name,
                            seseytdlp.download_by_yt_dlp,
                            video_path, video_url)

        if ssreq.download_file(poster_path, cover_url) | \
                ssreq.download_file(fanart_path, video_thumbnail_url) == 0:

            # 创建source.txt文件保存下载地址
            with open(download_dir + '/' + 'source.txt', 'wb') as f:
                f.write(('video url: %s\r\n' % url).encode())
                f.write(('thumbnail url: %s\r\n' % video_thumbnail_url).encode())
                f.write(('cover url: %s\r\n' % cover_url).encode())
            metadata.describe = metadata.describe + '\r\n%s' % url
            metadata.back_ground_path = fanart_path

            # 生成metadata文件
            make_vsmeta_file(vsmeta_path, metadata)
            make_nfo_file(nfo_path, metadata)
        else:
            SESE_PRINT('download fail!')
