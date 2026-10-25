"""类型化配置 schema、默认值、UI 元数据和部分更新校验。"""

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, get_origin

from pydantic import BaseModel, ConfigDict, Field


class ConfigModel(BaseModel):
    """配置模型基类：允许旧配置中的废弃字段保留到迁移阶段。"""

    model_config = ConfigDict(extra="allow")


class CommonConfig(ConfigModel):
    proxy: str = Field(
        "",
        description="代理地址，留空使用系统代理",
        json_schema_extra={"label": "代理地址"},
    )


class HanimeConfig(ConfigModel):
    cookie: str = Field(
        "",
        description="请求被拦截时使用的 Cookie",
        json_schema_extra={"label": "Cookie", "secret": True},
    )
    organize_by_genre: bool = Field(
        False,
        description="是否按影片类型整理下载目录",
        json_schema_extra={"label": "按类型整理"},
    )


class BikaConfig(ConfigModel):
    username: str = Field(
        "",
        description="哔咔账号",
        json_schema_extra={"label": "用户名"},
    )
    password: str = Field(
        "",
        description="哔咔密码",
        json_schema_extra={"label": "密码", "secret": True},
    )


class JMComicLoginConfig(ConfigModel):
    username: str = Field(
        "",
        description="禁漫账号",
        json_schema_extra={"label": "用户名"},
    )
    password: str = Field(
        "",
        description="禁漫密码",
        json_schema_extra={"label": "密码", "secret": True},
    )


class JMComicConfig(ConfigModel):
    login: JMComicLoginConfig = Field(default_factory=JMComicLoginConfig)


class BilibiliConfig(ConfigModel):
    cookie: str = Field(
        "",
        description="B 站 Cookie，部分视频需要",
        json_schema_extra={"label": "Cookie", "secret": True},
    )


class TwitterConfig(ConfigModel):
    cookie_file: str = Field(
        "",
        description="Netscape 格式 Cookie 文件路径",
        json_schema_extra={"label": "Cookie 文件"},
    )


class DownloadComicConfig(ConfigModel):
    leave_images: bool = Field(
        False,
        description="打包后是否保留原始图片",
        json_schema_extra={"label": "保留下载图片"},
    )
    format: list[str] = Field(
        default_factory=lambda: ["cbz"],
        description="漫画成品格式",
        json_schema_extra={"label": "漫画格式"},
    )


class DownloadVideoConfig(ConfigModel):
    metadata_file: list[str] = Field(
        default_factory=lambda: ["nfo"],
        description="视频元数据文件格式",
        json_schema_extra={"label": "视频元数据格式"},
    )


class DownloadConfig(ConfigModel):
    max_history: int = Field(
        200,
        ge=1,
        description="下载历史最多保留条数",
        json_schema_extra={"label": "历史保留条数"},
    )
    save_source_info: bool = Field(
        False,
        description="是否在下载目录生成 source.txt",
        json_schema_extra={"label": "生成来源信息"},
    )
    comic: DownloadComicConfig = Field(default_factory=DownloadComicConfig)
    video: DownloadVideoConfig = Field(default_factory=DownloadVideoConfig)


class AppConfig(ConfigModel):
    common: CommonConfig = Field(default_factory=CommonConfig)
    hanime: HanimeConfig = Field(default_factory=HanimeConfig)
    bika: BikaConfig = Field(default_factory=BikaConfig)
    jmcomic: JMComicConfig = Field(default_factory=JMComicConfig)
    bilibili: BilibiliConfig = Field(default_factory=BilibiliConfig)
    twitter: TwitterConfig = Field(default_factory=TwitterConfig)
    download: DownloadConfig = Field(default_factory=DownloadConfig)


SECTION_META = {
    "common": {"label": "通用", "description": "代理等基础设置"},
    "hanime": {"label": "Hanime", "description": "Hanime 站点设置"},
    "bika": {"label": "哔咔", "description": "哔咔账号设置"},
    "jmcomic": {"label": "禁漫", "description": "禁漫账号设置"},
    "bilibili": {"label": "哔哩哔哩", "description": "B 站 Cookie"},
    "twitter": {"label": "Twitter", "description": "Twitter Cookie 文件"},
    "download": {"label": "下载", "description": "下载、历史与输出格式"},
}

SESSION_FIELDS = {
    "bika.token",
    "bika.nonce",
    "jmcomic.login.cookie",
}


@dataclass(frozen=True)
class FieldSpec:
    path: str
    kind: str
    secret: bool = False
    editable: bool = True
    label: str = ""
    description: str = ""


def _kind_for(annotation: Any) -> str:
    if annotation is str:
        return "str"
    if annotation is bool:
        return "bool"
    if annotation is int:
        return "int"
    if get_origin(annotation) is list:
        return "str_list"
    return "unknown"


def _walk_fields(model: type[BaseModel], prefix: str = ""):
    for name, field in model.model_fields.items():
        path = f"{prefix}.{name}" if prefix else name
        annotation = field.annotation
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            yield from _walk_fields(annotation, path)
            continue

        extra = field.json_schema_extra or {}
        yield FieldSpec(
            path=path,
            kind=_kind_for(annotation),
            secret=bool(extra.get("secret", False)),
            editable=bool(extra.get("editable", True)),
            label=str(extra.get("label", name)),
            description=field.description or "",
        )


CONFIG_FIELDS: dict[str, FieldSpec] = {
    spec.path: spec for spec in _walk_fields(AppConfig)
}

DEFAULTS: dict = AppConfig().model_dump()


def get_default_config() -> dict:
    return deepcopy(DEFAULTS)


def get_ui_schema() -> dict:
    return {
        "sections": deepcopy(SECTION_META),
        "fields": {
            path: {
                "label": spec.label,
                "description": spec.description,
                "kind": spec.kind,
                "secret": spec.secret,
                "editable": spec.editable,
            }
            for path, spec in CONFIG_FIELDS.items()
        },
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


def _path_exists(data: dict, path: str) -> bool:
    current = data
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return False
        current = current[key]
    return True


def redact_config(config_data: dict) -> tuple[dict, list[str], list[str]]:
    """只返回 schema 中允许的字段，并隐藏敏感值。"""
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

    return visible, sorted(path for path, spec in CONFIG_FIELDS.items() if spec.secret), configured


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


def build_patch(changes: dict[str, Any]) -> dict:
    """把扁平路径 changes 转成嵌套 patch。"""
    patch: dict = {}
    for path, value in changes.items():
        _set_by_path(patch, path, value)
    return patch


def validate_config(config_data: dict) -> dict:
    """用类型化模型校验并规范化配置；旧字段允许保留到迁移阶段。"""
    return AppConfig.model_validate(config_data).model_dump()
