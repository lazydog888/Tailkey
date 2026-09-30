const pwaStatus = document.createElement("p");
pwaStatus.className = "notice";
pwaStatus.id = "pwa-status";
document.querySelector("#pair-status").before(pwaStatus);

async function setupPWA() {
  if (!isSecureContext || !("serviceWorker" in navigator)) {
    pwaStatus.textContent = "離線鍵盤需透過 HTTPS 安裝；目前仍可使用一般網頁配對。";
    return;
  }
  pwaStatus.textContent = "正在儲存離線鍵盤與連線模組…";
  try {
    const registration = await navigator.serviceWorker.register("./sw.js");
    let readyTimeout;
    try {
      await Promise.race([navigator.serviceWorker.ready, new Promise((_, reject) => {
        readyTimeout = setTimeout(() => reject(new Error("Cache installation timed out")), 45000);
      })]);
    } finally { clearTimeout(readyTimeout); }
    pwaStatus.textContent = "離線鍵盤已儲存；iPhone 可用分享選單加入主畫面。配對仍需要網路。";
    registration.addEventListener("updatefound", () => {
      const worker = registration.installing;
      worker?.addEventListener("statechange", () => {
        if (worker.state === "installed" && navigator.serviceWorker.controller) {
          pwaStatus.textContent = "新版鍵盤已下載，結束配對並關閉所有 Tailkey 頁面後再開啟即可更新。";
        }
      });
    });
  } catch {
    pwaStatus.textContent = "離線鍵盤儲存失敗，請確認所有檔案可下載後重新開啟。";
  }
}
void setupPWA();
