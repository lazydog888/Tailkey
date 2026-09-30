// Same-origin static assets; no controller URL or pairing code is sent to DERP.
window.tailkeyTailcat = (async () => {
  const params = new URLSearchParams(location.hash.slice(1));
  const addr = params.get("tc");
  if (!addr) return null;
  let readyTimer;
  const ready = new Promise((resolve, reject) => {
    window.onTailcatReady = () => { clearTimeout(readyTimer); resolve(); };
    readyTimer = setTimeout(() => reject(new Error("tailcat 載入逾時")), 60000);
  });
  ready.catch(() => {});
  const go = new Go();
  const response = await fetch("./main.wasm.gz");
  if (!response.ok) throw new Error("找不到 tailcat 模組，請完成瀏覽器資產建置");
  const decompressed = response.body.pipeThrough(new DecompressionStream("gzip"));
  const wasm = await WebAssembly.instantiateStreaming(new Response(decompressed, {headers:{"Content-Type":"application/wasm"}}), go.importObject);
  void go.run(wasm.instance);
  await ready;
  if (typeof tailcatDial !== "function") throw new Error("tailcat 模組未就緒");
  const conn = await tailcatDial({addr, derpMapURL: "https://tailcat.dev/derpmap.json"});
  const decoder = new TextDecoder();
  const encoder = new TextEncoder();
  let buffer = "";
  return {
    async request(op, data) {
      await conn.write(encoder.encode(JSON.stringify({op, data}) + "\n"));
      while (!buffer.includes("\n")) {
        const chunk = await conn.read();
        if (!chunk) throw new Error("tailcat 配對通道已中斷");
        buffer += decoder.decode(chunk, {stream:true});
        if (buffer.length > 70000) throw new Error("配對回應過大");
      }
      const index = buffer.indexOf("\n");
      const reply = JSON.parse(buffer.slice(0, index));
      buffer = buffer.slice(index + 1);
      if (reply.status !== 200) throw new Error("邀請已過期、使用過或連線失敗，請重新掃碼");
      return reply.data;
    },
    close() { conn.close(); }
  };
})();
// Avoid an unhandled rejection before mobile.js awaits the transport.
window.tailkeyTailcat.catch(() => {});
