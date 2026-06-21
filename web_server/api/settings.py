from flask import request, Blueprint
from seseget.config.config_manager import config
from .response import ResponseCode, ApiResponse


settings_bp = Blueprint('api/settings', __name__)


@settings_bp.route('', methods=['GET'])
def settings():
    response = ApiResponse(
        code=ResponseCode.SUCCESS,
        message="Success",
        data=config.dict
    )
    print("response: ", response.to_dict())
    return response.to_response()


@settings_bp.route('/save', methods=['POST'])
def save():
    data = request.json
    print("data: ", data)

    print("old config: ", config.dict)
    config.update(data)
    print("new config: ", config.dict)

    response = ApiResponse(
        code=ResponseCode.SUCCESS,
        message="Success",
        data=""
    )
    print("response: ", response.to_dict())
    return response.to_response()
