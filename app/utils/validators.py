import uuid


def is_valid_uuid(value):
    """Check if a value is a valid UUID string."""
    if not value:
        return False
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False
