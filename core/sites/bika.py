import time
import hmac
from hashlib import sha256
from typing import List
from urllib.parse import urlparse, parse_qs
import core.config.path
from core.config.config_manager import config
from core.request.fetcher import FetcherRegistry, ComicFetcher
from core.utils.trace import *
from core.metadata.comic import ChapterInfo, ComicInfo
from core.request import seserequest as ssreq
from core.utils.file_utils import *


# 用来存储从bika获取到的数据
class BikaComicInfo:
    def __init__(self):
        self.view_url = ""
        self.title = ""
        self.author = ""
        self.genres = []
        self.description = ""
        self.chapter: List[dict] = []
        self.cover = ""


HEADERS_API = {
    "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    "nonce": "",
    "app-uuid": "webUUID",
    "time": "",
    "sec-ch-ua-mobile": "?0",
    "authorization": "",
    "app-channel": "1",
    "app-platform": "android",
    "content-type": "application/json; charset=UTF-8",
    "accept": "application/vnd.picacomic.com.v1+json",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "signature": "",
    "image-quality": "original",
    "sec-ch-ua-platform": "\"Windows\"",
    "origin": "https://manhuabika.com",
    "sec-fetch-site": "cross-site",
    "sec-fetch-mode": "cors",
    "sec-fetch-dest": "empty",
    "accept-encoding": "gzip, deflate",
    "accept-language": "zh-CN,zh-TW;q=0.9,zh;q=0.8,en-GB;q=0.7,en;q=0.6,zh-MO;q=0.5,zh-HK;q=0.4,ja-JP;q=0.3,ja;q=0.2",
}

HEADERS_IMAGE = {
    'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    'sec-ch-ua-mobile': '?0',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'sec-ch-ua-platform': '"Windows"',
    'accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
    'sec-fetch-site': 'cross-site',
    'sec-fetch-mode': 'no-cors',
    'sec-fetch-dest': 'image',
    'accept-encoding': 'gzip, deflate',
    'accept-language': 'zh-CN,zh-TW;q=0.9,zh;q=0.8,en-GB;q=0.7,en;q=0.6,zh-MO;q=0.5,zh-HK;q=0.4,ja-JP;q=0.3,ja;q=0.2'
}

host = "go2778.com"
base_url = "https://api." + host + "/"
applekillflag = "C69BAF41DA5ABD1FFEDC6D2FEA56B"
appleversion = r"~d}$Q7$eIni=V)9\RK/P.RM4;9[7|@/CA}b~OW!3?EV`:<>M7pddUBL5n|0/*Cn"


# comic_save_path = core.config.path.bika_data_local_path  # 漫画保存路径


class BikaClient:
    def __init__(self):
        self.context = BikaComicInfo()

    def get_token(self):
        return config["bika"]["token"]

    def get_nonce(self):
        return config["bika"]["nonce"]

    def get_signature(self, url, ts, method):
        raw = url.replace(base_url, "") + ts + self.get_nonce() + method + applekillflag
        raw = raw.lower()
        hmac_object = hmac.new(appleversion.encode(), raw.encode(), digestmod=sha256)
        return hmac_object.hexdigest()

    def login(self) -> bool:
        path_name = "auth/sign-in"
        url = base_url + path_name

        data = {
            "email": config["bika"]["username"],
            "password": config["bika"]["password"]
        }

        headers_api = HEADERS_API.copy()
        headers_api["time"] = str(int(time.time()))
        headers_api["nonce"] = self.get_nonce()
        headers_api["signature"] = self.get_signature(path_name, headers_api["time"], "POST")
        response = ssreq.request("POST", url, headers=headers_api, json=data)
        # print(response.text)
        resp_json = response.json()

        if "token" in response.text:
            config["bika"]["token"] = resp_json["data"]["token"]
            return True
        else:
            return False

    def request_api(self, method, path_name):
        url = base_url + path_name
        headers_api = HEADERS_API.copy()
        headers_api["time"] = str(int(time.time()))
        headers_api["authorization"] = self.get_token()
        headers_api["nonce"] = self.get_nonce()
        headers_api["signature"] = self.get_signature(path_name, headers_api["time"], method)

        response = ssreq.request(method, url, headers=headers_api)
        if "unauthorized" in response.text:
            SESE_PRINT("哔咔认证失败，重新登录")
            if self.login():
                headers_api["time"] = str(int(time.time()))
                headers_api["authorization"] = self.get_token()
                headers_api["nonce"] = self.get_nonce()
                headers_api["signature"] = self.get_signature(path_name, headers_api["time"], method)
                response = ssreq.request(method, url, headers=headers_api)
                # print(response.text)
            else:
                SESE_TRACE(LOG_ERROR, "哔咔登录失败")

        return response

    # 获取漫画详情页面的信息
    def get_comic_view_info(self, cid):
        path_name = "comics/" + cid
        response = self.request_api("GET", path_name)
        resp_json = response.json()
        comic_json = resp_json["data"]["comic"]

        self.context.title = comic_json["title"]
        self.context.author = comic_json["author"]
        self.context.genres = list(set(comic_json["categories"] + comic_json["tags"]))
        self.context.description = comic_json["description"]
        self.context.cover = comic_json["thumb"]["path"]

    # 获取漫画章节
    def get_comic_chapter(self, cid, page_cnt=1):
        path_name = "comics/" + cid + "/eps?page=" + str(page_cnt)
        response = self.request_api("GET", path_name)

        resp_json = response.json()
        self.context.chapter = self.context.chapter + resp_json["data"]["eps"]["docs"]
        page_max = int(resp_json["data"]["eps"]["pages"])

        if page_cnt < page_max:
            self.get_comic_chapter(cid, page_cnt + 1)
        else:
            # 获取完所有章节信息后，列表中order是降序的，将列表反转便于后续通过order查找元素，由于order从1开始，在列表前面补位一个和列表index对齐
            self.context.chapter.reverse()
            self.context.chapter.insert(0, {"order": "0", "title": "占位用的，使 chapter order 和列表 index 对齐，方便定位"})

    # 获取漫画章节图片
    def get_comic_chapter_pages(self, cid, chapter_id, page_cnt=1):
        path_name = "comics/" + cid + "/order/" + str(chapter_id) + "/pages?page=" + str(page_cnt)
        response = self.request_api("GET", path_name)

        resp_json = response.json()
        if "pages" in self.context.chapter[chapter_id]:
            self.context.chapter[chapter_id]["pages"] = self.context.chapter[chapter_id]["pages"] + \
                                                        resp_json["data"]["pages"]["docs"]
        else:
            self.context.chapter[chapter_id]["pages"] = resp_json["data"]["pages"]["docs"]

        pages_max = int(resp_json["data"]["pages"]["pages"])
        if page_cnt < pages_max:
            self.get_comic_chapter_pages(cid, chapter_id, page_cnt + 1)

    def get_bika_comic_info(self, cid, chapter_id_list) -> BikaComicInfo:
        # 获取详情页信息
        self.get_comic_view_info(cid)

        # 获取全部章节信息
        self.get_comic_chapter(cid)

        # 若未指定章节，则默认下载全部章节
        if not chapter_id_list:
            chapter_id_list = range(1, len(self.context.chapter))

        for chapter_id in chapter_id_list:
            chapter = self.context.chapter[int(chapter_id)]
            if int(chapter_id) != chapter["order"]:
                raise Exception("哔咔章节号无法匹配！")

            # 获取章节图片信息
            self.get_comic_chapter_pages(cid, chapter["order"])

        return self.context


