import base64
import json
import os
import re
from typing import Dict
import jmcomic
from bs4 import BeautifulSoup
import shutil
from jmcomic import JmOption, JmDownloader, DirRule, JmHtmlClient
from core.metadata.comic import ChapterInfo, ComicInfo, comic_to_epub
from core.request import seserequest as ssreq
from core.config import path
from core.utils.file_utils import *
from core.utils.trace import *
from core.config.config_manager import config
from core.request.downloadtask import ProgressCallback


class SeseJmDownloader(JmDownloader):
    """继承JmDownloader类，加入漫画下载过程追踪和处理功能"""
    def __init__(self, option: JmOption):
        super().__init__(option)
        self.progress_callback: ProgressCallback = None

    def before_photo(self, photo: jmcomic.JmPhotoDetail):
        jmcomic.jm_log('photo.before',
                       f'开始下载章节: {photo.id} ({photo.album_id}[{photo.index}/{len(photo.from_album)}]), '
                       f'标题: [{photo.name}], '
                       f'图片数为[{len(photo)}]'
                       )
        if self.progress_callback is not None:
            self.progress_callback(photo.name, total=len(photo), status="downloading")

    def after_photo(self, photo: jmcomic.JmPhotoDetail):
        jmcomic.jm_log('photo.after',
                       f'章节下载完成: [{photo.id}] ({photo.album_id}[{photo.index}/{len(photo.from_album)}])')
        if self.progress_callback is not None:
            self.progress_callback(photo.name, status="OK")

    def after_image(self, image: jmcomic.JmImageDetail, img_save_path):
        # jmcomic.jm_log('image.after',
        #                f'图片下载完成: {image.tag}, [{image.img_url}] → [{img_save_path}]')
        if self.progress_callback is not None:
            self.progress_callback(image.from_photo.name, new_downloaded=1)


class SeseJmOption(JmOption):
    def __init__(self, dir_rule: Dict, download: Dict, client: Dict, plugins: Dict):
        super().__init__(dir_rule, download, client, plugins)

    @classmethod
    def default(cls) -> 'JmOption':
        option = cls.construct({})
        try:
            option.update_cookies(json.loads(config["jmcomic"]["login"]["cookie"]))
        except json.JSONDecodeError:
            SESE_TRACE(LOG_WARNING, "load jmcomic cookie failed!")
        #option.client['domain'] = ["18comic.vip"]
        #option.client['impl'] = "html"
        option.plugins['login'] = [{'plugin': 'login', 'kwargs': {'username': config["jmcomic"]["login"]["username"], 'password': config["jmcomic"]["login"]["password"]}}]
        return option


# 使用自定义JmDownloader类
jmcomic.JmModuleConfig.CLASS_DOWNLOADER = SeseJmDownloader
jm_option = SeseJmOption.default()


def jm_login():
    try:
        if config["jmcomic"]["login"]["username"] and config["jmcomic"]["login"]["password"]:
            jm_option.call_all_plugin("login")
            cookie = jm_option.client.src_dict["postman"]["meta_data"]["cookies"]
            if cookie:
                config["jmcomic"]["login"]["cookie"] = json.dumps(cookie)
    except Exception as result:
        SESE_TRACE(LOG_WARNING, f"JM登录失败, info: {result}")


