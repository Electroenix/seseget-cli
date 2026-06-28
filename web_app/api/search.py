import os

from fastapi import APIRouter, Request, Form

from seseget.request.fetcher import FetcherRegistry, VideoInfo, ComicInfo
from seseget.request.downloader import download_file, download_files_ex
from seseget.request.downloadtask import TaskDLProgress, FileDLProgress
from .response import ResponseCode, ApiResponse
from ..config.path import (
    STATIC_COVER_DIR,
    STATIC_COVER_URI,
    STATIC_THUMBNAIL_DIR,
    STATIC_THUMBNAIL_URI,
)

router = APIRouter()


async def download_cover(site: str, filename: str, url: str):
    site_dir = os.path.join(STATIC_COVER_DIR, site)
    if not os.path.exists(site_dir):
        os.mkdir(site_dir)
    cover_file_path = os.path.join(STATIC_COVER_DIR, f"{site}/{filename}")
    print(f"Download [{url}] to [{cover_file_path}]")
    await download_file(cover_file_path, url)


async def download_thumbnail(site: str, filename: str, url: str):
    site_dir = os.path.join(STATIC_THUMBNAIL_DIR, site)
    if not os.path.exists(site_dir):
        os.mkdir(site_dir)
    thumbnail_file_path = os.path.join(STATIC_THUMBNAIL_DIR, f"{site}/{filename}")
    print(f"Download [{url}] to [{thumbnail_file_path}]")
    await download_file(thumbnail_file_path, url)


async def download_thumbnails(site: str, filenames: list, urls: list):
    site_dir = os.path.join(STATIC_THUMBNAIL_DIR, site)
    if not os.path.exists(site_dir):
        os.mkdir(site_dir)
    thumbnail_file_paths = [
        os.path.join(STATIC_THUMBNAIL_DIR, f"{site}/{filename}")
        for filename in filenames
    ]

    progress = TaskDLProgress("下载缩略图")
    progress.init_progress()
    progress.set_progress_count(len(urls))
    progress.set_status(FileDLProgress.Status.DOWNLOADING)
    await download_files_ex(thumbnail_file_paths, urls, progress=progress)
    progress.set_status(FileDLProgress.Status.DOWNLOAD_OK)


@router.post("")
async def search(
    station: str = Form(...),
    url: str = Form(...),
):
    site = station
    print(f"form: station={site}, url={url}")

    if site and url:
        fetcher = FetcherRegistry.get_fetcher(site)
        info = await fetcher.info(url)
        info.print_info()
        print("fetch info OK!")

        if isinstance(info, VideoInfo):
            print("Media Type: Video")

            cover_filename = f"{info.vid}.jpg"
            await download_cover(site, cover_filename, info.cover_url)
            cover_uri = f"{STATIC_COVER_URI}/{site}/{cover_filename}"

            thumbnail_filename = f"{info.vid}.jpg"
            thumbnail_url = next(
                (
                    video["thumbnail"]
                    for video in info.series_info
                    if video.get("vid") == info.vid
                ),
                info.thumbnail_url,
            )
            await download_thumbnail(site, thumbnail_filename, thumbnail_url)
            thumbnail_uri = f"{STATIC_THUMBNAIL_URI}/{site}/{thumbnail_filename}"

            data = {
                "station": site,
                "url": url,
                "title": info.metadata.title,
                "sub_title": info.metadata.sub_title,
                "date": info.metadata.public_time,
                "series": info.metadata.series,
                "author": info.metadata.author,
                "genres": info.metadata.tag_list,
                "description": info.metadata.describe,
                "cover": cover_uri,
                "chapter": [
                    {
                        "title": info.metadata.title,
                        "url": info.view_url,
                        "thumbnail": thumbnail_uri,
                        "order": 0,
                    }
                ],
            }
            print("response: ", data)
            return ApiResponse(code=ResponseCode.SUCCESS, message="Success", data=data)

        elif isinstance(info, ComicInfo):
            print("Media Type: Comic")

            cover_filename = f"{info.cid}.jpg"
            await download_cover(site, cover_filename, info.cover_url)
            cover_uri = f"{STATIC_COVER_URI}/{site}/{cover_filename}"

            chapters = []
            for chapter in info.chapter_list:
                chapters.append(
                    {
                        "title": chapter.title,
                        "url": info.view_url,
                        "order": chapter.id,
                    }
                )

            data = {
                "station": site,
                "url": url,
                "title": info.title,
                "author": info.author,
                "genres": info.genres,
                "description": info.description,
                "cover": cover_uri,
                "chapter": chapters,
            }
            print("response: ", data)
            return ApiResponse(code=ResponseCode.SUCCESS, message="Success", data=data)

        else:
            return ApiResponse(code=ResponseCode.NOT_FOUND, message="Error")

    else:
        return ApiResponse(code=ResponseCode.NOT_FOUND, message="Error")


@router.post("/series")
async def search_series(request: Request):
    data = await request.json()
    print("data: ", data)

    site = data.get("station")
    url = data.get("url")

    if site and url:
        fetcher = FetcherRegistry.get_fetcher(site)
        info = await fetcher.info(url)
        info.print_info()
        print("fetch info OK!")

        if isinstance(info, VideoInfo):
            print("Media Type: Video")
            series = info.series_info

            first_video_info = await fetcher.info(series[-1]["url"])
            cover_filename = f"{first_video_info.vid}.jpg"
            await download_cover(site, cover_filename, first_video_info.cover_url)
            series_cover_uri = f"{STATIC_COVER_URI}/{site}/{cover_filename}"

            thumbnail_filenames = [f"{video['vid']}.jpg" for video in series]
            urls = [f'{video["thumbnail"]}' for video in series]
            await download_thumbnails(site, thumbnail_filenames, urls)
            thumbnail_uris = [
                f"{STATIC_THUMBNAIL_URI}/{site}/{filename}"
                for filename in thumbnail_filenames
            ]

            chapters = []
            for index, video in enumerate(series):
                chapters.append(
                    {
                        "title": video["title"],
                        "url": video["url"],
                        "thumbnail": thumbnail_uris[index],
                        "order": index,
                    }
                )

            data = {
                "station": site,
                "url": url,
                "title": info.metadata.series,
                "author": info.metadata.author,
                "cover": series_cover_uri,
                "chapter": chapters,
            }
            print("response: ", data)
            return ApiResponse(code=ResponseCode.SUCCESS, message="Success", data=data)

        else:
            return ApiResponse(code=ResponseCode.NOT_FOUND, message="Error")

    else:
        return ApiResponse(code=ResponseCode.NOT_FOUND, message="Error")


@router.get("/site_list")
def get_site_list():
    sites = FetcherRegistry.list_sites()
    print("sites: ", sites)
    return ApiResponse(code=ResponseCode.SUCCESS, message="Success", data=sites)
