# config_manager.py
import os
import shutil
from copy import deepcopy
from typing import Dict

from ruamel.yaml import YAML

from ..utils.trace import logger
from .path import CONFIG_PATH, TEMPLATE_CONFIG_PATH
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
    _template_config_path: str = TEMPLATE_CONFIG_PATH
    _yaml = YAML()
    _yaml.preserve_quotes = True
    _yaml.width = 2147483647

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_config()
        return cls._instance

    def _init_config(self) -> None:
        try:
            if not os.path.exists(self._config_path):
                os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
                if os.path.exists(self._template_config_path):
                    shutil.copy2(self._template_config_path, self._config_path)
                else:
                    with open(self._config_path, "w", encoding="utf-8") as f:
                        self._yaml.dump(get_default_config(), f)

            with open(self._config_path, "r", encoding="utf-8") as f:
                raw_config = self._yaml.load(f) or {}

            if not isinstance(raw_config, dict):
                raise ValueError("配置文件根节点必须是对象")

            # schema 默认值作为唯一默认来源；已有配置中缺失的字段自动补齐
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
        self._save_data(validated)
        self._config = validated

    def save(self) -> None:
        """校验当前配置并写回。迁移后使用。"""
        validated = validate_config(self._config)
        self._save_data(validated)
        self._config = validated

    def _save_data(self, data: dict) -> None:
        try:
            temp_path = f"{self._config_path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                self._yaml.dump(data, f)
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
