from fastapi import APIRouter

from . import auth, download, search, settings, version

api_router: APIRouter = APIRouter()

api_router.include_router(download.router, prefix="/download")
api_router.include_router(search.router, prefix="/search")
api_router.include_router(settings.router, prefix="/settings")
api_router.include_router(auth.router, prefix="/auth")
api_router.include_router(version.router, prefix="/version")
