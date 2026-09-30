"""Outbound signaling only. Pairing codes and keyboard messages stay on the DataChannel."""
import asyncio
import contextlib
import json
import secrets
from urllib.parse import urlsplit

from aiohttp import ClientError, ClientSession, ClientTimeout, WSMsgType, web


def validate_config(config):
    url = urlsplit(config["brokerUrl"])
    if url.scheme != "https" or not url.hostname or url.path not in ("", "/") or url.query or url.fragment or url.username or url.password:
        raise ValueError("HTTPS origin required")
    _ = url.port
    if not isinstance(config["hostKey"], str) or len(config["hostKey"]) < 32:
        raise ValueError("Host key must have at least 32 characters")
    config["brokerUrl"] = f"https://{url.netloc}"
    return config


class BrokerBridge:
    def __init__(self, state, config, process_offer):
        self.state, self.config, self.process_offer = state, config, process_offer
        self.ws = None
        self.online = False
        self.ready = asyncio.Event()
        self.pending = {}
        self.work = set()

    async def publish(self, token):
        await asyncio.wait_for(self.ready.wait(), 5)
        ident = secrets.token_hex(16)
        future = asyncio.get_running_loop().create_future()
        self.pending[ident] = future
        try:
            await self.ws.send_json({"type": "publish", "id": ident, "token": token,
                                     "iceServers": self.config.get("iceServers", [])})
            reply = await asyncio.wait_for(future, 5)
            if reply.get("error"):
                raise ConnectionError("Invite registration failed")
            return reply["iceServers"]
        finally:
            self.pending.pop(ident, None)

    async def revoke(self):
        if self.online and self.ws and not self.ws.closed:
            with contextlib.suppress(ConnectionError, RuntimeError):
                await self.ws.send_json({"type": "revoke"})

    async def answer(self, message, ws):
        try:
            data = await self.process_offer(self.state, message["data"], "Internet peer")
            result = {"type": "answer", "id": message["id"], "status": 200, "data": data}
        except web.HTTPException as error:
            result = {"type": "answer", "id": message["id"], "status": error.status}
        except Exception:
            result = {"type": "answer", "id": message["id"], "status": 400}
        if not ws.closed:
            await ws.send_json(result)

    async def run(self):
        delay = 1
        async with ClientSession(timeout=ClientTimeout(total=None, sock_connect=10)) as session:
            try:
                while True:
                    try:
                        url = self.config["brokerUrl"].replace("https://", "wss://", 1) + "/host-channel"
                        async with session.ws_connect(url, headers={"Authorization": "Bearer " + self.config["hostKey"]}, heartbeat=10, max_msg_size=65536) as ws:
                            self.ws, self.online = ws, True
                            self.ready.set()
                            delay = 1
                            async for frame in ws:
                                if frame.type != WSMsgType.TEXT:
                                    break
                                message = json.loads(frame.data)
                                if message.get("type") == "published":
                                    future = self.pending.get(message.get("id"))
                                    if future and not future.done():
                                        future.set_result(message)
                                elif message.get("type") == "offer":
                                    if self.work:
                                        await ws.send_json({"type": "answer", "id": message["id"], "status": 409})
                                    else:
                                        task = asyncio.create_task(self.answer(message, ws))
                                        self.work.add(task)
                                        task.add_done_callback(self.work.discard)
                    except (ClientError, OSError, ValueError, ConnectionError, RuntimeError):
                        # No URLs, credentials or SDP in console output.
                        pass
                    finally:
                        self.online = False
                        self.ready.clear()
                        for future in self.pending.values():
                            if not future.done():
                                future.set_exception(ConnectionError("Broker disconnected"))
                        for task in tuple(self.work):
                            task.cancel()
                        await asyncio.gather(*self.work, return_exceptions=True)
                        await self.state.end()
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 30)
            finally:
                self.online = False
                self.ready.clear()
                for task in tuple(self.work):
                    task.cancel()
                await asyncio.gather(*self.work, return_exceptions=True)
