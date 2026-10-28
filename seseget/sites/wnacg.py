import os
import re
from typing import List

from bs4 import BeautifulSoup

from ..request.errors import SiteParseError
from ..request.fetcher import ChapterInfo, ComicInfo, FetcherRegistry, ComicFetcher
from ..request.requests import async_request
from ..config.path import DATA_DIR


def _parse_error(message: str, url: str = "") -> SiteParseError:
    return SiteParseError(f"页面解析失败：{message}", site="wnacg", url=url)


def _require_cid(url: str) -> str:
    match = re.search(r"\d+(?=\.html)", url)
    if not match:
        raise _parse_error("无法从 URL 中解析作品 ID", url)
    return match.group()


def parse_image_urls(html: str, source_url: str = "") -> List[str]:
    """从 wnacg 的 imglist 脚本中提取图片 URL。"""
    match = re.search(r"(?<=var imglist = )\[[\s\S]+]", html)
    if not match:
        raise _parse_error("未找到图片列表 imglist", source_url)

    image_list_str = match.group()
    image_list_str = image_list_str.replace("\\", "")
    image_list_str = image_list_str.replace("fast_img_host+", "")
    raw_urls = re.findall(r'url"?\s*:\s*"([^"]+)"', image_list_str)

    image_urls = []
    for raw_url in raw_urls:
        if "//" in raw_url:
            image_urls.append("https:" + raw_url)
    return image_urls


def parse_comic_info(
    html: str,
    url: str,
    cid: str,
    image_urls: List[str],
) -> ComicInfo:
    """解析 wnacg 作品详情页。所有缺失的关键元素统一转为 SiteParseError。"""
    soup = BeautifulSoup(html, "html.parser")
    bodywraps = soup.find_all("div", attrs={"id": "bodywrap"})
    if len(bodywraps) < 2:
        raise _parse_error("页面缺少 bodywrap 容器", url)

    soup_userwrap = bodywraps[0]
    soup_cc = bodywraps[1]
    soup_info = soup_userwrap.find("div", attrs={"class": "asTBcell uwconn"})
    soup_uinfo = soup_userwrap.find("div", attrs={"class": "asTBcell uwuinfo"})
    if soup_info is None or soup_uinfo is None:
        raise _parse_error("页面缺少作品信息容器", url)

    title_element = soup_userwrap.find("h2")
    cover_element = soup_userwrap.find("img")
    author_element = soup_uinfo.find("p")
    date_element = soup_cc.find("div", string=re.compile(r"上傳於"))
    if title_element is None:
        raise _parse_error("页面缺少作品标题", url)
    if cover_element is None or not cover_element.get("src"):
        raise _parse_error("页面缺少封面地址", url)
    if author_element is None:
        raise _parse_error("页面缺少作者信息", url)
    if date_element is None or not date_element.string:
        raise _parse_error("页面缺少上传日期", url)

    comic_title = title_element.get_text(strip=True)
    if not comic_title:
        raise _parse_error("作品标题为空", url)

    comic_cover_url = "https://" + str(cover_element.get("src")).lstrip("/")
    comic_author = author_element.get_text(strip=True)
    if not comic_author:
        raise _parse_error("作者信息为空", url)

    comic_tag_list = [
        tag.get_text(strip=True)
        for tag in soup_info.find_all("a", attrs={"class": "tagshow"})
        if tag.get_text(strip=True)
    ]

    type_match = re.search(
        r"(?<=<label>分類：)[\s\S]+?(?=</label>)", str(soup_info)
    )
    if not type_match:
        raise _parse_error("页面缺少分类信息", url)
    comic_type = type_match.group().strip()
    comic_tag_list.append(comic_type)

    comic_lang = "zh"
    if "日語" in comic_type:
        comic_lang = "ja"
    elif "漢化" in comic_type:
        comic_lang = "zh"

    desc_element = soup_info.find("p", string=re.compile(r"簡介："))
    if desc_element is None:
        raise _parse_error("页面缺少简介信息", url)
    comic_desc = desc_element.get_text().split("簡介：", 1)[-1].strip()

    date_match = re.search(r"(\d+)-(\d+)-(\d+)", date_element.get_text())
    if not date_match:
        raise _parse_error("无法解析上传日期", url)

    comic_info = ComicInfo()
    comic_info.view_url = url
    comic_info.cid = cid
    comic_info.cover_url = comic_cover_url
    comic_info.title = comic_title
    comic_info.author = comic_author
    comic_info.genres = comic_tag_list
    comic_info.description = comic_desc

    comic_chapter = ChapterInfo()
    comic_chapter.title = comic_title
    comic_chapter.id = 1
    comic_chapter.metadata.series = comic_title
    comic_chapter.metadata.title = comic_title
    comic_chapter.metadata.number = 1
    comic_chapter.metadata.language = comic_lang
    comic_chapter.metadata.creator = comic_author
    comic_chapter.metadata.subjects = comic_tag_list
    comic_chapter.metadata.description = comic_desc
    comic_chapter.metadata.year = date_match.group(1)
    comic_chapter.metadata.month = date_match.group(2)
    comic_chapter.metadata.day = date_match.group(3)
    comic_chapter.comic_info = comic_info
    comic_chapter.image_urls = image_urls

    comic_info.chapter_list.append(comic_chapter)
    return comic_info


@FetcherRegistry.register("wnacg")
class WnacgFetcher(ComicFetcher):
    site_dir = os.path.join(DATA_DIR, "wnacg")

    async def _get_image_urls(self, url: str) -> List[str]:
        cid = _require_cid(url)
        base_url = url.replace("/" + url.split("/")[-1], "")
        webp_url = base_url + "/photos-webp-aid-%s.html" % cid

        response = await async_request("GET", webp_url)
        return parse_image_urls(response.text, webp_url)

    async def _fetch_info(self, url, **kwargs) -> ComicInfo:
        cid = _require_cid(url)
        response = await async_request("GET", url)
        image_urls = await self._get_image_urls(url)
        return parse_comic_info(response.text, url, cid, image_urls)
