from backend.routes.auth import auth_bp
from backend.routes.collab import collab_bp
from backend.routes.documents import documents_bp
from backend.routes.health import health_bp


def register_blueprints(app):
    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(documents_bp, url_prefix="/api/documents")
    app.register_blueprint(collab_bp, url_prefix="/api/documents")
