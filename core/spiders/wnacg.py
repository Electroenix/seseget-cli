from bs4 import BeautifulSoup
from core.metadata.comic import ChapterInfo, ComicInfo
from core.utils.file_utils import *
from core.utils.trace import *
from core.request import seserequest as ssreq
from core.config import path
from core.utils.file_process import make_source_info_file


headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
}


def get_image_url_list(url):
    cid = re.search(r"\d+(?=\.html)", url).group()
    base_url = url.replace("/" + url.split("/")[-1], "")
    webp_url = base_url + "/photos-webp-aid-%s.html" % cid

    response = ssreq.request("GET", webp_url, headers=headers)

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


def get_comic_info(url, comic_info):
    cid = re.search(r"\d+(?=\.html)", url).group()
    base_url = url.replace("/" + url.split("/")[-1], "")

    # 请求详情页
    response = ssreq.request("GET", url, headers=headers)

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

    comic_info.view_url = url
    comic_info.cid = cid
    comic_info.cover = comic_cover_url
    comic_info.title = comic_title
    comic_info.author = comic_author
    comic_info.genres = comic_tag_list
    comic_info.description = comic_desc
    comic_info.chapter_list.append(comic_chapter)


def download(url, chapter=None):
    # 请求漫画详细信息
    comic_info = ComicInfo()
    get_comic_info(url, comic_info)
    comic_info.print_info()

    save_dir = path.wnacg_data_local_path
    comic_dir = save_dir + "/" + make_filename_valid(comic_info.title)
    if not os.path.exists(save_dir):
        os.mkdir(save_dir)
    if not os.path.exists(comic_dir):
        os.mkdir(comic_dir)

    for c in comic_info.chapter_list:

        image_urls = get_image_url_list(url)

        # 创建下载任务
        SESE_PRINT("\r\n正在下载第%d章" % c.id)
        comic_title = make_filename_valid(comic_info.title + "_%03d" % c.id)
        task_name = comic_title
        ssreq.download_task(task_name, ssreq.download_comic_capter, comic_dir, comic_title, image_urls, c)

        # 创建source.txt文件保存下载地址
        make_source_info_file(comic_dir, comic_info)