def get_comic_info(url, comic_info):
    cid = ""
    match = re.search(r"(?:album|photo)/(\d+)", url)
    if match:
        cid = match.group(1)

    # 生成详情页url
    url = f"/album/{cid}"

    # 请求详情页
    jm_login()
    client = jm_option.new_jm_client(impl=JmHtmlClient)
    response = client.get_jm_html(url)

    html_encode = re.search(r"const html = base64DecodeUtf8\(\"([\s\S].*?)\"\);", response.text).group(1)
    html = base64.b64decode(html_encode).decode()
    soup = BeautifulSoup(html, 'html.parser')

    # 关键元素
    container = soup.find('div', attrs={'class': 'container'})
    panel_body = container.find_all('div', attrs={'class': 'panel-body'})[1]
    cover_soup = panel_body.find("div", attrs={"id": "album_photo_cover"}).find("img", attrs={"itemprop": "image"})
    web_tags_tag_list = panel_body.find("span", attrs={"data-type": "tags"}).find_all("a", attrs={"name": "vote_"})
    author_soup = panel_body.find("span", attrs={"data-type": "author"}).find_all("a")
    descrip_soup = panel_body.find("h2", text=re.compile(r"叙述："))
    date_published_soup = panel_body.find("span", attrs={"itemprop": "datePublished"}, text=re.compile(r"上架日期"))

    comic_title = soup.find("h1").string
    comic_cover_url = cover_soup.get("src")
    authors = []
    for author_element in author_soup:
        authors.append(author_element.string)
    comic_author = " & ".join(authors)
    comic_desc = descrip_soup.string.lstrip().removeprefix("叙述：")
    comic_date = date_published_soup.get("content")

    comic_tag_list = []
    for t in web_tags_tag_list:
        comic_tag_list.append(t.string)

    comic_lang = "zh"
    if "中文" in comic_tag_list:
        comic_lang = "zh"
    elif "日文" in comic_tag_list:
        comic_lang = "ja"
    elif "英文" in comic_tag_list:
        comic_lang = "en"

    comic_chapter = ChapterInfo()
    comic_chapter.title = comic_title
    comic_chapter.id = 1
    comic_chapter.metadata.title = comic_title
    comic_chapter.metadata.language = comic_lang
    comic_chapter.metadata.creator = comic_author
    comic_chapter.metadata.subjects = comic_tag_list
    comic_chapter.metadata.description = comic_desc
    comic_chapter.metadata.date = comic_date
    comic_chapter.print_info()

    comic_info.view_url = url
    comic_info.cid = cid
    comic_info.cover = comic_cover_url
    comic_info.series_title = comic_title
    comic_info.author = comic_author
    comic_info.genres = comic_tag_list
    comic_info.description = comic_desc
    comic_info.chapter_list.append(comic_chapter)


def download_jmcomic(file_name, url, metadata, progress_callback: ProgressCallback = None):
    cid = ""
    match = re.search(r"(?:album|photo)/(\d+)", url)
    if match:
        cid = match.group(1)

    comic_dir = os.path.dirname(file_name)
    comic_title = os.path.splitext(file_name)[0].split("/")[-1]
    image_temp_dir_path = comic_dir + "/" + comic_title

    if not os.path.exists(image_temp_dir_path):
        os.mkdir(image_temp_dir_path)

    if progress_callback:
        progress_callback(status="downloading")

    # 创建option
    jm_option.dir_rule = DirRule("Bd", image_temp_dir_path)

    # 创建downloader并下载
    downloader = SeseJmDownloader(jm_option)
    downloader.progress_callback = progress_callback  # 传递进度回调给downloader
    print("int(cid):", int(cid))
    downloader.download_album(int(cid))

    if progress_callback:
        progress_callback(status="转换中")

    # 下载完成，生成epub文件
    comic_to_epub(file_name, image_temp_dir_path, metadata)

    if progress_callback:
        progress_callback(status="OK")



def download(url):
    comic_info = ComicInfo()
    get_comic_info(url, comic_info)
    comic_info.print_info()
    SESE_PRINT("系列:%s" % comic_info.series_title)
    SESE_PRINT("作者:%s" % comic_info.author)
    SESE_PRINT("标签:%s" % comic_info.genres)
    SESE_PRINT("获取到%d个章节" % len(comic_info.chapter_list))

    save_dir = path.jmcomic_data_local_path
    comic_dir = save_dir + "/" + make_filename_valid(comic_info.series_title)
    if not os.path.exists(save_dir):
        os.mkdir(save_dir)
    if not os.path.exists(comic_dir):
        os.mkdir(comic_dir)

    chapter_index = 1
    for c in comic_info.chapter_list:
        epub_name = make_filename_valid(comic_info.series_title) + "_%03d.epub" % chapter_index
        epub_path = comic_dir + "/" + epub_name

        # 创建下载任务
        SESE_PRINT("\r\n正在下载第%d章" % c.id)
        task_name = comic_info.series_title + "_%03d_" % chapter_index
        ssreq.download_task(task_name, download_jmcomic, epub_path, url, c.metadata)

        chapter_index = chapter_index + 1
