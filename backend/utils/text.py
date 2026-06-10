def clean_title(title):
    if not isinstance(title, str) or not title.strip():
        return "Untitled document"
    return title.strip()[:120]


def clean_optional_text(value):
    if not isinstance(value, str):
        return ""
    return value.strip()[:240]