@FetcherRegistry.register("bika")
class BikaFetcher(ComicFetcher):
    site_dir = core.config.path.BIKA_DATA_LOCAL_DIR

    def _get_image_urls(self, bika_context: BikaComicInfo, chapter: ChapterInfo) -> List[str]:
        # 获取图片url列表
        image_urls = []
        for page in bika_context.chapter[chapter.id]["pages"]:
            # 这里 page["path"] 不用处理也能get到图片，但是看浏览器里地址 “static/” 后面直接跟的文件名，就改成一样吧
            url = page["media"]["fileServer"] + "/static/" + page["media"]["path"].split("/")[-1]
            image_urls.append(url)

        return image_urls

    def get_info(self, url, **kwargs) -> ComicInfo:
        chapter_id_list = kwargs.get("chapter_id_list", None)

        view_url_parse = urlparse(url)
        cid = parse_qs(view_url_parse.query)["cid"][0]
        comic_info = ComicInfo()
        comic_info.view_url = url
        comic_info.cid = cid

        bika_client = BikaClient()
        bika_context = bika_client.get_bika_comic_info(cid, chapter_id_list)

        comic_info.title = bika_context.title
        comic_info.author = bika_context.author
        comic_info.genres = bika_context.genres

        for bika_chapter in bika_context.chapter:
            if "pages" not in bika_chapter:
                SESE_TRACE(LOG_DEBUG, f"无章节图片，跳过")
                continue

            chapter_info = ChapterInfo()
            chapter_info.title = bika_chapter["title"]
            chapter_info.id = bika_chapter["order"]

            chapter_info.metadata.series = bika_context.title
            chapter_info.metadata.title = bika_chapter["title"]
            chapter_info.metadata.number = bika_chapter["order"]
            chapter_info.metadata.creator = bika_context.author
            chapter_info.metadata.subjects = bika_context.genres

            date_match = re.search(r"^(\d+)-(\d+)-(\d+)", bika_chapter["updated_at"])
            chapter_info.metadata.year = date_match.group(1)
            chapter_info.metadata.month = date_match.group(2)
            chapter_info.metadata.day = date_match.group(3)
            chapter_info.comic_info = comic_info

            if "英語 ENG" in bika_context.genres:
                chapter_info.metadata.language = "en"
            elif "生肉" in bika_context.genres:
                chapter_info.metadata.language = "ja"
            else:
                chapter_info.metadata.language = "zh"
            chapter_info.metadata.description = bika_context.description

            # 请求章节图片url列表
            chapter_info.image_urls = self._get_image_urls(bika_context, chapter_info)

            comic_info.chapter_list.append(chapter_info)

        return comic_info
