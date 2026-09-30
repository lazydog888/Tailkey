"""Real localhost WebRTC negotiation; injected keys are recorded, never sent to Windows."""
import asyncio
import json
import time
import unittest

from aiohttp import ClientSession
from aiohttp.test_utils import TestServer
from aiortc import RTCConfiguration, RTCPeerConnection, RTCSessionDescription
from app import IDLE_TIMEOUT, STATE, make_app


class PairingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.keys = []
        self.app = make_app("127.0.0.1", 0, inject=self.keys.append, dry_run=True)
        self.server = TestServer(self.app)
        await self.server.start_server()
        self.state = self.app[STATE]
        self.state.port = self.server.port
        self.base = str(self.server.make_url("/")).rstrip("/")
        self.headers = {"Origin": self.base}
        self.owner = {**self.headers, "X-Owner-Token": self.state.owner}
        self.http = ClientSession()
        self.pcs = []

    async def asyncTearDown(self):
        for pc in self.pcs:
            await pc.close()
        await self.http.close()
        await self.server.close()

    async def post(self, path, data, headers=None):
        return await self.http.post(self.base + path, json=data, headers=headers or self.headers)

    async def make_offer(self):
        pc = RTCPeerConnection(RTCConfiguration(iceServers=[]))
        self.pcs.append(pc)
        channel = pc.createDataChannel("tailkey")
        opened = asyncio.Event()
        messages = asyncio.Queue()

        @channel.on("open")
        def open_channel():
            opened.set()

        @channel.on("message")
        def message(raw):
            messages.put_nowait(json.loads(raw))

        await pc.setLocalDescription(await pc.createOffer())
        return pc, channel, opened, messages

    async def pair(self):
        response = await self.post("/api/invite", {}, self.owner)
        self.assertEqual(response.status, 200)
        pc, channel, opened, messages = await self.make_offer()
        payload = {"token": self.state.invite, "type": "offer", "sdp": pc.localDescription.sdp}
        response = await self.post("/api/offer", payload)
        self.assertEqual(response.status, 200)
        answer = await response.json()
        await pc.setRemoteDescription(RTCSessionDescription(**answer))
        await asyncio.wait_for(opened.wait(), 10)
        return channel, messages, payload

    async def receive(self, queue, kind):
        async with asyncio.timeout(5):
            while True:
                msg = await queue.get()
                if msg["type"] == kind:
                    return msg

    async def test_real_channel_approval_replay_and_disconnect(self):
        channel, messages, payload = await self.pair()
        self.assertEqual((await self.post("/api/offer", payload)).status, 403)
        channel.send(json.dumps({"type": "ping", "id": 1}))
        self.assertFalse((await self.receive(messages, "pong"))["approved"])
        channel.send(json.dumps({"type": "press", "seq": 1, "key": "BACKSPACE", "at": time.time() * 1000}))
        self.assertEqual((await self.receive(messages, "ack"))["error"], "not_approved")
        self.assertEqual(self.keys, [])
        self.assertEqual((await self.post("/api/approve", {}, self.owner)).status, 403)
        channel.send(json.dumps({"type": "pair", "code": self.state.peer.code}))
        await self.receive(messages, "approved")
        channel.send(json.dumps({"type": "press", "seq": 2, "key": "BACKSPACE", "at": time.time() * 1000}))
        self.assertIsNone((await self.receive(messages, "ack"))["error"])
        self.assertEqual(self.keys, ["BACKSPACE"])
        channel.send(json.dumps({"type": "press", "seq": 3, "key": "NOT_A_KEY", "at": time.time() * 1000}))
        self.assertEqual((await self.receive(messages, "ack"))["error"], "unknown_key")
        channel.send(json.dumps({"type": "press", "seq": 4, "key": "NUMPAD1", "at": time.time() * 1000 - 5000}))
        self.assertEqual((await self.receive(messages, "ack"))["error"], "stale_press")
        channel.send(json.dumps({"type": "press", "seq": 2, "key": "NUMPAD1", "at": time.time() * 1000}))
        channel.send(json.dumps({"type": "disconnect"}))
        for _ in range(30):
            if self.state.peer is None:
                break
            await asyncio.sleep(0.05)
        self.assertIsNone(self.state.peer)
        self.assertEqual(self.keys, ["BACKSPACE"])

    async def test_expiry_bad_origin_and_owner_authorization(self):
        self.assertEqual((await self.post("/api/invite", {})).status, 403)
        headers = {**self.owner, "Origin": "http://untrusted.invalid"}
        self.assertEqual((await self.post("/api/invite", {}, headers)).status, 403)
        await self.post("/api/invite", {}, self.owner)
        pc, _, _, _ = await self.make_offer()
        token = self.state.invite
        self.state.expires = time.monotonic() - 1
        response = await self.post("/api/offer", {"token": token, "type": "offer", "sdp": pc.localDescription.sdp})
        self.assertEqual(response.status, 410)
        self.assertIsNone(self.state.peer)

    async def test_concurrent_invite_use_and_missing_heartbeat(self):
        await self.post("/api/invite", {}, self.owner)
        pc, channel, opened, messages = await self.make_offer()
        payload = {"token": self.state.invite, "type": "offer", "sdp": pc.localDescription.sdp}
        responses = await asyncio.gather(self.post("/api/offer", payload), self.post("/api/offer", payload))
        self.assertEqual(sorted(response.status for response in responses), [200, 403])
        answer = await next(response for response in responses if response.status == 200).json()
        await pc.setRemoteDescription(RTCSessionDescription(**answer))
        await asyncio.wait_for(opened.wait(), 10)
        channel.send(json.dumps({"type": "ping", "id": 1}))
        await self.receive(messages, "pong")
        channel.send(json.dumps({"type": "pair", "code": self.state.peer.code}))
        await self.receive(messages, "approved")
        self.state.peer.last_ping = time.monotonic() - 10
        await asyncio.sleep(0.8)
        self.assertIsNone(self.state.peer)
        self.assertEqual(self.keys, [])

    async def test_pairing_notifies_and_idle_session_ends(self):
        notices = []
        self.state.notify = lambda title, body: notices.append(title)
        channel, messages, _ = await self.pair()
        channel.send(json.dumps({"type": "ping", "id": 1}))
        await self.receive(messages, "pong")
        channel.send(json.dumps({"type": "pair", "code": self.state.peer.code}))
        await self.receive(messages, "approved")
        self.assertEqual(len(notices), 1)
        channel.send(json.dumps({"type": "ping", "id": 2}))
        await self.receive(messages, "pong")
        self.state.peer.last_active = time.monotonic() - IDLE_TIMEOUT - 1
        await self.receive(messages, "idle")
        for _ in range(30):
            if self.state.peer is None:
                break
            await asyncio.sleep(0.05)
        self.assertIsNone(self.state.peer)


if __name__ == "__main__":
    unittest.main()
