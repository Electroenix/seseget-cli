"""配置数据版本与顺序迁移链。"""

from typing import Any

from .session_store import SessionStore, migrate_legacy_sessions

CURRENT_CONFIG_VERSION = 2


def get_config_version(raw: dict) -> int:
    """读取配置版本；缺失视为 0。"""
    if "config_version" not in raw:
        return 0

    value = raw["config_version"]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"config_version 必须是非负整数，当前值: {value!r}")
    return value


def migrate_v0_to_v1(raw: dict, store: SessionStore | None = None) -> dict:
    """v0 -> v1：会话字段迁移到 sessions.json，并标记版本。"""
    migrate_legacy_sessions(raw, store=store)
    raw["config_version"] = 1
    return raw


def _move_site(raw: dict, sites: dict, key: str) -> None:
    old = raw.pop(key, None)
    if not isinstance(old, dict):
        return
    target = sites.setdefault(key, {})
    if not isinstance(target, dict):
        target = {}
        sites[key] = target
    for field, value in old.items():
        target.setdefault(field, value)


def migrate_v1_to_v2(raw: dict, store: SessionStore | None = None) -> dict:
    """v1 -> v2：按 UI 分组重整 network/sites/download。"""
    common = raw.pop("common", None)
    if isinstance(common, dict):
        network = raw.setdefault("network", {})
        if isinstance(network, dict):
            for key, value in common.items():
                network.setdefault(key, value)

    sites = raw.setdefault("sites", {})
    if not isinstance(sites, dict):
        sites = {}
        raw["sites"] = sites

    jmcomic = raw.pop("jmcomic", None)
    if isinstance(jmcomic, dict):
        old_login = jmcomic.pop("login", None)
        flattened = {}
        if isinstance(old_login, dict):
            flattened.update(old_login)
        flattened.update(jmcomic)
        target = sites.setdefault("jmcomic", {})
        if isinstance(target, dict):
            for key, value in flattened.items():
                target.setdefault(key, value)

    for key in ("bika", "hanime", "bilibili", "twitter"):
        _move_site(raw, sites, key)

    raw["config_version"] = 2
    return raw


MIGRATIONS = {
    0: migrate_v0_to_v1,
    1: migrate_v1_to_v2,
}


def migrate_config(
    raw: dict,
    from_version: int,
    store: SessionStore | None = None,
) -> dict:
    """从 from_version 顺序迁移到当前版本。"""
    if from_version > CURRENT_CONFIG_VERSION:
        raise ValueError(
            f"配置版本 {from_version} 高于当前支持版本 {CURRENT_CONFIG_VERSION}"
        )

    current: dict[str, Any] = raw
    for version in range(from_version, CURRENT_CONFIG_VERSION):
        migration = MIGRATIONS.get(version)
        if migration is None:
            raise ValueError(f"缺少配置迁移: v{version} -> v{version + 1}")
        current = migration(current, store=store)

    current["config_version"] = CURRENT_CONFIG_VERSION
    return current
