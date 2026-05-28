# NotGoogleDocs

NUS Orbital 2026 Apollo 11 project: a document collaboration tool built around explicit saved versions and deterministic revision history.

This proof of concept implements email/password registration, login, document creation, auto-saved working drafts, explicit version saving, version restore, version history, and a split-screen diff viewer with red deletions and green insertions.

## Project Structure

```text
backend/   Flask API, SQLite database, password hashing, signed auth tokens, document/version APIs
frontend/  React + Vite app with a Google Docs-inspired editor and split diff viewer
```

## Run Locally

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The API runs at `http://127.0.0.1:5001`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app runs at `http://127.0.0.1:5173`.

## Implemented API

- `GET /api/health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/documents`
- `POST /api/documents`
- `GET /api/documents/:id`
- `PATCH /api/documents/:id`
- `GET /api/documents/:id/versions`
- `POST /api/documents/:id/versions`
- `POST /api/documents/:id/restore`
- `GET /api/documents/:id/diff?from=:versionId&to=:versionId`

## Implemented Unit Tests For Routes:
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/documents`
- `POST /api/documents`
- `GET /api/documents/:id`
- `PATCH /api/documents/:id`
- `GET /api/documents/:id/versions`
- `POST /api/documents/:id/versions`

## Notes

- Passwords are hashed with Werkzeug before storage.
- Auth tokens are signed with Flask's `SECRET_KEY` via `itsdangerous`.
- SQLite is used for the proof of concept and stored in `backend/notgoogledocs.sqlite3` by default.
- Documents keep an auto-saved mutable draft plus full-text saved snapshots for deterministic comparison.
- Restoring a saved version updates the current working draft without creating a new marked version.
- The commit summary is currently a deterministic stub that counts added and removed words. It can later be replaced by a server-side LLM call without changing the frontend contract.
- To run unit tests, download the libraries specified within `backend/requirements.txt` and run `pytest -v`
