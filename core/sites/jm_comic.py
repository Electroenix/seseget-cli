import base64
import json
import os
import re
from typing import Dict, List
import jmcomic
import requests
from bs4 import BeautifulSoup
from common import Postman
from jmcomic import JmOption, JmDownloader, DirRule, JmHtmlClient, JmApiClient, catch_exception, JmImageDetail, jm_log
from core.metadata.comic import ChapterInfo, ComicInfo
from core.request.fetcher import FetcherRegistry, ComicFetcher
from core.utils.file_process import make_comic
from core.request import seserequest as ssreq
from core.config import path
from core.utils.file_utils import *
from core.utils.trace import *
from core.config.config_manager import config
from core.request.downloadtask import TaskDLProgress, ProgressStatus


class JMChapterInfo(ChapterInfo):
    def __init__(self):
        super().__init__()
        self.url = ""   # 章节的url


class JMComicInfo(ComicInfo):
    def __init__(self):
        super().__init__()
        self.chapter_list: list[JMChapterInfo] = []


class SeseJmStreamResponse:
    """包装JM请求的响应体，内部使用Stream方式读取响应并更新进度，且支持非Stream的调用属性"""

    def __init__(self, response):
        self._response = response
        self._content = b""
        self._text = None
        self._json = None
        self._encoding = response.encoding

    def iter_content(self, chunk_size=1024):
        for chunk in self._response.iter_content(chunk_size=chunk_size):
            if chunk:
                self._content += chunk
                yield chunk

    @property
    def content(self):
        """模拟response.content属性"""
        return self._content

    @property
    def text(self):
        """模拟response.text属性"""
        # 解码内容
        self._text = self._content.decode(
            self._encoding or 'utf-8',
            errors='replace'
        )

        return self._text

    def json(self, **kwargs):
        """解析JSON响应（基于已加载的内容）"""
        if self._json is None:
            try:
                self._json = json.loads(self.text, **kwargs)
            except json.JSONDecodeError:
                try:
                    self._json = json.loads(self._content.decode('utf-8', errors='replace'), **kwargs)
                except json.JSONDecodeError as e:
                    raise requests.exceptions.JSONDecodeError(
                        f"Failed to parse JSON: {e}",
                        doc=self.text
                    )
        return self._json

    def __getattr__(self, name):
        """代理其他属性到原始响应对象"""
        return getattr(self._response, name)


