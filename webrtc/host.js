const owner = new URLSearchParams(location.hash.slice(1)).get("owner");
history.replaceState(null, "", location.pathname);
window.addEventListener("tailkey-language-change", () => {
  if (owner) history.replaceState(null, "", location.pathname + "#" + new URLSearchParams({owner}));
});
const el = (id) => document.getElementById(id);
let imageURL = null;
let pollPending = false;
let waitingForService = false;
async function api(path, post = false) {
  const response = await fetch(`/api/${path}`, {
    method: post ? "POST" : "GET",
    headers: { "X-Owner-Token": owner || "", ...(post ? { "Content-Type": "application/json" } : {}) },
    ...(post ? { body: "{}" } : {}), cache: "no-store", signal: AbortSignal.timeout(12000),
  });
  if (!response.ok) throw new Error(response.status === 503 ? "配對服務尚未連線，請稍後產生新邀請" : "操作失敗，請重新啟動服務開啟電腦配對頁面");
  return response;
}
async function newInvite() {
  el("new").disabled = true;
  try {
    const data = await (await api("invite", true)).json();
    waitingForService = false;
    el("url").value = data.url;
    const qr = await (await api("qr")).blob();
    if (imageURL) URL.revokeObjectURL(imageURL);
    imageURL = URL.createObjectURL(qr);
    el("qr").src = imageURL;
    await poll();
  } catch (error) { waitingForService = error.message.includes("尚未連線"); el("status").textContent = error.message; }
  finally { el("new").disabled = false; }
}
async function poll() {
  if (pollPending) return;
  pollPending = true;
  try {
    const data = await (await api("status")).json();
    el("status").textContent = { idle: "請產生邀請", inviting: "等待手機掃碼", connecting: "正在建立 WebRTC 連線", pending: "請在手機輸入下方配對碼", connected: "已配對，可以輸入", ended: "連線已結束，請產生新的邀請", expired: "邀請已過期，請產生新的邀請" }[data.phase];
    el("mode").textContent = data.dryRun ? "測試模式：不會輸入 Windows" : "手機輸入正確配對碼後會輸入 Windows 目前作用中的程式";
    el("network").textContent = data.internet ? (data.brokerOnline ? "網際網路配對服務已連線" : "正在重新連接配對服務，請稍後產生新邀請") : "同 Wi-Fi 模式";
    el("invitation").hidden = data.phase !== "inviting";
    el("countdown").textContent = `邀請還有 ${data.remaining} 秒失效，成功使用後即作廢`;
    el("request").hidden = data.phase !== "pending";
    el("peer").textContent = data.code ? `配對碼：${data.code}` : "";
    el("presses").textContent = `本次啟動已接受 ${data.presses} 次按鍵`;
    el("disconnect").disabled = !["pending", "connected", "connecting", "inviting"].includes(data.phase);
    if (waitingForService && data.brokerOnline) {
      waitingForService = false;
      // The poll completes before generating a new invite.
      setTimeout(newInvite, 0);
    }
  } catch (error) { el("status").textContent = error.message; }
  finally { pollPending = false; }
}
el("new").onclick = newInvite;
for (const action of ["disconnect"]) el(action).onclick = async () => {
  el(action).disabled = true;
  try { await api(action, true); await poll(); }
  catch (error) { el("status").textContent = error.message; }
  finally { el(action).disabled = false; }
};
el("copy").onclick = async () => {
  try { await navigator.clipboard.writeText(el("url").value); el("copy").textContent = "已複製"; }
  catch { el("url").select(); el("copy").textContent = "請複製選取的網址"; }
};
if (owner) { void newInvite(); setInterval(poll, 1000); }
else el("status").textContent = "請使用 start-webrtc.cmd 開啟電腦配對頁面";
