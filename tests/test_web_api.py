import pytest

from seseget.request.downloadtask import download_manager
from web_app.api import settings as settings_api


AUTH = {"Authorization": "Bearer test-token"}


@pytest.mark.asyncio
async def test_version_is_public(api_client):
    response = await api_client.get("/api/version")

    assert response.status_code == 200
    assert response.json()["code"] == 200


@pytest.mark.asyncio
async def test_auth_verify_rejects_invalid_token(api_client):
    response = await api_client.post(
        "/api/auth/verify",
        json={"token": "wrong-token"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == 401


@pytest.mark.asyncio
async def test_auth_verify_accepts_valid_token(api_client):
    response = await api_client.post(
        "/api/auth/verify",
        json={"token": "test-token"},
    )

    assert response.status_code == 200
    assert response.json()["code"] == 200


@pytest.mark.asyncio
async def test_protected_api_requires_token(api_client):
    response = await api_client.get("/api/download/history")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_history_api_lists_and_clears(api_client):
    download_manager.history_store.add(
        {
            "id": "history-1",
            "name": "Task One",
            "status": "success",
            "started_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T00:00:01+00:00",
            "duration": 1,
            "file_count": 1,
            "file_finish_count": 1,
            "progress": 100,
            "error": "",
        },
        max_items=200,
    )

    response = await api_client.get("/api/download/history", headers=AUTH)
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    assert payload["data"]["total"] == 1
    assert payload["data"]["items"][0]["id"] == "history-1"

    response = await api_client.delete("/api/download/history", headers=AUTH)
    assert response.status_code == 200
    assert response.json()["code"] == 200
    assert download_manager.history_store.items == []


@pytest.mark.asyncio
async def test_format_options_are_exposed(api_client):
    response = await api_client.get("/api/settings/formats", headers=AUTH)

    assert response.status_code == 200
    data = response.json()["data"]
    assert "nfo" in data["download.video.metadata_file"]
    assert "vsmeta" in data["download.video.metadata_file"]
    assert "cbz" in data["download.comic.format"]
    assert "epub" in data["download.comic.format"]


@pytest.mark.asyncio
async def test_settings_get_redacts_secrets_and_sessions(api_client):
    response = await api_client.get("/api/settings", headers=AUTH)

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    data = payload["data"]
    assert "config" in data
    assert data["config"]["bika"]["password"] == ""
    assert data["config"]["bilibili"]["cookie"] == ""
    assert "token" not in data["config"].get("bika", {})
    assert "cookie" not in data["config"].get("jmcomic", {}).get("login", {})
    assert "bika.password" in data["secret_fields"]
    assert "bilibili.cookie" in data["secret_fields"]


@pytest.mark.asyncio
async def test_settings_patch_applies_changes_and_keeps_secrets(api_client):
    response = await api_client.patch(
        "/api/settings",
        headers=AUTH,
        json={
            "changes": {
                "download.max_history": 123,
                "bika.password": "new-secret",
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    data = payload["data"]
    assert data["config"]["download"]["max_history"] == 123
    assert data["config"]["bika"]["password"] == ""
    assert "bika.password" in data["secret_configured"]

    response = await api_client.get("/api/settings", headers=AUTH)
    data = response.json()["data"]
    assert data["config"]["download"]["max_history"] == 123
    assert data["config"]["bika"]["password"] == ""
    assert "bika.password" in data["secret_configured"]

    # 未提交的敏感字段必须保持原值
    response = await api_client.patch(
        "/api/settings",
        headers=AUTH,
        json={"changes": {"download.max_history": 124}},
    )
    assert response.status_code == 200
    assert settings_api.config_manager.data["bika"]["password"] == "new-secret"

    # 空字符串表示显式清空
    response = await api_client.patch(
        "/api/settings",
        headers=AUTH,
        json={"changes": {"bika.password": ""}},
    )
    assert response.status_code == 200
    assert settings_api.config_manager.data["bika"]["password"] == ""
    assert "bika.password" not in response.json()["data"]["secret_configured"]


@pytest.mark.asyncio
async def test_settings_schema_exposes_labels(api_client):
    response = await api_client.get("/api/settings/schema", headers=AUTH)

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    assert payload["data"]["sections"]["bika"]["label"] == "哔咔"
    assert payload["data"]["fields"]["bika.password"]["secret"] is True


@pytest.mark.asyncio
async def test_settings_patch_rejects_invalid_changes(api_client):
    response = await api_client.patch(
        "/api/settings",
        headers=AUTH,
        json={"changes": {"unknown.field": "x"}},
    )
    assert response.status_code == 400

    response = await api_client.patch(
        "/api/settings",
        headers=AUTH,
        json={"changes": {"bika.token": "x"}},
    )
    assert response.status_code == 400

    response = await api_client.patch(
        "/api/settings",
        headers=AUTH,
        json={"changes": {"download.max_history": "123"}},
    )
    assert response.status_code == 400
