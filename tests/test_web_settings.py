import pytest

from web_app.api import web_settings as web_settings_api


AUTH = {"Authorization": "Bearer test-token"}


@pytest.mark.asyncio
async def test_web_settings_get_redacts_auth_token(api_client, monkeypatch):
    monkeypatch.setattr(
        web_settings_api, "web_config", {"auth_token": "real-secret"}
    )

    response = await api_client.get("/api/web-settings", headers=AUTH)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["config"]["auth_token"] == ""
    assert "auth_token" in data["secret_fields"]
    assert "auth_token" in data["secret_configured"]
    assert "real-secret" not in response.text


@pytest.mark.asyncio
async def test_web_settings_patch_applies_partial_changes(api_client, monkeypatch):
    class FakeManager:
        def __init__(self):
            self.updated = {}

        def update(self, data):
            self.updated.update(data)

    manager = FakeManager()
    monkeypatch.setattr(web_settings_api, "web_config_manager", manager)
    monkeypatch.setattr(web_settings_api, "web_config", {"auth_token": ""})

    response = await api_client.patch(
        "/api/web-settings",
        headers=AUTH,
        json={"changes": {"auth_token": "new-token"}},
    )

    assert response.status_code == 200
    assert manager.updated == {"auth_token": "new-token"}


@pytest.mark.asyncio
async def test_web_settings_patch_rejects_unknown_and_invalid(api_client):
    response = await api_client.patch(
        "/api/web-settings",
        headers=AUTH,
        json={"changes": {"unknown": "x"}},
    )
    assert response.status_code == 400

    response = await api_client.patch(
        "/api/web-settings",
        headers=AUTH,
        json={"changes": {"auth_token": 123}},
    )
    assert response.status_code == 400
