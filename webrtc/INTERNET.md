# Internet signaling implementation (not deployed)

The code includes a provider-independent signaling broker and an outbound Windows client. A phone opens the broker's HTTPS page. Windows connects to the broker via WSS; its local controller stays on localhost. The broker exchanges ICE settings and SDP only. Pairing codes and keys travel over the WebRTC DataChannel. A trusted broker is still required: this prototype does not authenticate SDP fingerprints independently of the broker.

## What is ready / what is missing

- `start-webrtc.cmd`: same-Wi-Fi version, reported working by the user on iPhone and via phone hotspot on 2026-09-30. Hotspot success is not proof of connectivity between separate carrier/home networks.
- `start-internet.cmd`: Windows Internet-mode entry point, using the ignored `tailkey.internet.local.json` configuration.
- `webrtc/broker.py`: service which can run on the same computer or on a separate public server. It never imports the Windows injector and requires only `broker-requirements.txt` on Linux servers.
- Neither the broker nor STUN/TURN has been deployed. This revision has not been tested across 4G, and does not yet provide an installer or bundled hosting.
- No Cloudflare integration, tunnel tool, VPN installation or cloud account is required by the code. Reachable HTTPS/WSS signaling and suitable ICE infrastructure remain necessary for this architecture.

## Service operator setup

Use a valid public TLS certificate and a DNS name reachable from the phone. A server on the Windows PC still needs reachable public IPv4/IPv6 and applicable router/firewall rules; carrier-grade NAT may prevent inbound connections. Starting a local server alone does not create public reachability.

1. Install `webrtc/broker-requirements.txt` on the server.
2. Set `TAILKEY_BROKER_HOST_KEY` to a generated random secret of at least 32 characters. Do not place the secret in source or command-line arguments. This is an operator credential for the private prototype, not a public customer-account design.
3. Run the broker behind a local HTTPS reverse proxy, forwarding WebSocket upgrades and retaining the public Host header:

   `python webrtc/broker.py --origin https://pair.example.com`

   The default backend binds only `127.0.0.1:8780`. The HTTPS proxy must connect from that same machine. Alternatively, let the broker terminate TLS itself with a valid certificate:

   `python webrtc/broker.py --origin https://pair.example.com --bind 0.0.0.0 --port 443 --tls-cert /path/fullchain.pem --tls-key /path/privkey.pem`

   Windows operators may use `start-broker.cmd` with the same arguments. This starts Tailkey's own server without needing a separate proxy executable when native TLS is configured. Certificate issuance/renewal and network routing must still be arranged by the operator.

4. Apply request/connection limits at the public edge. This small prototype caps authenticated hosts at 32, pending offers at one per host, HTTP/WS payloads at 64 KiB and publications at one per second. It is not a public multi-tenant service.

No access log is enabled by the program. Avoid body/Authorization logging at the HTTPS proxy. The URL fragment contains a one-use invite; codes, full SDP, credentials and controller URLs must not be published.

## STUN and TURN

For self-hosted coturn, configure its REST shared secret and set these broker environment variables:

- `TAILKEY_TURN_SECRET`: the same coturn shared secret (server only).
- `TAILKEY_TURN_URLS`: comma-separated TURN URLs, for example `turn:turn.example.com:3478,turns:turn.example.com:5349`.
- `TAILKEY_STUN_URLS`: optional comma-separated STUN URLs.

The broker generates distinct time-limited TURN credentials per invitation with a one-hour lifetime. Those credentials are sent to the invited phone and Windows, as required for ICE; the shared secret is never sent to them. A relay session may need re-pairing when the credentials expire. Direct connections do not eliminate the initial signaling dependency. TCP/TLS TURN support is configured via URLs; deployment must open the actual coturn transport and relay ports. This project does not bundle or configure coturn.

Alternatively, trusted operators can set an `iceServers` array in the Windows configuration using short-lived credentials from another provider. Never put provider administration/API keys in that array. With no STUN/TURN configured, only local candidates are gathered and general 4G connectivity is not assured.

## Windows client setup

Copy `webrtc/internet.example.json` to `tailkey.internet.local.json` in the repository root. Replace `brokerUrl` and `hostKey` with your service details. This private file is ignored by Git.

Run `start-internet.cmd`. The desktop controller generates the QR code. Turn off phone Wi-Fi, scan/open the invite, then enter the desktop's six-digit code on the phone. The code is never included in the broker protocol or phone HTTP API. Three wrong entries end the session.

The app retries broker connections with a delay up to 30 seconds. A lost broker connection closes the local pairing and discards invitations; create a new invitation after reconnection. There is no automatic restoration of keyboard access. Invites expire after 120 seconds and are consumed before negotiating the first offer. Leaving the phone page or losing DataChannel heartbeats stops input.

The phone shows connection type (direct or TURN) and approximate heartbeat round-trip latency. A timeout suggesting TURN does not prove that NAT is the cause; DNS, TLS, UDP filtering and service availability can also prevent pairing.

## Alternative: tailcat browser transport

The tailcat native library can perform NAT traversal and fall back to DERP. Its current browser/WASM implementation uses DERP only. That may reduce infrastructure operated by this project by relying on tailcat's external DERP services and a hosted static browser page, but would replace the WebRTC transport and requires a separate integration. None of the files here claim to implement that integration. See the upstream README and WebRTC issue #4.
