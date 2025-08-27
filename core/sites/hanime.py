import copy
import re
import json
import html
from bs4 import BeautifulSoup, element
from urllib.parse import urlparse, parse_qs

import core.config.path
from core.metadata.video import *
from core.request.fetcher import VideoFetcher, FetcherRegistry
from core.utils.thread_utils import SeseThreadPool, Future
from core.utils.trace import *
from core.request import seserequest as ssreq
from core.utils.file_utils import *


@FetcherRegistry.register("hanime")
class HanimeFetcher(VideoFetcher):
    site_dir = core.config.path.HANIME_DATA_LOCAL_DIR + "/"

    @staticmethod
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
                    video_thumb_url = video_thumb_url_element.attrs["src"]
                    video_title = video_title_element.string
                    series.append({"title": video_title, "url": video_url, "thumbnail": video_thumb_url})

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
        response = ssreq.request("GET", url)
        video_soup = BeautifulSoup(response.text, 'html.parser')

        # 提取其中有关视频信息的json数据
        video_context_text = video_soup.find('script', {'type': 'application/ld+json'}).string
        video_context_text = video_context_text.replace('\n', '')
        video_context_text = video_context_text.replace('\r', '')
        video_context_json = json.loads(video_context_text)

        # 解析其中内容
        video_name = html.unescape(video_context_json['name'])
        video_thumbnail_url = video_context_json['thumbnailUrl'][0]
        video_download_url = video_context_json['contentUrl']

        # 从html中获取metadata
        metadata = self.get_metadata(video_name, video_soup)
        series_info = self.get_series_info(video_soup)

        # 通过视频类别和视频名字请求搜索页面，可以获取到搜索页面中视频的封面，主要是因为里番在搜索里有竖版封面，但是在视频页面里只有预览图
        cover_url = None
        search_genre = video_soup.find('a', attrs={'class': "hidden-sm hidden-md hidden-lg hidden-xl"}).string
        search_genre = search_genre.replace('\n', '')
        search_genre = search_genre.replace(' ', '')

        if search_genre == "裏番" or search_genre == "泡麵番":
            search_url = 'https://hanime1.me/search?type=&genre=%s&sort=&year=&month=' % search_genre
            response = ssreq.request("GET", search_url, params={'query': video_name})

            search_soup = BeautifulSoup(response.text, 'html.parser')

            # 匹配封面url
            cover_element = (search_soup.find('a', href=url)).find('img', src=re.compile('cover'))
            if cover_element:
                cover_url = cover_element.attrs['src']

        if cover_url is None:
            cover_url = video_thumbnail_url

        video_info = VideoInfo()

        video_info.vid = vid
        video_info.name = video_name
        video_info.view_url = url
        video_info.download_url = video_download_url
        video_info.cover_url = cover_url
        video_info.thumbnail_url = video_thumbnail_url
        video_info.metadata = metadata
        video_info.series_info = series_info

        # 将video_info保存，供后续使用
        self.video_info_cache.update_cache(vid, video_info)

        return copy.deepcopy(video_info)
