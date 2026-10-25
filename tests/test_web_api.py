import pytest

from seseget.request.downloadtask import download_manager


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
