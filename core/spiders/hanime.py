import os
import copy
import re
import json
import html
from bs4 import BeautifulSoup, element
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed

import core.config.path
from core.metadata.video import *
from core.metadata.vsmeta import *
from core.metadata.nfo import *
from core.utils.trace import SESE_PRINT
from core.request import seserequest as ssreq
from core.utils.file_utils import *


headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
}
save_path = core.config.path.hanime_data_local_path + "/"
video_info_cache = VideoInfoCache(10)


# 从html数据中获取数据到metadata
def get_metadata(video_name, soup):
    metadata = VideoMetaData()

    # 提取视频信息到metadata
    metadata.title = video_name
    metadata.sub_title = soup.find_all('div', attrs={'style': 'margin-bottom: 5px'})[1].string
    metadata.describe = soup.find('div', attrs={'class': 'video-caption-text caption-ellipsis',
                                                'style': 'color: #b8babc; font-weight: normal;'}).string
    metadata.director = soup.find('a', attrs={'id': "video-artist-name"}).string
    metadata.director = metadata.director.replace('\n', '')
    metadata.director = metadata.director.replace(' ', '')
    metadata.artist = (soup.find('div', attrs={'class': 'video-playlist-top'})).find('h4').string

    tags_element_list = soup.find_all('div', attrs={'class': "single-video-tag",
                                                    'style': "margin-bottom: 18px; font-weight: normal"})
    metadata.tag_list.clear()
    for t in tags_element_list:
        metadata.tag_list.append(t.contents[0]["href"][t.contents[0]["href"].find("=") + 1:])
    metadata.public_time = re.search(
        r"\d{4}-\d{2}-\d{2}",
        soup.find('div', attrs={'class': 'hidden-xs', 'style': 'margin-bottom: 5px'}).string).group()

    metadata.year = metadata.public_time[:4]

    return metadata


# 通过视频页面url请求hanime.me,获取视频信息和下载地址
def get_video_info_from_hanime(video_url):
    view_url_parse = urlparse(video_url)
    vid = parse_qs(view_url_parse.query)["v"][0]

    video_info = video_info_cache.get_video_info(vid)
    if video_info is not None:
        SESE_PRINT("匹配到缓存中的视频信息(vid-%s)" % vid)
        return copy.deepcopy(video_info)

    # 发送请求获取网页html
    response = ssreq.request("GET", video_url, headers=headers)
    video_soup = BeautifulSoup(response.text, 'html.parser')

    # 提取其中有关视频信息的json数据
    video_context_text = video_soup.find('script', {'type': 'application/ld+json'}).string
    video_context_text = video_context_text.replace('\n', '')
    video_context_text = video_context_text.replace('\r', '')
    video_context_json = json.loads(video_context_text)
    #print(video_context_json)

    # 解析其中内容
    video_name = html.unescape(video_context_json['name'])
    video_thumbnail_url = video_context_json['thumbnailUrl'][0]
    video_download_url = video_context_json['contentUrl']

    # 从html中获取metadata
    metadata = get_metadata(video_name, video_soup)
    series_info = get_series_info(video_soup)

    # 通过视频类别和视频名字请求搜索页面，可以获取到搜索页面中视频的封面，主要是因为里番在搜索里有竖版封面，但是在视频页面里只有预览图
    cover_url = None
    search_genre = video_soup.find('a', attrs={'class': "hidden-sm hidden-md hidden-lg hidden-xl"}).string
    search_genre = search_genre.replace('\n', '')
    search_genre = search_genre.replace(' ', '')

    if search_genre == "裏番" or search_genre == "泡麵番":
        search_url = 'https://hanime1.me/search?type=&genre=%s&sort=&year=&month=' % search_genre
        response = ssreq.request("GET", search_url, params={'query': video_name}, headers=headers)

        search_soup = BeautifulSoup(response.text, 'html.parser')

        # 匹配封面url
        cover_element = (search_soup.find('a', href=video_url)).find('img', src=re.compile('cover'))
        if cover_element:
            cover_url = cover_element.attrs['src']

    if cover_url is None:
        cover_url = video_thumbnail_url

    video_info = VideoInfo()

    video_info.vid = vid
    video_info.name = video_name
    video_info.download_url = video_download_url
    video_info.cover_url = cover_url
    video_info.thumbnail_url = video_thumbnail_url
    video_info.metadata = metadata
    video_info.series_info = series_info

    # 将video_info保存，供后续使用
    video_info_cache.update_cache(vid, video_info)

    return copy.deepcopy(video_info)


