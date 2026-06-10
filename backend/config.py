import os

DATABASE_PATH = os.environ.get(
    "DATABASE_PATH",
    os.path.join(os.path.dirname(__file__), "notgoogledocs.sqlite3"),
)
TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24 * 7
DEFAULT_SECRET_KEY = "dev-only-change-me-before-deployment"
