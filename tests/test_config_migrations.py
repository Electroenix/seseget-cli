import pytest

from seseget.config.migrations import (
    CURRENT_CONFIG_VERSION,
    get_config_version,
    migrate_config,
)
from seseget.config.session_store import SessionStore


def test_missing_version_is_zero():
    assert get_config_version({}) == 0


def test_invalid_version_is_rejected():
    with pytest.raises(ValueError):
        get_config_version({"config_version": "1"})
    with pytest.raises(ValueError):
        get_config_version({"config_version": -1})


def test_future_version_is_rejected():
    with pytest.raises(ValueError):
        migrate_config({"config_version": CURRENT_CONFIG_VERSION + 1}, 99)


def test_migrate_v0_to_current_moves_sessions_and_reorganizes(tmp_path):
    store = SessionStore(str(tmp_path / "sessions.json"))
    raw = {
        "bika": {"token": "legacy-bika-token", "nonce": "", "username": "user"},
        "jmcomic": {"login": {"cookie": "legacy-jm-cookie", "password": "pw"}},
        "common": {"proxy": "http://proxy"},
        "download": {"max_history": 10},
    }

    migrated = migrate_config(raw, 0, store=store)

    assert migrated["config_version"] == CURRENT_CONFIG_VERSION
    assert migrated["network"] == {"proxy": "http://proxy"}
    assert migrated["sites"]["bika"] == {"username": "user"}
    assert migrated["sites"]["jmcomic"] == {"password": "pw"}
    assert migrated["download"] == {"max_history": 10}
    assert store.get("bika", "token") == "legacy-bika-token"
    assert store.get("jmcomic", "cookie") == "legacy-jm-cookie"


def test_migrate_v1_to_v2_reorganizes_sites(tmp_path):
    store = SessionStore(str(tmp_path / "sessions.json"))
    raw = {
        "config_version": 1,
        "common": {"proxy": "http://proxy"},
        "bika": {"username": "bika-user", "password": "bika-pass"},
        "jmcomic": {"login": {"username": "jm-user", "password": "jm-pass"}},
        "hanime": {"cookie": "hanime-cookie", "organize_by_genre": True},
        "bilibili": {"cookie": "bili-cookie"},
        "twitter": {"cookie_file": "cookies.txt"},
        "download": {"max_history": 20},
    }

    migrated = migrate_config(raw, 1, store=store)

    assert migrated["config_version"] == CURRENT_CONFIG_VERSION
    assert migrated["network"] == {"proxy": "http://proxy"}
    assert migrated["sites"]["bika"] == {
        "username": "bika-user",
        "password": "bika-pass",
    }
    assert migrated["sites"]["jmcomic"] == {
        "username": "jm-user",
        "password": "jm-pass",
    }
    assert migrated["sites"]["hanime"]["organize_by_genre"] is True
    assert migrated["sites"]["bilibili"]["cookie"] == "bili-cookie"
    assert migrated["sites"]["twitter"]["cookie_file"] == "cookies.txt"
    assert migrated["download"] == {"max_history": 20}
    assert "common" not in migrated
    assert "bika" not in migrated


def test_migrate_v1_without_legacy_fields_only_reorganizes(tmp_path):
    store = SessionStore(str(tmp_path / "sessions.json"))
    raw = {"config_version": 1, "bika": {"username": "user"}}

    migrated = migrate_config(raw, 1, store=store)

    assert migrated == {
        "config_version": CURRENT_CONFIG_VERSION,
        "sites": {"bika": {"username": "user"}},
    }


def test_session_write_failure_aborts_migration():
    class FailingStore:
        def get(self, site, key):
            return None

        def set(self, site, key, value):
            raise OSError("disk full")

    with pytest.raises(RuntimeError, match="会话"):
        migrate_config({"bika": {"token": "legacy"}}, 0, store=FailingStore())


def test_config_manager_migrates_and_backs_up(tmp_path, monkeypatch):
    from ruamel.yaml import YAML

    from seseget.config.config_manager import ConfigManager

    config_path = tmp_path / "conf.yaml"
    config_path.write_text("bika:\n  username: user\n", encoding="utf-8")
    monkeypatch.setattr(ConfigManager, "_instance", None)
    monkeypatch.setattr(ConfigManager, "_config_path", str(config_path))

    manager = ConfigManager()

    assert manager.data["config_version"] == CURRENT_CONFIG_VERSION
    assert manager.data["sites"]["bika"]["username"] == "user"
    assert (tmp_path / "conf.backup.yaml").is_file()
    with open(config_path, encoding="utf-8") as f:
        saved = YAML().load(f)
    assert saved["config_version"] == CURRENT_CONFIG_VERSION


def test_config_manager_rejects_newer_version(tmp_path, monkeypatch):
    from seseget.config.config_manager import ConfigManager

    config_path = tmp_path / "conf.yaml"
    config_path.write_text("config_version: 99\n", encoding="utf-8")
    monkeypatch.setattr(ConfigManager, "_instance", None)
    monkeypatch.setattr(ConfigManager, "_config_path", str(config_path))

    with pytest.raises(ValueError, match="高于"):
        ConfigManager()


def test_config_manager_aborts_when_backup_fails(tmp_path, monkeypatch):
    from seseget.config import config_manager as config_manager_module

    config_path = tmp_path / "conf.yaml"
    config_path.write_text("bika:\n  username: user\n", encoding="utf-8")
    monkeypatch.setattr(config_manager_module.ConfigManager, "_instance", None)
    monkeypatch.setattr(
        config_manager_module.ConfigManager, "_config_path", str(config_path)
    )

    def fail_backup(path):
        raise OSError("disk full")

    monkeypatch.setattr(config_manager_module, "backup_config", fail_backup)

    with pytest.raises(RuntimeError, match="备份"):
        config_manager_module.ConfigManager()
