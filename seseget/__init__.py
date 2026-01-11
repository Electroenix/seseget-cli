from .config import settings
from .request.fetcher import FetcherRegistry

# 注册站点
FetcherRegistry.discover(settings.SITE_FETCHERS_PACKAGE)
