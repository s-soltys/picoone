try:
    import errno
except ImportError:
    try:
        import uerrno as errno
    except ImportError:
        errno = None

try:
    import gc
except ImportError:
    gc = None

try:
    import ujson as json
except ImportError:
    import json

try:
    import socket
except ImportError:
    try:
        import usocket as socket
    except ImportError:
        socket = None

from core.temperature import ticks_diff, ticks_ms


HTTP_STATUS_TEXT = {
    200: "OK",
    204: "No Content",
    400: "Bad Request",
    404: "Not Found",
    405: "Method Not Allowed",
    408: "Request Timeout",
    413: "Payload Too Large",
    500: "Internal Server Error",
    503: "Service Unavailable",
}

MAX_REQUEST_BYTES = 1024
CLIENT_IDLE_MS = 2500
SEND_CHUNK_BYTES = 384

_WOULD_BLOCK_ERRNOS = {11, 35, 10035, 115}
if errno is not None:
    for name in ("EAGAIN", "EWOULDBLOCK", "EINPROGRESS", "ETIMEDOUT"):
        value = getattr(errno, name, None)
        if value is not None:
            _WOULD_BLOCK_ERRNOS.add(value)


def _normalize_errno(exc):
    value = getattr(exc, "errno", None)
    if value is not None:
        return value
    args = getattr(exc, "args", ())
    if args:
        code = args[0]
        if isinstance(code, int):
            return code
    return None


def _is_would_block(exc):
    code = _normalize_errno(exc)
    return code in _WOULD_BLOCK_ERRNOS or exc.__class__.__name__ == "BlockingIOError"


def _close_socket(sock):
    if sock is None:
        return
    try:
        sock.close()
    except Exception:
        pass


def _to_bytes(value):
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    return str(value).encode("utf-8")


def _json_body(payload):
    return _to_bytes(json.dumps(payload))


def _addr_text(addr):
    if isinstance(addr, tuple) and addr:
        host = str(addr[0])
        if len(addr) > 1:
            return host + ":" + str(addr[1])
        return host
    return str(addr or "")


class RollingRequestWindow:
    def __init__(self, window_seconds=60):
        self.window_seconds = max(1, window_seconds)
        self.reset()

    def reset(self):
        self.total = 0
        self._epochs = [-1] * self.window_seconds
        self._counts = [0] * self.window_seconds

    def record(self, now_ms):
        second = now_ms // 1000
        slot = second % self.window_seconds
        if self._epochs[slot] != second:
            self._epochs[slot] = second
            self._counts[slot] = 0
        self._counts[slot] += 1
        self.total += 1

    def recent(self, now_ms):
        second = now_ms // 1000
        total = 0
        for index in range(self.window_seconds):
            age = second - self._epochs[index]
            if 0 <= age < self.window_seconds:
                total += self._counts[index]
        return total