class SeseJmClient(JmApiClient):
    """自定义 JM Client, 继承JmApiClient, 增加了下载进度功能"""
    client_key = 'sese_jm_client'

    def __init__(self, postman: Postman, domain_list: List[str], **kwargs):
        super().__init__(postman, domain_list)
        self.progress: TaskDLProgress | None = None

    def set_progress(self, progress: TaskDLProgress):
        self.progress = progress

    def request_with_retry(self,
                           request,
                           url,
                           domain_index=0,
                           retry_count=0,
                           callback=None,
                           **kwargs,
                           ):
        """
        支持重试和切换域名的机制

        如果url包含了指定域名，则不会切换域名，例如图片URL。

        如果需要拿到域名进行回调处理，可以重写 self.update_request_with_specify_domain 方法，例如更新headers

        :param request: 请求方法
        :param url: 图片url / path (/album/xxx)
        :param domain_index: 域名下标
        :param retry_count: 重试次数
        :param callback: 回调，可以接收resp返回新的resp，也可以抛出异常强制重试
        :param kwargs: 请求方法的kwargs
        """
        if domain_index >= len(self.domain_list):
            return self.fallback(request, url, domain_index, retry_count, **kwargs)

        url_backup = url

        if url.startswith('/'):
            # path → url
            domain = self.domain_list[domain_index]
            url = self.of_api_url(url, domain)

            self.update_request_with_specify_domain(kwargs, domain)

            jm_log(self.log_topic(), self.decode(url))
        else:
            # 图片url
            self.update_request_with_specify_domain(kwargs, None, True)

        if domain_index != 0 or retry_count != 0:
            jm_log(f'req.retry',
                   ', '.join([
                       f'次数: [{retry_count}/{self.retry_times}]',
                       f'域名: [{domain_index} of {self.domain_list}]',
                       f'路径: [{url}]',
                       f'参数: [{kwargs if "login" not in url else "#login_form#"}]'
                   ])
                   )

        try:
            # 增加进度更新
            resp = None
            if self.progress is None:
                resp = request(url, **kwargs)
            else:
                STREAM_REQUEST = False
                if STREAM_REQUEST:
                    # 此处原本用来支持实时更新下载进度的，后来发现JM图片响应头没有'Content-Length'，无法计算下载进度，暂时保留这部分代码
                    # if "stream" not in kwargs:
                    #     kwargs["stream"] = True
                    # resp = request(url, **kwargs)
                    # try:
                    #     total_size = int(resp.headers['Content-Length'])
                    #     self.progress.set_total(url, total_size)
                    # except Exception as e:
                    #     SESE_TRACE(LOG_WARNING, f"resp header no 'Content-Length', url[{url}]")
                    #     SESE_PRINT(f"{resp.headers}")
                    #
                    # resp = SeseJmStreamResponse(resp)
                    # for chunk in resp.iter_content():
                    #     self.progress.update(url, len(chunk))
                    pass
                else:
                    resp = request(url, **kwargs)
                    self.progress.set_total(url, len(resp.content))
                    self.progress.update(url, len(resp.content))

            # 回调，可以接收resp返回新的resp，也可以抛出异常强制重试
            if callback is not None:
                resp = callback(resp)

            # 依然是回调，在最后返回之前，还可以判断resp是否重试
            resp = self.raise_if_resp_should_retry(resp)

            return resp
        except Exception as e:
            if self.retry_times == 0:
                raise e

            self.before_retry(e, kwargs, retry_count, url)

        if retry_count < self.retry_times:
            return self.request_with_retry(request, url_backup, domain_index, retry_count + 1, callback, **kwargs)
        else:
            return self.request_with_retry(request, url_backup, domain_index + 1, 0, callback, **kwargs)


class SeseJmDownloader(JmDownloader):
    """继承JmDownloader类，加入漫画下载过程追踪和处理功能"""

    def __init__(self, option: JmOption, progress: TaskDLProgress):
        super().__init__(option)
        self.client: SeseJmClient = option.new_jm_client(impl=SeseJmClient)
        self.progress: TaskDLProgress = progress
        try:
            self.client.set_progress(self.progress)
        except Exception as e:
            SESE_TRACE(LOG_WARNING, f"Client注入progress失败！info: {e}")
            raise e

    @catch_exception
    def download_by_image_detail(self, image: JmImageDetail):
        img_save_path = self.option.decide_image_filepath(image)

        image.save_path = img_save_path
        image.exists = jmcomic.file_exists(img_save_path)

        self.before_image(image, img_save_path)

        if image.skip:
            self.after_image(image, img_save_path)
            return

        # let option decide use_cache and decode_image
        use_cache = self.option.decide_download_cache(image)
        decode_image = self.option.decide_download_image_decode(image)

        # skip download
        if use_cache is True and image.exists:
            self.after_image(image, img_save_path)
            return

        self.client.download_by_image_detail(
            image,
            img_save_path,
            decode_image=decode_image,
        )

        self.after_image(image, img_save_path)

    def before_photo(self, photo: jmcomic.JmPhotoDetail):
        if self.progress is not None:
            self.progress.set_progress_count(len(photo))

    def after_photo(self, photo: jmcomic.JmPhotoDetail):
        pass

    def before_image(self, image: jmcomic.JmImageDetail, img_save_path):
        self.progress.add_progress(image.img_url)
        pass

    def after_image(self, image: jmcomic.JmImageDetail, img_save_path):
        pass


