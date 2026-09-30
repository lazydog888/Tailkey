"""Manage the bundled tailcat helper; it carries signaling, never keyboard input."""
import asyncio
import contextlib
import json
import os
from pathlib import Path
import secrets
import sys


class TailcatBridge:
    def __init__(self, state, web_url, fallback=False):
        self.state, self.web_url, self.fallback = state, web_url, fallback
        self.secret = secrets.token_urlsafe(32)
        self.addr = None
        self.online = False
        self.process = None
        self.ready = asyncio.Event()

    async def run(self):
        bundle_root = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
        executable = bundle_root / "tools/tailkey-tailcat.exe"
        try:
            self.process = await asyncio.create_subprocess_exec(str(executable), "--target", f"http://127.0.0.1:{self.state.port}",
                env={**os.environ, "TAILKEY_SIGNAL_TOKEN": self.secret}, stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
                creationflags=0x08000000 if os.name == "nt" else 0)
            line = await asyncio.wait_for(self.process.stdout.readline(), 50)
            self.addr = json.loads(line)["addr"]
            self.online = True
            self.ready.set()
            await self.process.wait()
        except (OSError, ValueError, KeyError, TimeoutError):
            pass
        finally:
            self.online = False
            self.ready.clear()
            if self.process and self.process.returncode is None:
                self.process.stdin.close()
                try:
                    await asyncio.wait_for(self.process.wait(), 3)
                except TimeoutError:
                    self.process.kill()
                    await self.process.wait()
            await self.state.end()
            if self.fallback and self.state.tailcat is self:
                # Auto mode: without DERP, keep working as the plain same-Wi-Fi keypad.
                self.state.tailcat = None
                self.state.ice_servers = []
                print("Tailcat unavailable; switched to same-Wi-Fi mode.", flush=True)
