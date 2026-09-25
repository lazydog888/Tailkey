const connection = document.querySelector("#connection");
const connectionLabel = document.querySelector("#connection-label");
const toast = document.querySelector("#toast");
const disconnectButton = document.querySelector("#disconnect-button");
const keys = [...document.querySelectorAll(".key")];

let connectionState = "connecting";
let healthFailures = 0;
let healthPending = false;
let activePointer = null;
let activeKey = null;
let repeatDelay = 0;
let repeatTimer = 0;
let pressPending = false;
let tapQueueRunning = false;
const tapQueue = [];
const TAP_QUEUE_LIMIT = 4;
const TAP_QUEUE_TTL_MS = 1500;
let toastTimer = 0;

function setConnection(state) {
  if (state === "disconnected") {
    stopRepeat();
    tapQueue.length = 0;
  }
  connectionState = state;
  connection.dataset.state = state;
  connectionLabel.textContent = {
    connecting: "連線中",
    connected: "已連線",
    disconnected: "未連線",
  }[state];
  for (const key of keys) key.disabled = state !== "connected";
  disconnectButton.disabled = state !== "connected";
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("visible"), 2200);
}

async function checkHealth() {
  if (healthPending) return;
  healthPending = true;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 1600);
  try {
    const response = await fetch("/api/health", { cache: "no-store", signal: controller.signal });
    if (!response.ok) throw new Error("health request failed");
    healthFailures = 0;
    setConnection("connected");
  } catch {
    healthFailures += 1;
    if (healthFailures >= 2) setConnection("disconnected");
  } finally {
    clearTimeout(timeout);
    healthPending = false;
  }
}

async function sendPressNow(name) {
  if (connectionState !== "connected" || pressPending) return false;
  pressPending = true;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 2200);
  try {
    const response = await fetch("/api/press", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: name }),
      cache: "no-store",
      signal: controller.signal,
    });
    if (response.status === 429) {
      showToast("輸入太快，請稍候一下");
      return false;
    }
    if (response.status === 500) {
      showToast("Windows 沒有接受這個按鍵");
      return false;
    }
    if (!response.ok) {
      showToast(response.status === 403 ? "此網址未列入允許來源" : "按鍵傳送失敗");
      return false;
    }
    return true;
  } catch {
    healthFailures = Math.max(healthFailures, 2);
    setConnection("disconnected");
    showToast("連線中斷，未送出的按鍵已清除");
    return false;
  } finally {
    clearTimeout(timeout);
    pressPending = false;
    if (tapQueue.length && !tapQueueRunning && connectionState === "connected") {
      void drainTapQueue();
    }
  }
}

function enqueueTap(name) {
  if (connectionState !== "connected") return;
  if (tapQueue.length + Number(pressPending) >= TAP_QUEUE_LIMIT) {
    showToast("連按太快，部分按鍵未加入佇列");
    return;
  }
  tapQueue.push({ name, expiresAt: Date.now() + TAP_QUEUE_TTL_MS });
  void drainTapQueue();
}

async function drainTapQueue() {
  if (tapQueueRunning || pressPending || connectionState !== "connected") return;
  tapQueueRunning = true;
  try {
    while (tapQueue.length && connectionState === "connected") {
      const next = tapQueue.shift();
      if (Date.now() > next.expiresAt) {
        showToast("等待過久，未送出的按鍵已略過");
        continue;
      }
      if (!(await sendPressNow(next.name))) {
        tapQueue.length = 0;
        break;
      }
    }
  } finally {
    tapQueueRunning = false;
  }
}

async function stopTailkey() {
  if (connectionState !== "connected") return;
  const confirmed = window.confirm(
    "要停止 Windows 上的 Tailkey 服務嗎？所有 iPad/iPhone 都會斷線。要重新使用，請在 Windows 上啟動 start.cmd。",
  );
  if (!confirmed) return;

  disconnectButton.disabled = true;
  stopRepeat();
  tapQueue.length = 0;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 3000);
  try {
    const response = await fetch("/api/shutdown", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "shutdown" }),
      cache: "no-store",
      signal: controller.signal,
    });
    if (!response.ok) throw new Error("shutdown request failed");
    setConnection("disconnected");
    showToast("Tailkey 已停止；請在 Windows 上重新啟動才能連線");
  } catch {
    setConnection("disconnected");
    showToast("已送出停止要求；連線中斷，請確認 Windows 上的服務狀態");
  } finally {
    clearTimeout(timeout);
  }
}

function stopRepeat(pointerId = null) {
  if (pointerId !== null && pointerId !== activePointer) return;
  clearTimeout(repeatDelay);
  clearInterval(repeatTimer);
  repeatDelay = 0;
  repeatTimer = 0;
  if (activeKey) activeKey.classList.remove("pressed");
  activePointer = null;
  activeKey = null;
}

for (const key of keys) {
  key.addEventListener("pointerdown", (event) => {
    if (activePointer !== null || connectionState !== "connected") return;
    event.preventDefault();
    activePointer = event.pointerId;
    activeKey = key;
    key.setPointerCapture(event.pointerId);
    key.classList.add("pressed");
    enqueueTap(key.dataset.key);
    repeatDelay = setTimeout(() => {
      if (activePointer !== event.pointerId) return;
      repeatTimer = setInterval(() => {
        if (
          activePointer === event.pointerId &&
          !pressPending &&
          !tapQueueRunning &&
          tapQueue.length === 0
        ) {
          void sendPressNow(key.dataset.key);
        }
      }, 80);
    }, 400);
  });
  key.addEventListener("pointerup", (event) => stopRepeat(event.pointerId));
  key.addEventListener("pointercancel", (event) => stopRepeat(event.pointerId));
  key.addEventListener("lostpointercapture", (event) => stopRepeat(event.pointerId));
  key.addEventListener("click", (event) => {
    // Preserve keyboard activation without double-sending pointer-generated clicks.
    if (event.detail === 0) enqueueTap(key.dataset.key);
  });
}

disconnectButton.addEventListener("click", () => void stopTailkey());

window.addEventListener("blur", () => stopRepeat());
window.addEventListener("pagehide", () => stopRepeat());
document.addEventListener("visibilitychange", () => {
  if (document.hidden) stopRepeat();
});

setConnection("connecting");
void checkHealth();
setInterval(checkHealth, 2000);