class SeseJmOption(JmOption):
    """自定义JmOption, 修改部分默认配置"""

    def __init__(self,
                 dir_rule: Dict,
                 download: Dict,
                 client: Dict,
                 plugins: Dict,
                 filepath=None,
                 call_after_init_plugin=True,
                 ):
        super().__init__(dir_rule, download, client, plugins, filepath, call_after_init_plugin)

    @classmethod
    def default(cls) -> 'JmOption':
        option = cls.construct({})
        try:
            option.update_cookies(json.loads(config["jmcomic"]["login"]["cookie"]))
        except json.JSONDecodeError:
            SESE_TRACE(LOG_DEBUG, "load jmcomic cookie failed!")
            pass
        # option.client['domain'] = ["18comic.vip"]
        # option.client['impl'] = "sese_jm_client"
        option.plugins['login'] = [{'plugin': 'login', 'kwargs': {'username': config["jmcomic"]["login"]["username"],
                                                                  'password': config["jmcomic"]["login"]["password"]}}]
        return option


def seseJmLog(topic: str, msg: str):
    SESE_PRINT(f"[{topic}] {msg}")


# jmcomic自定义配置
jmcomic.JmModuleConfig.CLASS_DOWNLOADER = SeseJmDownloader
jmcomic.JmModuleConfig.EXECUTOR_LOG = seseJmLog
jmcomic.JmModuleConfig.CLASS_OPTION = SeseJmOption
jmcomic.JmModuleConfig.register_client(SeseJmClient)


