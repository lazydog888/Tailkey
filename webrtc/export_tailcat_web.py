"""Create the static mobile distribution; no secrets or local controller code."""
from pathlib import Path
import shutil
import struct
import zlib
import hashlib

ROOT = Path(__file__).resolve().parent
DEST = ROOT.parent / "tools/tailkey-web"
DEST.mkdir(parents=True, exist_ok=True)
html = (ROOT.parent / "static/index.html").read_text(encoding="utf-8")
html = html.replace('src="/app.js"', 'src="./wasm_exec.js" defer></script><script src="./tailcat_transport.js" defer></script><script src="./pwa.js" defer></script><script src="./mobile.js"')
# Static hosts (e.g. GitHub Pages) cannot send headers; keep in sync with the tailcat CSP in app.py.
csp = ("default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; img-src 'self' blob:; "
       "connect-src 'self' https://tailcat.dev https://*.ipn.dev wss://*.ipn.dev; object-src 'none'; base-uri 'none'")
html = html.replace('<meta charset="utf-8" />', f'<meta charset="utf-8" />\n    <meta http-equiv="Content-Security-Policy" content="{csp}" />')
html = html.replace('</head>', '<link rel="manifest" href="./manifest.webmanifest"><link rel="apple-touch-icon" href="./icon-192.png"></head>')
html = html.replace('src="/i18n.js"', 'src="./i18n.js"')
html = html.replace('<link rel="stylesheet" href="/style.css" />', '<link rel="stylesheet" href="./style.css" /><link rel="stylesheet" href="./prototype.css" />')
html = html.replace('停止 Tailkey 連線', '中斷這次連線').replace('由 Tailscale 私密連線', 'WebRTC 直連試作').replace('TAILNET', 'WEBRTC')
html = html.replace('<section class="keypad-card"', '<p id="pair-status" role="status">正在配對</p><section class="keypad-card"')
(DEST / "index.html").write_text(html, encoding="utf-8")
for name in ("mobile.js", "tailcat_transport.js", "prototype.css", "pwa.js", "sw.js", "manifest.webmanifest", "icon.svg"):
    shutil.copyfile(ROOT / name, DEST / name)
shutil.copyfile(ROOT.parent / "static/style.css", DEST / "style.css")
shutil.copyfile(ROOT.parent / "static/i18n.js", DEST / "i18n.js")
for name in ("wasm_exec.js", "main.wasm.gz"):
    shutil.copyfile(ROOT.parent / "tools/tailcat-web" / name, DEST / name)
shutil.copyfile(ROOT.parent / "tools/tailcat-src/LICENSE", DEST / "TAILCAT-LICENSE.txt")

def icon_png(size):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            px, py = x * 192 / size, y * 192 / size
            border = 45 <= px <= 147 and 29 <= py <= 163 and not (53 < px < 139 and 37 < py < 155)
            key = any(abs(px - cx) < 9 and abs(py - cy) < 6 for cx in (74, 118) for cy in (62, 94, 126))
            row.extend((172, 232, 197) if border or key else (12, 16, 23))
        rows.append(row)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(b"".join(rows))) + chunk(b"IEND", b"")

for size in (192, 512):
    (DEST / f"icon-{size}.png").write_bytes(icon_png(size))
version_files = sorted(path for path in DEST.iterdir() if path.is_file() and path.name not in ("sw.js", "TAILCAT-LICENSE.txt"))
version = hashlib.sha256(b"".join(path.read_bytes() for path in version_files)).hexdigest()[:16]
(DEST / "sw.js").write_text((ROOT / "sw.js").read_text(encoding="utf-8").replace("tailkey-pwa-v1", f"tailkey-pwa-{version}"), encoding="utf-8")
print("Static browser distribution created at tools/tailkey-web (no controller or private configuration).")
