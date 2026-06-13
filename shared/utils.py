"""
Liar's Deck Online - Shared Utilities
Serialization, ID generation.
"""

import json
import uuid

from shared.constants import ENCODING, PACKET_DELIMITER


def serialize(packet: dict) -> bytes:
    """Dict -> JSON string + newline -> bytes. Ready to send over socket."""
    return (json.dumps(packet, separators=(",", ":")) + PACKET_DELIMITER).encode(ENCODING)


def deserialize(data: str | bytes) -> dict:
    """JSON string or bytes -> dict. Raises ValueError on bad JSON."""
    if isinstance(data, bytes):
        data = data.decode(ENCODING)
    return json.loads(data.strip())


def generate_id() -> str:
    """Short unique ID (12 hex chars)."""
    return uuid.uuid4().hex[:12]


def generate_session_token() -> str:
    """Full UUID4 string for session auth."""
    return str(uuid.uuid4())
