# Tailkey portable / 可攜版

## 繁體中文

1. 解壓縮整個資料夾，雙擊 `Tailkey.exe`。
2. 選 1：同 Wi-Fi／手機熱點。電腦會開啟配對頁面。
3. 手機掃 QR code，輸入電腦上的六位配對碼。
4. 電腦點選要輸入的程式，手機即可當數字鍵盤。
5. 頁面右上角可切換繁體中文／English。服務視窗按 Ctrl+C 可停止。

不需要另裝 Python、Node.js、Go 或 Tailscale。接收端目前只支援 Windows x64。請保留整個資料夾，不能只搬走 exe。請勿分享電腦控制網址；邀請是短效且一次性的。

選 2 使用 tailcat + WebRTC 實驗模式。需要網際網路，依賴外部 DERP/STUN；手機跨網路使用還需要先取得可信 HTTPS 鍵盤頁面或已儲存的 PWA。此包沒有自動安裝憑證、建立公開網站或更改路由器。iPhone 4G 跨網路仍待實測。原本 Tailscale 版本保留在原始碼的 `start.cmd`。

此程式未做 Windows 程式碼簽署，系統可能顯示發行者不明。不要以系統管理員執行。NumPad 的數字輸入受 Windows NumLock 狀態影響。

## English

1. Extract the entire folder and double-click `Tailkey.exe`.
2. Choose 1 for the same Wi-Fi or a phone hotspot. The desktop pairing page opens.
3. Scan its QR code on your phone and enter the six-digit code shown on the PC.
4. Focus the Windows application that should receive input, then use the phone keypad.
5. Switch between English and Traditional Chinese using the page's language selector. Press Ctrl+C in the service window to stop.

No separate Python, Node.js, Go or Tailscale installation is required. The receiver supports Windows x64 only. Keep the complete folder, including `_internal`. Never share the desktop controller URL. Invitations expire and can be used once.

Option 2 is the tailcat + WebRTC experiment. It requires Internet access and external DERP/STUN services. A phone on another network still needs a trusted HTTPS keypad page or a previously saved PWA. This package does not install certificates, publish a website or change router settings. iPhone 4G connectivity remains unverified. The original Tailscale version is available in the source through `start.cmd`.

The executable is unsigned. Run as your normal Windows user, not Administrator. NumPad digit behavior depends on Windows NumLock state.
