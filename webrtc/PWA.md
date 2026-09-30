# PWA prototype and test results

The exported `tools/tailkey-web/` distribution now includes a Web App Manifest, icons and a Service Worker. The worker caches a fixed list of application files, including the tailcat WASM module. It never caches API responses, controller pages, pairing codes or invitation-specific navigation URLs. The installed start URL contains no invitation. Updates wait until existing app tabs close so an ongoing pairing is not replaced midway.

## Start and use

1. Provide this static distribution through a trusted HTTPS origin for the iPhone's first visit. A regular `http://192.168...` LAN URL cannot register this Service Worker. Desktop localhost is a special secure-context exception, not an exception available when the phone opens the PC's LAN IP.
2. Wait for **離線鍵盤已儲存** before closing the page. On iPhone, use Safari's Share menu to add it to the Home Screen.
3. Start `start-tailcat.cmd` on Windows, and generate a new invitation on the desktop controller.
4. Open the installed PWA and paste the full new mobile invitation into **新配對網址**. The PWA stays on its own origin and extracts only the ephemeral tailcat address and invitation token. It does not visit the pasted site's host. Controller URLs are rejected.
5. Enter the desktop's six-digit code when prompted. Select the Windows app which should receive keys.

The app shell can start while its original website is unreachable, but tailcat signaling and WebRTC still need Internet connectivity. It does not work as a remote keypad in airplane mode. A cleared/evicted browser cache requires downloading the app again. An expired or consumed invitation cannot be reused. iPhone's PWA may have separate storage from Safari; confirm its saved state after launching from the Home Screen.

The local `start-tailcat.cmd` mobile page also includes this PWA support and shows an HTTPS requirement when opened through ordinary LAN HTTP. It remains usable for the existing same-Wi-Fi pairing. No website was published and no certificates, router rules or Funnel settings were changed.

## Tests performed on 2026-09-30

- Three existing native-peer WebRTC integration tests passed after the PWA change: approval/code gate, replay/invalid key protection, invitation expiry/origin checks and heartbeat teardown.
- JavaScript syntax checks passed for the mobile script, Service Worker and PWA registration script.
- A desktop browser opened the static distribution at localhost port 8870 and completed caching.
- The static HTTP server was then shut down. Reloading the page still displayed the keypad and invitation form from the Service Worker cache.
- The offline shell rejected a desktop-controller-style URL rather than navigating to it.
- A separate Windows dry-run receiver at localhost port 8871 started the real bundled tailcat helper with DERP connectivity. The offline shell accepted a fresh invitation, used its cached WASM to exchange signaling over tailcat and then established a WebRTC direct DataChannel.
- Entering the displayed code enabled the keypad. A Backspace press increased the dry-run receiver's accepted count from zero to one. No real Windows keyboard injection occurred.
- Mobile-side disconnection disabled the keys and restored the new-invitation form.

This establishes desktop cache loading plus a real tailcat-to-WebRTC integration on one computer. It does not establish cross-network NAT traversal, iPhone standalone installation, mobile-cache retention or carrier 4G connectivity. Those need a trusted HTTPS bootstrap and physical-phone testing. Temporary test servers were shut down after the checks.
