# Tailkey portable / 可攜版

## 繁體中文

1. 解壓縮整個資料夾，雙擊 `Tailkey.exe`。電腦會自動開啟配對頁面，不需要選模式。
2. 手機與電腦連同一個 Wi-Fi（或電腦連手機熱點），掃 QR code，輸入電腦上的六位配對碼。
3. 電腦點選要輸入的程式，手機即可當數字鍵盤。配對成功時 Windows 會跳出通知；若不是你本人，請在配對頁按「中斷連線」。
4. 閒置 5 分鐘會自動中斷，需重新掃碼。頁面右上角可切換繁體中文／English。服務視窗按 Ctrl+C 可停止。

程式會自動選擇連線方式：能連上網際網路時用 tailcat 交換配對資訊（依賴外部 DERP/STUN），否則改用純同 Wi-Fi 模式。要強制只用同 Wi-Fi 模式，請用命令列執行 `Tailkey.exe --lan`。手機跨網路（4G）使用還需要可信的 HTTPS 鍵盤頁面，目前仍待實測。原本 Tailscale 版本保留在原始碼的 `start.cmd`。

不需要另裝 Python、Node.js、Go 或 Tailscale。接收端目前只支援 Windows x64。請保留整個資料夾，不能只搬走 exe。請勿分享電腦控制網址；邀請是短效且一次性的。同 Wi-Fi 配對未加密保護網頁本身，請只在自己家或信任的網路使用。

此程式未做 Windows 程式碼簽署，系統可能顯示發行者不明。下載後可比對發行頁公布的 SHA-256：在 PowerShell 執行 `Get-FileHash Tailkey-Windows-x64.zip`，結果需與 `SHA256SUMS.txt` 相同。不要以系統管理員執行。NumPad 的數字輸入受 Windows NumLock 狀態影響。

## English

1. Extract the entire folder and double-click `Tailkey.exe`. The desktop pairing page opens automatically; there is no mode menu.
2. Put the phone on the same Wi-Fi as the PC (or connect the PC to the phone's hotspot), scan the QR code and enter the six-digit code shown on the PC.
3. Focus the Windows application that should receive input, then use the phone keypad. Windows shows a notification when a phone pairs; if it was not you, click Disconnect on the pairing page.
4. Five idle minutes end the session automatically; scan a new code to continue. Switch between English and Traditional Chinese with the page's language selector. Press Ctrl+C in the service window to stop.

Tailkey picks the connection method itself: with Internet access it exchanges pairing data over tailcat (external DERP/STUN services), otherwise it falls back to plain same-Wi-Fi mode. Run `Tailkey.exe --lan` to force same-Wi-Fi mode. Using a phone on another network (4G) additionally needs a trusted HTTPS keypad page and remains unverified. The original Tailscale version is available in the source through `start.cmd`.

No separate Python, Node.js, Go or Tailscale installation is required. The receiver supports Windows x64 only. Keep the complete folder, including `_internal`. Never share the desktop controller URL. Invitations expire and can be used once. Same-Wi-Fi pairing does not protect the web page itself; use it only on home or other trusted networks.

The executable is unsigned. Verify a download against the published SHA-256: run `Get-FileHash Tailkey-Windows-x64.zip` in PowerShell and compare with `SHA256SUMS.txt`. Run as your normal Windows user, not Administrator. NumPad digit behavior depends on Windows NumLock state.
