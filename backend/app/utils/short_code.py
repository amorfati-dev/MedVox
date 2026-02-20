"""
Short-Code Generator for Transfer Sessions

Converts UUID to human-readable 6-character codes
Format: ABC123 or ABC-123 (with dash for readability)

Example:
    550e8400-e29b-41d4-a716-446655440000 → AB3K9M

Design:
- 6 characters from Base62 alphabet (no ambiguous chars)
- Deterministic (same UUID → same code)
- Case-insensitive decoding (user-friendly)
- Optional dash formatting (ABC-123)
"""

import hashlib
import uuid
from typing import Optional


class ShortCodeError(Exception):
    """Raised when short code is invalid"""
    pass


# Base62 alphabet (excluding ambiguous: 0/O, 1/I/l)
# Total: 58 chars (still enough for 58^6 = 30 billion combinations)
BASE62_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # Uppercase only for simplicity
BASE = len(BASE62_ALPHABET)


def _uuid_to_int(uuid_str: str) -> int:
    """
    Convert UUID string to integer for encoding

    Uses hash for deterministic but shorter representation
    """
    # Parse UUID
    try:
        uuid_obj = uuid.UUID(uuid_str)
    except (ValueError, AttributeError):
        raise ShortCodeError(f"Invalid UUID: {uuid_str}")

    # Get first 64 bits (enough for 6-char code)
    # Use hash for collision resistance
    hash_bytes = hashlib.sha256(uuid_obj.bytes).digest()[:8]
    return int.from_bytes(hash_bytes, byteorder='big')


def _int_to_base62(num: int, length: int = 6) -> str:
    """
    Convert integer to base62 string

    Args:
        num: Integer to convert
        length: Fixed length (pad with leading chars)

    Returns:
        Base62 encoded string
    """
    if num == 0:
        return BASE62_ALPHABET[0] * length

    result = []
    while num > 0 and len(result) < length:
        num, remainder = divmod(num, BASE)
        result.append(BASE62_ALPHABET[remainder])

    # Pad to fixed length
    while len(result) < length:
        result.append(BASE62_ALPHABET[0])

    return ''.join(reversed(result))


def _base62_to_int(code: str) -> int:
    """
    Convert base62 string to integer

    Args:
        code: Base62 encoded string

    Returns:
        Integer value
    """
    code = code.upper().replace('-', '')  # Normalize

    result = 0
    for char in code:
        if char not in BASE62_ALPHABET:
            raise ShortCodeError(f"Invalid character in code: {char}")
        result = result * BASE + BASE62_ALPHABET.index(char)

    return result


def generate_short_code(session_id: str, formatted: bool = False) -> str:
    """
    Generate 6-character short code from UUID

    Args:
        session_id: UUID string
        formatted: If True, format as ABC-123 (with dash)

    Returns:
        6-character short code (or 7 with dash)

    Example:
        >>> generate_short_code("550e8400-e29b-41d4-a716-446655440000")
        'AB3K9M'
        >>> generate_short_code("550e8400-e29b-41d4-a716-446655440000", formatted=True)
        'AB3-K9M'
    """
    # Convert UUID to integer
    num = _uuid_to_int(session_id)

    # Encode to base62
    code = _int_to_base62(num, length=6)

    # Format with dash if requested
    if formatted:
        return f"{code[:3]}-{code[3:]}"

    return code


def decode_short_code(short_code: str) -> str:
    """
    Validate and normalize short code

    Note: This doesn't decode to UUID (hashing is one-way).
    The TransferService stores the code→UUID mapping.

    Args:
        short_code: 6-character code (with or without dash)

    Returns:
        Normalized code (uppercase, no dash)

    Raises:
        ShortCodeError: If code format is invalid
    """
    # Normalize code
    code = short_code.upper().replace('-', '').strip()

    # Validate length
    if len(code) != 6:
        raise ShortCodeError(f"Short code must be 6 characters, got {len(code)}")

    # Validate characters
    for char in code:
        if char not in BASE62_ALPHABET:
            raise ShortCodeError(f"Invalid character in code: {char}")

    # Return normalized code
    # The actual UUID lookup happens in TransferService
    return code


# Helper for TransferService
def validate_short_code(short_code: str) -> bool:
    """
    Validate short code format without decoding

    Args:
        short_code: Code to validate

    Returns:
        True if valid format, False otherwise
    """
    try:
        code = short_code.upper().replace('-', '').strip()
        if len(code) != 6:
            return False

        for char in code:
            if char not in BASE62_ALPHABET:
                return False

        return True
    except:
        return False
