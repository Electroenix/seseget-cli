import os
from flask import request, Blueprint

from seseget.request.fetcher import FetcherRegistry, VideoInfo, ComicInfo
from seseget.request.downloader import download_file, download_files_ex
from seseget.request.downloadtask import TaskDLProgress, FileDLProgress
from .response import ResponseCode, ApiResponse, SearchApiResponse
from ..config.path import STATIC_COVER_DIR, STATIC_COVER_URI, STATIC_THUMBNAIL_DIR, \
    STATIC_THUMBNAIL_URI
from ..utils import run_async

search_bp = Blueprint('api/search', __name__)


def download_cover(site: str, filename: str, url: str):
    site_dir = os.path.join(STATIC_COVER_DIR, site)
    if not os.path.exists(site_dir):
        os.mkdir(site_dir)

    cover_file_path = os.path.join(STATIC_COVER_DIR, f"{site}/{filename}")
    print(f"Download [{url}] to [{cover_file_path}]")
    run_async(download_file(cover_file_path, url))


def download_thumbnail(site: str, filename: str, url: str):
    site_dir = os.path.join(STATIC_THUMBNAIL_DIR, site)
    if not os.path.exists(site_dir):
        os.mkdir(site_dir)

    thumbnail_file_path = os.path.join(STATIC_THUMBNAIL_DIR, f"{site}/{filename}")
    print(f"Download [{url}] to [{thumbnail_file_path}]")
    run_async(download_file(thumbnail_file_path, url))


def download_thumbnails(site: str, filenames: list, urls: list):
    site_dir = os.path.join(STATIC_THUMBNAIL_DIR, site)
    if not os.path.exists(site_dir):
        os.mkdir(site_dir)

    thumbnail_file_paths = [os.path.join(STATIC_THUMBNAIL_DIR, f"{site}/{filename}") for filename in filenames]

    progress = TaskDLProgress("下载缩略图")
    progress.init_progress()
    progress.set_progress_count(len(urls))
    progress.set_status(FileDLProgress.Status.DOWNLOADING)
    run_async(download_files_ex(thumbnail_file_paths, urls, progress=progress))
    progress.set_status(FileDLProgress.Status.DOWNLOAD_OK)


@search_bp.route('', methods=['POST'])
def search():
    form = request.form
    print("form: ", form)

    site = form.get("station")
    url = form.get("url")

    if site and url:
        fetcher = FetcherRegistry.get_fetcher(site)
        info = run_async(fetcher.info(url))
        info.print_info()
        print("fetch info OK!")

        if isinstance(info, VideoInfo):
            print("Media Type: Video")

            # 下载视频封面
            cover_filename = f"{info.vid}.jpg"
            download_cover(site, cover_filename, info.cover_url)
            cover_uri = f"{STATIC_COVER_URI}/{site}/{cover_filename}"

            # 下载视频缩略图
            thumbnail_filename = f"{info.vid}.jpg"
            thumbnail_url = next(
                (video['thumbnail'] for video in info.series_info if video.get('vid') == info.vid),
                info.thumbnail_url
            )
            download_thumbnail(site, thumbnail_filename, thumbnail_url)
            thumbnail_uri = f"{STATIC_THUMBNAIL_URI}/{site}/{thumbnail_filename}"

            response = SearchApiResponse(
                site,
                url,
                info.metadata.title,
                info.metadata.sub_title,
                info.metadata.public_time,
                info.metadata.series,
                info.metadata.author,
                info.metadata.tag_list,
                info.metadata.describe,
                cover_uri
            )

            response.add_chapter(info.metadata.title, info.view_url, thumbnail_uri, 0)
            print("response: ", response.to_dict())
            return response.to_response()
        elif isinstance(info, ComicInfo):
            print("Media Type: Comic")

            # 下载漫画封面
            cover_filename = f"{info.cid}.jpg"
            download_cover(site, cover_filename, info.cover_url)
            cover_uri = f"{STATIC_COVER_URI}/{site}/{cover_filename}"

            response = SearchApiResponse(
                site,
                url,
                title=info.title,
                author=info.author,
                genres=info.genres,
                descrip=info.description,
                cover=cover_uri
            )

            for chapter in info.chapter_list:
                response.add_chapter(
                    title=chapter.title,
                    url=info.view_url,
                    order=chapter.id)
            print("response: ", response.to_dict())
            return response.to_response()
        else:
            response = ApiResponse(
                code=ResponseCode.NOT_FOUND,
                message="Error",
                data={}
            )
            return response.to_response()
    else:
        response = ApiResponse(
            code=ResponseCode.NOT_FOUND,
            message="Error",
            data={}
        )
        return response.to_response()


@search_bp.route('/series', methods=['POST'])
def search_series():
    data = request.json
    print("data: ", data)

    site = data.get("station")
    url = data.get("url")

    if site and url:
        fetcher = FetcherRegistry.get_fetcher(site)
        info = run_async(fetcher.info(url))
        info.print_info()
        print("fetch info OK!")

        if isinstance(info, VideoInfo):
            print("Media Type: Video")
            series = info.series_info

            # 下载系列第一个视频封面作为系列封面
            first_video_info = run_async(fetcher.info(series[-1]["url"]))
            cover_filename = f"{first_video_info.vid}.jpg"
            download_cover(site, cover_filename, first_video_info.cover_url)
            series_cover_uri = f"{STATIC_COVER_URI}/{site}/{cover_filename}"

            # 下载全部视频缩略图
            thumbnail_filenames = [f"{video['vid']}.jpg" for video in series]
            urls = [f'{video["thumbnail"]}' for video in series]
            download_thumbnails(site, thumbnail_filenames, urls)
            thumbnail_uris = [f"{STATIC_THUMBNAIL_URI}/{site}/{filename}" for filename in thumbnail_filenames]

            response = SearchApiResponse(
                site=site,
                url=url,
                title=info.metadata.series,
                author=info.metadata.author,
                cover=series_cover_uri,
            )

            for index, video in enumerate(series):
                response.add_chapter(
                    title=video["title"],
                    url=video["url"],
                    thumbnail=thumbnail_uris[index],
                    order=index,
                )

            print("response: ", response.to_dict())
            return response.to_response()
        else:
            response = ApiResponse(
                code=ResponseCode.NOT_FOUND,
                message="Error",
                data={}
            )
            return response.to_response()
    else:
        response = ApiResponse(
            code=ResponseCode.NOT_FOUND,
            message="Error",
            data={}
        )
        return response.to_response()


@search_bp.route('site_list', methods=['GET'])
def get_site_list():
    sites = FetcherRegistry.list_sites()
    print("sites: ", sites)
    response = ApiResponse(
        code=ResponseCode.SUCCESS,
        message="Success",
        data=sites
    )
    return response.to_response()
