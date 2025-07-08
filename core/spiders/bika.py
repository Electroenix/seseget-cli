import time
import hmac
import os.path
from hashlib import sha256
from urllib.parse import urlparse, parse_qs
import core.config.path
from core.config.config_manager import config
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
        self.chapter = []
        self.cover = ""


headers_api = {
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

headers_image = {
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
comic_save_path = core.config.path.bika_data_local_path  # 漫画保存路径


def create_context():
    context = BikaComicInfo()
    
    return context


def get_token():
    return config["bika"]["token"]


def get_nonce():
    return config["bika"]["nonce"]


def get_signature(url, ts, method):
    raw = url.replace(base_url, "") + ts + get_nonce() + method + applekillflag
    raw = raw.lower()
    hmac_object = hmac.new(appleversion.encode(), raw.encode(), digestmod=sha256)
    return hmac_object.hexdigest()


def login() -> bool:
    path_name = "auth/sign-in"
    url = base_url + path_name

    data = {
        "email": config["bika"]["username"],
        "password": config["bika"]["password"]
    }

    headers_api["time"] = str(int(time.time()))
    headers_api["nonce"] = get_nonce()
    headers_api["signature"] = get_signature(path_name, headers_api["time"], "POST")
    response = ssreq.request("POST", url, headers=headers_api, json=data)
    # print(response.text)
    resp_json = response.json()

    if "token" in response.text:
        config["bika"]["token"] = resp_json["data"]["token"]
        return True
    else:
        return False


def request_api(method, path_name):
    url = base_url + path_name
    headers_api["time"] = str(int(time.time()))
    headers_api["authorization"] = get_token()
    headers_api["nonce"] = get_nonce()
    headers_api["signature"] = get_signature(path_name, headers_api["time"], method)

    response = ssreq.request(method, url, headers=headers_api)
    if "unauthorized" in response.text:
        SESE_PRINT("哔咔认证失败，重新登录")
        if login():
            headers_api["time"] = str(int(time.time()))
            headers_api["authorization"] = get_token()
            headers_api["nonce"] = get_nonce()
            headers_api["signature"] = get_signature(path_name, headers_api["time"], method)
            response = ssreq.request(method, url, headers=headers_api)
            # print(response.text)
        else:
            SESE_TRACE(LOG_ERROR, "哔咔登录失败")

    return response


# 获取漫画详情页面的信息
def get_comic_view_info(bika_context, cid):
    path_name = "comics/" + cid
    response = request_api("GET", path_name)
    resp_json = response.json()
    comic_json = resp_json["data"]["comic"]

    bika_context.title = comic_json["title"]
    bika_context.author = comic_json["author"]
    bika_context.genres = list(set(comic_json["categories"] + comic_json["tags"]))
    bika_context.description = comic_json["description"]
    bika_context.cover = comic_json["thumb"]["path"]


# 获取漫画章节
def get_comic_chapter(bika_context, cid, page_cnt=1):
    path_name = "comics/" + cid + "/eps?page=" + str(page_cnt)
    response = request_api("GET", path_name)

    resp_json = response.json()
    bika_context.chapter = bika_context.chapter + resp_json["data"]["eps"]["docs"]
    page_max = int(resp_json["data"]["eps"]["pages"])

    if page_cnt < page_max:
        get_comic_chapter(bika_context, cid, page_cnt + 1)
    else:
        # 获取完所有章节信息后，列表中order是降序的，将列表反转便于后续通过order查找元素，由于order从1开始，在列表前面补位一个和列表index对齐
        bika_context.chapter.reverse()
        bika_context.chapter.insert(0, "占位用的，使 chapter order 和列表 index 对齐，方便定位")


# 获取漫画章节图片
def get_comic_chapter_pages(bika_context, cid, chapter_id, page_cnt=1):
    path_name = "comics/" + cid + "/order/" + str(chapter_id) + "/pages?page=" + str(page_cnt)
    response = request_api("GET", path_name)

    resp_json = response.json()
    if "pages" in bika_context.chapter[chapter_id]:
        bika_context.chapter[chapter_id]["pages"] = bika_context.chapter[chapter_id]["pages"] + \
                                                       resp_json["data"]["pages"]["docs"]
    else:
        bika_context.chapter[chapter_id]["pages"] = resp_json["data"]["pages"]["docs"]

    pages_max = int(resp_json["data"]["pages"]["pages"])
    if page_cnt < pages_max:
        get_comic_chapter_pages(bika_context, cid, chapter_id, page_cnt + 1)


def request_comic_info(bika_context, view_url, comic_info, chapter_id_list=None):
    view_url_parse = urlparse(view_url)
    cid = parse_qs(view_url_parse.query)["cid"][0]
    comic_info.view_url = view_url
    comic_info.cid = cid
    bika_context.view_url = view_url

    # 获取详情页信息
    get_comic_view_info(bika_context, cid)
    # 获取全部章节信息
    get_comic_chapter(bika_context, cid)

    comic_info.series_title = bika_context.title
    comic_info.author = bika_context.author
    comic_info.genres = bika_context.genres

    # 若未指定章节，则默认下载全部章节
    if not chapter_id_list:
        chapter_id_list = range(1, len(bika_context.chapter))

    for chapter_id in chapter_id_list:
        # 获取章节图片信息
        get_comic_chapter_pages(bika_context, cid, int(chapter_id))

        chapter_info = ChapterInfo()
        chapter_info.title = bika_context.chapter[int(chapter_id)]["title"]
        chapter_info.id = int(chapter_id)

        chapter_info.metadata.title = bika_context.chapter[int(chapter_id)]["title"]
        chapter_info.metadata.creator = bika_context.author
        chapter_info.metadata.subjects = bika_context.genres

        if "英語 ENG" in bika_context.genres:
            chapter_info.metadata.language = "en"
        elif "生肉" in bika_context.genres:
            chapter_info.metadata.language = "ja"
        else:
            chapter_info.metadata.language = "zh"
        chapter_info.metadata.description = bika_context.description

        comic_info.chapter_list.append(chapter_info)

    return 0


def download(bika_context, url, chapter=None):
    # 请求bika数据
    comic_info = ComicInfo()
    request_comic_info(bika_context, url, comic_info, chapter)
    SESE_PRINT("系列:%s" % comic_info.series_title)
    SESE_PRINT("作者:%s" % comic_info.author)
    SESE_PRINT("标签:%s" % comic_info.genres)
    SESE_PRINT("获取到%d个章节" % len(comic_info.chapter_list))

    comic_dir = str(comic_save_path) + "/" + make_filename_valid(comic_info.series_title)
    if not os.path.exists(comic_save_path):
        os.mkdir(comic_save_path)
    if not os.path.exists(comic_dir):
        os.mkdir(comic_dir)

    chapter_index = 1
    for c in comic_info.chapter_list:
        # 配置下载路径
        epub_name = make_filename_valid(bika_context.title) + "_%03d.epub" % bika_context.chapter[c.id]["order"]
        epub_path = comic_dir + "/" + epub_name

        # 获取图片url列表
        image_urls = []
        for page in bika_context.chapter[c.id]["pages"]:
            # 这里 page["path"] 不用处理也能get到图片，但是看浏览器里地址 “static/” 后面直接跟的文件名，就改成一样吧
            url = page["media"]["fileServer"] + "/static/" + page["media"]["path"].split("/")[-1]
            image_urls.append(url)

        # 创建下载任务
        SESE_PRINT("\r\n正在下载第%d章" % c.id)
        task_name = bika_context.title + "_%03d_" % bika_context.chapter[c.id]["order"] + bika_context.chapter[c.id]["title"]
        ssreq.download_task(task_name, ssreq.download_epub_by_images, epub_path, image_urls, c.metadata)

        chapter_index = chapter_index + 1

