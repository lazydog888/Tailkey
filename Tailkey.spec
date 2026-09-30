# Build a portable folder. Only explicit public assets are bundled.
from pathlib import Path
from importlib.metadata import distributions
from PyInstaller.utils.hooks import collect_submodules
root = Path(SPECPATH)
datas = [(str(root / "static"), "static")]
for name in ("host.html", "host.js", "mobile.js", "prototype.css", "tailcat_transport.js"):
    datas.append((str(root / "webrtc" / name), "webrtc"))
datas += [(str(root / "tools/tailkey-web"), "tools/tailkey-web"),
          (str(root / "tools/tailcat-web/main.wasm.gz"), "tools/tailcat-web"),
          (str(root / "tools/tailcat-web/wasm_exec.js"), "tools/tailcat-web")]
for distribution in distributions():
    for file in distribution.files or []:
        if any(word in file.name.lower() for word in ("license", "copying", "notice")):
            path = distribution.locate_file(file)
            if path.is_file():
                datas.append((str(path), "licenses/" + distribution.metadata["Name"]))
python_license = Path(__import__('sys').base_prefix) / "LICENSE.txt"
if python_license.exists():
    datas.append((str(python_license), "licenses/Python"))
a = Analysis([str(root / "launcher.py")], pathex=[str(root), str(root / "webrtc")],
    binaries=[(str(root / "tools/tailkey-tailcat.exe"), "tools")], datas=datas,
    hiddenimports=["app", "tailcat", "internet", "qrcode.image.svg"] + collect_submodules("av"),
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Tailkey", debug=False,
    bootloader_ignore_signals=False, strip=False, upx=False, console=True)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Tailkey")
