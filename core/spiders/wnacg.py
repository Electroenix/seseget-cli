from bs4 import BeautifulSoup
from core.metadata.comic import ChapterInfo, ComicInfo
from core.utils.file_utils import *
from core.utils.trace import *
from core.request import seserequest as ssreq
from core.config import path
from core.utils.file_process import create_source_info_file


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

    soup = BeautifulSoup(response.text, 'html.parser')

    soup_bodywrap = soup.find('div', attrs={'id': 'bodywrap'})
    comic_title = soup_bodywrap.find("h2").string
    comic_cover_url = "https://" + soup_bodywrap.find("img").get("src").lstrip("/")

    soup_info = soup_bodywrap.find("div", attrs={"class": "asTBcell uwconn"})
    tag_soup_list = soup_info.find_all("a", attrs={"class": "tagshow"})

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

    soup_uinfo = soup_bodywrap.find("div", attrs={"class": "asTBcell uwuinfo"})
    comic_author = soup_uinfo.find("p").string

    comic_chapter = ChapterInfo()
    comic_chapter.title = comic_title
    comic_chapter.id = 1
    comic_chapter.metadata.title = comic_title
    comic_chapter.metadata.language = comic_lang
    comic_chapter.metadata.creator = comic_author
    comic_chapter.metadata.subjects = comic_tag_list
    comic_chapter.metadata.description = comic_desc
    comic_chapter.print_info()

    comic_info.view_url = url
    comic_info.cid = cid
    comic_info.cover = comic_cover_url
    comic_info.series_title = comic_title
    comic_info.author = comic_author
    comic_info.genres = comic_tag_list
    comic_info.description = comic_desc
    comic_info.chapter_list.append(comic_chapter)


def download(url, chapter=None):
    # 请求漫画详细信息
    comic_info = ComicInfo()
    get_comic_info(url, comic_info)
    comic_info.print_info()
    SESE_PRINT("系列:%s" % comic_info.series_title)
    SESE_PRINT("作者:%s" % comic_info.author)
    SESE_PRINT("标签:%s" % comic_info.genres)
    SESE_PRINT("获取到%d个章节" % len(comic_info.chapter_list))

    save_dir = path.wnacg_data_local_path
    comic_dir = save_dir + "/" + make_filename_valid(comic_info.series_title)
    if not os.path.exists(save_dir):
        os.mkdir(save_dir)
    if not os.path.exists(comic_dir):
        os.mkdir(comic_dir)

    chapter_index = 1
    for c in comic_info.chapter_list:
        epub_name = make_filename_valid(comic_info.series_title) + "_%03d.epub" % chapter_index
        epub_path = comic_dir + "/" + epub_name

        image_urls = get_image_url_list(url)

        # 创建下载任务
        SESE_PRINT("\r\n正在下载第%d章" % c.id)
        task_name = comic_info.series_title + "_%03d_" % chapter_index
        ssreq.download_task(task_name, ssreq.download_epub_by_images, epub_path, image_urls, c.metadata)

        # 创建source.txt文件保存下载地址
        create_source_info_file(comic_dir, comic_info)

        chapter_index = chapter_index + 1


