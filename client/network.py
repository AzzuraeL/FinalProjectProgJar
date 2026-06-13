"""
client/network.py - TCP networking with newline-delimited JSON.
Runs receive loop in daemon thread, puts packets into queue.Queue.
"""

import socket
import threading
import queue
import time


from shared.utils import serialize, deserialize


class NetworkClient:
    """Thread-safe TCP client. Receive loop -> queue. Main thread polls queue."""

    def __init__(self):
        self._sock: socket.socket | None = None
        self._connected = False
        self._lock = threading.Lock()
        self._recv_thread: threading.Thread | None = None
        self.inbox: queue.Queue = queue.Queue()
        self._buffer = b""

    # ── properties ────────────────────────────────────────────────
    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── connect / disconnect ──────────────────────────────────────
    def connect(self, ip: str, port: int) -> bool:
        """Blocking connect. Returns True on success."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.settimeout(5.0)
            sock.connect((ip, port))
            sock.settimeout(None)

            with self._lock:
                self._sock = sock
                self._connected = True
                self._buffer = b""

            # drain old queue
            while not self.inbox.empty():
                try:
                    self.inbox.get_nowait()
                except queue.Empty:
                    break

            self._recv_thread = threading.Thread(
                target=self._receive_loop, daemon=True
            )
            self._recv_thread.start()
            return True
        except (OSError, ConnectionRefusedError, TimeoutError) as exc:
            print(f"[NET] connect failed: {exc}")
            return False

    def disconnect(self):
        with self._lock:
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

    # ── send ──────────────────────────────────────────────────────
    def send_packet(self, packet: dict):
        """Serialize + send. Thread-safe."""
        with self._lock:
            if not self._connected or not self._sock:
                return
            try:
                data = serialize(packet)
                self._sock.sendall(data)
            except OSError as exc:
                print(f"[NET] send error: {exc}")
                self._connected = False

    # ── receive loop (daemon thread) ──────────────────────────────
    def _receive_loop(self):
        while True:
            with self._lock:
                if not self._connected or not self._sock:
                    break
                sock = self._sock

            try:
                chunk = sock.recv(4096)
                if not chunk:
                    # server closed connection
                    print("[NET] server closed connection")
                    break

                self._buffer += chunk
                # process newline-delimited messages
                while b"\n" in self._buffer:
                    line, self._buffer = self._buffer.split(b"\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        packet = deserialize(line)
                        self.inbox.put(packet)
                    except Exception as exc:
                        print(f"[NET] deserialize error: {exc} | raw={line[:120]}")

            except OSError:
                break
            except Exception as exc:
                print(f"[NET] recv error: {exc}")
                break

        with self._lock:
            self._connected = False
        # push a disconnect sentinel so main loop knows
        self.inbox.put({"type": "__DISCONNECTED__"})

    # ── helpers ───────────────────────────────────────────────────
    def poll_packets(self) -> list[dict]:
        """Drain inbox. Call once per frame from main thread."""
        packets = []
        while True:
            try:
                packets.append(self.inbox.get_nowait())
            except queue.Empty:
                break
        return packets
