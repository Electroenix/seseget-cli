import os

from seseget.config.path import CONFIG_DIR


SESEGET_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
WEB_PKG_BASE_DIR = os.path.dirname(os.path.dirname(__file__))

WEB_CONFIG_PATH = str(CONFIG_DIR / "web_conf.yaml")

STATIC_FILES_URI = "/static/files"
STATIC_COVER_URI = STATIC_FILES_URI + "/cover"
STATIC_THUMBNAIL_URI = STATIC_FILES_URI + "/thumbnail"
STATIC_FILES_DIR = WEB_PKG_BASE_DIR + STATIC_FILES_URI
STATIC_COVER_DIR = WEB_PKG_BASE_DIR + STATIC_COVER_URI
STATIC_THUMBNAIL_DIR = WEB_PKG_BASE_DIR + STATIC_THUMBNAIL_URI


def mk_static_path():
    if not os.path.exists(STATIC_FILES_DIR):
        os.mkdir(STATIC_FILES_DIR)
    if not os.path.exists(STATIC_COVER_DIR):
        os.mkdir(STATIC_COVER_DIR)
    if not os.path.exists(STATIC_THUMBNAIL_DIR):
        os.mkdir(STATIC_THUMBNAIL_DIR)
