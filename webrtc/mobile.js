const token = new URLSearchParams(location.hash.slice(1)).get("pair");
const usesTailcat = new URLSearchParams(location.hash.slice(1)).has("tc");
history.replaceState(null, "", location.pathname);
const keys = [...document.querySelectorAll(".key")];
const label = document.querySelector("#connection-label");
const indicator = document.querySelector("#connection");
const pairStatus = document.querySelector("#pair-status");
const disconnect = document.querySelector("#disconnect-button");
const toast = document.querySelector("#toast");
const inviteForm = document.createElement("form");
inviteForm.className = "pair-form";
inviteForm.id = "invite-form";
inviteForm.innerHTML = '<label for="new-invite">貼上電腦產生的新配對網址</label><textarea id="new-invite" rows="2" required autocomplete="off" autocapitalize="off" spellcheck="false" aria-label="新配對網址"></textarea><button type="submit">連接電腦</button><p id="invite-error" role="alert"></p>';
pairStatus.after(inviteForm);
inviteForm.hidden = Boolean(token);
inviteForm.onsubmit = (event) => {
  event.preventDefault();
  try {
    const value = document.querySelector("#new-invite").value.trim();
    const url = new URL(value);
    const params = new URLSearchParams(url.hash.slice(1));
    const nextToken = params.get("pair"), addr = params.get("tc");
    if (!/^https?:$/.test(url.protocol) || !/^[A-Za-z0-9_-]{40,64}$/.test(nextToken || "") || !/^tc[A-Za-z0-9_-]+$/.test(addr || "") || params.has("owner")) throw new Error();
    // Stay on the installed app's origin; the pasted URL is data, not a navigation destination.
    if (!ended) end();
    document.querySelector("#new-invite").value = "";
    location.replace(location.pathname + "#" + new URLSearchParams({pair:nextToken, tc:addr}));
    location.reload();
  } catch {
    document.querySelector("#invite-error").textContent = "請貼上 start-tailcat.cmd 產生的完整手機配對網址，勿貼電腦控制網址。";
  }
};
let pc, dc, approved = false, ended = false;
let signaling;
let active = null, repeatDelay, repeatTimer, heartbeat, approvalTimer, ackTimer, toastTimer;
let seq = 0, pingId = 0, pending = null, lastPong = 0, offset = 0;
const pings = new Map();
const networkStatus = document.createElement("p");
networkStatus.className = "notice";
pairStatus.after(networkStatus);
let connectionPath = "WebRTC", latency = 0, statsTimer;
async function connectionStats() {
  if (!pc || ended) return;
  try {
    const stats = await pc.getStats();
    let pair;
    stats.forEach((entry) => {
      if (entry.type === "transport" && entry.selectedCandidatePairId) pair = stats.get(entry.selectedCandidatePairId);
    });
    if (!pair) stats.forEach((entry) => { if (entry.type === "candidate-pair" && entry.nominated && entry.state === "succeeded") pair = entry; });
    if (pair) {
      const local = stats.get(pair.localCandidateId), remote = stats.get(pair.remoteCandidateId);
      connectionPath = local?.candidateType === "relay" || remote?.candidateType === "relay" ? "TURN 中繼" : "WebRTC 直連";
    }
    networkStatus.textContent = `${connectionPath} · 延遲約 ${latency} ms`;
  } catch { /* Diagnostics must not interrupt input. */ }
}
const pairForm = document.createElement("form");
pairForm.hidden = true;
pairForm.innerHTML = '<label for="pair-code">輸入電腦上的六位配對碼</label><input id="pair-code" inputmode="numeric" autocomplete="off" pattern="[0-9]{6}" minlength="6" maxlength="6" required aria-label="電腦配對碼"><button type="submit">配對</button><p id="pair-error" role="alert"></p>';
pairStatus.after(pairForm);
pairForm.className = "pair-form";
pairForm.onsubmit = (event) => {
  event.preventDefault();
  const code = document.querySelector("#pair-code").value;
  if (!/^[0-9]{6}$/.test(code) || dc?.readyState !== "open") return;
  pairForm.querySelector("button").disabled = true;
  dc.send(JSON.stringify({type: "pair", code}));
};

