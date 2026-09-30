"""Trusted-LAN WebRTC prototype. Signaling is HTTP; not an Internet service."""
from __future__ import annotations

import argparse
import asyncio
import contextlib
from dataclasses import dataclass
import io
import ipaddress
import json
from pathlib import Path
import secrets
import socket
import sys
import time
import webbrowser

from aiohttp import web
from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription
import qrcode
import qrcode.image.svg

ROOT = Path(sys._MEIPASS) / "webrtc" if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from server import KEYS, allow_press, press_key

INVITE_TTL = 120
PAIR_DEADLINE = 120
HEARTBEAT_TIMEOUT = 4
KEY_TTL_MS = 1000
STATE = web.AppKey("state", object)


@dataclass
class Peer:
    pc: RTCPeerConnection
    address: str
    code: str
    started: float
    channel: object = None
    approved: bool = False
    last_ping: float = 0
    last_seq: int = 0
    attempts: int = 0


class State:
    def __init__(self, lan_ip, port, inject, dry_run=False):
        self.lan_ip, self.port = lan_ip, port
        self.inject, self.dry_run = inject, dry_run
        self.owner = secrets.token_urlsafe(32)
        self.invite = None
        self.expires = 0.0
        self.peer = None
        self.phase = "idle"
        self.presses = 0
        self.lock = asyncio.Lock()
        self.public_url = None
        self.ice_servers = []
        self.bridge = None
        self.tailcat = None

    def invite_url(self):
        if self.tailcat:
            from urllib.parse import urlencode
            base = self.tailcat.web_url or f"http://{self.lan_ip}:{self.port}/"
            return base + "#" + urlencode({"pair": self.invite, "tc": self.tailcat.addr})
        return f"{self.public_url or f'http://{self.lan_ip}:{self.port}'}/#pair={self.invite}"

    async def end(self, peer=None):
        # ponytail: one controller per process; add multiple sessions only if needed.
        async with self.lock:
            if peer is not None and self.peer is not peer:
                return
            old, self.peer = self.peer, None
            self.invite = None
            self.phase = "ended"
            if old:
                old.approved = False
        if old:
            await old.pc.close()
        if self.bridge:
            await self.bridge.revoke()

    def send(self, peer, payload):
        if peer.channel and peer.channel.readyState == "open":
            peer.channel.send(json.dumps(payload))

    def message(self, peer, raw):
        if self.peer is not peer or not isinstance(raw, str) or len(raw.encode()) > 256:
            return
        try:
            msg = json.loads(raw)
        except (ValueError, TypeError):
            return
        if not isinstance(msg, dict):
            return
        if set(msg) == {"type", "id"} and msg["type"] == "ping":
            if type(msg["id"]) is not int or not 0 <= msg["id"] <= 2**53 - 1:
                return
            peer.last_ping = time.monotonic()
            self.send(peer, {"type": "pong", "id": msg["id"], "approved": peer.approved,
                             "serverTime": time.time() * 1000})
            return
        if set(msg) == {"type", "code"} and msg["type"] == "pair":
            if peer.approved or self.phase != "pending":
                return
            if time.monotonic() - peer.started > PAIR_DEADLINE:
                asyncio.create_task(self.end(peer))
                return
            peer.attempts += 1
            code = msg["code"]
            if not isinstance(code, str) or len(code) != 6 or not code.isascii() or not code.isdigit() or not secrets.compare_digest(code, peer.code):
                self.send(peer, {"type": "pair_error", "remaining": max(0, 3 - peer.attempts)})
                if peer.attempts >= 3:
                    self.phase = "ended"
                    asyncio.create_task(self.end(peer))
                return
            peer.approved = True
            self.phase = "connected"
            self.send(peer, {"type": "approved"})
            return
        if msg == {"type": "disconnect"}:
            peer.approved = False
            asyncio.create_task(self.end(peer))
            return
        if set(msg) != {"type", "seq", "key", "at"} or msg["type"] != "press":
            return
        seq = msg["seq"]
        if type(seq) is not int or not peer.last_seq < seq <= 2**53 - 1:
            return
        peer.last_seq = seq
        error = None
        if not peer.approved:
            error = "not_approved"
        elif not peer.last_ping or time.monotonic() - peer.last_ping > HEARTBEAT_TIMEOUT:
            error = "heartbeat_expired"
        elif type(msg["at"]) not in (int, float) or not -250 <= time.time() * 1000 - msg["at"] <= KEY_TTL_MS:
            error = "stale_press"
        elif not isinstance(msg["key"], str) or msg["key"] not in KEYS:
            error = "unknown_key"
        elif not allow_press():
            error = "rate_limited"
        else:
            try:
                self.inject(msg["key"])
                self.presses += 1
            except OSError:
                error = "input_failed"
        self.send(peer, {"type": "ack", "seq": seq, "error": error})


