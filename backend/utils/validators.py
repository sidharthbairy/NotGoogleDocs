def normalize_email(email):
    if not isinstance(email, str):
        return ""
    return email.strip().lower()


def validate_credentials(email, password):
    if "@" not in email or "." not in email:
        return "Enter a valid email address."
    if len(password) < 8:
        return "Password must be at least 8 characters."
    return None
