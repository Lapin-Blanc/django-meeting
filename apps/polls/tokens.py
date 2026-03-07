import secrets


def generate_participant_token():
    """Generate a cryptographically secure token for a participant."""
    return secrets.token_urlsafe(48)
