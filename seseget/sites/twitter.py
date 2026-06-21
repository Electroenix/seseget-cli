import asyncio
import copy

from ..config.path import DATA_DIR
from ..metadata.video import VideoMetaData
from ..request.fetcher import VideoInfo, VideoFetcher, FetcherRegistry
from ..utils.trace import logger
from ..request.downloadtask import TaskDLProgress
from ..utils.file_utils import *
from ..request import ytdlp
from ..config.config_manager import config


@FetcherRegistry.register("twitter")
class TwitterFetcher(VideoFetcher[VideoInfo]):
    site_dir = os.path.join(DATA_DIR, "twitter")

    def __init__(self, max_tasks=1):
        super().__init__(max_tasks=max_tasks)

    async def _get_video_info_list_by_yt_dlp(self, video_url):
        """
        通过yt_dlp请求视频信息，
        由于一个推文下可能存在多个视频，如果传入的是推文页面url，列表中将包含所有视频信息，
        如果传入的是单个视频的url，列表中只包含该视频的信息
        """
        extend_opts = {
            'cookiefile': config["twitter"]["cookie_file"]
        }
        # yt-dlp 是同步的，放到线程池执行
        twitter_info = await asyncio.to_thread(ytdlp.get_info, video_url, extend_opts)

        if not twitter_info:
            logger.error("video info is None!")
            return None

        if "id" not in twitter_info:
            logger.error("video info is error!")
            return None

        tt_video_info_list = []
        if twitter_info.get("_type") == "playlist":
            logger.info(f"检测到推文包含{twitter_info['playlist_count']}个视频")

            if twitter_info["id"] == twitter_info["webpage_url_basename"]:
                for info in twitter_info["entries"]:
                    tt_video_info_list.append(info)
            else:
                video_index = int(twitter_info["webpage_url_basename"])
                tt_video_info_list.append(twitter_info["entries"][video_index - 1])
        else:
            tt_video_info_list.append(twitter_info)

        video_info_list = []
        for info in tt_video_info_list:

            vid = info["id"]

            video_title = f'{info["uploader_id"]}_{info["upload_date"]}_{info["id"]}'
            video_descript = info["description"]
            video_author = info["uploader"]
            video_date = f'{info["upload_date"][0:4]}-{info["upload_date"][4:6]}-{info["upload_date"][6:8]}'
            video_tags: list = [info["uploader"], info["uploader_id"]]
            video_cover = info["thumbnail"]
            video_thumbnail = info["thumbnail"]

            metadata = VideoMetaData()
            metadata.title = video_title
            metadata.sub_title = video_title
            metadata.describe = video_descript
            metadata.public_time = video_date[0:10]
            metadata.year = video_date[0:4]
            metadata.author = video_author
            metadata.series = video_author
            metadata.tag_list = video_tags.copy()

            video_info = VideoInfo()

            video_info.vid = vid
            video_info.name = video_title
            video_info.view_url = video_url
            video_info.cover_url = video_cover
            video_info.thumbnail_url = video_thumbnail
            video_info.metadata = metadata

            video_info_list.append(video_info)

        return video_info_list

    async def _fetch_info(self, url, **kwargs) -> VideoInfo:
        video_info_list = await self._get_video_info_list_by_yt_dlp(url)
        return video_info_list[0] if video_info_list else None

    async def _download_process(self, video_info: VideoInfo, progress: TaskDLProgress | None = None):
        artist_dir = os.path.dirname(video_info.video_dir)

        extend_opts = {
            'outtmpl': artist_dir + '/%(uploader_id)s_%(upload_date)s_%(id)s/%(uploader_id)s_%(upload_date)s_%(id)s.%(ext)s',
            'cookiefile': config["twitter"]["cookie_file"],
        }

        # yt-dlp 是同步的，放到线程池执行
        await asyncio.to_thread(ytdlp.download_by_yt_dlp, "", video_info.view_url, extend_opts, progress)

    def _make_save_dir(self, info: VideoInfo):
        if not self.__class__.site_dir:
            raise ValueError("未指定下载目录!")
        if not os.path.exists(self.__class__.site_dir):
            os.mkdir(self.__class__.site_dir)

        series_dir = os.path.join(self.__class__.site_dir, make_filename_valid(info.metadata.series))
        info.video_dir = os.path.join(series_dir, make_filename_valid(info.name))

        if not os.path.exists(series_dir):
            os.mkdir(series_dir)
        if not os.path.exists(info.video_dir):
            os.mkdir(info.video_dir)

    async def download(self, url, **kwargs):
        default_params = {
            "no_download": False,
        }
        params = {**default_params, **kwargs}
        await self.task_semaphore.acquire()

        logger.info(f"开始请求资源信息")
        video_info_list = await self._get_video_info_list_by_yt_dlp(url)

        if video_info_list:
            logger.info(f"获取到{len(video_info_list)}个视频")
            for index, video_info in enumerate(video_info_list):
                logger.info(f"视频{index + 1}")
                video_info.print_info()

            if params["no_download"]:
                self.task_semaphore.release()
                return

            # 遍历所有视频信息，创建目录和元数据文件
            for video_info in video_info_list:
                self._make_save_dir(video_info)
                await self._make_metadata_file(video_info)
                self._make_source_info_file(video_info)

            # 创建下载任务，yt-dlp只需要提供页面url，调用一次可以下载所有视频
            await self._start_download_task(video_info_list[0])
        else:
            logger.warning("未获取到任何视频")
