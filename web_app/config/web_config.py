# web_config.py — Web 服务端配置管理器
# 配置文件位于 web_app/web_conf.yaml，独立于 seseget 配置系统
import os
from ruamel.yaml import YAML

from seseget.config.config_manager import ObservableDict

# 配置文件路径：web_app/web_conf.yaml
_WEB_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_CONFIG_PATH = os.path.join(_WEB_APP_DIR, "web_conf.yaml")

_yaml = YAML()
_yaml.preserve_quotes = True
_yaml.width = 2147483647

# 默认配置内容
_DEFAULT_CONFIG = {"auth_token": ""}


def _init_web_config():
    """初始化 web 配置文件"""
    if not os.path.exists(WEB_CONFIG_PATH):
        with open(WEB_CONFIG_PATH, "w", encoding="utf-8") as f:
            _yaml.dump(_DEFAULT_CONFIG, f)

    with open(WEB_CONFIG_PATH, "r", encoding="utf-8") as f:
        raw_config = _yaml.load(f)

    return raw_config or _DEFAULT_CONFIG


class WebConfigManager:
    _instance = None
    _config: ObservableDict = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        raw_config = _init_web_config()

        def save_callback():
            self._save()

        self._config = ObservableDict(save_callback, raw_config)

    def _save(self):
        try:
            temp_path = f"{WEB_CONFIG_PATH}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                _yaml.dump(self._config.origin_data, f)
            os.replace(temp_path, WEB_CONFIG_PATH)
        except Exception as e:
            print(f"[WebConfig] Save failed: {e}")
            raise

    @property
    def data(self) -> ObservableDict:
        return self._config


web_config = WebConfigManager().data
