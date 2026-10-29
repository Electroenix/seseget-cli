"""站点 HTML 解析辅助：统一查找失败上下文。"""

from __future__ import annotations

import inspect
import os
import re
from typing import Any, NoReturn

from bs4 import BeautifulSoup
from bs4.element import Tag

from ..request.errors import SiteParseError


def _format_value(value: Any) -> str:
    if isinstance(value, re.Pattern):
        return f"re.compile({value.pattern!r})"
    text = repr(value)
    if len(text) > 160:
        text = text[:157] + "..."
    return text


def _format_query(query: dict[str, Any]) -> str:
    if not query:
        return "{}"
    return "{" + ", ".join(
        f"{key}: {_format_value(value)}" for key, value in query.items()
    ) + "}"


def _node_label(node: Tag | BeautifulSoup | None) -> str:
    if node is None or isinstance(node, BeautifulSoup):
        return "soup"
    parts = [node.name]
    node_id = node.get("id")
    if isinstance(node_id, str) and node_id:
        parts.append(f"#{node_id}")
    node_class = node.get("class")
    if isinstance(node_class, list):
        parts.extend(f".{item}" for item in node_class if isinstance(item, str))
    elif isinstance(node_class, str) and node_class:
        parts.append(f".{node_class}")
    return "".join(parts)


class SiteParser:
    """保存页面 soup，并为查找失败提供统一上下文。"""

    def __init__(self, html: str, *, site: str, url: str = ""):
        self.site = site
        self.url = url
        self.soup = BeautifulSoup(html, "html.parser")

    @staticmethod
    def _caller_location() -> str:
        frame = inspect.currentframe()
        try:
            while frame is not None:
                filename = frame.f_code.co_filename
                if os.path.abspath(filename) != os.path.abspath(__file__):
                    return f"{os.path.basename(filename)}:{frame.f_lineno}"
                frame = frame.f_back
        finally:
            del frame
        return ""

    def _error(self, *, operation: str, message: str) -> SiteParseError:
        """拼接站点、调用位置和已经组装好的操作上下文。"""
        parts = [f"site={self.site}"]
        caller = self._caller_location()
        if caller:
            parts.append(f"at={caller}")
        parts.append(f"{operation}: {message}")
        message_text = f"页面解析失败：{', '.join(parts)}"
        return SiteParseError(message_text, site=self.site, url=self.url)

    @staticmethod
    def _context(
        query: dict[str, Any],
        node: Tag | BeautifulSoup | None = None,
    ) -> str:
        context = _format_query(query)
        if node is not None:
            return f"node={_node_label(node)}, {context}"
        return context

    def fail(self, message: str) -> NoReturn:
        """抛出明确的解析失败原因，并自动附带调用位置。"""
        raise self._error(operation="fail", message=message)

    def find(
        self,
        *,
        node: Tag | BeautifulSoup | None = None,
        **query: Any,
    ) -> Tag:
        container = self.soup if node is None else node
        result = container.find(**query)
        if not isinstance(result, Tag):
            raise self._error(
                operation="find",
                message=self._context(query, node),
            )
        return result

    def find_all(
        self,
        *,
        node: Tag | BeautifulSoup | None = None,
        **query: Any,
    ) -> list[Tag]:
        container = self.soup if node is None else node
        results = [
            item for item in container.find_all(**query) if isinstance(item, Tag)
        ]
        if not results:
            raise self._error(
                operation="find_all",
                message=self._context(query, node),
            )
        return results

    def find_all_optional(
        self,
        *,
        node: Tag | BeautifulSoup | None = None,
        **query: Any,
    ) -> list[Tag]:
        container = self.soup if node is None else node
        return [
            item for item in container.find_all(**query) if isinstance(item, Tag)
        ]
