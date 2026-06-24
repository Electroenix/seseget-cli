from flask import Flask, send_from_directory, abort
from flask_socketio import SocketIO
import os
import secrets

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from web_app.config.web_config import web_config


app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 3600


# --- 认证 token 初始化 ---
def _init_auth_token():
    """启动时检查/生成认证 token"""
    if not web_config.get('auth_token', ''):
        token = secrets.token_urlsafe(16)
        web_config['auth_token'] = token
    else:
        token = web_config['auth_token']


_init_auth_token()

# --- 注册认证中间件 ---
from .api.auth import check_auth


@app.before_request
def _auth_middleware():
    return check_auth()


# --- 注册蓝图 ---
from .api import api_bp

app.register_blueprint(api_bp, url_prefix='/api')


@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    print(f"path: {path}")

    # 查找静态文件
    static_file = os.path.join(os.path.dirname(__file__), 'static', path)
    print(f"static_file: {static_file}")
    if os.path.exists(static_file) and os.path.isfile(static_file):
        return send_from_directory('static', path)

    return abort(404)
