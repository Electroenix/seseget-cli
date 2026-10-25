"""Web/站点自动维护的会话数据存储。

与用户配置分离，避免 token/cookie 出现在 conf.yaml 和配置 API 中。
"""

import json
import os
import shutil
from pathlib import Path
from threading import RLock
from typing import Any

from ..utils.trace import logger
from .path import CONFIG_DIR

SESSIONS_PATH = Path(CONFIG_DIR) / "sessions.json"
LEGACY_SESSION_PATHS = (
    ("bika", "token"),
    ("jmcomic", "login", "cookie"),
)


class SessionStore:
    """保存按站点分组的会话字段。"""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else SESSIONS_PATH
        self._lock = RLock()
        self._data: dict[str, dict[str, Any]] = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"读取会话文件失败，将使用空会话: {e}")
            return {}

        if not isinstance(data, dict):
            logger.warning("会话文件格式无效，将使用空会话")
            return {}

        result: dict[str, dict[str, Any]] = {}
        for site, values in data.items():
            if isinstance(values, dict):
                result[str(site)] = dict(values)
        return result

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_name(self.path.name + ".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, self.path)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def get(self, site: str, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(site, {}).get(key, default)

    def set(self, site: str, key: str, value: Any) -> None:
        with self._lock:
            self._data.setdefault(site, {})[key] = value
            self._save()

    def delete(self, site: str, key: str) -> None:
        with self._lock:
            values = self._data.get(site)
            if values is not None and key in values:
                del values[key]
                if not values:
                    del self._data[site]
                self._save()

    def clear(self, site: str | None = None) -> None:
        with self._lock:
            if site is None:
                self._data = {}
            else:
                self._data.pop(site, None)
            self._save()


session_store = SessionStore()


def _get_config_path(config, path: tuple[str, ...]) -> Any:
    current = config
    for key in path:
        try:
            current = current[key]
        except (KeyError, TypeError):
            return None
    return current


def _pop_config_path(config, path: tuple[str, ...]) -> bool:
    current = config
    for key in path[:-1]:
        try:
            current = current[key]
        except (KeyError, TypeError):
            return False
    try:
        if path[-1] not in current:
            return False
        del current[path[-1]]
        return True
    except (KeyError, TypeError):
        return False


def _has_config_path(config, path: tuple[str, ...]) -> bool:
    current = config
    for key in path:
        try:
            if key not in current:
                return False
            current = current[key]
        except (KeyError, TypeError):
            return False
    return True


def backup_config(config_path: str | Path) -> Path:
    """迁移前备份配置文件，返回备份路径。

    固定使用同目录下的 <name>.backup<ext>，只保留最近一次迁移前副本。
    """
    source = Path(config_path)
    if not source.is_file():
        raise FileNotFoundError(f"配置文件不存在: {source}")

    target = source.with_name(f"{source.stem}.backup{source.suffix}")
    temp_path = target.with_name(target.name + ".tmp")

    try:
        shutil.copy2(source, temp_path)
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, target)
    except OSError:
        temp_path.unlink(missing_ok=True)
        raise
    return target


def migrate_legacy_sessions(
    config,
    store: SessionStore | None = None,
    config_path: str | Path | None = None,
) -> None:
    """把旧配置中的会话字段迁移到 sessions.json。

    迁移前先备份配置文件；备份失败时不修改配置。
    只有成功写入会话文件后，才删除旧配置字段，避免迁移失败丢失登录态。
    """
    store = store or session_store
    migration_paths = LEGACY_SESSION_PATHS + (("bika", "nonce"),)
    if not any(_has_config_path(config, path) for path in migration_paths):
        return

    if config_path is not None:
        try:
            backup_path = backup_config(config_path)
            logger.info(f"配置迁移前已备份: {backup_path}")
        except OSError as e:
            logger.error(f"配置备份失败，取消迁移: {e}")
            return

    for path in LEGACY_SESSION_PATHS:
        site = path[0]
        key = path[-1]
        value = _get_config_path(config, path)
        if value:
            if not store.get(site, key):
                try:
                    store.set(site, key, value)
                except OSError as e:
                    logger.error(f"迁移 {site}.{key} 会话失败: {e}")
                    continue

        if _pop_config_path(config, path):
            logger.info(f"已从配置迁移会话字段 {'.'.join(path)}")

    # nonce 已确认恒为空，不再作为用户配置项
    if _pop_config_path(config, ("bika", "nonce")):
        logger.info("已移除废弃配置字段 bika.nonce")
