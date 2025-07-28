from typing import List

from bs4 import BeautifulSoup
from core.metadata.comic import ChapterInfo, ComicInfo
from core.request.fetcher import FetcherRegistry, ComicFetcher
from core.utils.file_utils import *
from core.request import seserequest as ssreq
from core.config import path


@FetcherRegistry.register("wnacg")
class WnacgFetcher(ComicFetcher):
    site_dir = path.WNACG_DATA_LOCAL_DIR

    def _get_image_urls(self, url: str) -> List[str]:
        cid = re.search(r"\d+(?=\.html)", url).group()
        base_url = url.replace("/" + url.split("/")[-1], "")
        webp_url = base_url + "/photos-webp-aid-%s.html" % cid

        response = ssreq.request("GET", webp_url)

        image_list_str = re.search(r"(?<=var imglist = )\[[\s\S]+]", response.text).group()
        image_list_str = image_list_str.replace("\\", "")
        image_list_str = image_list_str.replace("fast_img_host+", "")
        image_url_list = re.findall(r"(?<=url: \")[\s\S]+?(?=\")", image_list_str)

        for i in range(len(image_url_list)):
            if "//" in image_url_list[i]:
                image_url_list[i] = "https:" + image_url_list[i]
            else:
                #image_url_list[i] = base_url + image_url_list[i]
                image_url_list.pop(i)

        return image_url_list

    def _fetch_info(self, url, **kwargs) -> ComicInfo:
        cid = re.search(r"\d+(?=\.html)", url).group()
        base_url = url.replace("/" + url.split("/")[-1], "")

        # 请求详情页
        response = ssreq.request("GET", url)

        # 关键元素
        soup = BeautifulSoup(response.text, 'html.parser')
        soup_userwrap = soup.find_all('div', attrs={'id': 'bodywrap'})[0]
        soup_cc = soup.find_all('div', attrs={'id': 'bodywrap'})[1]
        soup_info = soup_userwrap.find("div", attrs={"class": "asTBcell uwconn"})
        tag_soup_list = soup_info.find_all("a", attrs={"class": "tagshow"})
        soup_uinfo = soup_userwrap.find("div", attrs={"class": "asTBcell uwuinfo"})
        soup_date = soup_cc.find('div', text=re.compile(r"上傳於"))

        comic_title = soup_userwrap.find("h2").string
        comic_cover_url = "https://" + soup_userwrap.find("img").get("src").lstrip("/")

        comic_tag_list = []
        for t in tag_soup_list:
            comic_tag_list.append(t.contents[0].string)

        comic_type = re.search(r"(?<=<label>分類：)[\s\S]+?(?=</label>)", str(soup_info)).group()
        comic_tag_list.append(comic_type)

        comic_lang = "zh"
        if "日語" in comic_type:
            comic_lang = "ja"
        elif "漢化" in comic_type:
            comic_lang = "zh"

        comic_desc = re.search(r"(?<=<p>簡介：)[\s\S]*?(?=</p>)", str(soup_info)).group()
        comic_author = soup_uinfo.find("p").string
        date_match = re.search(r"(\d+)-(\d+)-(\d+)", soup_date.string)

        comic_info = ComicInfo()
        comic_info.view_url = url
        comic_info.cid = cid
        comic_info.cover = comic_cover_url
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

        # 获取章节所有图片的url
        comic_chapter.image_urls = self._get_image_urls(url)

        comic_info.chapter_list.append(comic_chapter)

        return comic_info
