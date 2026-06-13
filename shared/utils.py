import json
import uuid
from shared.constants import ENCODING, PACKET_DELIMITER

def serialize(packet: dict) -> bytes:
    """
    /**
     * Function serialize
     * 
     * Converts a standard Python dictionary into a compacted JSON string, then encodes it into raw UTF-8 bytes ready to be shoved through the TCP socket.
     * 
     * parameters:
     * - packet: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
    return (json.dumps(packet, separators=(',', ':')) + PACKET_DELIMITER).encode(ENCODING)

def deserialize(data: str | bytes) -> dict:
    """
    /**
     * Function deserialize
     * 
     * Takes a chunk of UTF-8 bytes pulled from the socket, decodes them to a string, and attempts to parse them back into a native Python dictionary.
     * 
     * parameters:
     * - data: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
    if isinstance(data, bytes):
        data = data.decode(ENCODING)
    return json.loads(data.strip())

def generate_id() -> str:
    """
    /**
     * Function generate_id
     * 
     * Uses the OS-level urandom function via the uuid4 library to create a guaranteed unique string identifier for players or rooms.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
    return uuid.uuid4().hex[:12]

def generate_session_token() -> str:
    """
    /**
     * Function generate_session_token
     * 
     * Spits out a massive, highly secure random hex string used as a password. When a client disconnects, they must provide this exact token to reconnect to their body.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
    return str(uuid.uuid4())

def generate_room_code(length: int = 6) -> str:
    """
    Generate a short alphanumeric room code for players to share.
    Uses uppercase letters + digits, excluding ambiguous chars (0/O/I/1/L).
    """
    import random
    chars = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
    return ''.join(random.choices(chars, k=length))