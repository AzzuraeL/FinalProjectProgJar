"""
Liar's Deck Online - Server Configuration
"""

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 12345
MAX_ROOMS = 10
RECONNECT_TIMEOUT = 60          # seconds before disconnected player forfeits
RATE_LIMIT_MAX = 10             # max packets per second per client
INVALID_PACKET_THRESHOLD = 5    # kick after N invalid packets
SOCKET_TIMEOUT = 0.5            # recv timeout for clean shutdown checks
BACKLOG = 20                    # listen backlog
