# config_manager.py
import os
from collections import UserDict
from typing import Any, Dict, Optional, Union, Self
from ruamel.yaml import YAML
import shutil

from ..utils.trace import logger
from .path import CONFIG_PATH, DEFAULT_CONFIG_PATH


def _update_nested_dict(target: dict, source: dict) -> None:
    """将 source 中的值合并到 target 的同名键上。

    只更新 target 中已存在的键；字典递归合并，列表和其它值整体替换。
    列表不能按下标合并，否则列表缩短时旧元素会残留。
    """
    for key, new_value in source.items():
        if key not in target:
            continue

        old_value = target[key]
        if isinstance(old_value, dict) and isinstance(new_value, dict):
            _update_nested_dict(old_value, new_value)
        else:
            target[key] = new_value


def _merge_missing_defaults(target: dict, defaults: dict) -> None:
    """把默认配置中存在、用户配置中缺失的键补进用户配置。"""
    for key, value in defaults.items():
        if key not in target:
            target[key] = value
        elif isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge_missing_defaults(target[key], value)


class ObservableDict(UserDict):
    """
    模拟字典类型，支持在检测到内容修改时自动更新文件
    save_callback   - 初始化时设置save_callback回调函数，如果内部数据修改，将会触发回调将最新内容保存到文件
    origin_data     - 初始化时传入的原始类型数据，如果内部数据修改，将会同步修改此数据内容
    """

    def __init__(self, save_callback: callable, initial_data: Optional[Dict] = None):
        self.origin_data = initial_data  # 保留原始数据类型，数据被修改时同步修改原始数据
        self.save_callback = save_callback
        initial_data = initial_data or {}
        super().__init__()

        for key, value in initial_data.items():
            if isinstance(value, dict):
                super().__setitem__(key, ObservableDict(self.save_callback, value))
            else:
                super().__setitem__(key, value)

    def __setitem__(self, key: str, value: Any) -> None:
        self._set_no_save(key, value)
        self.save_callback()

    def __delitem__(self, key: str) -> None:
        super().__delitem__(key)
        self.origin_data.__delitem__(key)
        self.save_callback()

    def _set_no_save(self, key: str, value: Any) -> None:
        """修改键值，不支持添加新键，不更新文件，只接受原生python类型数据"""
        if key in self:
            # 1. 更新ObservableDict对象内部数据，如果源数据为dict，递归转换为ObservableDict类型
            observ_value = value
            if isinstance(value, dict) and not isinstance(value, ObservableDict):
                observ_value = ObservableDict(self.save_callback, value)
            super().__setitem__(key, observ_value)

            # 2. 同步更新内部origin_data中的值
            origin_value = self.origin_data.get(key)
            if isinstance(value, dict) and isinstance(origin_value, dict):
                _update_nested_dict(origin_value, value)
            else:
                self.origin_data[key] = value

    def update(self, new_data: Optional[Dict] = None, **kwargs) -> None:
        new_data = new_data or {}
        for k, v in new_data.items():
            self._set_no_save(k, v)
        for k, v in kwargs.items():
            self._set_no_save(k, v)
        self.save_callback()

    @property
    def dict(self) -> dict:
        """获取一个普通字典类型"""
        return self.origin_data


class ConfigManager:
    _instance = None
    _config: ObservableDict = None
    _config_path: str = CONFIG_PATH
    _default_config_path: str = DEFAULT_CONFIG_PATH
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
            if not os.path.exists(self._config_path) and not os.path.exists(self._default_config_path):
                raise FileNotFoundError("Can`t find config")

            if not os.path.exists(self._config_path):
                # 复制默认配置文件到配置文件目录
                shutil.copy2(self._default_config_path, self._config_path)

            with open(self._config_path, "r", encoding='utf-8') as f:
                raw_config = self._yaml.load(f)

            # 让已有配置文件自动获得新版本新增的默认配置项，例如 max_history
            if os.path.exists(self._default_config_path):
                with open(self._default_config_path, "r", encoding='utf-8') as f:
                    default_config = self._yaml.load(f)
                if isinstance(raw_config, dict) and isinstance(default_config, dict):
                    _merge_missing_defaults(raw_config, default_config)

            self._config = self._wrap_dict(raw_config)
            logger.debug("Config loaded.")
        except Exception as e:
            logger.error(f"Config init failed: {str(e)}")
            raise

    def _wrap_dict(self, data: Dict) -> ObservableDict:
        def save_callback():
            self._save()

        return ObservableDict(save_callback, data)

    def _save(self) -> None:
        try:
            temp_path = f"{self._config_path}.tmp"
            with open(f"{temp_path}", "w", encoding='utf-8') as f:
                self._yaml.dump(self._config.origin_data, f)
            os.replace(temp_path, self._config_path)
            logger.info("Config saved.")
        except Exception as e:
            logger.error(f"Save failed: {str(e)}")
            raise

    @property
    def data(self) -> ObservableDict:
        return self._config


# 全局单例（直接像字典一样操作）, 注：config内部的字典默认是ObservableDict类型的，如果需要获取普通dict类型，需要加获取.dict属性
config = ConfigManager().data
# logger.info(f"{config}")
