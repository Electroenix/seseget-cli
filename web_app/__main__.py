import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import uvicorn
from web_app import socket_app
from web_app.config.web_config import web_config

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seseget Web Server")
    parser.add_argument(
        "--prod",
        action="store_true",
        help="Run in Production mode (debug disabled, no auto-reload)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=12450,
        help="Port to bind (default: 12450)",
    )
    args = parser.parse_args()

    use_debug = not args.prod
    mode_label = "Production" if args.prod else "Development"

    print(f"\n{'='*50}")
    print(f"  [{mode_label} Mode]  FastAPI + Socket.IO (ASGI)")
    print(f"  debug={use_debug}")
    print(f"  Listening on http://{args.host}:{args.port}")
    print(f"{'='*50}\n")
    print(f"{'='*50}")
    print(f"  [Auth Token]: {web_config['auth_token']}")
    print(f"{'='*50}\n")

    uvicorn.run(
        "web_app:socket_app",
        host=args.host,
        port=args.port,
        reload=use_debug,
        log_level="info",
    )
