/* Presentation only: pairing, transport and key validation stay language-neutral. */
(() => {
  const translations = {
    "Tailkey · 配對": "Tailkey · Pairing",
    "手機掃碼後，請在手機輸入電腦顯示的六位配對碼。": "Scan with your phone, then enter the six-digit code shown on the PC.",
    "預設為同 Wi-Fi 原型，請使用可信任的網路。": "Same-Wi-Fi mode is intended for trusted networks.",
    "準備中": "Preparing",
    "限時配對 QR code": "Temporary pairing QR code",
    "配對網址": "Pairing URL",
    "複製網址": "Copy URL",
    "請在你的手機輸入這個六位配對碼。輸錯三次會取消連線。": "Enter this six-digit code on your phone. Three incorrect attempts end the connection.",
    "產生新的邀請": "New invitation",
    "中斷連線": "Disconnect",
    "配對成功後，請在 Windows 點選要接收按鍵的程式。關閉服務視窗或按 Ctrl+C 可停止服務。": "After pairing, focus the Windows app that should receive keys. Close the service window or press Ctrl+C to stop.",
    "Tailkey 首頁": "Tailkey home",
    "數字鍵盤": "Number keypad",
    "按鍵會送到 Windows 目前作用中的程式": "Keys go to the active Windows application",
    "遠端數字鍵盤": "Remote number keypad",
    "Backspace，刪除一個字元": "Backspace, delete one character",
    "NumPad 除": "NumPad divide", "NumPad 乘": "NumPad multiply",
    "NumPad 減": "NumPad subtract", "NumPad 加": "NumPad add", "NumPad 小數點": "NumPad decimal",
    "數字與運算鍵": "Numbers and operators", "按住可連續輸入": "Hold to repeat",
    "停止 Tailkey 連線": "Stop Tailkey", "中斷這次連線": "Disconnect this session",
    "Windows 桌面": "Windows desktop", "由 Tailscale 私密連線": "Private connection via Tailscale",
    "WebRTC 直連試作": "WebRTC direct prototype",
    "WebRTC 直接連線": "WebRTC direct connection",
    "配對服務尚未連線，請稍後產生新邀請": "Pairing service is offline. Try a new invitation shortly.",
    "操作失敗，請重新啟動服務開啟電腦配對頁面": "Operation failed. Restart Tailkey to reopen the desktop pairing page.",
    "請產生邀請": "Create an invitation", "等待手機掃碼": "Waiting for your phone to scan",
    "正在建立 WebRTC 連線": "Establishing WebRTC connection",
    "請在手機輸入下方配對碼": "Enter the code below on your phone",
    "已配對，可以輸入": "Paired — keypad ready",
    "連線已結束，請產生新的邀請": "Session ended. Create a new invitation.",
    "邀請已過期，請產生新的邀請": "Invitation expired. Create a new invitation.",
    "測試模式：不會輸入 Windows": "Dry run: no Windows input",
    "手機輸入正確配對碼後會輸入 Windows 目前作用中的程式": "After the phone enters the correct code, keys go to the active Windows app.",
    "網際網路配對服務已連線": "Internet pairing service connected",
    "正在重新連接配對服務，請稍後產生新邀請": "Reconnecting to pairing service. Create a new invitation shortly.",
    "同 Wi-Fi 模式": "Same-Wi-Fi mode",
    "邀請還有 ": "Invitation expires in ", " 秒失效，成功使用後即作廢": " seconds and is single-use",
    "配對碼：": "Pairing code: ", "本次啟動已接受 ": "Accepted ", " 次按鍵": " key presses this run",
    "已複製": "Copied", "請複製選取的網址": "Copy the selected URL",
    "請使用 start-webrtc.cmd 開啟電腦配對頁面": "Start Tailkey on the PC to open the pairing page",
    "貼上電腦產生的新配對網址": "Paste a new invitation URL from your PC",
    "新配對網址": "New invitation URL", "連接電腦": "Connect to PC",
    "請貼上 start-tailcat.cmd 產生的完整手機配對網址，勿貼電腦控制網址。": "Paste the full mobile invitation from Tailcat mode, not the desktop controller URL.",
    "TURN 中繼": "TURN relay", "WebRTC 直連": "WebRTC direct", "延遲約 ": "Latency about ",
    "輸入電腦上的六位配對碼": "Enter the six-digit code shown on the PC",
    "電腦配對碼": "PC pairing code", "配對": "Pair",
    "連線已結束，請在電腦產生新的邀請": "Session ended. Create a new invitation on the PC.",
    "連線沒有回應，已停止輸入": "Connection unresponsive. Input stopped.",
    "等待上一個按鍵回應，請稍後再按": "Waiting for the previous key acknowledgement. Try again shortly.",
    "按鍵傳送逾時，已停止輸入": "Key acknowledgement timed out. Input stopped.",
    "已配對 · 按鍵透過 WebRTC 傳送到電腦": "Paired · Keys are sent to the PC over WebRTC",
    "等待配對碼": "Waiting for pairing code", "請查看電腦畫面，輸入配對碼": "Enter the code shown on your PC",
    "配對碼錯誤，還有 ": "Incorrect code. ", " 次機會": " attempts left",
    "配對碼輸錯三次，請在電腦產生新邀請": "Three incorrect codes. Create a new invitation on the PC.",
    "按鍵等待過久，已略過": "Stale key skipped", "輸入太快，請稍後": "Input too fast. Please wait.",
    "Windows 未接受按鍵": "Windows did not accept the key", "尚未獲得電腦允許": "Not paired with the PC yet",
    "按鍵未送出": "Key not sent", "網路資訊收集逾時": "Network discovery timed out",
    "請掃描電腦顯示的新 QR code，或開啟完整配對網址": "Scan a new PC QR code or open the complete invitation URL",
    "此瀏覽器無法使用 WebRTC，請更新 Safari 或 Chrome": "WebRTC is unavailable. Update Safari or Chrome.",
    "正在透過 tailcat 建立配對通道，接著嘗試 WebRTC 直連": "Establishing tailcat signaling, then attempting WebRTC direct connection",
    "此頁面沒有 tailcat 支援，請使用完整 Tailkey 瀏覽器版本": "This page lacks tailcat support. Use the complete Tailkey browser distribution.",
    "邀請已過期或使用過，請重新掃碼": "Invitation expired or already used. Scan a new code.",
    "WebRTC 連線中斷，請重新配對": "WebRTC disconnected. Pair again.",
    "無法完成配對": "Pairing failed", "配對等待逾時，請產生新邀請": "Pairing timed out. Create a new invitation.",
    "無法跨網路連線，此網路可能需要 TURN 中繼；請在電腦產生新邀請": "Direct connection failed. This network may require TURN. Create a new invitation on the PC.",
    "頁面已離開前景，已停止輸入；請重新配對": "Page left the foreground. Input stopped; pair again.",
    "閒置超過 5 分鐘，已自動中斷；請在電腦產生新邀請": "Idle for 5 minutes, disconnected automatically. Create a new invitation on the PC.",
    "連線失敗": "Connection failed", "正在配對": "Pairing",
    "未連線": "Disconnected", "已連線": "Connected", "連線中": "Connecting",
    "離線鍵盤需透過 HTTPS 安裝；目前仍可使用一般網頁配對。": "Offline installation requires HTTPS. Regular webpage pairing is still available.",
    "正在儲存離線鍵盤與連線模組…": "Saving the offline keypad and connection module…",
    "離線鍵盤已儲存；iPhone 可用分享選單加入主畫面。配對仍需要網路。": "Offline keypad saved. On iPhone, use Share → Add to Home Screen. Pairing still requires network access.",
    "新版鍵盤已下載，結束配對並關閉所有 Tailkey 頁面後再開啟即可更新。": "Update downloaded. End pairing and close all Tailkey pages, then reopen to update.",
    "離線鍵盤儲存失敗，請確認所有檔案可下載後重新開啟。": "Offline installation failed. Check that all files are available, then reopen.",
    "tailcat 載入逾時": "tailcat loading timed out",
    "找不到 tailcat 模組，請完成瀏覽器資產建置": "tailcat module missing. Build the browser assets first.",
    "tailcat 模組未就緒": "tailcat module is not ready", "tailcat 配對通道已中斷": "tailcat signaling disconnected",
    "配對回應過大": "Pairing response too large",
    "邀請已過期、使用過或連線失敗，請重新掃碼": "Invitation expired, used, or connection failed. Scan a new code.",
    "輸入太快，請稍候一下": "Input too fast. Please wait.", "Windows 沒有接受這個按鍵": "Windows did not accept this key",
    "此網址未列入允許來源": "This URL is not an allowed origin", "按鍵傳送失敗": "Key transmission failed",
    "連線中斷，未送出的按鍵已清除": "Disconnected. Unsent keys cleared.",
    "連按太快，部分按鍵未加入佇列": "Tapping too fast. Some keys were not queued.",
    "等待過久，未送出的按鍵已略過": "Queue timed out. Unsent keys skipped.",
    "要停止 Windows 上的 Tailkey 服務嗎？所有 iPad/iPhone 都會斷線。要重新使用，請在 Windows 上啟動 start.cmd。": "Stop the Windows Tailkey service? All phones and tablets will disconnect. Run start.cmd on Windows to restart.",
    "Tailkey 已停止；請在 Windows 上重新啟動才能連線": "Tailkey stopped. Restart it on Windows to reconnect.",
    "已送出停止要求；連線中斷，請確認 Windows 上的服務狀態": "Stop requested. Disconnected; check the Windows service status."
  };
  let language;
  try { language = localStorage.getItem("tailkey-language"); } catch {}
  language ||= navigator.language.toLowerCase().startsWith("zh") ? "zh-Hant" : "en";
  if (!["en", "zh-Hant"].includes(language)) language = "en";
  const entries = Object.entries(translations).sort((a, b) => b[0].length - a[0].length);
  function translate(value) {
    if (language !== "en") return value;
    if (translations[value]) return translations[value];
    for (const [source, target] of entries) value = value.split(source).join(target);
    return value;
  }
  window.TailkeyI18n = { translate };
  document.documentElement.lang = language;
  function visit(root) {
    if (root.nodeType === Node.TEXT_NODE) {
      if (!root.parentElement?.closest("script,style,textarea,select")) {
        const value = translate(root.nodeValue);
        if (value !== root.nodeValue) root.nodeValue = value;
      }
      return;
    }
    if (root.nodeType !== Node.ELEMENT_NODE) return;
    for (const attr of ["aria-label", "alt", "placeholder", "title"]) {
      if (root.hasAttribute(attr)) {
        const old = root.getAttribute(attr), value = translate(old);
        if (old !== value) root.setAttribute(attr, value);
      }
    }
    for (const child of root.childNodes) visit(child);
  }
  function start() {
    const selector = document.createElement("select");
    selector.className = "language-selector";
    selector.setAttribute("aria-label", "Language / 語言");
    selector.innerHTML = '<option value="zh-Hant">繁體中文</option><option value="en">English</option>';
    selector.value = language;
    selector.onchange = () => {
      try { localStorage.setItem("tailkey-language", selector.value); }
      catch { selector.value = language; return; }
      window.dispatchEvent(new Event("tailkey-language-change"));
      // Reload closes the existing connection; never silently restore pairing.
      location.reload();
    };
    (document.querySelector(".topbar") || document.querySelector("main")).prepend(selector);
    visit(document.documentElement);
    new MutationObserver((records) => {
      for (const record of records) {
        if (record.type === "characterData") visit(record.target);
        else if (record.type === "attributes") visit(record.target);
        else for (const node of record.addedNodes) visit(node);
      }
    }).observe(document.documentElement, {subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ["aria-label", "alt", "placeholder", "title"]});
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
