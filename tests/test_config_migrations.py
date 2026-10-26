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


def test_migrate_v0_to_v1_moves_sessions_and_sets_version(tmp_path):
    store = SessionStore(str(tmp_path / "sessions.json"))
    raw = {
        "bika": {"token": "legacy-bika-token", "nonce": ""},
        "jmcomic": {"login": {"cookie": "legacy-jm-cookie"}},
    }

    migrated = migrate_config(raw, 0, store=store)

    assert migrated["config_version"] == CURRENT_CONFIG_VERSION
    assert "token" not in migrated["bika"]
    assert "nonce" not in migrated["bika"]
    assert "cookie" not in migrated["jmcomic"]["login"]
    assert store.get("bika", "token") == "legacy-bika-token"
    assert store.get("jmcomic", "cookie") == "legacy-jm-cookie"


def test_migrate_v0_without_legacy_fields_only_sets_version(tmp_path):
    store = SessionStore(str(tmp_path / "sessions.json"))
    raw = {"bika": {"username": "user"}}

    migrated = migrate_config(raw, 0, store=store)

    assert migrated == {
        "bika": {"username": "user"},
        "config_version": CURRENT_CONFIG_VERSION,
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
