import logging

# 包含所有站点Fetcher的包，注册器会注册其中可注册的所有Fetcher类
SITE_FETCHERS_PACKAGE = "seseget.sites"

# 控制打印Log是否显示时间戳
LOG_SHOW_TIMESTAMP = False

# 控制打印Log是否显示Log等级
LOG_SHOW_LEVEL = False

# 打印Log等级
LOG_LEVEL = logging.INFO

# 全局请求超时时间(s)
REQUEST_TIMEOUT = 10

# 工作进程退出超时时间(s)，超过设定时间还在运行则强制中断进程
WORKER_PROGRESS_TERMINAL_TIMEOUT = 3
