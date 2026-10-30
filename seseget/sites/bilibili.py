import copy
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from ..config.config_manager import config
from ..config.path import DATA_DIR
from ..metadata.video import VideoMetaData
from ..request import downloader
from ..request.downloadtask import TaskDLProgress
from ..request.errors import RequestError, SiteParseError
from ..request.fetcher import FetcherRegistry, VideoFetcher, VideoInfo, make_source_info_file
from ..request.requests import async_request
from ..utils.file_utils import make_filename_valid
from ..utils.trace import logger
from .parser import SiteParser

BILI_API_PLAYURL = "https://api.bilibili.com/x/player/playurl"
BILI_API_VIEW_DETAIL = "https://api.bilibili.com/x/web-interface/view/detail"
BILI_TZ = timezone(timedelta(hours=8))


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

    def print_info(self):
        logger.info("---------------------------------")
        logger.info(f"BV号: {self.vid}")
        logger.info(f"标题: {self.metadata.title}")
        logger.info(f"简介: {self.metadata.describe}")
        logger.info(f"up主: {self.metadata.author}")
        logger.info(f"日期: {self.metadata.public_time}")
        logger.info(f"标签: {self.metadata.tag_list}")
        logger.info(f"播放: {self.video_view}")
        logger.info(f"点赞: {self.video_like}")
        logger.info(f"投币: {self.video_coin}")
        logger.info(f"收藏: {self.video_fav}")
        logger.info(f"转发: {self.video_share}")
        logger.info("---------------------------------")


@dataclass
class BiliPageData:
    bvid: str
    cid: str
    info: BiliVideoInfo


def _extract_bvid(url: str) -> str:
    match = re.search(
        r"https?://(?:www\.)?bilibili\.com/video/(BV[0-9A-Za-z]+)",
        url,
    )
    if match is None:
        raise SiteParseError(
            "未匹配到 BV 号（仅支持 /video/BV... 链接）",
            site="bilibili",
            url=url,
        )
    return match.group(1)


