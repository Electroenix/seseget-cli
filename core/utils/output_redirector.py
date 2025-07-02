import sys
import io
from tqdm import tqdm


class TQDMSafeOutput(io.TextIOWrapper):
    def __init__(self, orig_stream):
        # 代理原始流的所有属性
        super().__init__(
            buffer=getattr(orig_stream, 'buffer', orig_stream),
            encoding=getattr(orig_stream, 'encoding', 'utf-8'),
            errors=getattr(orig_stream, 'errors', 'replace'),
            newline=getattr(orig_stream, 'newline', '\n'),
            line_buffering=getattr(orig_stream, 'line_buffering', False)
        )
        self._orig_stream = orig_stream

    def write(self, msg):
        if msg:
            tqdm.write(msg, file=sys.__stdout__, end="")

    def flush(self):
        self._orig_stream.flush()

    def __getattr__(self, name):
        """代理其他属性到原始流"""
        return getattr(self._orig_stream, name)


# 初始化（兼容Windows ANSI）
try:
    import colorama

    colorama.init()
except ImportError:
    pass

sese_stdout = TQDMSafeOutput(sys.__stdout__)

