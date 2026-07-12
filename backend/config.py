import os


def _load_env_file(path):
    if not os.path.exists(path):
        return

    with open(path, encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("\"'")
            os.environ.setdefault(key, value)


_load_env_file(os.path.join(os.path.dirname(__file__), ".env"))

DATABASE_PATH = os.environ.get(
    "DATABASE_PATH",
    os.path.join(os.path.dirname(__file__), "notgoogledocs.sqlite3"),
)
TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24 * 7
DEFAULT_SECRET_KEY = "dev-only-change-me-before-deployment"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_RESPONSES_URL = os.environ.get(
    "OPENAI_RESPONSES_URL",
    "https://api.openai.com/v1/responses",
)