def require_owner(request):
    state = request.app[STATE]
    try:
        local = ipaddress.ip_address(request.remote).is_loopback
    except ValueError:
        local = False
    if not local or request.host not in {f"127.0.0.1:{state.port}", f"localhost:{state.port}"} or not secrets.compare_digest(request.headers.get("X-Owner-Token", ""), state.owner):
        raise web.HTTPForbidden(text="Local desktop authorization required")


@web.middleware
async def guards(request, handler):
    state = request.app[STATE]
    hosts = {f"{ip}:{state.port}" for ip in (state.lan_ip, "127.0.0.1", "localhost")}
    public_host = state.public_url.removeprefix("https://") if state.public_url else None
    if public_host:
        hosts.add(public_host)
    if request.host not in hosts:
        raise web.HTTPForbidden(text="Unrecognized host")
    if state.tailcat and request.path in ("/api/ice", "/api/offer"):
        if request.remote != "127.0.0.1" or not secrets.compare_digest(request.headers.get("X-Tailcat-Token", ""), state.tailcat.secret):
            raise web.HTTPForbidden()
    origin = f"{'https' if request.host == public_host else 'http'}://{request.host}"
    if (request.method == "POST" or request.path == "/api/ice") and request.headers.get("Origin") != origin:
        raise web.HTTPForbidden(text="Same-origin request required")
    response = await handler(request)
    response.headers.update({"Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
        "Content-Security-Policy": ("default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; img-src 'self' blob:; connect-src 'self' https://tailcat.dev wss:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'" if state.tailcat else "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")})
    return response


async def body_json(request):
    if request.content_type != "application/json":
        raise web.HTTPUnsupportedMediaType()
    try:
        data = await request.json()
    except ValueError:
        raise web.HTTPBadRequest()
    if not isinstance(data, dict):
        raise web.HTTPBadRequest()
    return data


async def invite(request):
    require_owner(request)
    await body_json(request)
    state = request.app[STATE]
    if state.tailcat:
        try:
            await asyncio.wait_for(state.tailcat.ready.wait(), 5)
        except TimeoutError:
            raise web.HTTPServiceUnavailable(text="tailcat 啟動中或無法連到 DERP，請稍後產生邀請")
    await state.end()
    async with state.lock:
        state.invite = secrets.token_urlsafe(32)
        state.expires = time.monotonic() + INVITE_TTL
        state.phase = "inviting"
    if state.bridge:
        try:
            state.ice_servers = await state.bridge.publish(state.invite)
        except (TimeoutError, ConnectionError):
            await state.end()
            raise web.HTTPServiceUnavailable(text="配對服務尚未連線，請稍後產生新邀請")
    return web.json_response({"url": state.invite_url(), "seconds": INVITE_TTL})


async def status(request):
    require_owner(request)
    state = request.app[STATE]
    peer = state.peer
    phase = state.phase
    if state.invite and time.monotonic() >= state.expires:
        state.invite = None
        state.phase = phase = "expired"
    return web.json_response({"phase": phase, "remaining": max(0, int(state.expires - time.monotonic())),
        "client": peer.address if peer else None, "code": peer.code if peer else None,
        "presses": state.presses, "dryRun": state.dry_run,
        "internet": bool(state.bridge or state.tailcat),
        "brokerOnline": bool((state.bridge and state.bridge.online) or (state.tailcat and state.tailcat.online))})


