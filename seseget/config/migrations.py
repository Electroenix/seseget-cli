"""配置数据版本与顺序迁移链。"""

from typing import Any

from .session_store import SessionStore, migrate_legacy_sessions

CURRENT_CONFIG_VERSION = 1


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


MIGRATIONS = {
    0: migrate_v0_to_v1,
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
