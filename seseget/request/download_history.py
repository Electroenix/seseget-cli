"""下载历史记录的 JSON 持久化。"""

import json
import os
from pathlib import Path
from typing import Any

from ..config.path import DATA_DIR
from ..utils.trace import logger

DEFAULT_HISTORY_PATH = os.path.join(DATA_DIR, "download_history.json")


class DownloadHistoryStore:
    """保存终态下载记录，按完成时间从新到旧排列。"""

    def __init__(self, path: str | None = None):
        self.path = Path(path or DEFAULT_HISTORY_PATH)
        self.items: list[dict[str, Any]] = self._load()

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"读取下载历史失败，将使用空历史: {e}")
            return []

        if isinstance(data, dict):
            items = data.get("items", [])
        elif isinstance(data, list):
            items = data
        else:
            items = []

        if not isinstance(items, list):
            logger.warning("下载历史格式无效，将使用空历史")
            return []

        records = [item for item in items if isinstance(item, dict)]
        records.sort(key=lambda item: str(item.get("finished_at", "")), reverse=True)
        return records

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_name(self.path.name + ".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(
                {"version": 1, "items": self.items},
                f,
                ensure_ascii=False,
                indent=2,
            )
        os.replace(temp_path, self.path)

    def add(self, record: dict[str, Any], max_items: int) -> None:
        self.items.insert(0, record)
        self.items = self.items[: max(1, int(max_items))]
        try:
            self._save()
        except OSError as e:
            logger.error(f"保存下载历史失败: {e}")

    def trim(self, max_items: int) -> None:
        max_items = max(1, int(max_items))
        if len(self.items) > max_items:
            self.items = self.items[:max_items]
            try:
                self._save()
            except OSError as e:
                logger.error(f"裁剪下载历史失败: {e}")

    def clear(self) -> None:
        self.items = []
        self._save()

    @property
    def latest_id(self) -> str | None:
        if not self.items:
            return None
        return self.items[0].get("id")