def _require_dict(value: Any, field: str, url: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SiteParseError(
            f"Bilibili 数据解析失败：{field} 缺失或不是对象",
            site="bilibili",
            url=url,
        )
    return value


def _require_text(value: Any, field: str, url: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SiteParseError(
            f"Bilibili 数据解析失败：{field} 为空",
            site="bilibili",
            url=url,
        )
    return value.strip()


def _require_int(value: Any, field: str, url: str) -> int:
    if not isinstance(value, int):
        raise SiteParseError(
            f"Bilibili 数据解析失败：{field} 不是整数",
            site="bilibili",
            url=url,
        )
    return value


def _normalize_image_url(value: str) -> str:
    if value.startswith("//"):
        return "https:" + value
    if value.startswith("http://"):
        return "https://" + value[len("http://"):]
    return value


def _extract_initial_state(parser: SiteParser) -> dict[str, Any]:
    for script in parser.find_all_optional(name="script"):
        text = script.string or script.get_text()
        marker = re.search(r"window\.__INITIAL_STATE__\s*=\s*", text)
        if marker is None:
            continue
        payload = text[marker.end():]
        try:
            state, _ = json.JSONDecoder().raw_decode(payload)
        except json.JSONDecodeError as exc:
            parser.fail(f"__INITIAL_STATE__ JSON 解析失败: {exc}")
        if not isinstance(state, dict):
            parser.fail("__INITIAL_STATE__ 不是对象")
        return state

    parser.fail("未匹配到 __INITIAL_STATE__")
    raise AssertionError("unreachable")


def _stat_text(stat: dict[str, Any], key: str) -> str:
    value = stat.get(key, 0)
    return str(value) if value is not None else "0"


def _extract_tag_names(raw_tags: Any) -> list[str]:
    tags: list[str] = []
    if not isinstance(raw_tags, list):
        return tags
    for item in raw_tags:
        if not isinstance(item, dict):
            continue
        tag_name = item.get("tag_name")
        if isinstance(tag_name, str) and tag_name.strip():
            tags.append(tag_name.strip())
    return tags


def _build_page_data(
    *,
    bvid: str,
    cid: str,
    title: str,
    description: str,
    author: str,
    cover: str,
    pubdate: int,
    tags: list[str],
    stat: dict[str, Any],
    url: str,
) -> BiliPageData:
    published_at = datetime.fromtimestamp(pubdate, tz=BILI_TZ)

    metadata = VideoMetaData()
    metadata.title = title
    metadata.sub_title = title
    metadata.describe = description
    metadata.public_time = published_at.strftime("%Y-%m-%d")
    metadata.year = published_at.strftime("%Y")
    metadata.author = author
    metadata.series = author
    metadata.tag_list = tags

    video_info = BiliVideoInfo()
    video_info.vid = bvid
    video_info.name = title
    video_info.view_url = url
    video_info.cover_url = cover
    video_info.thumbnail_url = cover
    video_info.metadata = metadata
    video_info.video_view = _stat_text(stat, "view")
    video_info.video_like = _stat_text(stat, "like")
    video_info.video_coin = _stat_text(stat, "coin")
    video_info.video_fav = _stat_text(stat, "favorite")
    video_info.video_share = _stat_text(stat, "share")

    return BiliPageData(bvid=bvid, cid=cid, info=video_info)


def parse_video_page(html: str, url: str, expected_bvid: str = "") -> BiliPageData:
    parser = SiteParser(html, site="bilibili", url=url)
    state = _extract_initial_state(parser)
    video_data = _require_dict(state.get("videoData"), "videoData", url)
    owner = _require_dict(video_data.get("owner"), "videoData.owner", url)
    stat = _require_dict(video_data.get("stat"), "videoData.stat", url)

    bvid = _require_text(state.get("bvid"), "bvid", url)
    cid_value = state.get("cid")
    if not isinstance(cid_value, (int, str)) or not str(cid_value):
        raise SiteParseError(
            "Bilibili 数据解析失败：cid 为空",
            site="bilibili",
            url=url,
        )
    cid = str(cid_value)
    if expected_bvid and bvid != expected_bvid:
        raise SiteParseError(
            f"页面 BV 号 {bvid} 与 URL {expected_bvid} 不一致",
            site="bilibili",
            url=url,
        )

    title = _require_text(video_data.get("title"), "videoData.title", url)
    author = _require_text(owner.get("name"), "videoData.owner.name", url)
    cover = _normalize_image_url(
        _require_text(video_data.get("pic"), "videoData.pic", url)
    )
    desc = video_data.get("desc")
    description = desc.strip() if isinstance(desc, str) else ""
    pubdate = _require_int(video_data.get("pubdate"), "videoData.pubdate", url)

    return _build_page_data(
        bvid=bvid,
        cid=cid,
        title=title,
        description=description,
        author=author,
        cover=cover,
        pubdate=pubdate,
        tags=_extract_tag_names(state.get("tags")),
        stat=stat,
        url=url,
    )


def parse_video_detail(
    payload: Any,
    url: str = "",
    expected_bvid: str = "",
) -> BiliPageData:
    response = _require_dict(payload, "响应对象", url)
    if response.get("code") != 0:
        raise SiteParseError(
            f"view/detail 返回错误 code={response.get('code')}: {response.get('message', '')}",
            site="bilibili",
            url=url,
        )
    data = _require_dict(response.get("data"), "data", url)
    view = _require_dict(data.get("View") or data.get("view"), "View", url)

    owner = _require_dict(view.get("owner"), "View.owner", url)
    stat = _require_dict(view.get("stat"), "View.stat", url)

    bvid = _require_text(view.get("bvid"), "View.bvid", url)
    cid_value = view.get("cid")
    if not isinstance(cid_value, (int, str)) or not str(cid_value):
        raise SiteParseError(
            "view/detail 响应中的 View.cid 为空",
            site="bilibili",
            url=url,
        )
    cid = str(cid_value)
    if expected_bvid and bvid != expected_bvid:
        raise SiteParseError(
            f"API BV 号 {bvid} 与 URL {expected_bvid} 不一致",
            site="bilibili",
            url=url,
        )

    title = _require_text(view.get("title"), "View.title", url)
    author = _require_text(owner.get("name"), "View.owner.name", url)
    cover = _normalize_image_url(
        _require_text(view.get("pic"), "View.pic", url)
    )
    desc = view.get("desc")
    description = desc.strip() if isinstance(desc, str) else ""
    pubdate = _require_int(view.get("pubdate"), "View.pubdate", url)

    return _build_page_data(
        bvid=bvid,
        cid=cid,
        title=title,
        description=description,
        author=author,
        cover=cover,
        pubdate=pubdate,
        tags=_extract_tag_names(data.get("Tags")),
        stat=stat,
        url=url,
    )


def _pick_play_url(streams: Any, kind: str, url: str) -> str:
    if not isinstance(streams, list) or not streams:
        raise SiteParseError(
            f"playurl 响应中没有可用的 {kind} 流",
            site="bilibili",
            url=url,
        )
    first = streams[0]
    if not isinstance(first, dict):
        raise SiteParseError(
            f"playurl 的 {kind} 流格式异常",
            site="bilibili",
            url=url,
        )
    play_url = first.get("baseUrl") or first.get("base_url")
    if not isinstance(play_url, str) or not play_url:
        raise SiteParseError(
            f"playurl 的 {kind} 流缺少 baseUrl",
            site="bilibili",
            url=url,
        )
    return play_url


def parse_play_urls(payload: Any, url: str = "") -> tuple[str, str]:
    if not isinstance(payload, dict):
        raise SiteParseError(
            "playurl 响应不是对象",
            site="bilibili",
            url=url,
        )
    if payload.get("code") != 0:
        raise SiteParseError(
            f"playurl 返回错误 code={payload.get('code')}: {payload.get('message', '')}",
            site="bilibili",
            url=url,
        )
    data = payload.get("data")
    if not isinstance(data, dict):
        raise SiteParseError("playurl 响应缺少 data", site="bilibili", url=url)
    dash = data.get("dash")
    if not isinstance(dash, dict):
        raise SiteParseError("playurl 响应缺少 dash", site="bilibili", url=url)

    video_url = _pick_play_url(dash.get("video"), "video", url)
    audio_url = _pick_play_url(dash.get("audio"), "audio", url)
    return video_url, audio_url


@FetcherRegistry.register("bilibili")
class BilibiliFetcher(VideoFetcher[BiliVideoInfo]):
    site_dir = os.path.join(DATA_DIR, "bilibili")
    BILI_HEADERS = {
        "Referer": "",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    }

    def _headers(self, url: str) -> dict[str, str]:
        headers = self.BILI_HEADERS.copy()
        headers["Referer"] = url
        cookie = config["sites"]["bilibili"].get("cookie", "")
        if cookie:
            headers["Cookie"] = cookie
        return headers

    async def _fetch_play_urls(self, bvid: str, cid: str, url: str) -> tuple[str, str]:
        response = await async_request(
            "GET",
            BILI_API_PLAYURL,
            params={
                "bvid": bvid,
                "cid": cid,
                "fnval": 4048,
                "fnver": 0,
                "fourk": 1,
            },
            headers=self._headers(url),
        )
        try:
            payload = response.json()
        except Exception as exc:
            raise SiteParseError(
                "playurl 响应不是合法 JSON",
                site="bilibili",
                url=url,
                cause=exc,
            ) from exc
        return parse_play_urls(payload, url)

    async def _fetch_api_page(self, bvid: str, url: str) -> BiliPageData:
        response = await async_request(
            "GET",
            BILI_API_VIEW_DETAIL,
            params={"bvid": bvid},
            headers=self._headers(url),
        )
        try:
            payload = response.json()
        except Exception as exc:
            raise SiteParseError(
                "view/detail 响应不是合法 JSON",
                site="bilibili",
                url=url,
                cause=exc,
            ) from exc
        return parse_video_detail(payload, url, expected_bvid=bvid)

    async def _fetch_html_page(self, bvid: str, url: str) -> BiliPageData:
        response = await async_request("GET", url, headers=self._headers(url))
        return parse_video_page(response.text, url, expected_bvid=bvid)

    async def _fetch_page(self, bvid: str, url: str) -> BiliPageData:
        try:
            return await self._fetch_api_page(bvid, url)
        except (RequestError, SiteParseError, ValueError) as exc:
            logger.warning("Bilibili API 获取失败，回退页面解析: %s", exc)
            return await self._fetch_html_page(bvid, url)

    async def _fetch_info(self, url, **kwargs) -> BiliVideoInfo:
        bvid = _extract_bvid(url)
        page = await self._fetch_page(bvid, url)

        video_url, audio_url = await self._fetch_play_urls(page.bvid, page.cid, url)
        page.info.video_download_url = video_url
        page.info.audio_download_url = audio_url
        return copy.deepcopy(page.info)

    async def _download_process(
        self,
        video_info: BiliVideoInfo,
        progress: TaskDLProgress | None = None,
    ):
        video_path = video_info.video_dir + '/' + make_filename_valid('%s.mp4' % video_info.name)

        headers = self._headers(video_info.view_url)

        await downloader.download_mp4_by_merge_video_audio(
            video_path,
            video_info.audio_download_url,
            video_info.video_download_url,
            headers,
            progress)

    def _make_source_info_file(self, info: BiliVideoInfo):
        source_info = 'video url: %s\r\n' % info.view_url
        source_info = source_info + 'thumbnail url: %s\r\n' % info.thumbnail_url
        source_info = source_info + 'cover url: %s\r\n' % info.cover_url
        source_info = source_info + 'video download url: %s\r\n' % info.video_download_url
        source_info = source_info + 'audio download url: %s\r\n' % info.audio_download_url
        make_source_info_file(info.video_dir, source_info)
