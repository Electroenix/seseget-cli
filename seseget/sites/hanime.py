import copy
import re
import json
import html
from bs4 import BeautifulSoup, element
from urllib.parse import urlparse, parse_qs

from ..config.path import DATA_DIR
from ..metadata.video import VideoMetaData
from ..request.fetcher import VideoInfo, VideoFetcher, FetcherRegistry
from ..utils.thread_utils import SeseThreadPool, Future
from ..utils.trace import *
from ..request import seserequest as ssreq
from ..utils.file_utils import *
from ..config.config_manager import config


HANIME_HEADERS = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'zh-CN,zh-TW;q=0.9,zh;q=0.8,en-GB;q=0.7,en;q=0.6,zh-MO;q=0.5,zh-HK;q=0.4,ja-JP;q=0.3,ja;q=0.2',
    'cache-control': 'no-cache',
    'pragma': 'no-cache',
    'priority': 'u=0, i',
    'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    'sec-ch-ua-arch': '"x86"',
    'sec-ch-ua-bitness': '"64"',
    'sec-ch-ua-full-version': '"143.0.7499.170"',
    'sec-ch-ua-full-version-list': '"Google Chrome";v="143.0.7499.170", "Chromium";v="143.0.7499.170", "Not A(Brand";v="24.0.0.0"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-model': '""',
    'sec-ch-ua-platform': '"Windows"',
    'sec-ch-ua-platform-version': '"19.0.0"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
    'cookie': '',
}


@FetcherRegistry.register("hanime")
class HanimeFetcher(VideoFetcher):
    site_dir = os.path.join(DATA_DIR, "hanime")

    @staticmethod
    # 从html数据中获取数据到metadata
    def get_metadata(soup):
        metadata = VideoMetaData()

        # 提取视频信息到metadata
        metadata.title = soup.find('h3', attrs={'id': 'shareBtn-title'}).string
        metadata.sub_title = soup.find_all('div', attrs={'style': 'margin-bottom: 5px'})[1].string
        metadata.describe = soup.find('div', attrs={'class': 'video-caption-text caption-ellipsis',
                                                    'style': 'color: #b8babc; font-weight: normal;'}).string
        metadata.author = soup.find('a', attrs={'id': "video-artist-name"}).string
        metadata.author = metadata.author.replace('\n', '')
        metadata.author = metadata.author.replace(' ', '')
        metadata.series = (soup.find('div', attrs={'class': 'video-playlist-top'})).find('h4').string

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

    @staticmethod
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
                    vid = parse_qs(urlparse(video_url).query)["v"][0]
                    video_thumb_url = video_thumb_url_element.attrs["src"]
                    video_title = video_title_element.string
                    series.append({"vid": vid, "title": video_title, "url": video_url, "thumbnail": video_thumb_url})

        return series

    @staticmethod
    def download_series_thumbnail(series, dir):
        totle_cnt = len(series)
        finish_cnt = 0

        def done_callback(future: Future):
            nonlocal finish_cnt
            finish_cnt = finish_cnt + 1
            SESE_PRINT('下载系列视频缩略图中(%d/%d)' % (finish_cnt, totle_cnt), end="\r")

        with SeseThreadPool(max_workers=10) as pool:
            pool.set_done_callback(done_callback)

            for video in series:
                video_url = video["url"]
                view_url_parse = urlparse(video_url)
                vid = parse_qs(view_url_parse.query)["v"][0]

                # 下载封面
                thumbnail_url = video["thumbnail"]
                thumbnail_path = dir + "%s.jpg" % vid

                # 加入下载线程
                pool.submit(ssreq.download_file, thumbnail_path, thumbnail_url)
                video["thumbnail"] = thumbnail_path

            try:
                pool.wait_all()
            except Exception as e:
                SESE_TRACE(LOG_ERROR, '\n下载失败!')
                raise

        SESE_PRINT('\n下载完成!')

    def _fetch_info(self, url, **kwargs) -> VideoInfo:
        view_url_parse = urlparse(url)
        vid = parse_qs(view_url_parse.query)["v"][0]

        video_info = self.video_info_cache.get_video_info(vid)
        if video_info is not None:
            SESE_PRINT("匹配到缓存中的视频信息(vid-%s)" % vid)
            return copy.deepcopy(video_info)

        # 发送请求获取网页html
        req_kwargs = {}
        if config["hanime"]["cookie"]:
            req_kwargs["headers"] = HANIME_HEADERS.copy()
            req_kwargs["headers"]["cookie"] = config["hanime"]["cookie"]
        response = ssreq.request("GET", url, **req_kwargs)
        video_soup = BeautifulSoup(response.text, 'html.parser')

        # 提取视频信息
        video_elem = video_soup.find('video')
        video_thumbnail_url = video_elem.get("poster")
        video_source = video_elem.find("source", {"size": "1080"})
        if video_source is None:
            video_source = video_elem.find("source", {"size": "720"})
        if video_source is None:
            video_source = video_elem.find("source", {"size": "480"})

        video_download_url = video_source.get("src")

        # 从html中获取metadata
        metadata = self.get_metadata(video_soup)
        series_info = self.get_series_info(video_soup)

        # 通过视频类别和视频名字请求搜索页面，可以获取到搜索页面中视频的封面，主要是因为里番在搜索里有竖版封面，但是在视频页面里只有预览图
        cover_url = None
        search_genre = video_soup.find('a', attrs={'class': "hidden-sm hidden-md hidden-lg hidden-xl"}).string
        search_genre = search_genre.replace('\n', '')
        search_genre = search_genre.replace(' ', '')

        genres_simp = ["里番", "泡面番"]
        genres_trad = ["裏番", "泡麵番"]
        if search_genre in genres_simp + genres_trad:
            if search_genre in genres_simp:
                search_genre = dict(zip(genres_simp, genres_trad)).get(search_genre)
            search_url = f'https://hanime1.me/search?type=&genre={search_genre}&sort=&date=&duration='
            req_kwargs = {}
            if config["hanime"]["cookie"]:
                req_kwargs["headers"] = HANIME_HEADERS.copy()
                req_kwargs["headers"]["cookie"] = config["hanime"]["cookie"]
            response = ssreq.request("GET", search_url, params={'query': metadata.title}, **req_kwargs)

            search_soup = BeautifulSoup(response.text, 'html.parser')

            # 匹配封面url
            cover_element = (search_soup.find('a', href=url)).find('img', src=re.compile('cover'))
            if cover_element:
                cover_url = cover_element.attrs['src']

        if cover_url is None:
            cover_url = video_thumbnail_url

        video_info = VideoInfo()

        video_info.vid = vid
        video_info.name = metadata.title
        video_info.view_url = url
        video_info.download_url = video_download_url
        video_info.cover_url = cover_url
        video_info.thumbnail_url = video_thumbnail_url
        video_info.metadata = metadata
        video_info.series_info = series_info

        # 将video_info保存，供后续使用
        self.video_info_cache.update_cache(vid, video_info)

        return copy.deepcopy(video_info)