async def qr(request):
    require_owner(request)
    state = request.app[STATE]
    if not state.invite or time.monotonic() >= state.expires:
        raise web.HTTPGone()
    image = qrcode.make(state.invite_url(), image_factory=qrcode.image.svg.SvgPathImage)
    out = io.BytesIO()
    image.save(out)
    return web.Response(body=out.getvalue(), content_type="image/svg+xml")


async def offer(request):
    data = await body_json(request)
    if request.app[STATE].bridge:
        raise web.HTTPForbidden(text="Use the Internet pairing service")
    return web.json_response(await process_offer(request.app[STATE], data, request.remote))


async def process_offer(state, data, address):
    if set(data) != {"token", "sdp", "type"} or data["type"] != "offer" or not isinstance(data["sdp"], str):
        raise web.HTTPBadRequest()
    async with state.lock:
        if not isinstance(data["token"], str) or not state.invite or not secrets.compare_digest(data["token"], state.invite):
            raise web.HTTPForbidden(text="Invitation already used or invalid")
        if time.monotonic() >= state.expires:
            state.invite = None
            state.phase = "expired"
            raise web.HTTPGone(text="Invitation expired")
        # Consume before awaiting SDP processing, preventing concurrent/replayed offers.
        state.invite = None
        peer = Peer(RTCPeerConnection(RTCConfiguration(iceServers=[RTCIceServer(**entry) for entry in state.ice_servers])), address,
                    f"{secrets.randbelow(1000000):06d}", time.monotonic())
        state.peer = peer
        state.phase = "connecting"

    @peer.pc.on("datachannel")
    def channel_open(channel):
        if channel.label != "tailkey" or peer.channel is not None:
            channel.close()
            return
        peer.channel = channel
        if state.peer is peer:
            state.phase = "pending"

        @channel.on("message")
        def message(raw):
            state.message(peer, raw)

        @channel.on("close")
        def closed():
            peer.approved = False
            asyncio.create_task(state.end(peer))

    @peer.pc.on("connectionstatechange")
    async def connection_changed():
        if peer.pc.connectionState in ("failed", "closed", "disconnected"):
            await state.end(peer)

    try:
        async with asyncio.timeout(30):
            await peer.pc.setRemoteDescription(RTCSessionDescription(sdp=data["sdp"], type="offer"))
            await peer.pc.setLocalDescription(await peer.pc.createAnswer())
        if state.peer is not peer:
            raise web.HTTPGone(text="Pairing cancelled")
        return {"sdp": peer.pc.localDescription.sdp, "type": "answer"}
    except web.HTTPException:
        raise
    except Exception:
        await state.end(peer)
        raise web.HTTPBadRequest(text="Unable to establish WebRTC session")


async def approve(request):
    raise web.HTTPForbidden(text="Enter the desktop pairing code on the phone")


async def ice(request):
    data = await body_json(request)
    state = request.app[STATE]
    if state.bridge:
        raise web.HTTPForbidden()
    if set(data) != {"token"} or not isinstance(data["token"], str) or not state.invite or time.monotonic() >= state.expires or not secrets.compare_digest(data["token"], state.invite):
        raise web.HTTPForbidden()
    return web.json_response({"iceServers": state.ice_servers})


async def disconnect(request):
    require_owner(request)
    await body_json(request)
    await request.app[STATE].end()
    return web.json_response({"ok": True})


