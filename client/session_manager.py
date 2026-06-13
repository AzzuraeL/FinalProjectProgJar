import json
import os
import re

SESSION_DIR = os.path.join('data')
DEFAULT_SESSION_FILE = os.path.join(SESSION_DIR, 'session.json')

def _safe_username(username: str) -> str:
    cleaned = re.sub(r'[^A-Za-z0-9_-]', '_', (username or 'player').strip() or 'player')
    return cleaned[:32]

def _session_path(username: str | None = None) -> str:
    if not username:
        return DEFAULT_SESSION_FILE
    return os.path.join(SESSION_DIR, f'session_{_safe_username(username)}.json')

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
        os.makedirs(SESSION_DIR, exist_ok=True)
        path = _session_path(username)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    except Exception:
        pass

def load_session(username: str | None = None) -> dict | None:
    """
    /**
     * Function load_session
     *
     * Reads the saved session file from disk and returns the credentials dict if valid, or None if no session exists or the file is corrupted.
     * When a username is provided, it loads that user's dedicated session file.
     * When no username is provided, it scans the session directory and returns the most recent session (for the reconnect button preview).
     *
     * parameters:
     * - username: Optional username to load a specific session.
     *
     * returns:
     * - State modification or queried value based on execution.
     */
    """
    required = ['player_id', 'session_token', 'username', 'ip', 'port']
    try:
        if username:
            path = _session_path(username)
            if not os.path.exists(path):
                return None
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if all(k in data for k in required):
                return data
            return None
        candidates = []
        if not os.path.isdir(SESSION_DIR):
            return None
        for name in os.listdir(SESSION_DIR):
            if not name.startswith('session_') or not name.endswith('.json'):
                if name == 'session.json':
                    try:
                        with open(os.path.join(SESSION_DIR, name), 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        if all(k in data for k in required):
                            candidates.append((os.path.getmtime(os.path.join(SESSION_DIR, name)), data))
                    except Exception:
                        pass
                    continue
                continue
            full = os.path.join(SESSION_DIR, name)
            try:
                with open(full, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if all(k in data for k in required):
                    candidates.append((os.path.getmtime(full), data))
            except Exception:
                continue
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    except Exception:
        return None

def clear_session(username: str | None = None):
    """
    /**
     * Function clear_session
     *
     * Deletes the saved session file from disk, typically called when the player intentionally disconnects or logs out.
     *
     * parameters:
     * - username: Optional username to clear a specific session file.
     *
     * returns:
     * - State modification or queried value based on execution.
     */
    """
    try:
        path = _session_path(username)
        if os.path.exists(path):
            os.remove(path)
        if username and os.path.exists(DEFAULT_SESSION_FILE):
            os.remove(DEFAULT_SESSION_FILE)
    except Exception:
        pass
