from flask import Blueprint

api_bp = Blueprint('api', __name__)

from . import download, search, settings, auth, web_settings

api_bp.register_blueprint(download.download_bp, url_prefix='/download')
api_bp.register_blueprint(search.search_bp, url_prefix='/search')
api_bp.register_blueprint(settings.settings_bp, url_prefix='/settings')
api_bp.register_blueprint(auth.auth_bp, url_prefix='/auth')
api_bp.register_blueprint(web_settings.web_settings_bp, url_prefix='/web-settings')
