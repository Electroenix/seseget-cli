import io
import logging

import seseget.utils.trace as trace_module
from seseget.utils.trace import SSGLogger


def make_logger(monkeypatch, name):
    output = io.StringIO()
    monkeypatch.setattr(trace_module, "ssg_stdout", output)
    return SSGLogger(name, level=logging.DEBUG), output


def test_logger_formats_args_like_stdlib(monkeypatch):
    logger, output = make_logger(monkeypatch, "test-logger-args")

    logger.warning("下载失败: %s", "原因")

    text = output.getvalue()
    assert "下载失败: 原因" in text


def test_logger_supports_exc_info(monkeypatch):
    logger, output = make_logger(monkeypatch, "test-logger-exc")

    try:
        raise RuntimeError("boom")
    except RuntimeError as e:
        logger.warning("下载失败: %s", e, exc_info=True)

    text = output.getvalue()
    assert "下载失败: boom" in text
    assert "RuntimeError" in text


def test_logger_keeps_custom_end(monkeypatch):
    logger, output = make_logger(monkeypatch, "test-logger-end")

    logger.info("progress", end="\r")

    text = output.getvalue()
    assert "progress" in text
    assert text.endswith("\r")
