import os

from flask import Flask
from flask_cors import CORS

from backend.config import DEFAULT_SECRET_KEY
from backend.database import close_db, init_db
from backend.routes import register_blueprints
from backend.sockets.collab_socket import socketio, register_collab_socket_handlers

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", DEFAULT_SECRET_KEY)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    @app.before_request
    def ensure_database():
        init_db()

    app.teardown_appcontext(close_db)
    register_blueprints(app)

    socketio.init_app(app)
    register_collab_socket_handlers(socketio)

    return app
