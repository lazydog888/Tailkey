"""Self-hosted Tailkey signaling service. No keyboard injector or desktop controller."""
import argparse
import asyncio
import base64
import contextlib
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import ssl
import time
from urllib.parse import urlsplit

from aiohttp import web, WSMsgType

ROOT = Path(__file__).resolve().parent
SERVICE = web.AppKey("service", object)


@dataclass(eq=False)
class Host:
    ws: object
    token: str = None
    expires: float = 0
    ice: list = field(default_factory=list)
    pending: dict = field(default_factory=dict)
    last_publish: float = 0


class Service:
    def __init__(self, origin, key):
        self.origin, self.key = origin, key
        self.hosts = set()
        self.invites = {}

    def revoke(self, host):
        if host.token:
            self.invites.pop(host.token, None)
        host.token = None

    def ice_config(self, requested):
        # Optional coturn REST credentials; the shared TURN secret stays on this server.
        secret = os.environ.get("TAILKEY_TURN_SECRET")
        urls = os.environ.get("TAILKEY_TURN_URLS")
        if secret and urls:
            username = f"{int(time.time()) + 3600}:{secrets.token_hex(8)}"
            credential = base64.b64encode(hmac.new(secret.encode(), username.encode(), hashlib.sha1).digest()).decode()
            return [{"urls": item} for item in os.environ.get("TAILKEY_STUN_URLS", "").split(",") if item] + [
                {"urls": urls.split(","), "username": username, "credential": credential}]
        if not isinstance(requested, list) or len(requested) > 8:
            raise ValueError("Invalid ICE configuration")
        for entry in requested:
            if not isinstance(entry, dict) or not set(entry) <= {"urls", "username", "credential", "credentialType"} or "urls" not in entry:
                raise ValueError("Invalid ICE configuration")
        return requested


@web.middleware
async def guard(request, handler):
    service = request.app[SERVICE]
    if request.host != urlsplit(service.origin).netloc:
        raise web.HTTPForbidden()
    if request.method == "POST" and request.headers.get("Origin") != service.origin:
        raise web.HTTPForbidden()
    try:
        response = await handler(request)
    except web.HTTPException as error:
        response = error
    if not isinstance(response, web.WebSocketResponse):
        response.headers.update({"Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'"})
    return response


async def channel(request):
    service = request.app[SERVICE]
    if not secrets.compare_digest(request.headers.get("Authorization", ""), "Bearer " + service.key):
        raise web.HTTPForbidden()
    if len(service.hosts) >= 32:
        raise web.HTTPServiceUnavailable()
    ws = web.WebSocketResponse(heartbeat=10, max_msg_size=65536, compress=False)
    await ws.prepare(request)
    host = Host(ws)
    service.hosts.add(host)
    try:
        async for frame in ws:
            if frame.type != WSMsgType.TEXT:
                break
            try:
                message = json.loads(frame.data)
                if not isinstance(message, dict):
                    break
                if message.get("type") == "publish":
                    ident, token = message.get("id"), message.get("token")
                    if not isinstance(ident, str) or len(ident) > 64 or not isinstance(token, str) or not 40 <= len(token) <= 64:
                        break
                    service.revoke(host)
                    if time.monotonic() - host.last_publish < 1 or token in service.invites:
                        await ws.send_json({"type": "published", "id": ident, "error": True})
                        continue
                    host.ice = service.ice_config(message.get("iceServers", []))
                    host.token, host.expires = token, time.monotonic() + 120
                    host.last_publish = time.monotonic()
                    service.invites[token] = host
                    await ws.send_json({"type": "published", "id": ident, "iceServers": host.ice})
                elif message.get("type") == "revoke":
                    service.revoke(host)
                elif message.get("type") == "answer":
                    future = host.pending.get(message.get("id"))
                    if future and not future.done():
                        future.set_result(message)
                else:
                    break
            except (ValueError, TypeError):
                break
    finally:
        service.revoke(host)
        service.hosts.discard(host)
        for future in host.pending.values():
            if not future.done():
                future.set_exception(ConnectionError("Host offline"))
        await ws.close()
    return ws


async def json_body(request):
    if request.content_type != "application/json":
        raise web.HTTPUnsupportedMediaType()
    try:
        data = await request.json()
    except ValueError:
        raise web.HTTPBadRequest()
    if not isinstance(data, dict):
        raise web.HTTPBadRequest()
    return data


