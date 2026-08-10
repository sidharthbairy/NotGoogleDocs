def serialize_document(row, current_user_id=None):
    collaborator_count = (
        int(row["collaborator_count"])
        if "collaborator_count" in row.keys() and row["collaborator_count"] is not None
        else 0
    )
    return {
        "id": row["id"],
        "title": row["title"],
        "content": row["current_content"],
        "isOwner": row["owner_id"] == current_user_id if current_user_id is not None else None,
        "isShared": collaborator_count > 0,
        "collaboratorCount": collaborator_count,
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
        "versionCount": row["version_count"] if "version_count" in row.keys() else None,
    }


def serialize_version(row, include_content=True):
    version = {
        "id": row["id"],
        "documentId": row["document_id"],
        "versionNumber": row["user_version_number"] if "user_version_number" in row.keys() else row["version_number"],
        "commitMessage": row["commit_message"],
        "summary": row["summary"],
        "createdAt": row["created_at"],
    }
    if include_content:
        version["content"] = row["content"]
    return version
