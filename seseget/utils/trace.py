import logging
from logging import Formatter, LogRecord, StreamHandler
from .output import sese_stdout
from ..config import settings


class DynamicFormatter(Formatter):
    """ 根据日志等级动态切换格式的 Formatter """

    def __init__(self):
        # 定义不同等级的格式模板
        super().__init__()
        asctime_str = "[%(asctime)s] " if settings.LOG_SHOW_TIMESTAMP else ""
        levelname_str = "[%(levelname)s] " if settings.LOG_SHOW_LEVEL else ""
        self._formats = {
            logging.DEBUG: asctime_str + levelname_str + "[%(filename)s:%(lineno)d] %(message)s",
            logging.INFO: asctime_str + levelname_str + "%(message)s",
            logging.WARNING: asctime_str + levelname_str + "%(message)s",
            logging.ERROR: asctime_str + levelname_str + "[%(filename)s:%(lineno)d] %(message)s",
            logging.CRITICAL: asctime_str + levelname_str + "[%(filename)s:%(lineno)d] %(message)s"
        }

        # 统一日期格式
        self._datefmt = "%d/%b/%Y %H:%M:%S"

    def format(self, record: LogRecord) -> str:
        # 动态选择格式模板
        formatter = logging.Formatter(
            fmt=self._formats.get(record.levelno, self._formats[logging.DEBUG]),
            datefmt=self._datefmt
        )
        return formatter.format(record)


class ColorDynamicFormatter(DynamicFormatter):
    """ 带颜色支持的动态格式 """
    COLOR_MAP = {
        logging.DEBUG: "\033[36m",  # 青色
        #logging.INFO: "\033[32m",  # 绿色
        logging.INFO: "\033[0m",  # 绿色
        logging.WARNING: "\033[33m",  # 黄色
        logging.ERROR: "\033[31m",  # 红色
        logging.CRITICAL: "\033[31;1m"  # 亮红色
    }
    RESET = "\033[0m"

    def format(self, record: LogRecord) -> str:
        # 获取原始日志内容
        message = super().format(record)

        # 添加颜色
        color = self.COLOR_MAP.get(record.levelno, "")
        return f"{color}{message}{self.RESET}"


class NoNewlineHandler(StreamHandler):
    """ 不自动添加换行的处理器 """
    def emit(self, record: LogRecord) -> None:
        try:
            # 获取 end 参数（默认为 \n）
            end = getattr(record, "end", "\n")
            msg = self.format(record) + end  # 添加自定义结尾


            # 输出到控制台
            sese_stdout.write(msg)
            self.flush()
        except Exception as e:
            self.handleError(record)


# 配置日志系统
def setup_logger():
    logger = logging.getLogger("sese_trace")
    logger.setLevel(settings.LOG_LEVEL)  # 设置日志级别

    # 创建控制台处理器
    handler = NoNewlineHandler()
    handler.setFormatter(ColorDynamicFormatter())  # 应用动态格式

    # 只保留一个处理器避免重复输出
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(handler)


LOG_DEBUG = logging.DEBUG
LOG_INFO = logging.INFO
LOG_WARNING = logging.WARNING
LOG_ERROR = logging.ERROR
LOG_CRITICAL = logging.CRITICAL


def SESE_TRACE(level, msg: str, end="\n"):
    extra = {"end": end}  # 将 end 存入 extra
    logger = logging.getLogger("sese_trace")  # 获取Logger
    logger.log(level, msg, extra=extra, stacklevel=2)


def SESE_PRINT(msg: str, end="\n"):
    SESE_TRACE(LOG_INFO, msg, end)

