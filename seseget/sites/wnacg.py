import os
import re
from typing import List

from ..config.path import DATA_DIR
from ..request.errors import SiteParseError
from ..request.fetcher import ChapterInfo, ComicInfo, FetcherRegistry, ComicFetcher
from ..request.requests import async_request
from .parser import SiteParser


def _require_cid(url: str) -> str:
    match = re.search(r"\d+(?=\.html)", url)
    if not match:
        raise SiteParseError(
            "未匹配到作品 ID（URL 期望匹配 /<数字>.html）",
            site="wnacg",
            url=url,
        )
    return match.group()


def parse_image_urls(html: str, source_url: str = "") -> List[str]:
    """从 wnacg 的 imglist 脚本中提取图片 URL。"""
    parser = SiteParser(html, site="wnacg", url=source_url)
    image_list_match = re.search(r"(?<=var imglist = )\[[\s\S]+]", html)
    if image_list_match is None:
        parser.fail("image_list_match 匹配失败")

    image_list_str = image_list_match.group()
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
    parser = SiteParser(html, site="wnacg", url=url)

    bodywraps = parser.find_all(name="div",
        attrs={"id": "bodywrap"},
    )
    if len(bodywraps) < 2:
        parser.fail(
            f"bodywraps 数量不足，期望至少 2 个，实际 {len(bodywraps)} 个"
        )

    soup_userwrap = bodywraps[0]
    soup_cc = bodywraps[1]
    soup_info = parser.find(node=soup_userwrap,
        name="div",
        attrs={"class": "asTBcell uwconn"},
    )
    soup_uinfo = parser.find(node=soup_userwrap,
        name="div",
        attrs={"class": "asTBcell uwuinfo"},
    )

    title_element = parser.find(node=soup_userwrap, name="h2")
    cover_element = parser.find(node=soup_userwrap, name="img")
    author_element = parser.find(node=soup_uinfo, name="p")
    date_element = parser.find(node=soup_cc,
        name="div",
        string=re.compile(r"上傳於"),
    )

    cover_src = cover_element.get("src")
    if not isinstance(cover_src, str):
        parser.fail("cover_element 的 src 为空")

    comic_title = title_element.get_text(strip=True)
    if not comic_title:
        parser.fail("comic_title 内容为空")

    comic_cover_url = "https://" + cover_src.lstrip("/")
    comic_author = author_element.get_text(strip=True)
    if not comic_author:
        parser.fail("comic_author 内容为空")

    comic_tag_list = []
    for tag in parser.find_all(node=soup_info,
        name="a",
        attrs={"class": "tagshow"},
    ):
        text = tag.get_text(strip=True)
        if text:
            comic_tag_list.append(text)

    type_match = re.search(
        r"(?<=<label>分類：)[\s\S]+?(?=</label>)",
        str(soup_info),
    )
    if type_match is None:
        parser.fail("type_match 匹配失败")
    comic_type = type_match.group().strip()
    comic_tag_list.append(comic_type)

    comic_lang = "zh"
    if "日語" in comic_type:
        comic_lang = "ja"
    elif "漢化" in comic_type:
        comic_lang = "zh"

    desc_element = parser.find(node=soup_info,
        name="p",
        string=re.compile(r"簡介："),
    )
    comic_desc = desc_element.get_text().split("簡介：", 1)[-1].strip()

    date_match = re.search(r"(\d+)-(\d+)-(\d+)", date_element.get_text())
    if date_match is None:
        parser.fail("date_match 匹配失败")

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
    comic_chapter.metadata.number = "1"
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
