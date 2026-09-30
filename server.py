from __future__ import annotations

import ctypes
from collections import deque
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import threading
import time
from urllib.parse import urlsplit
from ctypes import wintypes


ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
MAX_BODY = 256
PRESS_LIMIT = 20
MAX_CLIENTS = 8
CLIENT_TIMEOUT_SECONDS = 5


def _canonical_origin(value: str) -> str | None:
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme.lower() not in ("http", "https")
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            return None
        _ = parsed.port  # Validate the port syntax.
    except ValueError:
        return None
    return f"{parsed.scheme.lower()}://{parsed.netloc.casefold()}"


_default_origins = "http://127.0.0.1:8765,http://localhost:8765"
_origin_setting = os.environ.get("TAILKEY_ALLOWED_ORIGINS", _default_origins)
ALLOWED_ORIGINS = frozenset(
    origin
    for item in _origin_setting.split(",")
    if (origin := _canonical_origin(item.strip())) is not None
)
ALLOWED_HOSTS = frozenset(
    {"127.0.0.1:8765", "localhost:8765"}
    | {"127.0.0.1", "localhost"}
    | {
        host
        for origin in ALLOWED_ORIGINS
        for host in (
            urlsplit(origin).netloc.casefold(),
            (urlsplit(origin).hostname or "").casefold(),
        )
    }
)

INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

# The browser can request only these named keypad keys; it never supplies a VK.
KEYS: dict[str, tuple[int, int, int]] = {
    **{f"NUMPAD{digit}": (0x60 + digit, 0, 0) for digit in range(10)},
    "MULTIPLY": (0x6A, 0, 0),
    "ADD": (0x6B, 0, 0),
    "SUBTRACT": (0x6D, 0, 0),
    "DECIMAL": (0x6E, 0, 0),
    # A physical NumPad divide key uses the extended E0 35 scan code.
    "DIVIDE": (0, 0x35, KEYEVENTF_SCANCODE | KEYEVENTF_EXTENDEDKEY),
    # Windows has no separate VK_NUMPAD_ENTER. Its scan code is E0 1C.
    "NUMPAD_ENTER": (0, 0x1C, KEYEVENTF_SCANCODE | KEYEVENTF_EXTENDEDKEY),
    "BACKSPACE": (0x08, 0, 0),
}


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUTUNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = [("type", wintypes.DWORD), ("union", INPUTUNION)]


if os.name == "nt":
    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _send_input = _user32.SendInput
    _send_input.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
    _send_input.restype = wintypes.UINT
else:
    _send_input = None


def _event(vk: int, scan: int, flags: int) -> INPUT:
    event = INPUT()
    event.type = INPUT_KEYBOARD
    event.ki = KEYBDINPUT(vk, scan, flags, 0, 0)
    return event


def press_key(name: str) -> None:
    vk, scan, flags = KEYS[name]
    events = (INPUT * 2)(
        _event(vk, scan, flags),
        _event(vk, scan, flags | KEYEVENTF_KEYUP),
    )
    sent = _send_input(2, events, ctypes.sizeof(INPUT))
    if sent == 2:
        return
    # If Windows accepted key-down but not key-up, make one best-effort release.
    if sent == 1:
        release = _event(vk, scan, flags | KEYEVENTF_KEYUP)
        _send_input(1, ctypes.byref(release), ctypes.sizeof(INPUT))
    raise OSError("Windows did not accept the complete key press")


_press_times: deque[float] = deque()
_press_lock = threading.Lock()


def allow_press() -> bool:
    now = time.monotonic()
    with _press_lock:
        while _press_times and now - _press_times[0] >= 1:
            _press_times.popleft()
        if len(_press_times) >= PRESS_LIMIT:
            return False
        _press_times.append(now)
        return True


class KeypadHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, _format: str, *_args: object) -> None:
        # Do not log which keys the user pressed.
        return

    def _respond(self, status: int, body: bytes = b"", content_type: str = "text/plain; charset=utf-8") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "connect-src 'self'; img-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'",
        )
        self.send_header("Connection", "close")
        self.end_headers()
        if body:
            self.wfile.write(body)
        self.close_connection = True

    def _json(self, status: int, value: dict[str, object]) -> None:
        self._respond(status, json.dumps(value).encode("utf-8"), "application/json; charset=utf-8")

    def _same_origin(self) -> bool:
        origin = _canonical_origin(self.headers.get("Origin", ""))
        host = self.headers.get("Host", "").strip().casefold()
        # X-Forwarded-Host is deliberately ignored: clients can supply it.
        # Serve may preserve the public Host or proxy through the local listener.
        return origin in ALLOWED_ORIGINS and host in ALLOWED_HOSTS

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/api/health":
            self._json(200, {"ok": True})
            return

        files = {
            "/": (STATIC / "index.html", "text/html; charset=utf-8"),
            "/app.js": (STATIC / "app.js", "text/javascript; charset=utf-8"),
            "/i18n.js": (STATIC / "i18n.js", "text/javascript; charset=utf-8"),
            "/style.css": (STATIC / "style.css", "text/css; charset=utf-8"),
        }
        item = files.get(path)
        if item is None:
            self._respond(404, b"Not found")
            return
        file_path, content_type = item
        try:
            self._respond(200, file_path.read_bytes(), content_type)
        except OSError:
            self._respond(500, b"Unable to read keypad page")

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if path not in ("/api/press", "/api/shutdown"):
            self._respond(404, b"Not found")
            return
        if not self._same_origin():
            self._json(403, {"error": "origin_denied"})
            return
        if self.headers.get_content_type() != "application/json":
            self._json(415, {"error": "json_required"})
            return

        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            length = -1
        if length <= 0:
            self._json(400, {"error": "invalid_request"})
            return
        if length > MAX_BODY:
            self._json(413, {"error": "request_too_large"})
            return

        try:
            body = self.rfile.read(length)
        except OSError:
            return
        if len(body) != length:
            self._json(400, {"error": "invalid_request"})
            return
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._json(400, {"error": "invalid_json"})
            return
        if not isinstance(payload, dict):
            self._json(400, {"error": "invalid_request"})
            return

        if path == "/api/shutdown":
            if payload != {"action": "shutdown"}:
                self._json(400, {"error": "invalid_request"})
                return
            self._json(202, {"ok": True, "stopping": True})
            self.server.request_shutdown()
            return

        if set(payload) != {"key"}:
            self._json(400, {"error": "invalid_request"})
            return
        key = payload["key"]
        if not isinstance(key, str) or key not in KEYS:
            self._json(400, {"error": "unknown_key"})
            return
        if not allow_press():
            self._json(429, {"error": "rate_limited"})
            return

        try:
            press_key(key)
        except (OSError, AttributeError):
            self._json(500, {"error": "input_failed"})
            return
        self._respond(204)

    def do_OPTIONS(self) -> None:
        # Same-origin fetch does not need CORS; reject cross-origin preflights.
        self._respond(405, b"Method not allowed")


def main() -> None:
    if os.name != "nt":
        raise SystemExit("Tailkey sends keys through Windows SendInput and must run on Windows.")
    server = BoundedThreadingHTTPServer(("127.0.0.1", 8765), KeypadHandler)
    print("Tailkey is running at http://127.0.0.1:8765")
    print("This window must stay open. Press Ctrl+C to stop the keypad server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nTailkey stopped.")
    finally:
        server.server_close()


class BoundedThreadingHTTPServer(ThreadingHTTPServer):
    request_queue_size = 16
    daemon_threads = True

    def __init__(self, server_address: tuple[str, int], handler: type[BaseHTTPRequestHandler]):
        self._client_slots = threading.BoundedSemaphore(MAX_CLIENTS)
        self._shutdown_lock = threading.Lock()
        self._shutdown_requested = False
        super().__init__(server_address, handler)

    def request_shutdown(self) -> None:
        with self._shutdown_lock:
            if self._shutdown_requested:
                return
            self._shutdown_requested = True
        threading.Thread(target=self.shutdown, name="tailkey-shutdown", daemon=True).start()

    def get_request(self) -> tuple[socket.socket, tuple[str, int]]:
        request, client_address = super().get_request()
        request.settimeout(CLIENT_TIMEOUT_SECONDS)
        return request, client_address

    def process_request(self, request: socket.socket, client_address: tuple[str, int]) -> None:
        if not self._client_slots.acquire(blocking=False):
            try:
                request.sendall(
                    b"HTTP/1.1 503 Service Unavailable\r\n"
                    b"Content-Length: 0\r\nConnection: close\r\n\r\n"
                )
            except OSError:
                pass
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._client_slots.release()
            raise

    def process_request_thread(self, request: socket.socket, client_address: tuple[str, int]) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._client_slots.release()


if __name__ == "__main__":
    main()
