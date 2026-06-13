import json
import os

SESSION_FILE = os.path.join('data', 'session.json')

def save_session(player_id: str, session_token: str, username: str, ip: str, port: int):
    """
    /**
     * Function save_session
     * 
     * Persists the current connection credentials to disk so the client can attempt an automatic reconnect if it crashes or is closed mid-game.
     * 
     * parameters:
     * - player_id: Method argument required for execution.
     * - session_token: Method argument required for execution.
     * - username: Method argument required for execution.
     * - ip: Method argument required for execution.
     * - port: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
    data = {
        'player_id': player_id,
        'session_token': session_token,
        'username': username,
        'ip': ip,
        'port': port
    }
    try:
        os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
        with open(SESSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    except Exception:
        pass

def load_session() -> dict | None:
    """
    /**
     * Function load_session
     * 
     * Reads the saved session file from disk and returns the credentials dict if valid, or None if no session exists or the file is corrupted.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
    try:
        if not os.path.exists(SESSION_FILE):
            return None
        with open(SESSION_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        required = ['player_id', 'session_token', 'username', 'ip', 'port']
        if all(k in data for k in required):
            return data
        return None
    except Exception:
        return None

def clear_session():
    """
    /**
     * Function clear_session
     * 
     * Deletes the saved session file from disk, typically called when the player intentionally disconnects or logs out.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
    try:
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
    except Exception:
        pass