function state(text, ready = false) {
  approved = ready;
  label.textContent = text;
  indicator.dataset.state = ready ? "connected" : ended ? "disconnected" : "connecting";
  for (const key of keys) key.disabled = !ready;
  if (!ready) stopRepeat();
}
function notify(text) {
  toast.textContent = text;
  toast.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("visible"), 2500);
}
function stopRepeat() {
  clearTimeout(repeatDelay); clearInterval(repeatTimer);
  if (active) active.key.classList.remove("pressed");
  active = null;
}
function end(text = "連線已結束，請在電腦產生新的邀請") {
  if (ended) return;
  ended = true; state("未連線");
  pairForm.hidden = true;
  inviteForm.hidden = false;
  document.querySelector("#pair-code").value = "";
  clearInterval(heartbeat); clearTimeout(approvalTimer); clearTimeout(ackTimer);
  clearInterval(statsTimer);
  networkStatus.textContent = "";
  pending = null; pings.clear();
  if (dc?.readyState === "open") dc.send(JSON.stringify({ type: "disconnect" }));
  dc?.close(); pc?.close();
  signaling?.close();
  disconnect.disabled = true;
  pairStatus.textContent = text;
}
function ping() {
  if (dc?.readyState !== "open") return;
  if (Date.now() - lastPong > 3500) { end("連線沒有回應，已停止輸入"); return; }
  const id = ++pingId;
  pings.set(id, Date.now());
  dc.send(JSON.stringify({ type: "ping", id }));
}
function press(key, repeating = false) {
  if (!approved || dc?.readyState !== "open") return;
  if (pending !== null || dc.bufferedAmount > 1024) {
    if (!repeating) notify("等待上一個按鍵回應，請稍後再按");
    return;
  }
  pending = ++seq;
  dc.send(JSON.stringify({ type: "press", seq, key, at: Date.now() + offset }));
  ackTimer = setTimeout(() => end("按鍵傳送逾時，已停止輸入"), 1200);
}
function message(event) {
  let data;
  try { data = JSON.parse(event.data); } catch { return; }
  if (data.type === "pong" && pings.has(data.id)) {
    const sent = pings.get(data.id);
    const now = Date.now();
    latency = now - sent;
    pings.delete(data.id);
    lastPong = now;
    offset = data.serverTime + (now - sent) / 2 - now;
    if (data.approved) {
      clearTimeout(approvalTimer);
      pairForm.hidden = true;
      state("已連線", true); pairStatus.textContent = "已配對 · 按鍵透過 WebRTC 傳送到電腦";
    } else { state("等待配對碼"); pairStatus.textContent = "請查看電腦畫面，輸入配對碼";
      pairForm.hidden = false;
    }
  } else if (data.type === "pair_error") {
    pairForm.querySelector("button").disabled = false;
    document.querySelector("#pair-code").value = "";
    document.querySelector("#pair-error").textContent = `配對碼錯誤，還有 ${data.remaining} 次機會`;
    if (!data.remaining) end("配對碼輸錯三次，請在電腦產生新邀請");
  } else if (data.type === "idle") {
    end("閒置超過 5 分鐘，已自動中斷；請在電腦產生新邀請");
  } else if (data.type === "approved") {
    // A heartbeat also confirms approval and synchronizes the clock before typing.
    ping();
  } else if (data.type === "ack" && data.seq === pending) {
    clearTimeout(ackTimer); pending = null;
    if (data.error) notify({ stale_press: "按鍵等待過久，已略過", rate_limited: "輸入太快，請稍後", input_failed: "Windows 未接受按鍵", not_approved: "尚未獲得電腦允許" }[data.error] || "按鍵未送出");
  }
}
async function gather() {
  if (pc.iceGatheringState === "complete") return;
  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => { pc.removeEventListener("icegatheringstatechange", check); reject(new Error("網路資訊收集逾時")); }, 10000);
    function check() { if (pc.iceGatheringState === "complete") { clearTimeout(timeout); pc.removeEventListener("icegatheringstatechange", check); resolve(); } }
    pc.addEventListener("icegatheringstatechange", check); check();
  });
}
async function connect() {
  state("連線中");
  if (!token) { end("請掃描電腦顯示的新 QR code，或開啟完整配對網址"); return; }
  if (!window.RTCPeerConnection) { end("此瀏覽器無法使用 WebRTC，請更新 Safari 或 Chrome"); return; }
  try {
    let configuration;
    if (usesTailcat) {
      pairStatus.textContent = "正在透過 tailcat 建立配對通道，接著嘗試 WebRTC 直連";
      signaling = await window.tailkeyTailcat;
      if (!signaling) throw new Error("此頁面沒有 tailcat 支援，請使用完整 Tailkey 瀏覽器版本");
      configuration = await signaling.request("ice", {token});
    } else {
      const settings = await fetch("/api/ice", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({token}), cache: "no-store", signal: AbortSignal.timeout(10000)});
      if (!settings.ok) throw new Error("邀請已過期或使用過，請重新掃碼");
      configuration = await settings.json();
    }
    if (ended) { signaling?.close(); return; }
    pc = new RTCPeerConnection(configuration);
    dc = pc.createDataChannel("tailkey", { ordered: true });
    dc.onmessage = message;
    dc.onopen = () => { lastPong = Date.now(); disconnect.disabled = false; ping(); heartbeat = setInterval(ping, 1000); void connectionStats(); statsTimer = setInterval(connectionStats, 5000); };
    dc.onclose = () => end();
    pc.onconnectionstatechange = () => { if (["failed", "disconnected", "closed"].includes(pc.connectionState)) end("WebRTC 連線中斷，請重新配對"); };
    await pc.setLocalDescription(await pc.createOffer()); await gather();
    const offer = { token, sdp: pc.localDescription.sdp, type: "offer" };
    let answer;
    if (usesTailcat) {
      answer = await signaling.request("offer", offer);
      signaling.close();
    } else {
      const response = await fetch("/api/offer", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(offer), cache: "no-store", signal: AbortSignal.timeout(40000) });
      if (!response.ok) throw new Error(response.status === 403 || response.status === 410 ? "邀請已過期或使用過，請重新掃碼" : "無法完成配對");
      answer = await response.json();
    }
    await pc.setRemoteDescription(answer);
    if (ended) return;
    approvalTimer = setTimeout(() => end(dc?.readyState === "open" ? "配對等待逾時，請產生新邀請" : "無法跨網路連線，此網路可能需要 TURN 中繼；請在電腦產生新邀請"), 90000);
  } catch (error) { end(error.message || "連線失敗"); }
}
for (const key of keys) {
  key.addEventListener("pointerdown", (event) => {
    if (!approved || active) return;
    event.preventDefault(); active = { key, id: event.pointerId };
    key.setPointerCapture(event.pointerId); key.classList.add("pressed");
    press(key.dataset.key);
    repeatDelay = setTimeout(() => { repeatTimer = setInterval(() => { if (active && approved) press(key.dataset.key, true); }, 100); }, 400);
  });
  for (const name of ["pointerup", "pointercancel", "lostpointercapture"]) key.addEventListener(name, (event) => { if (active?.id === event.pointerId) stopRepeat(); });
  key.addEventListener("click", (event) => { if (event.detail === 0) press(key.dataset.key); });
}
disconnect.onclick = () => end();
window.addEventListener("blur", stopRepeat);
window.addEventListener("pagehide", () => end());
document.addEventListener("visibilitychange", () => { if (document.hidden) end("頁面已離開前景，已停止輸入；請重新配對"); });
void connect();
