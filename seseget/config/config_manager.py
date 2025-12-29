# config_manager.py
import os
from collections import UserDict
from typing import Any, Dict, Optional, Union
from ruamel.yaml import YAML
import shutil

from ..utils.trace import *
from .path import CONFIG_PATH, DEFAULT_CONFIG_PATH


class ObservableDict(UserDict):
    """
    模拟字典类型，支持在检测到内容修改时自动更新文件
    save_callback   - 初始化时设置save_callback回调函数，如果内部数据修改，将会触发回调将最新内容保存到文件
    origin_data     - 初始化时传入的原始类型数据，如果内部数据修改，将会同步修改此数据内容
    """
    def __init__(self, save_callback: callable, initial_data: Optional[Dict] = None):
        self.origin_data = initial_data  # 保留原始数据类型，数据被修改时同步修改原始数据
        self.save_callback = save_callback  # 先设置回调
        initial_data = initial_data or {}
        super().__init__()  # 不传数据，避免触发父类 update

        # 手动初始化数据（确保使用覆盖后的 __setitem__）
        for key, value in initial_data.items():
            # 直接操作父类方法，避免触发回调
            super().__setitem__(key, value)
            if isinstance(value, dict):
                super().__setitem__(key, ObservableDict(self.save_callback, value))

    def __setitem__(self, key: str, value: Any) -> None:
        if isinstance(value, dict) and not isinstance(value, ObservableDict):
            value = ObservableDict(self.save_callback, value)
        super().__setitem__(key, value)
        self.origin_data.__setitem__(key, value)
        self.save_callback()

    def __delitem__(self, key: str) -> None:
        super().__delitem__(key)
        self.origin_data.__delitem__(key)
        self.save_callback()

    def _set_no_save(self, key: str, value: Any) -> None:
        """修改键值，但不更新文件"""
        if isinstance(value, dict) and not isinstance(value, ObservableDict):
            value = ObservableDict(self.save_callback, value)
        super().__setitem__(key, value)
        self.origin_data.__setitem__(key, value)

    def update(self, new_data: Optional[Dict] = None, **kwargs) -> None:
        new_data = new_data or {}
        for k, v in new_data.items():
            self._set_no_save(k, v)
        for k, v in kwargs.items():
            self._set_no_save(k, v)
        self.save_callback()

    def _to_dict(self, node: Union["ObservableDict", Any]) -> Any:
        """递归转换 ObservableDict 为原生 Python 类型"""
        if isinstance(node, ObservableDict):
            return {k: self._to_dict(v) for k, v in node.items()}
        elif isinstance(node, list):
            return [self._to_dict(item) for item in node]
        else:
            return node

    @property
    def dict(self) -> dict:
        """获取一个普通字典类型"""
        return self._to_dict(self)


class ConfigManager:
    _instance = None
    _config: ObservableDict = None
    _config_path: str = CONFIG_PATH
    _default_config_path: str = DEFAULT_CONFIG_PATH
    _yaml = YAML()
    _yaml.preserve_quotes = True

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
            self._config = self._wrap_dict(raw_config)
            SESE_TRACE(LOG_DEBUG, "Config loaded.")
        except Exception as e:
            SESE_TRACE(LOG_ERROR, f"Config init failed: {str(e)}")
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
            SESE_PRINT("Config saved.")
        except Exception as e:
            SESE_TRACE(LOG_ERROR, f"Save failed: {str(e)}")
            raise

    @property
    def data(self) -> ObservableDict:
        return self._config


# 全局单例（直接像字典一样操作）, 注：config内部的字典默认是ObservableDict类型的，如果需要获取普通dict类型，需要加获取.dict属性
config = ConfigManager().data
# SESE_TRACE(LOG_INFO, f"{config}")