class PicoHTTPServer:
    def __init__(self, port=80, backlog=2, max_clients=3):
        self.port = port
        self.backlog = backlog
        self.max_clients = max(1, max_clients)
        self._listener = None
        self._clients = []
        self._handler = None
        self._request_window = RollingRequestWindow(60)
        self._listen_started_ms = 0
        self._metrics_started_ms = 0
        self.error = ""
        self.last_error = ""
        self.last_method = ""
        self.last_path = ""
        self.last_client = ""
        self.last_request_ms = None

    def set_handler(self, handler):
        self._handler = handler

    def running(self):
        return self._listener is not None

    def start(self):
        if self.running():
            return True
        if socket is None:
            self.error = "socket module unavailable"
            self.last_error = self.error
            return False
        if self._handler is None:
            self.error = "request handler missing"
            self.last_error = self.error
            return False

        listener = None
        try:
            listener = socket.socket()
            if hasattr(socket, "SOL_SOCKET") and hasattr(socket, "SO_REUSEADDR"):
                try:
                    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                except Exception:
                    pass
            listener.bind(socket.getaddrinfo("0.0.0.0", self.port)[0][-1])
            listener.listen(self.backlog)
            try:
                listener.setblocking(False)
            except Exception:
                listener.settimeout(0)
        except Exception as exc:
            _close_socket(listener)
            self.error = str(exc)
            self.last_error = self.error
            return False

        self._listener = listener
        self.error = ""
        self.last_error = ""
        now = ticks_ms()
        self._listen_started_ms = now
        self._metrics_started_ms = now
        self._request_window.reset()
        self.last_method = ""
        self.last_path = ""
        self.last_client = ""
        self.last_request_ms = None
        return True

    def stop(self):
        for state in self._clients:
            _close_socket(state.get("sock"))
        self._clients = []
        _close_socket(self._listener)
        self._listener = None
        self.error = ""

    def reset_metrics(self):
        self._request_window.reset()
        self._metrics_started_ms = ticks_ms()
        self.last_method = ""
        self.last_path = ""
        self.last_client = ""
        self.last_request_ms = None

    def snapshot(self, now_ms=None):
        now = ticks_ms() if now_ms is None else now_ms
        last_age_s = None
        if self.last_request_ms is not None:
            last_age_s = max(0, ticks_diff(now, self.last_request_ms) // 1000)

        server_uptime_s = 0
        if self._listen_started_ms:
            server_uptime_s = max(0, ticks_diff(now, self._listen_started_ms) // 1000)

        metrics_uptime_s = 0
        if self._metrics_started_ms:
            metrics_uptime_s = max(0, ticks_diff(now, self._metrics_started_ms) // 1000)

        return {
            "running": self.running(),
            "port": self.port,
            "active_clients": len(self._clients),
            "requests_total": self._request_window.total,
            "requests_60s": self._request_window.recent(now),
            "last_method": self.last_method,
            "last_path": self.last_path,
            "last_client": self.last_client,
            "last_request_age_s": last_age_s,
            "server_uptime_s": server_uptime_s,
            "metrics_uptime_s": metrics_uptime_s,
            "error": self.error,
            "last_error": self.last_error,
        }

    def poll(self):
        if not self.running():
            return
        self._accept_new()
        for state in self._clients[:]:
            self._poll_client(state)

    def _accept_new(self):
        while self.running() and len(self._clients) < self.max_clients:
            try:
                client, addr = self._listener.accept()
            except Exception as exc:
                if _is_would_block(exc):
                    break
                self.error = str(exc)
                self.last_error = self.error
                break

            try:
                client.setblocking(False)
            except Exception:
                try:
                    client.settimeout(0)
                except Exception:
                    pass
            self._clients.append(
                {
                    "sock": client,
                    "addr": addr,
                    "buffer": bytearray(),
                    "last_io_ms": ticks_ms(),
                    "payload": None,
                    "write_offset": 0,
                }
            )

    def _poll_client(self, state):
        now = ticks_ms()
        if ticks_diff(now, state["last_io_ms"]) > CLIENT_IDLE_MS:
            if state.get("payload") is None:
                payload = self._build_payload(408, "text/plain; charset=utf-8", b"Request timeout")
                self._queue_payload(state, payload)
            else:
                self._close_client(state)
            return

        if state.get("payload") is not None:
            self._send_chunk(state)
            return

        try:
            chunk = state["sock"].recv(256)
        except Exception as exc:
            if _is_would_block(exc):
                return
            self.error = str(exc)
            self.last_error = self.error
            self._close_client(state)
            return

        if not chunk:
            if state["buffer"]:
                self._handle_request(state)
            else:
                self._close_client(state)
            return

        state["last_io_ms"] = now
        state["buffer"].extend(chunk)
        if len(state["buffer"]) > MAX_REQUEST_BYTES:
            payload = self._build_payload(413, "text/plain; charset=utf-8", b"Request too large")
            self._queue_payload(state, payload)
            return

        if b"\r\n\r\n" in state["buffer"] or b"\n\n" in state["buffer"]:
            self._handle_request(state)

    def _close_client(self, state):
        _close_socket(state.get("sock"))
        if state in self._clients:
            self._clients.remove(state)
        if gc is not None:
            gc.collect()

    def _queue_payload(self, state, payload):
        state["payload"] = payload
        state["write_offset"] = 0
        state["buffer"] = bytearray()
        state["last_io_ms"] = ticks_ms()

    def _send_chunk(self, state):
        sock = state.get("sock")
        payload = state.get("payload")
        if sock is None or payload is None:
            self._close_client(state)
            return

        start = state.get("write_offset", 0)
        if start >= len(payload):
            self._close_client(state)
            return

        end = min(len(payload), start + SEND_CHUNK_BYTES)
        try:
            count = sock.send(payload[start:end])
        except Exception as exc:
            if _is_would_block(exc):
                return
            self.error = str(exc)
            self.last_error = self.error
            self._close_client(state)
            return

        if count is None:
            count = 0
        if count <= 0:
            return

        state["write_offset"] = start + count
        state["last_io_ms"] = ticks_ms()
        if state["write_offset"] >= len(payload):
            self._close_client(state)

    def _handle_request(self, state):
        try:
            method, path, query = self._parse_request(bytes(state["buffer"]))
        except ValueError as exc:
            self.error = ""
            payload = self._build_payload(400, "text/plain; charset=utf-8", _to_bytes(str(exc)))
            self._queue_payload(state, payload)
            return

        now = ticks_ms()
        self._request_window.record(now)
        self.last_request_ms = now
        self.last_method = method
        self.last_path = path
        self.last_client = _addr_text(state["addr"])

        try:
            result = self._handler(method, path, query, state["addr"], self) or {}
            status = int(result.get("status", 200))
            content_type = result.get("content_type", "text/plain; charset=utf-8")
            body = result.get("body", b"")
            headers = result.get("headers", {})
            if method == "HEAD":
                body = b""
        except Exception as exc:
            self.error = str(exc)
            self.last_error = self.error
            payload = self._build_payload(500, "text/plain; charset=utf-8", _to_bytes(self.error))
            self._queue_payload(state, payload)
            return

        self.error = ""
        payload = self._build_payload(status, content_type, body, headers)
        self._queue_payload(state, payload)

    def _parse_request(self, raw):
        head = raw.split(b"\r\n\r\n", 1)[0].split(b"\n\n", 1)[0]
        first_line = head.splitlines()[0] if head else b""
        pieces = _to_bytes(first_line).decode("utf-8", "ignore").strip().split()
        if len(pieces) < 2:
            raise ValueError("Malformed request")

        method = pieces[0].upper()
        target = pieces[1]
        if "?" in target:
            path, query = target.split("?", 1)
        else:
            path = target
            query = ""
        return method, path or "/", query

    def _build_payload(self, status, content_type, body, headers=None):
        body_bytes = _to_bytes(body)
        headers = headers or {}
        lines = [
            "HTTP/1.1 " + str(status) + " " + HTTP_STATUS_TEXT.get(status, "OK"),
            "Content-Type: " + str(content_type),
            "Content-Length: " + str(len(body_bytes)),
            "Connection: close",
        ]
        for key in headers:
            lines.append(str(key) + ": " + str(headers[key]))
        lines.append("")
        lines.append("")
        return "\r\n".join(lines).encode("utf-8") + body_bytes


def json_response(payload, status=200):
    return {
        "status": status,
        "content_type": "application/json; charset=utf-8",
        "body": _json_body(payload),
        "headers": {
            "Cache-Control": "no-store",
        },
    }
