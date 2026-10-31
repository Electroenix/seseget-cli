import copy
import os
import re
from urllib.parse import parse_qs, urlparse

from bs4.element import Tag

from ..config.config_manager import config
from ..config.path import DATA_DIR
from ..metadata.video import VideoMetaData
from ..request import downloader
from ..request.errors import SiteParseError
from ..request.fetcher import FetcherRegistry, VideoFetcher, VideoInfo
from ..request.requests import async_request
from ..utils.file_utils import make_diff_dir_name, make_filename_valid
from ..utils.trace import logger
from .parser import SiteParser

HANIME_HEADERS = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'zh-CN,zh-TW;q=0.9,zh;q=0.8,en-GB;q=0.7,en;q=0.6,zh-MO;q=0.5,zh-HK;q=0.4,ja-JP;q=0.3,ja;q=0.2',
    'cache-control': 'no-cache',
    'pragma': 'no-cache',
    'priority': 'u=0, i',
    'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    'sec-ch-ua-arch': '"x86"',
    'sec-ch-ua-bitness': '"64"',
    'sec-ch-ua-full-version': '"143.0.7499.170"',
    'sec-ch-ua-full-version-list': '"Google Chrome";v="143.0.7499.170", "Chromium";v="143.0.7499.170", "Not A(Brand";v="24.0.0.0"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-model': '""',
    'sec-ch-ua-platform': '"Windows"',
    'sec-ch-ua-platform-version': '"19.0.0"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
    'cookie': '',
}

GENRES_SIMP = ["里番", "泡面番", "Motion Anime", "3DCG", "2.5D", "2D动画", "AI生成", "MMD", "Cosplay"]
GENRES_TRAD = ["裏番", "泡麵番", "Motion Anime", "3DCG", "2.5D", "2D動畫", "AI生成", "MMD", "Cosplay"]

class HanimeVideoInfo(VideoInfo):
    def __init__(self):
        super().__init__()
        self.video_genre = ""         # 视频类型


