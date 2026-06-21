import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from web_server import app, socketio
from web_server.utils import get_or_create_event_loop, shutdown_event_loop
from web_server.api.download import emit_download_status

if __name__ == "__main__":
    get_or_create_event_loop()

    socketio.start_background_task(emit_download_status)
    try:
        socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
    finally:
        shutdown_event_loop()
