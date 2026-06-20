from backend.models import document as document_model
from backend.models import document_access
from backend.models import user as user_model
from backend.services import diff_service
from backend.utils.text import clean_optional_text, clean_title
from backend.utils.time import utc_now


def list_documents(user_id):
    return document_access.list_documents_for_user(user_id)


def get_document(document_id, user_id):
    return document_access.find_document_for_user(document_id, user_id)


def create_document(owner_id, title, content):
    title = clean_title(title)
    now = utc_now()
    return document_model.create_document(owner_id, title, content, now, now)


def update_document(document_id, owner_id, title, content):
    title = clean_title(title)
    return document_model.update_document(
        document_id,
        owner_id,
        title,
        content,
        utc_now(),
    )


def list_versions(document_id, owner_id):
    if document_access.find_document_for_user(document_id, owner_id) is None:
        return None
    return document_model.list_versions(document_id, owner_id)


def save_version(document_id, owner_id, content, commit_message):
    document = document_access.find_document_for_user(document_id, owner_id)
    if document is None:
        return None, None

    commit_message = clean_optional_text(commit_message)
    previous = document_model.get_latest_version(document_id, owner_id)
    next_number = document_model.get_latest_document_version_number(document_id) + 1
    diff_chunks = diff_service.build_diff(previous["content"] if previous else "", content)
    summary = diff_service.generate_stub_summary(diff_chunks, previous is None)
    now = utc_now()

    version = document_model.create_version(
        document_id,
        owner_id,
        next_number,
        document["title"],
        content,
        commit_message,
        summary,
        now,
    )
    return version, summary


def restore_version(document_id, owner_id, version_id):
    document = document_access.find_document_for_user(document_id, owner_id)
    if document is None:
        return None, None, "Document not found."

    version = document_model.get_version(version_id, document_id, owner_id)
    if version is None:
        return None, None, "Version not found."

    document_model.restore_document_content(
        document_id,
        version["content"],
        utc_now(),
    )
    restored = document_access.find_document_for_user(document_id, owner_id)
    return restored, version, None


def compare_versions(document_id, owner_id, from_version_id, to_version_id):
    if document_access.find_document_for_user(document_id, owner_id) is None:
        return None, "Document not found."

    from_version = document_model.get_version(from_version_id, document_id, owner_id)
    to_version = document_model.get_version(to_version_id, document_id, owner_id)
    if from_version is None or to_version is None:
        return None, "One or both versions were not found."

    chunks = diff_service.build_diff(from_version["content"], to_version["content"])
    return {
        "from": from_version,
        "to": to_version,
        "chunks": chunks,
        "summary": diff_service.generate_stub_summary(chunks, False),
    }, None


def share_document(document_id, owner_id, collaborator_email):
    document = document_model.find_document(document_id, owner_id)
    if document is None:
        return None, "Document not found."

    email = clean_optional_text(collaborator_email).lower()
    if not email:
        return None, "Collaborator email is required."

    collaborator = user_model.find_user_by_email(email)
    if collaborator is None:
        return None, "User not found."
    if collaborator["id"] == owner_id:
        return None, "You already own this document."

    row = document_access.add_document_collaborator(
        document_id,
        collaborator["id"],
        utc_now(),
    )
    return {
        "id": row["id"],
        "documentId": row["document_id"],
        "userId": row["user_id"],
        "email": collaborator["email"],
        "role": row["role"],
        "createdAt": row["created_at"],
    }, None
