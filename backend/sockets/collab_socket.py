from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room

from backend.middleware.socket_auth import authenticate_socket
from backend.models.document_access import find_document_for_user
from backend.services.collab_service import CollabError, submit_collab_change
from backend.utils.revision_serializers import serialize_revision_row, serialize_submit_collab_result

socketio = SocketIO(cors_allowed_origins="*", async_mode="eventlet")

socket_users = {}

def get_socket_user():
    return socket_users.get(request.sid)

def document_room(document_id: int) -> str:
    return f"document:{document_id}"

def broadcast_revision(document_id: int, revision_row, head_revision: int):
    socketio.emit(
        "revision_applied",
        {
            "documentId": document_id,
            "headRevision": head_revision,
            "revision": serialize_revision_row(revision_row)
        },
        room=document_room(document_id)
    )

def register_collab_socket_handlers(socketio_instance):
    @socketio_instance.on("connect")
    def on_connect(auth):
        user = authenticate_socket(auth)
        if user is None:
            return False
        
        socket_users[request.sid] = user
        emit("connected", {"userId": user["id"], "email": user["email"]})

    @socketio_instance.on("disconnect")
    def on_disconnect():
        socket_users.pop(request.sid, None)

    @socketio_instance.on("join_document")
    def on_join_document(data):
        user = get_socket_user()
        if user is None:
            emit("error", {"message": "Not authenticated."})
            return

        document_id = int(data["documentId"])

        if find_document_for_user(document_id, user["id"]) is None:
            emit("error", {"message": "Document not found"})
            return

        join_room(document_room(document_id))
        emit("joined_document", {"documentId": document_id})

    @socketio_instance.on("leave_document")
    def on_leave_document(data):
        leave_room(document_room(int(data["document_id"])))

    @socketio_instance.on("submit_revision")
    def on_submit_revision(data):
        user = get_socket_user()
        if user is None:
            emit("submit_error", {"message": "Not authenticated."})
            return

        document_id = int(data["document_id"])
        client_id = data.get("clientId")
        change_set = data.get("changeSet")
        if not isinstance(client_id, str) or not client_id.strip():
            emit("submit_error", {"message": "clientId is required."})
            return
        if not isinstance(change_set, dict):
            emit("submit_error", {"message": "changeSet is required."})
            return
        try:
            base_revision = int(data["baseRevision"])
        except (TypeError, ValueError):
            emit("submit_error", {"message": "baseRevision must be a number."})
            return
        try:
            result = submit_collab_change(
                document_id=document_id,
                user_id=user["id"],
                client_id=client_id,
                base_revision=base_revision,
                incoming_change_dict=change_set,
            )
        except CollabError as error:
            emit("submit_error", {"message": error.message, "code": error.code})
            return
        except (KeyError, TypeError, ValueError):
            emit("submit_error", {"message": "Invalid changeSet."})
            return
        payload = serialize_submit_collab_result(result)
        emit("revision_ack", payload)
        broadcast_revision(document_id, result["revision"], result["revisionNumber"])