async def page(request):
    name = request.match_info.get("name", "")
    if request.app[STATE].tailcat and request.path in ("/", "/index.html"):
        return web.Response(body=(ROOT.parent / "tools/tailkey-web/index.html").read_bytes(), content_type="text/html")
    if request.path == "/host":
        state = request.app[STATE]
        if request.host not in {f"127.0.0.1:{state.port}", f"localhost:{state.port}"} or not ipaddress.ip_address(request.remote).is_loopback:
            raise web.HTTPForbidden()
        return web.Response(text=(ROOT / "host.html").read_text(encoding="utf-8"), content_type="text/html")
    if request.path == "/":
        html = (ROOT.parent / "static/index.html").read_text(encoding="utf-8")
        html = html.replace('src="/app.js"', 'src="/mobile.js"').replace('停止 Tailkey 連線', '中斷這次連線')
        html = html.replace('<link rel="stylesheet" href="/style.css" />', '<link rel="stylesheet" href="/style.css" /><link rel="stylesheet" href="/prototype.css" />')
        html = html.replace('由 Tailscale 私密連線', 'WebRTC 直接連線').replace('TAILNET', 'WEBRTC')
        html = html.replace('<section class="keypad-card"', '<p id="pair-status" role="status">正在配對</p><section class="keypad-card"')
        if request.app[STATE].tailcat:
            html = html.replace('<script src="/mobile.js"', '<script src="/wasm_exec.js" defer></script><script src="/tailcat_transport.js" defer></script><script src="/mobile.js"')
        return web.Response(text=html, content_type="text/html")
    assets = {"style.css": (ROOT.parent / "static/style.css", "text/css"),
              "i18n.js": (ROOT.parent / "static/i18n.js", "text/javascript"),
              "prototype.css": (ROOT / "prototype.css", "text/css"),
              "host.js": (ROOT / "host.js", "text/javascript"),
              "mobile.js": (ROOT / "mobile.js", "text/javascript")}
    if request.app[STATE].tailcat:
        for asset, mime in (("pwa.js", "text/javascript"), ("sw.js", "text/javascript"), ("manifest.webmanifest", "application/manifest+json"), ("icon.svg", "image/svg+xml"), ("icon-192.png", "image/png"), ("icon-512.png", "image/png")):
            assets[asset] = (ROOT.parent / "tools/tailkey-web" / asset, mime)
        assets.update({"tailcat_transport.js": (ROOT / "tailcat_transport.js", "text/javascript"),
                       "wasm_exec.js": (ROOT.parent / "tools/tailcat-web/wasm_exec.js", "text/javascript"),
                       "main.wasm.gz": (ROOT.parent / "tools/tailcat-web/main.wasm.gz", "application/gzip")})
    if name not in assets:
        raise web.HTTPNotFound()
    path, mime = assets[name]
    return web.Response(body=path.read_bytes(), content_type=mime)


async def watchdog(app):
    state = app[STATE]
    while True:
        await asyncio.sleep(0.5)
        peer = state.peer
        if not peer:
            continue
        age = time.monotonic() - peer.started
        if (not peer.approved and age > PAIR_DEADLINE) or (peer.last_ping and time.monotonic() - peer.last_ping > HEARTBEAT_TIMEOUT):
            await state.end(peer)


async def lifecycle(app):
    task = asyncio.create_task(watchdog(app))
    bridge_task = asyncio.create_task(app[STATE].bridge.run()) if app[STATE].bridge else None
    tailcat_task = asyncio.create_task(app[STATE].tailcat.run()) if app[STATE].tailcat else None
    yield
    if bridge_task:
        bridge_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await bridge_task
    if tailcat_task:
        tailcat_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await tailcat_task
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
    await app[STATE].end()


def make_app(lan_ip, port, inject=press_key, dry_run=False):
    app = web.Application(client_max_size=65536, middlewares=[guards])
    app[STATE] = State(lan_ip, port, inject, dry_run)
    app.router.add_get("/", page)
    app.router.add_get("/host", page)
    app.router.add_get("/api/status", status)
    app.router.add_get("/api/qr", qr)
    for path, handler in (("invite", invite), ("offer", offer), ("ice", ice), ("approve", approve), ("disconnect", disconnect)):
        app.router.add_post(f"/api/{path}", handler)
    app.router.add_get("/{name}", page)
    app.cleanup_ctx.append(lifecycle)
    return app


