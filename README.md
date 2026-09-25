# Tailkey

Use an iPhone or iPad as a remote NumPad for the Windows app that is currently in front.

## Start the keypad

Double-click `start.cmd`, or run `python server.py` from this folder. Leave the window open while using Tailkey. It runs as your signed-in Windows user so `SendInput` can reach the interactive desktop; do not run it as a Windows service or as Administrator.

The server listens only on `127.0.0.1:8765`. Open `http://127.0.0.1:8765` on the PC to use the local page.

`start.cmd` optionally loads `tailkey.local.cmd`, a local-only configuration file ignored by Git. It contains the exact browser origins allowed to send keys. The included local file allows this PC and the current Tailscale Serve URL; edit it if the tailnet URL or HTTPS port changes.

## Use it over Tailscale

Once the local page is running, configure Tailscale Serve:

```powershell
tailscale serve --bg --https=8443 8765
tailscale serve status
```

Tailscale Serve HTTPS requires HTTPS certificates to be enabled for the tailnet in the admin console under **DNS → HTTPS Certificates**. The `--bg` command may configure the route without opening the setup prompt. If the HTTPS URL fails during its TLS handshake, check this tailnet setting and then apply the Serve command again.

Open `https://<this-device>.ts.net:8443` in Safari on an iPhone or iPad connected to the same tailnet. The dedicated HTTPS port leaves other Serve routes on 443 and 8080 untouched. Serve applies the tailnet's existing access rules. Anyone in that tailnet who can reach this Windows device may be able to send keypad input, so restrict access with your tailnet's Grants or ACLs if other people or devices are present. Do not use Funnel; Funnel makes a service publicly reachable.

Use **停止 Tailkey 連線** on the keypad page to stop the Windows server for every device. Confirm the prompt; restart it on Windows with `start.cmd`. The Tailscale Serve route remains configured and will work again when the server starts. You can also stop the local server by focusing its console and pressing Ctrl+C. To remove the Tailscale Serve route, run:

```powershell
tailscale serve reset
```

This resets all Tailscale Serve routes configured on this device, not only Tailkey's route.

Tailscale notes that the machine's full `*.ts.net` DNS name is published in public Certificate Transparency records when HTTPS certificates are enabled; avoid sensitive device names.

## What it does

- Sends NumPad virtual keys 0–9, `/`, `*`, `−`, `+`, `.`, NumPad Enter, and Backspace.
- Each request sends key-down and key-up together. Holding a button repeats complete presses after a short delay. Short taps have a small, expiring queue; repeats are never queued, and disconnection clears pending taps and stops repeats.
- A request already in flight may still complete after the browser times out or the button is released; the browser cannot retract a request already received by Windows.
- Shows connection status from the local server's health endpoint.
- Uses only Python's standard library and the Windows `SendInput` API.

The active Windows app receives the keys. Programs running at a higher integrity level, the lock screen, UAC secure desktop, and software that rejects injected input may not accept them. `SendInput` creates Windows synthetic keyboard input, not USB HID hardware input.

## Troubleshooting history

### 2026-09-25 — `origin_denied` after a Tailscale hostname change

The keypad page loaded, but pressing a key returned `origin_denied`. The local origin allowlist still contained the device's previous MagicDNS HTTPS hostname after the Tailscale device name changed. The page could load while POST requests were rejected because their browser origin no longer matched the allowlist.

Fix: update the exact HTTPS origin in the local-only `tailkey.local.cmd`, keep the localhost origins, and restart Tailkey with `start.cmd`. Do not commit this local file: it contains the device-specific Tailscale hostname. The incident record intentionally omits the actual hostname and tailnet name.

## Network and input limits

The backend accepts only JSON requests whose exact `Origin` and `Host` match the configured allowlist; it ignores `X-Forwarded-Host`. It caps request bodies at 256 bytes, rate-limits presses to 20 per second, limits concurrent clients, and closes slow connections after a timeout. It has no CORS support, arbitrary key codes, macros, or shell commands. The page and API share one origin, so no WebSocket or extra package is needed.

Tailscale Serve references:

- [Serve](https://tailscale.com/docs/features/tailscale-serve)
- [Serve CLI](https://tailscale.com/docs/reference/tailscale-cli/serve)
- [Enabling HTTPS](https://tailscale.com/docs/how-to/set-up-https-certificates)
