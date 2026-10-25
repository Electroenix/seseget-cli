import os
import stat

import pytest
from seseget.config.schema import get_default_config
import seseget.config.session_store as session_store_module
from seseget.config.session_store import (
    SessionStore,
    backup_config,
    migrate_legacy_sessions,
)


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


def test_default_config_has_no_session_fields():
    data = get_default_config()

    assert "nonce" not in data["bika"]
    assert "token" not in data["bika"]
    assert "cookie" not in data["jmcomic"]["login"]


def test_migration_backs_up_config_before_changing(tmp_path):
    config_path = tmp_path / "conf.yaml"
    original = "bika:\n  token: old-token\n  nonce: ''\n"
    config_path.write_text(original, encoding="utf-8")
    store = SessionStore(str(tmp_path / "sessions.json"))
    config = {"bika": {"token": "old-token", "nonce": ""}}

    migrate_legacy_sessions(config, store, config_path=config_path)

    backup_path = tmp_path / "conf.backup.yaml"
    assert backup_path.is_file()
    assert backup_path.read_text(encoding="utf-8") == original
    if os.name != "nt":
        assert stat.S_IMODE(backup_path.stat().st_mode) == 0o600
    assert store.get("bika", "token") == "old-token"
    assert config == {"bika": {}}


def test_backup_uses_fixed_name_and_overwrites(tmp_path):
    config_path = tmp_path / "conf.yaml"
    config_path.write_text("version: 1\n", encoding="utf-8")

    first = backup_config(config_path)
    config_path.write_text("version: 2\n", encoding="utf-8")
    second = backup_config(config_path)

    assert first == second == tmp_path / "conf.backup.yaml"
    assert list(tmp_path.glob("conf.backup*.yaml")) == [second]
    assert second.read_text(encoding="utf-8") == "version: 2\n"


def test_migration_aborts_when_backup_fails(tmp_path, monkeypatch):
    config_path = tmp_path / "conf.yaml"
    config_path.write_text("bika:\n  token: old-token\n", encoding="utf-8")
    store = SessionStore(str(tmp_path / "sessions.json"))
    config = {"bika": {"token": "old-token"}}

    def fail_backup(path):
        raise OSError("disk full")

    monkeypatch.setattr(session_store_module, "backup_config", fail_backup)

    migrate_legacy_sessions(config, store, config_path=config_path)

    assert config == {"bika": {"token": "old-token"}}
    assert store.get("bika", "token") is None
    assert not (tmp_path / "conf.backup.yaml").exists()


def test_migration_skips_backup_without_legacy_fields(tmp_path):
    config_path = tmp_path / "conf.yaml"
    config_path.write_text("bika:\n  username: user\n", encoding="utf-8")
    store = SessionStore(str(tmp_path / "sessions.json"))
    config = {"bika": {"username": "user"}}

    migrate_legacy_sessions(config, store, config_path=config_path)

    assert not (tmp_path / "conf.backup.yaml").exists()
    assert store.get("bika", "token") is None
