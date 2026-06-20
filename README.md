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
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
python -m backend.app
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
- `POST /api/documents/:id/share`
- `GET /api/documents/:id/diff?from=:versionId&to=:versionId`
- `GET /api/documents/:id/state`
- `GET /api/documents/:id/revisions?since=:revisionNumber`
- `POST /api/documents/:id/revisions`

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
- `POST /api/documents/:id/share`
- `GET /api/documents/:id/state`
- `GET /api/documents/:id/revisions?since=:revisionNumber`
- `POST /api/documents/:id/revisions`

## Notes

- Passwords are hashed with Werkzeug before storage.
- Auth tokens are signed with Flask's `SECRET_KEY` via `itsdangerous`.
- SQLite is used for the proof of concept and stored in `backend/notgoogledocs.sqlite3` by default.
- Documents keep an auto-saved mutable draft plus full-text saved snapshots for deterministic comparison.
- Saved versions are private to the user who marks them, even on shared documents.
- Restoring a saved version updates the current working draft without creating a new marked version.
- Restoring a saved version changes the document content only; the document title stays unchanged.
- The commit summary is currently a deterministic stub that counts added and removed words. It can later be replaced by a server-side LLM call without changing the frontend contract.
- To run unit tests, download the libraries specified within `backend/requirements.txt` and run `pytest -v`

## Implementing OT Engine

When two users edit the same document:
    1. Each client sends a changeset (a list of retain/insert/delete ops) based on a base revision
    2. The server transforms the incoming edit against any edits it missed
    3. The server applies the result to the current document text
    4. The server stores a new row in document_revisions

The `transform()` and `apply_changeset()` method is tested and available in `ot_engine/`. `submit_collab_change(...)` method in `collab_service.py` orchestrates the whole flow for the backend.

## New model classes for document revisions added

- New model classes were also added and their tables are inserted into the sqlite file.
- These classes facilitates user collaboration and store document revision history in a format that allows OT to be performed on concurrent edits
