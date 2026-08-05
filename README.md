# NotGoogleDocs

NotGoogleDocs is a collaborative document editor built for **NUS Orbital 2026 (Apollo 11)**. It combines real-time editing with explicit, user-marked version snapshots so that collaborators can work together without losing a clear and deterministic document history.

Unlike editors that treat every autosave as a meaningful revision, NotGoogleDocs separates the mutable working document from versions that a user deliberately saves. Users can compare any two of their saved versions in a split diff, restore an earlier version, and receive a concise summary of what changed.

## Current Features

- Email and password registration and login
- Multiple documents per user
- Automatic saving of the current working draft
- Explicit saved versions with optional version notes
- Private version histories for each user on a shared document
- Stable version numbers after a saved version is deleted
- Content-only version restoration that preserves the document title
- Side-by-side comparison with red deletions and green insertions
- AI-generated comparison summaries with a deterministic fallback
- Owner-controlled document sharing by registered email address
- Real-time collaborative editing over WebSockets
- Server-side Operational Transformation (OT) for concurrent edits
- Owner-only document deletion and user-owned version deletion

## How the Main Workflows Fit Together

### Working draft and saved versions

Each document has one shared working draft. Ordinary edits are automatically saved, while **Save version** creates a full-text snapshot only when the user decides that a revision is worth preserving.

Saved versions are private to the user who creates them. If two users collaborate on one document, they see the same working content but maintain separate marked-version histories. Restoring a version replaces the shared working content without changing the document title or creating another marked version.

### Real-time collaboration

The document owner shares a document using another registered user's email address. Both users can then enter collaboration mode and edit the same working document.

Each client sends retain, insert, and delete operations based on the document revision it last observed. The backend transforms an incoming change against revisions that the client missed, applies the transformed change, stores the resulting revision, and broadcasts it to the other connected clients.

### Version comparison and summaries

The backend computes an exact text diff between two full snapshots. The frontend displays the earlier and later versions side by side, highlighting removed text in red and inserted text in green.

When `OPENAI_API_KEY` is configured, the backend sends selected diff context to the OpenAI Responses API to produce a one-sentence summary. API keys remain server-side. If the API is unavailable or not configured, the app uses a deterministic fallback summary.

## Technology Stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, Vite, Socket.IO Client, Lucide icons |
| Backend | Flask, Flask-SocketIO, Gunicorn, Eventlet |
| Database | PostgreSQL with psycopg2 |
| Authentication | Werkzeug password hashing and signed `itsdangerous` tokens |
| Collaboration | Custom text OT engine using retain/insert/delete operations |
| Diffing | Python `difflib.SequenceMatcher` |
| AI summaries | OpenAI Responses API with deterministic fallback logic |
| Testing | pytest, Flask test client, Flask-SocketIO test client |

## Project Structure

```text
backend/
  models/       PostgreSQL queries and persistence
  routes/       Authentication, document, version, diff and revision endpoints
  services/     Application logic, OT orchestration and AI summaries
  sockets/      WebSocket authentication and collaboration events
  utils/        Validation, serialization and shared helpers
frontend/
  src/          React workspace, styles and Socket.IO client
ot_engine/      Change-set models, transformation and application logic
scripts/        AI-summary evaluation script
tests/          API, PostgreSQL, WebSocket, configuration and AI tests
```

## Run Locally

### Prerequisites

- Python 3.9 or later (the deployment runtime uses Python 3.11)
- Node.js and npm
- PostgreSQL

All commands below assume that the current directory is the project root unless stated otherwise.

### 1. Create the PostgreSQL databases

The application database and test database should be separate. The following example can be run from `psql` while connected as a PostgreSQL administrator:

```sql
CREATE USER notgoogledocs WITH PASSWORD 'localdev';
CREATE DATABASE notgoogledocs OWNER notgoogledocs;
CREATE DATABASE notgoogledocs_test OWNER notgoogledocs;
```

Use different credentials if these names already exist on your machine.

### 2. Configure the backend

Create `backend/.env`:

```env
SECRET_KEY=replace-this-with-a-long-random-string

DB_HOST=localhost
DB_NAME=notgoogledocs
DB_USERNAME=notgoogledocs
DB_PASSWORD=localdev

OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
```

`OPENAI_API_KEY` is optional. The comparison workflow falls back to a deterministic summary when it is empty.

For hosted environments, the backend also accepts a single `DATABASE_URL`:

```env
DATABASE_URL=postgresql://username:password@host:5432/database
```

`DATABASE_URL` takes precedence over the individual `DB_*` variables. For local pytest runs, use the individual variables so the test fixture can switch `DB_NAME` to `notgoogledocs_test`.

### 3. Start the backend

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m backend.app
```

The API and Socket.IO server run at `http://127.0.0.1:5001`.

Run the backend from the project root. Running `python app.py` from inside `backend/` does not provide Python with the package path required by `from backend import ...` imports.

### 4. Start the frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://127.0.0.1:5173`. Vite proxies `/api` and `/socket.io` requests to the local backend.

For a separately hosted backend, set the frontend build variable:

```env
VITE_API_BASE_URL=https://your-backend.example.com
```

## Testing

The automated suite currently contains **55 pytest cases**. It covers:

- OT transformation and convergence
- Authentication and document API workflows
- Version saving, comparison, restoration and deletion
- Owner and collaborator access control
- PostgreSQL persistence, constraints, serial IDs and conflict handling
- Socket.IO authentication, acknowledgements and broadcasts
- AI prompt construction, fallback behavior and long-diff selection
- Configuration loading and regression cases for previously fixed bugs

Ensure that PostgreSQL is running and that `notgoogledocs_test` exists, then run:

```bash
source backend/.venv/bin/activate
python -m pytest -v
```

The test fixture truncates the tables in `notgoogledocs_test` before each case and resets PostgreSQL identity sequences. Do not point the test configuration at a database containing important data.

## AI Summary Evaluation

The repository includes eight representative evaluation cases covering additions, removals, wording changes, punctuation fixes, collaboration descriptions and multi-part revisions.

Validate the cases and generated prompts without making API calls:

```bash
python scripts/evaluate_ai_summaries.py --dry-run
```

Evaluate the configured model against all cases:

```bash
python scripts/evaluate_ai_summaries.py
```

Run one case while refining the prompt:

```bash
python scripts/evaluate_ai_summaries.py --case clarify-real-time-collaboration
```

Live evaluation uses the configured OpenAI API key and may incur API usage. Generated outputs should still be reviewed manually against their reference summaries.

## HTTP API

All document endpoints require an `Authorization: Bearer <token>` header unless stated otherwise.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Check backend availability; no authentication required |
| `POST` | `/api/auth/register` | Create an account |
| `POST` | `/api/auth/login` | Sign in and receive a token |
| `GET` | `/api/auth/me` | Retrieve the authenticated user |
| `GET` | `/api/documents` | List owned and shared documents |
| `POST` | `/api/documents` | Create a document |
| `GET` | `/api/documents/:id` | Retrieve an accessible document |
| `PATCH` | `/api/documents/:id` | Autosave the working draft |
| `DELETE` | `/api/documents/:id` | Delete an owned document and its history |
| `GET` | `/api/documents/:id/versions` | List the current user's private saved versions |
| `POST` | `/api/documents/:id/versions` | Save a marked version |
| `DELETE` | `/api/documents/:id/versions/:versionId` | Delete one of the current user's versions |
| `POST` | `/api/documents/:id/restore` | Restore a private saved version |
| `POST` | `/api/documents/:id/share` | Share an owned document by registered email |
| `GET` | `/api/documents/:id/diff?from=:versionId&to=:versionId` | Compare two private versions |
| `GET` | `/api/documents/:id/state` | Retrieve content and the current head revision |
| `GET` | `/api/documents/:id/revisions?since=:revisionNumber` | Retrieve revisions after a known revision |
| `POST` | `/api/documents/:id/revisions` | Submit an OT change over HTTP |

## WebSocket Collaboration

The Socket.IO client connects with the signed authentication token in its `auth` payload. The main events are:

| Direction | Event | Purpose |
| --- | --- | --- |
| Client to server | `join_document` | Join an accessible document room |
| Client to server | `leave_document` | Leave a document room |
| Client to server | `submit_revision` | Submit a change set against a base revision |
| Server to client | `connected` | Confirm the authenticated socket user |
| Server to client | `joined_document` | Confirm room membership |
| Server to client | `revision_ack` | Acknowledge the submitting client's revision |
| Server to room | `revision_applied` | Broadcast the accepted revision to collaborators |
| Server to client | `submit_error` | Report an invalid or rejected revision |

HTTP revision submissions are also broadcast to connected Socket.IO clients, which provides a fallback path when a WebSocket submission is unavailable.

## OT Revision Flow

1. A client computes a change set from its last synchronized content to its current draft.
2. The change set includes a base revision and retain, insert, and delete operations.
3. The server loads revisions that the client has not seen.
4. The incoming change is transformed against those concurrent revisions in a deterministic order.
5. The transformed change is applied to the current document content.
6. PostgreSQL stores the operation, resulting content, author, client ID and revision number.
7. The server acknowledges the sender and broadcasts the accepted revision to the document room.

The core transformation and application code lives in `ot_engine/`, while `backend/services/collab_service.py` coordinates authorization, transformation, persistence and document updates.

## Data Model

- `users`: account email, password hash and creation time
- `documents`: owner, title and current mutable content
- `document_versions`: full snapshots, notes, summaries and per-user version numbers
- `document_revisions`: OT operations and resulting content for the shared working draft
- `document_collaborators`: document access granted by the owner

## Security and Configuration Notes

- Passwords are hashed with Werkzeug and are never stored as plain text.
- Authentication tokens are signed using the backend `SECRET_KEY` and expire after seven days.
- The OpenAI API key is loaded only by the backend and is not included in frontend requests or committed configuration.
- Authorization checks protect documents, private versions, collaboration state and revision submission.
- Production deployments must provide a strong, private `SECRET_KEY` and database credentials through environment variables.

## Deployment

The repository includes a `Procfile` for running the Flask-SocketIO server with a single Eventlet Gunicorn worker:

```text
web: gunicorn --worker-class eventlet -w 1 backend.app:create_app_instance
```

The deployment environment must provide PostgreSQL credentials, `SECRET_KEY`, and optionally the OpenAI configuration. The frontend must be built with `VITE_API_BASE_URL` pointing to the deployed backend.