def get_invite(request, data):
    token = data.get("token")
    host = request.app[SERVICE].invites.get(token) if isinstance(token, str) else None
    if not host or host.ws.closed:
        raise web.HTTPForbidden()
    if time.monotonic() >= host.expires:
        request.app[SERVICE].revoke(host)
        raise web.HTTPGone()
    return host


async def ice(request):
    data = await json_body(request)
    if set(data) != {"token"}:
        raise web.HTTPBadRequest()
    return web.json_response({"iceServers": get_invite(request, data).ice})


async def offer(request):
    data = await json_body(request)
    if set(data) != {"token", "sdp", "type"} or data["type"] != "offer" or not isinstance(data["sdp"], str):
        raise web.HTTPBadRequest()
    host = get_invite(request, data)
    request.app[SERVICE].revoke(host)  # Consume before the first await.
    if host.pending:
        raise web.HTTPConflict()
    ident = secrets.token_hex(16)
    future = asyncio.get_running_loop().create_future()
    host.pending[ident] = future
    try:
        await host.ws.send_json({"type": "offer", "id": ident, "data": data})
        answer = await asyncio.wait_for(future, 35)
        if answer.get("status") != 200 or not isinstance(answer.get("data"), dict):
            raise web.HTTPBadRequest(text="Unable to negotiate session")
        return web.json_response(answer["data"])
    except (TimeoutError, ConnectionError):
        raise web.HTTPServiceUnavailable(text="Desktop unavailable")
    finally:
        host.pending.pop(ident, None)


async def page(request):
    if request.path == "/":
        html = (ROOT.parent / "static/index.html").read_text(encoding="utf-8")
        html = html.replace('src="/app.js"', 'src="/mobile.js"').replace('停止 Tailkey 連線', '中斷這次連線')
        html = html.replace('<link rel="stylesheet" href="/style.css" />', '<link rel="stylesheet" href="/style.css" /><link rel="stylesheet" href="/prototype.css" />')
        html = html.replace('由 Tailscale 私密連線', 'WebRTC 連線').replace('TAILNET', 'WEBRTC')
        html = html.replace('<section class="keypad-card"', '<p id="pair-status" role="status">正在配對</p><section class="keypad-card"')
        return web.Response(text=html, content_type="text/html")
    assets = {"style.css": (ROOT.parent / "static/style.css", "text/css"),
              "i18n.js": (ROOT.parent / "static/i18n.js", "text/javascript"),
              "prototype.css": (ROOT / "prototype.css", "text/css"),
              "mobile.js": (ROOT / "mobile.js", "text/javascript")}
    name = request.match_info.get("name")
    if name not in assets:
        raise web.HTTPNotFound()
    path, mime = assets[name]
    return web.Response(body=path.read_bytes(), content_type=mime)


async def cleanup(app):
    yield
    await asyncio.gather(*(host.ws.close() for host in tuple(app[SERVICE].hosts)), return_exceptions=True)


def make_broker(origin, key):
    app = web.Application(client_max_size=65536, middlewares=[guard])
    app[SERVICE] = Service(origin, key)
    app.router.add_get("/host-channel", channel)
    app.router.add_post("/api/ice", ice)
    app.router.add_post("/api/offer", offer)
    app.router.add_get("/", page)
    app.router.add_get("/{name}", page)
    app.cleanup_ctx.append(cleanup)
    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True, help="Exact public HTTPS origin")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8780)
    parser.add_argument("--tls-cert")
    parser.add_argument("--tls-key")
    args = parser.parse_args()
    parsed = urlsplit(args.origin)
    if parsed.scheme != "https" or not parsed.hostname or parsed.path not in ("", "/") or parsed.query or parsed.fragment or parsed.username or parsed.password:
        parser.error("--origin must be an HTTPS origin")
    key = os.environ.get("TAILKEY_BROKER_HOST_KEY", "")
    if len(key) < 32:
        parser.error("Set TAILKEY_BROKER_HOST_KEY to a random secret of at least 32 characters")
    if bool(args.tls_cert) != bool(args.tls_key):
        parser.error("Both TLS certificate and key are required")
    tls = None
    if args.tls_cert:
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.minimum_version = ssl.TLSVersion.TLSv1_2
        tls.load_cert_chain(args.tls_cert, args.tls_key)
    elif args.bind not in ("127.0.0.1", "::1"):
        parser.error("Plain HTTP backend must bind to loopback behind a local HTTPS proxy")
    web.run_app(make_broker(f"https://{parsed.netloc}", key), host=args.bind, port=args.port,
                ssl_context=tls, access_log=None, print=None, reuse_address=False)


if __name__ == "__main__":
    main()
