import socket
import threading
import queue
from shared.utils import serialize, deserialize

class NetworkClient:
    """
    /**
     * Class NetworkClient
     * 
     * A non-blocking TCP socket manager. It spawns a daemon thread to quietly listen for incoming bytes from the server without freezing the Pygame graphics loop.
     */
    """

    def __init__(self):
        """
    /**
     * Function __init__
     *
     * Prepares the socket variable and the thread-safe deque which acts as an inbox for incoming parsed JSON packets.
     *
     * parameters:
     * - None
     *
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        self._sock: socket.socket | None = None
        self._connected = False
        self._lock = threading.Lock()
        self._recv_thread: threading.Thread | None = None
        self.inbox: queue.Queue = queue.Queue()
        self._buffer = b''
        self._generation = 0

    @property
    def is_connected(self) -> bool:
        """
    /**
     * Function is_connected
     * 
     * Checks if the underlying socket object exists and hasn't explicitly thrown a disconnection error yet.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        return self._connected

    def connect(self, ip: str, port: int) -> bool:
        """
    /**
     * Function connect
     * 
     * Tries to dial the server's IP and port. If it connects, it configures the socket to be non-blocking and launches the background listener thread.
     * 
     * parameters:
     * - ip: Method argument required for execution.
     * - port: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.settimeout(5.0)
            sock.connect((ip, port))
            sock.settimeout(None)
            with self._lock:
                self._sock = sock
                self._connected = True
                self._buffer = b''
            while not self.inbox.empty():
                try:
                    self.inbox.get_nowait()
                except queue.Empty:
                    break
            self._generation += 1
            this_gen = self._generation
            self._recv_thread = threading.Thread(target=self._receive_loop, args=(this_gen,), daemon=True)
            self._recv_thread.start()
            return True
        except (OSError, ConnectionRefusedError, TimeoutError) as exc:
            print(f'[NET] connect failed: {exc}')
            return False

    def disconnect(self):
        """
    /**
     * Function disconnect
     *
     * Gracefully shuts down the socket connection and cleans up the thread to prevent memory leaks when exiting the game.
     *
     * parameters:
     * - None
     *
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            self._generation += 1
            self._connected = False
            if self._sock:
                try:
                    self._sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                try:
                    self._sock.close()
                except OSError:
                    pass
                self._sock = None

    def send_packet(self, packet: dict):
        """
    /**
     * Function send_packet
     * 
     * Converts a Python dictionary into a UTF-8 JSON string, appends a newline delimiter, and flushes it down the TCP socket to the server.
     * 
     * parameters:
     * - packet: Method argument required for execution.
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        with self._lock:
            if not self._connected or not self._sock:
                return
            try:
                data = serialize(packet)
                self._sock.sendall(data)
            except OSError as exc:
                print(f'[NET] send error: {exc}')
                self._connected = False

    def _receive_loop(self, gen: int):
        """
    /**
     * Function _receive_loop
     *
     * The daemon thread's core logic. It reads chunks of bytes, buffers them until a newline is found, decodes the JSON, and appends it to the inbox queue.
     *
     * parameters:
     * - gen: The generation id of this connection, used to detect stale threads.
     *
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        while True:
            with self._lock:
                if not self._connected or not self._sock:
                    break
                sock = self._sock
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    print('[NET] server closed connection')
                    break
                with self._lock:
                    if self._generation != gen:
                        break
                self._buffer += chunk
                while b'\n' in self._buffer:
                    line, self._buffer = self._buffer.split(b'\n', 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        packet = deserialize(line)
                        self.inbox.put(packet)
                    except Exception as exc:
                        print(f'[NET] deserialize error: {exc} | raw={line[:120]}')
            except OSError:
                break
            except Exception as exc:
                print(f'[NET] recv error: {exc}')
                break
        with self._lock:
            still_current = self._generation == gen
            if still_current:
                self._connected = False
        if still_current:
            self.inbox.put({'type': '__DISCONNECTED__'})

    def poll_packets(self) -> list[dict]:
        """
    /**
     * Function poll_packets
     * 
     * Yields all the packets currently waiting in the thread-safe inbox and empties it, allowing the main Pygame thread to process them sequentially.
     * 
     * parameters:
     * - None
     * 
     * returns:
     * - State modification or queried value based on execution.
     */
    """
        packets = []
        while True:
            try:
                packets.append(self.inbox.get_nowait())
            except queue.Empty:
                break
        return packets