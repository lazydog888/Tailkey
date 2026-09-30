# Tailcat signaling + WebRTC direct-only experiment

This is a new transport experiment, not a change to tailcat's browser UDP support. Tailcat's browser WASM client reaches the native Windows helper over DERP. That encrypted stream carries only ICE configuration and an SDP offer/answer. The browser then closes tailcat signaling and attempts a native WebRTC DataChannel to Windows. The code and keys travel on that DataChannel only. TURN URLs are excluded in this mode, so inability to establish a direct connection produces an error rather than relayed keyboard input.

## Artifacts and startup

- `tools/tailkey-tailcat.exe`: native helper compiled from `webrtc/tailcat-helper` and pinned upstream source.
- `tools/tailkey-web/`: complete static mobile distribution, including the compiled tailcat WASM and its license. No host controller, private configuration, owner token or stored pairing code is included.
- `start-tailcat.cmd`: manually starts Tailkey with this transport. The stable `start.cmd` and same-Wi-Fi `start-webrtc.cmd` are separate.

The native helper and WASM were compiled on 2026-09-30. The upstream revision is `b4dc28e8aa8936f0a90a41ad8293a64e3d6b645f` with Go 1.27.1. The downloaded Go archive was checked against the official SHA-256 before extraction/execution. `webrtc/build-tailcat.ps1` rebuilds using that source revision and an installed or project-local Go SDK. Development tools are ignored by Git; users of a future installer should receive bundled binaries and will not need Go.

For a same-Wi-Fi trial, run `start-tailcat.cmd`; it serves the mobile files locally. For a separate-network 4G trial, first host **only the contents of `tools/tailkey-web/`** at an HTTPS static site. Then run:

`start-tailcat.cmd --web-url https://your-static-site.example/`

Scan the new QR code on the phone, enter the desktop's six-digit code and select the Windows target app. A fragment containing the ephemeral tailcat address and one-use invitation is added to that static URL. The browser removes it from the address bar after reading it. Do not publish the complete invitation/controller URL.

## Infrastructure

No inbound HTTP route, public desktop IP, port forwarding, custom signaling server or TURN server is needed for this experiment. The static HTTPS page, tailcat DERP map/relays and a STUN server are still external dependencies. Tailcat relays are used for the initial signaling exchange even when the final WebRTC path is direct. This design does not make a Windows HTTP server accessible through an ordinary Safari URL.

By default the WebRTC endpoint uses `stun:stun.cloudflare.com:3478`, an interchangeable public STUN service, not a Cloudflare account/tunnel. Set `iceServers` in ignored `tailkey.internet.local.json` to use your own STUN URLs. An empty array disables external STUN and generally limits connectivity. Only `stun:` URLs are used in this direct-only mode; TURN is excluded. The upstream browser module uses `https://tailcat.dev/derpmap.json`. The upstream DERP relays are rate limited and offer no guarantee that every NAT/carrier combination connects.

## Limits and validation status

The helper is a restricted signaling adapter, not a general port forwarder. It accepts at most four streams, each with at most two JSON signaling requests, a bounded 64 KiB body, and a 90-second deadline. It calls only `/api/ice` and `/api/offer` on loopback, with an in-memory token. It cannot access the controller or request arbitrary Windows keys. Invitations remain single-use with a 120-second lifetime; wrong pairing codes cancel the session after three attempts.

The UI reports selected direct/TURN candidate type and heartbeat round-trip latency. This mode supplies no TURN candidates. Desktop integration testing completed a real DERP signaling exchange followed by local WebRTC direct connection and a dry-run key acknowledgement; see [PWA.md](PWA.md). Separate-network 4G direct connectivity remains unverified. There is no automatic DERP keyboard fallback. A failed direct connection stops pairing/input.

The helper process lifetime is tied to Tailkey's stdin and explicit subprocess cleanup. Stop the service window with Ctrl+C when finished. No test service is launched by the build/export scripts.

Sources: [tailcat README](https://github.com/tailscale/tailcat), [browser API source](https://github.com/tailscale/tailcat/blob/main/web/main_js.go), [WebRTC tracking issue](https://github.com/tailscale/tailcat/issues/4).