def get_series_info(soup):
    series = []

    play_list = soup.find('div', {'id': 'playlist-scroll'})
    video_element_list = play_list.find_all("div", attrs={"class", "related-watch-wrap"}, recursive=False)

    for video_element in video_element_list:
        if isinstance(video_element, element.Tag):
            video_url_element = video_element.find("a", {"class": "overlay"})
            video_thumb_url_element = video_element.find_all("img")[1]
            video_title_element = video_element.find("div", {"class": "card-mobile-title"})
            if video_url_element and video_thumb_url_element and video_title_element:
                video_url = video_url_element.attrs["href"]
                video_thumb_url = video_thumb_url_element.attrs["src"]
                video_title = video_title_element.string
                series.append({"title": video_title, "url": video_url, "thumbnail": video_thumb_url})

    return series


def download_series_thumbnail(series, dir):
    threads_list = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        for video in series:
            video_url = video["url"]
            view_url_parse = urlparse(video_url)
            vid = parse_qs(view_url_parse.query)["v"][0]

            # 下载封面
            thumbnail_url = video["thumbnail"]
            thumbnail_path = dir + "%s.jpg" % vid

            # 加入下载线程
            threads_list.append(pool.submit(ssreq.download_file, thumbnail_path, thumbnail_url))
            video["thumbnail"] = thumbnail_path

        # 监测下载线程状态
        totle_cnt = len(threads_list)
        finish_cnt = 0
        for thread in as_completed(threads_list):
            finish_cnt = finish_cnt + 1
            SESE_PRINT('下载系列视频缩略图中(%d/%d)' % (finish_cnt, totle_cnt), end="\r")

    SESE_PRINT('\n下载完成!')


# 命名不重复的目录名
def make_diff_dir_name(dir):
    if os.path.exists(dir):
        regex_file_index = re.compile(r'(?<=_\[)\d+(?=\]$)')
        result = regex_file_index.search(dir)
        file_index = ''
        if result:
            file_index = result.group()

        # 如果目录没有序号，则目录名加上序号
        if file_index == '':
            dir = dir + '_[1]'
        # 如果目录已存在序号，则序号+1
        else:
            dir = regex_file_index.sub('%d' % (int(file_index) + 1), dir)

        dir = make_diff_dir_name(dir)

    return dir


def download(url):
    video_url_list = url.split(',')
    for video_url in video_url_list:
        # 请求url获取视频信息和下载地址
        video_info = get_video_info_from_hanime(video_url)

        video_name = video_info.name
        video_thumbnail_url = video_info.thumbnail_url
        cover_url = video_info.cover_url
        video_download_url = video_info.download_url
        metadata = video_info.metadata

        SESE_PRINT('video name: %s' % video_name)
        # SESE_PRINT('thumbnail url: %s' % video_thumbnail_url)
        # SESE_PRINT('cover url: %s' % cover_url)
        # SESE_PRINT('download url: %s' % video_download_url)

        # 创建下载目录
        middle_dir = save_path + '%s' % make_filename_valid(metadata.artist)  # 中间目录，主要用来分类同一个作者的作品
        download_dir = '%s/%s' % (middle_dir, make_filename_valid(video_name))  # 下载目录，以视频名命名

        # 如果目录已经存在，生成不同的目录名，避免视频名相同导致被覆盖
        download_dir = make_diff_dir_name(download_dir)

        if not os.path.exists(save_path):
            os.mkdir(save_path)
        if not os.path.exists(middle_dir):
            os.mkdir(middle_dir)
        if not os.path.exists(download_dir):
            os.mkdir(download_dir)

        poster_path = download_dir + '/' + 'poster.jpg'  # 封面图保存路径
        fanart_path = download_dir + '/' + 'fanart.jpg'  # 背景图保存路径
        video_path = download_dir + '/' + make_filename_valid('%s.mp4' % video_name)  # 视频保存路径
        vsmeta_path = download_dir + '/' + make_filename_valid('%s.mp4.vsmeta' % video_name)  # vsmeta文件保存路径
        nfo_path = download_dir + '/' + make_filename_valid('%s.nfo' % video_name)  # nfo文件保存路径

        # 创建下载任务
        if '.m3u8' in video_download_url.split('/')[-1]:
            ssreq.download_task(video_name, ssreq.download_mp4_by_m3u8, video_path, video_download_url)
        else:
            ssreq.download_task(video_name, ssreq.download_mp4, video_path, video_download_url)

        if ssreq.download_file(poster_path, cover_url) | \
                ssreq.download_file(fanart_path, video_thumbnail_url) == 0:

            # 创建source.txt文件保存下载地址
            with open(download_dir + '/' + 'source.txt', 'wb') as f:
                f.write(('video url: %s\r\n' % url).encode())
                f.write(('thumbnail url: %s\r\n' % video_thumbnail_url).encode())
                f.write(('cover url: %s\r\n' % cover_url).encode())
                f.write(('download url: %s\r\n' % video_download_url).encode())
            metadata.describe = metadata.describe + '\r\n%s' % url
            metadata.back_ground_path = fanart_path

            # 生成metadata文件
            make_vsmeta_file(vsmeta_path, metadata)
            make_nfo_file(nfo_path, metadata)
        else:
            SESE_PRINT('download fail!')
