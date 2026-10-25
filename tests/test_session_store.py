import os
import stat

import pytest
from ruamel.yaml import YAML

from seseget.config.config_manager import ObservableDict
from seseget.config.path import DEFAULT_CONFIG_PATH
from seseget.config.session_store import SessionStore, migrate_legacy_sessions


def test_session_store_roundtrip_and_clear(tmp_path):
    path = tmp_path / "sessions.json"
    store = SessionStore(str(path))

    store.set("bika", "token", "token-value")
    store.set("jmcomic", "cookie", "cookie-value")

    reloaded = SessionStore(str(path))
    assert reloaded.get("bika", "token") == "token-value"
    assert reloaded.get("jmcomic", "cookie") == "cookie-value"

    reloaded.delete("bika", "token")
    assert reloaded.get("bika", "token") is None
    assert reloaded.get("jmcomic", "cookie") == "cookie-value"

    reloaded.clear()
    assert SessionStore(str(path))._data == {}


def test_session_store_handles_corrupt_json(tmp_path):
    path = tmp_path / "sessions.json"
    path.write_text("{broken", encoding="utf-8")

    store = SessionStore(str(path))

    assert store._data == {}


def test_session_store_permissions(tmp_path):
    if os.name == "nt":
        pytest.skip("Windows 不检查 POSIX 权限")
    path = tmp_path / "sessions.json"
    store = SessionStore(str(path))
    store.set("bika", "token", "x")

    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_migrate_legacy_sessions(tmp_path):
    store = SessionStore(str(tmp_path / "sessions.json"))
    config = {
        "bika": {
            "username": "user",
            "password": "pass",
            "nonce": "",
            "token": "legacy-bika-token",
        },
        "jmcomic": {
            "login": {
                "username": "user",
                "password": "pass",
                "cookie": '{"token": "legacy-jm-cookie"}',
            }
        },
    }

    migrate_legacy_sessions(config, store)

    assert store.get("bika", "token") == "legacy-bika-token"
    assert store.get("jmcomic", "cookie") == '{"token": "legacy-jm-cookie"}'
    assert "token" not in config["bika"]
    assert "nonce" not in config["bika"]
    assert "cookie" not in config["jmcomic"]["login"]
    assert config["bika"]["password"] == "pass"
    assert config["jmcomic"]["login"]["password"] == "pass"


def test_migration_keeps_existing_session_value(tmp_path):
    store = SessionStore(str(tmp_path / "sessions.json"))
    store.set("bika", "token", "new-token")
    config = {"bika": {"token": "old-token"}}

    migrate_legacy_sessions(config, store)

    assert store.get("bika", "token") == "new-token"
    assert "token" not in config["bika"]


def test_migration_does_not_write_invalid_legacy_data(tmp_path):
    store = SessionStore(str(tmp_path / "sessions.json"))
    config = {"bika": {"token": ""}}

    migrate_legacy_sessions(config, store)

    assert store.get("bika", "token") is None
    assert "token" not in config["bika"]


def test_migration_persists_observable_config(tmp_path):
    saved = []
    config = ObservableDict(
        lambda: saved.append(True),
        {
            "bika": {"nonce": "", "token": "legacy-token"},
            "jmcomic": {"login": {"cookie": "legacy-cookie"}},
        },
    )
    store = SessionStore(str(tmp_path / "sessions.json"))

    migrate_legacy_sessions(config, store)

    assert config.origin_data["bika"] == {}
    assert config.origin_data["jmcomic"]["login"] == {}
    assert store.get("bika", "token") == "legacy-token"
    assert store.get("jmcomic", "cookie") == "legacy-cookie"
    assert saved


def test_default_config_has_no_session_fields():
    with open(DEFAULT_CONFIG_PATH, encoding="utf-8") as f:
        data = YAML(typ="safe").load(f)

    assert "nonce" not in data["bika"]
    assert "token" not in data["bika"]
    assert "cookie" not in data["jmcomic"]["login"]
