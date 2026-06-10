import os

from backend import create_app
from backend.config import DATABASE_PATH

create_app_instance = create_app()

__all__ = ["create_app", "create_app_instance", "DATABASE_PATH"]

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5001"))
    debug = os.environ.get("FLASK_DEBUG") == "1"
    create_app_instance.run(host="127.0.0.1", port=port, debug=debug)
