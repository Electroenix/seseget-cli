# config_manager.py
import os
from copy import deepcopy
from typing import Dict

from ruamel.yaml import YAML

from ..utils.trace import logger
from .path import CONFIG_PATH
from .schema import get_default_config, validate_config


def _update_nested_dict(target: dict, source: dict) -> None:
    """把 source 合并到 target；字典递归，列表和其它值整体替换。"""
    for key, new_value in source.items():
        old_value = target.get(key)
        if isinstance(old_value, dict) and isinstance(new_value, dict):
            _update_nested_dict(old_value, new_value)
        else:
            target[key] = new_value


def _merge_missing_defaults(target: dict, defaults: dict) -> None:
    """把默认配置中存在、用户配置中缺失的键补进用户配置。"""
    for key, value in defaults.items():
        if key not in target:
            target[key] = deepcopy(value)
        elif isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge_missing_defaults(target[key], value)


class ConfigManager:
    _instance = None
    _config: dict = None
    _config_path: str = CONFIG_PATH

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_config()
        return cls._instance

    def _init_config(self) -> None:
        try:
            if not os.path.exists(self._config_path):
                os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
                self._dump_data(get_default_config())

            with open(self._config_path, "r", encoding="utf-8") as f:
                raw_config = YAML().load(f) or {}

            if not isinstance(raw_config, dict):
                raise ValueError("配置文件根节点必须是对象")

            merged = deepcopy(raw_config)
            _merge_missing_defaults(merged, get_default_config())
            self._config = validate_config(merged)
            logger.debug("Config loaded.")
        except Exception as e:
            logger.error(f"Config init failed: {str(e)}")
            raise

    def update(self, patch: Dict) -> None:
        """校验并一次性保存配置 patch。"""
        merged = deepcopy(self._config)
        _update_nested_dict(merged, patch)
        validated = validate_config(merged)
        self._dump_data(validated)
        self._config = validated

    def save(self) -> None:
        """校验当前配置并写回。迁移后使用。"""
        validated = validate_config(self._config)
        self._dump_data(validated)
        self._config = validated

    def _dump_data(self, data: dict) -> None:
        try:
            yaml = YAML()
            yaml.preserve_quotes = True
            yaml.width = 2147483647
            temp_path = f"{self._config_path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f)
            os.replace(temp_path, self._config_path)
            logger.info("Config saved.")
        except Exception as e:
            logger.error(f"Save failed: {str(e)}")
            raise

    @property
    def data(self) -> dict:
        return self._config


# 全局单例，直接作为普通 dict 读取；写操作使用 config_manager.update/save
config_manager = ConfigManager()
config = config_manager.data