@FetcherRegistry.register("hanime", "Hanime")
class HanimeFetcher(VideoFetcher[HanimeVideoInfo]):
    site_dir = os.path.join(DATA_DIR, "hanime")

    @staticmethod
    def get_metadata(parser: SiteParser):
        metadata = VideoMetaData()

        title_element = parser.find(name="h3",
            attrs={"id": "shareBtn-title"},
        )
        metadata.title = title_element.get_text(strip=True)

        sub_titles = parser.find_all_optional(
            name="div",
            attrs={"style": "margin-bottom: 5px"},
        )
        if len(sub_titles) < 2:
            parser.fail(
                f"sub_titles 数量不足，期望至少 2 个，实际 {len(sub_titles)} 个"
            )
        metadata.sub_title = sub_titles[1].get_text(strip=True)

        describe_element = parser.find(name="div",
            attrs={
                "class": "video-caption-text caption-ellipsis",
                "style": "color: #b8babc; font-weight: normal;",
            },
        )
        metadata.describe = describe_element.get_text()

        author_element = parser.find(name="a",
            attrs={"id": "video-artist-name"},
        )
        metadata.author = (
            author_element.get_text(strip=True)
            .replace("\n", "")
            .replace(" ", "")
        )

        playlist_top = parser.find(name="div",
            attrs={"class": "video-playlist-top"},
        )
        playlist_h4 = parser.find(node=playlist_top, name="h4")
        series_element = parser.find(node=playlist_h4,
            name="a",
        )
        metadata.series = series_element.get_text(strip=True)

        metadata.tag_list.clear()
        for tag_element in parser.find_all_optional(
            name="div",
            attrs={
                "class": "single-video-tag",
                "style": "margin-bottom: 18px; font-weight: normal",
            },
        ):
            tag_link = tag_element.find("a")
            if not isinstance(tag_link, Tag):
                continue
            href = tag_link.get("href")
            if isinstance(href, str):
                metadata.tag_list.append(href[href.find("=") + 1:])

        date_element = parser.find(name="div",
            attrs={"class": "hidden-xs", "style": "margin-bottom: 5px"},
        )
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", date_element.get_text())
        if date_match is None:
            parser.fail("date_match 匹配失败")
        metadata.public_time = date_match.group()
        metadata.year = metadata.public_time[:4]

        return metadata

    @staticmethod
    def get_series_info(parser: SiteParser):
        series = []

        play_list = parser.find(name="div",
            attrs={"id": "playlist-scroll"},
        )
        video_element_list = parser.find_all(node=play_list,
            name="div",
            attrs={"class": "playlist-hover-wrap"},
            recursive=False,
        )

        for video_element in video_element_list:
            video_url_element = video_element.find("a")
            video_thumb_url_element = video_element.find("img")
            video_title_element = video_element.find("h4", {"class": "video-title"})
            if not (
                isinstance(video_url_element, Tag)
                and isinstance(video_thumb_url_element, Tag)
                and isinstance(video_title_element, Tag)
            ):
                continue
            video_url = video_url_element.get("href")
            video_thumb_url = video_thumb_url_element.get("src")
            if not isinstance(video_url, str) or not isinstance(video_thumb_url, str):
                continue
            vids = parse_qs(urlparse(video_url).query).get("v")
            if not vids:
                continue
            series.append(
                {
                    "vid": vids[0],
                    "title": video_title_element.get_text(strip=True),
                    "url": video_url,
                    "thumbnail": video_thumb_url,
                }
            )

        return series

    @staticmethod
    async def download_series_thumbnail(series, dir):
        import asyncio
        totle_cnt = len(series)
        finish_cnt = 0

        semaphore = asyncio.Semaphore(10)

        async def _download_one(video):
            nonlocal finish_cnt
            video_url = video["url"]
            view_url_parse = urlparse(video_url)
            vid = parse_qs(view_url_parse.query)["v"][0]

            thumbnail_url = video["thumbnail"]
            thumbnail_path = dir + "%s.jpg" % vid

            async with semaphore:
                await downloader.download_file(thumbnail_path, thumbnail_url)
                video["thumbnail"] = thumbnail_path
                finish_cnt = finish_cnt + 1
                logger.info('下载系列视频缩略图中(%d/%d)' % (finish_cnt, totle_cnt), end="\r")

        tasks = [_download_one(v) for v in series]
        try:
            await asyncio.gather(*tasks)
        except Exception:
            logger.error('\n下载失败!')
            raise

        logger.info('\n下载完成!')

    def _make_save_dir(self, info: HanimeVideoInfo):
        if not self.__class__.site_dir:
            raise ValueError("未指定下载目录!")
        if not os.path.exists(self.__class__.site_dir):
            os.mkdir(self.__class__.site_dir)

        if config["sites"]["hanime"]["organize_by_genre"]:
            genre_dir = os.path.join(self.__class__.site_dir, make_filename_valid(info.video_genre))
            series_dir = os.path.join(genre_dir, make_filename_valid(info.metadata.series))
            if not os.path.exists(genre_dir):
                os.mkdir(genre_dir)
        else:
            series_dir = os.path.join(self.__class__.site_dir, make_filename_valid(info.metadata.series))

        info.video_dir = os.path.join(series_dir, make_filename_valid(info.name))
        info.video_dir = make_diff_dir_name(info.video_dir)

        if not os.path.exists(series_dir):
            os.mkdir(series_dir)
        if not os.path.exists(info.video_dir):
            os.mkdir(info.video_dir)

    async def _fetch_info(self, url, **kwargs) -> HanimeVideoInfo:
        view_url_parse = urlparse(url)
        vids = parse_qs(view_url_parse.query).get("v")
        if not vids:
            raise SiteParseError(
                "页面解析失败：未匹配到视频 ID（URL 参数 v）",
                site="hanime",
                url=url,
            )
        vid = vids[0]

        video_info = self.video_info_cache.get_video_info(vid)
        if video_info is not None:
            logger.info("匹配到缓存中的视频信息(vid-%s)" % vid)
            return copy.deepcopy(video_info)

        req_kwargs = {}
        if config["sites"]["hanime"]["cookie"]:
            req_kwargs["headers"] = HANIME_HEADERS.copy()
            req_kwargs["headers"]["cookie"] = config["sites"]["hanime"]["cookie"]
        response = await async_request("GET", url, **req_kwargs)
        parser = SiteParser(response.text, site="hanime", url=url)

        video_elem = parser.find(name="video")
        poster = video_elem.get("poster")
        video_thumbnail_url = poster if isinstance(poster, str) else ""

        video_source = None
        for size in ("1080", "720", "480"):
            candidate = video_elem.find("source", {"size": size})
            if isinstance(candidate, Tag):
                video_source = candidate
                break
        if video_source is None:
            parser.fail("未找到可用的 video source（size=1080/720/480）")
        video_download_url = video_source.get("src")
        if not isinstance(video_download_url, str):
            parser.fail("video_source 缺少 src")

        metadata = self.get_metadata(parser)
        series_info = self.get_series_info(parser)

        cover_url = None
        genre_element = parser.find(name="a",
            attrs={"class": "hidden-sm hidden-md hidden-lg hidden-xl"},
        )
        video_genre = genre_element.get_text(strip=True).replace("\n", "").replace(" ", "")

        if video_genre in GENRES_SIMP + GENRES_TRAD:
            if video_genre in GENRES_SIMP:
                mapped_genre = dict(zip(GENRES_SIMP, GENRES_TRAD, strict=True)).get(video_genre)
                if mapped_genre:
                    video_genre = mapped_genre
            search_url = f'https://hanime1.me/search?type=&genre={video_genre}&sort=&date=&duration='
            req_kwargs = {}
            if config["sites"]["hanime"]["cookie"]:
                req_kwargs["headers"] = HANIME_HEADERS.copy()
                req_kwargs["headers"]["cookie"] = config["sites"]["hanime"]["cookie"]
            response = await async_request("GET", search_url, params={'query': metadata.title}, **req_kwargs)

            search_parser = SiteParser(response.text, site="hanime", url=search_url)

            cover_link = search_parser.soup.find("a", href=url)
            if isinstance(cover_link, Tag):
                cover_element = cover_link.find("img", src=re.compile("cover"))
                if isinstance(cover_element, Tag):
                    cover_src = cover_element.get("src")
                    if isinstance(cover_src, str):
                        cover_url = cover_src

        if cover_url is None:
            cover_url = video_thumbnail_url

        video_info = HanimeVideoInfo()

        video_info.vid = vid
        video_info.name = metadata.title
        video_info.view_url = url
        video_info.download_url = video_download_url
        video_info.cover_url = cover_url
        video_info.thumbnail_url = video_thumbnail_url
        video_info.metadata = metadata
        video_info.series_info = series_info
        video_info.video_genre = video_genre

        await self.video_info_cache.update_cache(vid, video_info)

        return copy.deepcopy(video_info)