def detect_lan_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("192.0.2.1", 9))
            return sock.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-ip", default=detect_lan_ip())
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--dry-run", action="store_true", help="Validate keys without injecting them")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--public-url", help="Exact HTTPS origin of the test tunnel")
    parser.add_argument("--internet", action="store_true", help="Outbound connection to your pairing broker")
    parser.add_argument("--tailcat", action="store_true", help="Exchange WebRTC signaling over bundled tailcat")
    parser.add_argument("--web-url", help="HTTPS URL of your static Tailkey browser page")
    args = parser.parse_args()
    if args.tailcat and (args.internet or args.public_url):
        parser.error("Tailcat mode is separate from broker/reverse-proxy mode")
    if args.web_url:
        from urllib.parse import urlsplit
        parsed_web = urlsplit(args.web_url)
        if not args.tailcat or parsed_web.scheme != "https" or not parsed_web.hostname or parsed_web.query or parsed_web.fragment or parsed_web.username or parsed_web.password:
            parser.error("--web-url requires tailcat mode and an HTTPS page URL without query/fragment")
    if args.internet and args.public_url:
        parser.error("Choose --internet or --public-url")
    config_root = Path(sys.executable).parent if getattr(sys, "frozen", False) else ROOT.parent
    config_path = config_root / "tailkey.internet.local.json"
    if args.internet:
        from internet import BrokerBridge, validate_config
        try:
            config = validate_config(json.loads(config_path.read_text(encoding="utf-8-sig")))
        except (OSError, ValueError, TypeError, KeyError):
            parser.error("Set brokerUrl and hostKey in tailkey.internet.local.json; see webrtc/INTERNET.md")
    if args.public_url:
        from urllib.parse import urlsplit
        parsed = urlsplit(args.public_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.path not in ("", "/") or parsed.query or parsed.fragment or parsed.username or parsed.password:
            parser.error("--public-url must be an HTTPS origin")
        args.public_url = f"https://{parsed.netloc}"
    ipaddress.IPv4Address(args.host_ip)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.bind(("127.0.0.1" if args.internet else "0.0.0.0", args.port))
    except OSError as error:
        listener.close()
        if getattr(error, "winerror", None) == 10048 or error.errno in (10048, 98):
            print(f"Tailkey WebRTC: port {args.port} is already in use. Close the existing service window first.", file=sys.stderr)
            print("Or start a separate instance with: start-webrtc.cmd --port 8767", file=sys.stderr)
            raise SystemExit(1) from None
        raise
    listener.setblocking(False)
    app = make_app(args.host_ip, args.port, (lambda _key: None) if args.dry_run else press_key, args.dry_run)
    app[STATE].public_url = args.public_url
    if args.tailcat:
        from tailcat import TailcatBridge
        if not (ROOT.parent / "tools/tailkey-tailcat.exe").exists() or not (ROOT.parent / "tools/tailcat-web/main.wasm.gz").exists():
            listener.close()
            parser.error("Build tailcat assets with webrtc/build-tailcat.ps1 first")
        app[STATE].tailcat = TailcatBridge(app[STATE], args.web_url)
        tailcat_config = json.loads(config_path.read_text(encoding="utf-8-sig")) if config_path.exists() else {}
        # Direct-only experiment: TURN is deliberately not offered in tailcat mode.
        for entry in tailcat_config.get("iceServers", [{"urls": "stun:stun.cloudflare.com:3478"}]):
            urls = entry.get("urls", [])
            urls = [urls] if isinstance(urls, str) else urls
            urls = [url for url in urls if isinstance(url, str) and url.startswith("stun:")]
            if urls:
                app[STATE].ice_servers.append({"urls": urls})
    if args.internet:
        app[STATE].public_url = config["brokerUrl"]
        app[STATE].bridge = BrokerBridge(app[STATE], config, process_offer)
        app[STATE].ice_servers = config.get("iceServers", [])
    if args.public_url:
        config = json.loads(config_path.read_text(encoding="utf-8-sig")) if config_path.exists() else {}
        app[STATE].ice_servers = config.get("iceServers", [])
        if not app[STATE].ice_servers:
            print("Internet mode has no STUN/TURN configured; cross-network connectivity may fail.", file=sys.stderr)

    async def ready(app):
        url = f"http://127.0.0.1:{args.port}/host#owner={app[STATE].owner}"
        print("Tailkey WebRTC: Ctrl+C stops it.", flush=True)
        print("The desktop page contains a private controller token; do not share it.", flush=True)
        if not args.no_browser:
            asyncio.get_running_loop().call_later(0.8, webbrowser.open, url)
        else:
            print(url, flush=True)

    app.on_startup.append(ready)
    try:
        web.run_app(app, sock=listener, access_log=None, print=None)
    finally:
        listener.close()


if __name__ == "__main__":
    main()