@FetcherRegistry.register("jmcomic")
class JmComicFetcher(ComicFetcher):
    site_dir = path.JMCOMIC_DATA_LOCAL_DIR

    def __init__(self):
        super().__init__()
        self.jm_option = jmcomic.JmModuleConfig.option_class().default()

    def jm_login(self):
        try:
            if config["jmcomic"]["login"]["username"] and config["jmcomic"]["login"]["password"]:
                self.jm_option.call_all_plugin("login")
                cookie = self.jm_option.client.src_dict["postman"]["meta_data"]["cookies"]
                if cookie:
                    config["jmcomic"]["login"]["cookie"] = json.dumps(cookie)
        except Exception as result:
            SESE_TRACE(LOG_WARNING, f"JM登录失败, info: {result}")

    def _fetch_info(self, url, **kwargs):
        chapter_id_list = kwargs.get("chapter_id_list", None)

        cid = ""
        match = re.search(r"(?:album|photo)/(\d+)", url)
        if match:
            cid = match.group(1)

        # 生成详情页url
        url = f"/album/{cid}"

        # 请求详情页
        self.jm_login()
        client = self.jm_option.new_jm_client(impl=JmHtmlClient)
        response = client.get_jm_html(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # 关键元素
        panel_body = soup.find_all('div', attrs={'class': 'panel-body'})[1]
        cover_soup = panel_body.find("div", attrs={"id": "album_photo_cover"}).find("img", attrs={"itemprop": "image"})
        web_tags_tag_list = panel_body.find("span", attrs={"data-type": "tags"}).find_all("a", attrs={"name": "vote_"})
        author_soup = panel_body.find("span", attrs={"data-type": "author"}).find_all("a")
        descrip_soup = panel_body.find("h2", text=re.compile(r"叙述："))
        date_published_soup = panel_body.find("span", attrs={"itemprop": "datePublished"}, text=re.compile(r"上架日期"))
        episode_soup = panel_body.find("div", attrs={"class": "episode"})

        comic_title = soup.find("h1").string
        comic_cover_url = cover_soup.get("src")
        authors = []
        for author_element in author_soup:
            authors.append(author_element.string)
        comic_author = " & ".join(authors)
        comic_desc = descrip_soup.string.lstrip().removeprefix("叙述：")
        comic_date = date_published_soup.get("content")
        date_match = re.search(r"^(\d+?)-(\d+?)-(\d+?)$", comic_date)

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

        photo_list = []
        if episode_soup:
            # 如果存在章节列表，则收集所有章节信息
            photo_soups = episode_soup.find_all("a")
            for photo_soup in photo_soups:
                photo_info = {
                    "href": photo_soup.get("href"),
                    "title": photo_soup.find("h3").string
                }
                photo_list.append(photo_info)
        else:
            # 如果不存在章节列表，则设置唯一的章节信息
            photo_info = {
                "href": url,
                "title": comic_title
            }
            photo_list.append(photo_info)

        comic_info = JMComicInfo()
        comic_info.view_url = url
        comic_info.cid = cid
        comic_info.cover = comic_cover_url
        comic_info.title = comic_title
        comic_info.author = comic_author
        comic_info.genres = comic_tag_list
        comic_info.description = comic_desc

        # 若未指定章节，则默认下载全部章节
        if not chapter_id_list:
            chapter_id_list = range(1, len(photo_list) + 1)

        for index, photo_info in enumerate(photo_list):
            chapter_id = index + 1
            if chapter_id in chapter_id_list:
                comic_chapter = JMChapterInfo()
                comic_chapter.id = chapter_id
                comic_chapter.metadata.series = comic_title
                comic_chapter.metadata.title = make_filename_valid(photo_info["title"])
                comic_chapter.metadata.number = chapter_id
                comic_chapter.metadata.language = comic_lang
                comic_chapter.metadata.creator = comic_author
                comic_chapter.metadata.subjects = comic_tag_list
                comic_chapter.metadata.description = comic_desc
                comic_chapter.metadata.year = date_match.group(1)
                comic_chapter.metadata.month = date_match.group(2)
                comic_chapter.metadata.day = date_match.group(3)
                comic_chapter.comic_info = comic_info
                comic_chapter.url = photo_info["href"]
                comic_chapter.title = make_filename_valid(photo_info["title"])

                comic_info.chapter_list.append(comic_chapter)

        return comic_info

    def download_jmcomic(self, save_dir: str, comic_title: str, url: str, chapter: ChapterInfo,
                         progress: TaskDLProgress = None):
        cid = ""
        match = re.search(r"(?:album|photo)/(\d+)", url)
        if match:
            cid = match.group(1)

        image_temp_dir_path = save_dir + "/" + comic_title

        if not os.path.exists(image_temp_dir_path):
            os.mkdir(image_temp_dir_path)

        if progress:
            progress.init_progress()
            progress.set_status(ProgressStatus.PROGRESS_STATUS_DOWNLOADING)

        # 创建option
        self.jm_option.dir_rule = DirRule("Bd", image_temp_dir_path)

        # 创建downloader并下载
        downloader = SeseJmDownloader(self.jm_option.copy_option(), progress)  # 传递进度回调给downloader
        downloader.download_photo(int(cid))
        if downloader.has_download_failures:
            SESE_TRACE(LOG_ERROR, "JM下载失败！")
            progress.set_status(ProgressStatus.PROGRESS_STATUS_DOWNLOAD_ERROR)
            return -1

        if progress:
            progress.set_status(ProgressStatus.PROGRESS_STATUS_PROCESS)

        # 下载完成，生成漫画文件
        make_comic(save_dir, comic_title, image_temp_dir_path, chapter.metadata)

        if progress:
            progress.set_status(ProgressStatus.PROGRESS_STATUS_DOWNLOAD_OK)

        return 0

    def _download_comic_capter(self, comic_title: str, chapter: ChapterInfo, progress: ssreq.TaskDLProgress = None):
        if not isinstance(chapter, JMChapterInfo):
            raise TypeError(f"chapter类型({type(chapter)})错误！不是JMChapterInfo")

        comic_info = chapter.comic_info
        with self.chapter_lock:
            res = self.download_jmcomic(comic_info.comic_dir, comic_title, chapter.url, chapter, progress)
        return res
