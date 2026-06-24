from flask import request, Blueprint
from web_app.config.web_config import web_config
from .response import ResponseCode, ApiResponse


web_settings_bp = Blueprint('api/web-settings', __name__)


@web_settings_bp.route('', methods=['GET'])
def web_settings():
    response = ApiResponse(
        code=ResponseCode.SUCCESS,
        message="Success",
        data=web_config.dict
    )
    return response.to_response()


@web_settings_bp.route('/save', methods=['POST'])
def save_web_settings():
    data = request.json
    web_config.update(data)

    response = ApiResponse(
        code=ResponseCode.SUCCESS,
        message="Success",
        data=""
    )
    return response.to_response()
