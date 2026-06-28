from fastapi import APIRouter
from . import download, search, settings, auth, web_settings

api_router = APIRouter()

api_router.include_router(download.router, prefix="/download")
api_router.include_router(search.router, prefix="/search")
api_router.include_router(settings.router, prefix="/settings")
api_router.include_router(auth.router, prefix="/auth")
api_router.include_router(web_settings.router, prefix="/web-settings")
