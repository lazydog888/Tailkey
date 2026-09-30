# WebRTC same-Wi-Fi prototype

For the new tailcat-assisted direct WebRTC experiment, see [TAILCAT.md](TAILCAT.md). For the offline PWA and desktop test results, see [PWA.md](PWA.md). Native/WASM artifacts are compiled and local tailcat-to-WebRTC integration passed; separate-network connectivity is not yet established. This avoids an application-specific signaling broker by using tailcat's DERP bootstrap and a static HTTPS browser page.

This prototype provides a browser keypad with a direct WebRTC DataChannel to Windows. It uses the existing `server.py` key allowlist and complete SendInput presses. It requires no Tailscale account, Tailscale client, or installation on the phone.

## Start

The portable Windows package opens through `Tailkey.exe`; choose option 1 for this mode. The source launcher is `Tailkey.cmd`. Both the desktop and phone pages include English/Traditional Chinese selection. Mobile language changes reload the page and require a new invitation.

Run `start-webrtc.cmd` in the repository root. The local virtual environment is already prepared on the development machine; for a fresh checkout, `setup-webrtc.cmd` installs Python dependencies. Keep the service window open.

1. The desktop pairing page opens automatically on localhost.
2. Connect your iPhone/iPad to the same trusted Wi-Fi as the PC, then scan the QR code or open the displayed invitation URL.
3. Enter the six-digit code displayed on the PC into the phone's pairing form. The server enables input only after verifying the code. Three wrong entries cancel the session.
4. Select the target Windows application. The mobile keypad can now send NumPad keys and Backspace.
5. Click **中斷這次連線** on the phone, or **中斷連線** on the PC. A new invitation is required to reconnect.

Windows may ask whether Python can receive connections; LAN access requires allowing it on the private network. The prototype does not create firewall rules. Guest Wi-Fi that isolates devices will not work.

The prototype uses HTTP on port 8766 for page delivery and signaling. WebRTC DataChannel traffic is encrypted, but HTTP page delivery/signaling is not protected against an attacker on the network. Use this prototype only on trusted LANs. The pairing number is a visual check, not cryptographic authentication. A hosted HTTPS frontend and authenticated signaling are required before Internet deployment.

If the automatically selected adapter is wrong, use `start-webrtc.cmd --host-ip <your-PC-LAN-IPv4>`. The invite URL contains a temporary secret; do not publish it or save it in logs. The desktop URL contains a separate local-only owner secret and must never be shared.

## Behavior

- Invitations expire in 120 seconds and are consumed atomically on the first valid offer. Only one phone can be paired.
- Input is disabled until the phone supplies the correct desktop code over its encrypted DataChannel. The code is not returned in mobile HTTP responses or heartbeats. Local control endpoints require a loopback connection, a localhost Host header and the in-memory owner token; a public reverse proxy cannot access them merely by connecting from loopback.
- Heartbeat loss closes the session after four seconds. Leaving the mobile page stops the session. Each key press is a complete down/up pair; old presses, unknown keys and replayed sequence numbers are rejected.
- A key already delivered to Windows cannot be retracted. The frontend keeps at most one unacknowledged press; it drops extra taps while waiting and queues no repeats.
- No STUN, TURN, cloud signaling, persistent pairing, or tailcat integration is configured. Both peers gather local ICE candidates. This is a LAN-only prototype, not the cross-network release.
- The stable Tailscale version continues to use `start.cmd` and port 8765. The prototype runs separately on port 8766 and does not change Serve routes.

## Validation

`start-webrtc.cmd --dry-run` opens the same UI but records accepted key counts without sending input to Windows.

Run the integration checks with `.venv-webrtc\Scripts\python.exe webrtc\test_app.py`. They negotiate real localhost WebRTC peers and check approval, invitation expiry/reuse, origin/owner guards, key validation, stale presses and heartbeat disconnection. The injector is replaced by an in-memory recorder.

The earlier desktop in-app browser dry-run check completed the previous click-to-approve flow, a Backspace press, and mobile disconnection. On 2026-09-30 the user confirmed the revised phone-entry pairing flow works on iPhone, including when the PC uses the phone's hotspot. Separate-network 4G connectivity remains unverified.

## Internet preparation (not a hosted release)

The next revision includes an outbound WSS signaling client and a standalone self-hostable broker. See [INTERNET.md](INTERNET.md) for setup and current limitations. The broker can run within the Tailkey checkout on the Windows PC or a separate server. It is not deployed and not yet integration-tested. `start-internet.cmd` requires private service configuration first. Internet mode binds the local controller to loopback only.

The optional `--public-url https://your-test-host.example` uses an exact HTTPS origin for phone invitations and origin checks. You must separately provide a trusted HTTPS reverse proxy for the mobile page and signaling. No Cloudflare integration, tunnel executable, cloud account, or hosted service is bundled or started.

For STUN/TURN, place an `iceServers` array using browser RTCIceServer fields (`urls`, optional `username` and `credential`) in the ignored `tailkey.internet.local.json` file at the repository root. Use short-lived TURN credentials, never a provider API key. These connection credentials are shared only with a valid invitation holder. The default has no external ICE service. Without configured STUN/TURN and reachable HTTPS signaling, this does not deliver general 4G connectivity.

Neither the private controller URL nor the code should be shared publicly. HTTPS signaling relies on the selected service operator; this revision does not implement an independent cryptographic identity check against a malicious signaling operator.

iPad Safari, separate-network 4G connectivity and mobile background behavior still require physical-device checks. Native-peer and desktop browser checks cannot establish general Safari compatibility.
