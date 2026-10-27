import os
from copy import deepcopy

from ruamel.yaml import YAML

from .path import WEB_CONFIG_PATH

_yaml = YAML()
_yaml.preserve_quotes = True
_yaml.width = 2147483647

_DEFAULT_CONFIG = {"auth_token": ""}


def _init_web_config():
    """初始化 web 配置文件。"""
    os.makedirs(os.path.dirname(WEB_CONFIG_PATH), exist_ok=True)
    if not os.path.exists(WEB_CONFIG_PATH):
        with open(WEB_CONFIG_PATH, "w", encoding="utf-8") as f:
            _yaml.dump(_DEFAULT_CONFIG, f)

    with open(WEB_CONFIG_PATH, "r", encoding="utf-8") as f:
        raw_config = _yaml.load(f) or _DEFAULT_CONFIG

    if not isinstance(raw_config, dict):
        raw_config = deepcopy(_DEFAULT_CONFIG)
    return raw_config


class WebConfigManager:
    _instance = None
    _config: dict = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._config = _init_web_config()

    def update(self, data: dict) -> None:
        merged = deepcopy(self._config)
        merged.update(data)
        self._save_data(merged)
        # 保持模块级 web_config 引用有效
        self._config.clear()
        self._config.update(merged)

    def save(self) -> None:
        self._save_data(self._config)

    def _save_data(self, data: dict) -> None:
        try:
            temp_path = f"{WEB_CONFIG_PATH}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                _yaml.dump(data, f)
            os.replace(temp_path, WEB_CONFIG_PATH)
        except Exception as e:
            print(f"[WebConfig] Save failed: {e}")
            raise

    @property
    def data(self) -> dict:
        return self._config


web_config_manager = WebConfigManager()
web_config = web_config_manager.data
