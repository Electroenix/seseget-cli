"""配置字段 schema、脱敏和部分更新校验。"""

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FieldSpec:
    path: str
    kind: str
    secret: bool = False
    editable: bool = True
    storage: str = "config"


CONFIG_FIELDS: dict[str, FieldSpec] = {
    "common.proxy": FieldSpec("common.proxy", "str"),
    "hanime.cookie": FieldSpec("hanime.cookie", "str", secret=True),
    "hanime.organize_by_genre": FieldSpec("hanime.organize_by_genre", "bool"),
    "bika.username": FieldSpec("bika.username", "str"),
    "bika.password": FieldSpec("bika.password", "str", secret=True),
    "jmcomic.login.username": FieldSpec("jmcomic.login.username", "str"),
    "jmcomic.login.password": FieldSpec("jmcomic.login.password", "str", secret=True),
    "bilibili.cookie": FieldSpec("bilibili.cookie", "str", secret=True),
    "twitter.cookie_file": FieldSpec("twitter.cookie_file", "str"),
    "download.max_history": FieldSpec("download.max_history", "int"),
    "download.save_source_info": FieldSpec("download.save_source_info", "bool"),
    "download.comic.leave_images": FieldSpec("download.comic.leave_images", "bool"),
    "download.comic.format": FieldSpec("download.comic.format", "str_list"),
    "download.video.metadata_file": FieldSpec("download.video.metadata_file", "str_list"),
}

SESSION_FIELDS = {
    "bika.token",
    "bika.nonce",
    "jmcomic.login.cookie",
}

SECRET_FIELDS = {
    path for path, spec in CONFIG_FIELDS.items() if spec.secret
}


def _get_by_path(data: dict, path: str):
    current = data
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _set_by_path(data: dict, path: str, value: Any) -> None:
    keys = path.split(".")
    current = data
    for key in keys[:-1]:
        current = current.setdefault(key, {})
    current[keys[-1]] = value


def redact_config(config_data: dict) -> tuple[dict, list[str], list[str]]:
    """只返回 schema 中允许的字段，并隐藏敏感值。

    返回：脱敏后的配置、敏感字段列表、已设置敏感字段列表。
    """
    raw = config_data.dict if hasattr(config_data, "dict") else config_data
    visible: dict = {}
    configured: list[str] = []

    for path, spec in CONFIG_FIELDS.items():
        if not _path_exists(raw, path):
            continue
        value = _get_by_path(raw, path)
        if spec.secret:
            if value not in (None, ""):
                configured.append(path)
            _set_by_path(visible, path, "")
        else:
            _set_by_path(visible, path, deepcopy(value))

    return visible, sorted(SECRET_FIELDS), configured


def _path_exists(data: dict, path: str) -> bool:
    current = data
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return False
        current = current[key]
    return True


def _validate_value(spec: FieldSpec, value: Any) -> str | None:
    if spec.kind == "str":
        if not isinstance(value, str):
            return "必须是字符串"
    elif spec.kind == "bool":
        if type(value) is not bool:
            return "必须是布尔值"
    elif spec.kind == "int":
        if type(value) is not int:
            return "必须是整数"
        if value < 1:
            return "必须大于等于 1"
    elif spec.kind == "str_list":
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            return "必须是字符串数组"
    else:
        return "字段类型未定义"
    return None


def validate_changes(config_data: dict, changes: Any) -> str | None:
    """校验扁平路径 changes，校验通过返回 None。"""
    if not isinstance(changes, dict):
        return "changes 必须是对象"

    raw = config_data.dict if hasattr(config_data, "dict") else config_data

    for path, value in changes.items():
        if not isinstance(path, str):
            return "字段路径必须是字符串"
        if path in SESSION_FIELDS:
            return f"{path} 是程序管理的会话字段，不能通过配置接口修改"
        spec = CONFIG_FIELDS.get(path)
        if spec is None:
            return f"未知配置字段: {path}"
        if not _path_exists(raw, path):
            return f"当前配置中不存在字段: {path}"
        error = _validate_value(spec, value)
        if error:
            return f"{path} {error}"
    return None


def build_patch(changes: dict[str, Any]) -> dict:
    """把扁平路径 changes 转成嵌套 patch。"""
    patch: dict = {}
    for path, value in changes.items():
        _set_by_path(patch, path, value)
    return patch
