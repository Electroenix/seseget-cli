from copy import deepcopy

import httpx
import pytest
import pytest_asyncio
from PIL import Image

import web_app
from seseget.config.config_manager import _update_nested_dict
from seseget.config.schema import validate_config
from seseget.metadata.comic import ComicMetaData
from seseget.metadata.video import VideoMetaData
from seseget.request.download_history import DownloadHistoryStore
from seseget.request.downloadtask import download_manager
from web_app.api import auth as auth_api
from web_app.api import settings as settings_api


@pytest.fixture
def video_metadata() -> VideoMetaData:
    metadata = VideoMetaData()
    metadata.title = "Video & Title"
    metadata.sub_title = "Sub <Title>"
    metadata.year = "2024"
    metadata.public_time = "2024-01-02"
    metadata.tag_list = ["tag & one", "tag <two>"]
    metadata.author = "Author"
    metadata.describe = "Description with & and < >"
    metadata.series = "Series"
    metadata.back_ground_path = ""
    return metadata


@pytest.fixture
def comic_metadata() -> ComicMetaData:
    metadata = ComicMetaData()
    metadata.series = "Series & Name"
    metadata.title = "Chapter <One>"
    metadata.number = "1"
    metadata.creator = "Author & Artist"
    metadata.year = "2024"
    metadata.month = "01"
    metadata.day = "02"
    metadata.description = "Description with & and < >"
    metadata.language = "zh"
    metadata.subjects = ["tag & one", "tag <two>"]
    return metadata


@pytest.fixture
def comic_images(tmp_path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    Image.new("RGB", (20, 30), (255, 0, 0)).save(image_dir / "00001.jpg")
    Image.new("RGB", (20, 30), (0, 255, 0)).save(image_dir / "00002.jpg")
    return image_dir


@pytest_asyncio.fixture
async def api_client(monkeypatch, tmp_path):
    """不启动真实端口的 FastAPI 测试客户端，并隔离下载历史文件。"""
    store = DownloadHistoryStore(str(tmp_path / "download_history.json"))
    monkeypatch.setattr(download_manager, "history_store", store)

    monkeypatch.setattr(web_app, "get_stored_token", lambda: "test-token")
    monkeypatch.setattr(web_app, "check_token", lambda token: token == "test-token")
    monkeypatch.setattr(auth_api, "get_stored_token", lambda: "test-token")
    monkeypatch.setattr(auth_api, "check_token", lambda token: token == "test-token")

    # 配置测试使用内存副本，避免修改真实 conf.yaml
    class FakeConfigManager:
        def __init__(self, data):
            self.data = deepcopy(data)

        def update(self, patch):
            merged = deepcopy(self.data)
            _update_nested_dict(merged, patch)
            self.data = validate_config(merged)

    monkeypatch.setattr(
        settings_api,
        "config_manager",
        FakeConfigManager(settings_api.config_manager.data),
    )

    transport = httpx.ASGITransport(app=web_app.app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client
