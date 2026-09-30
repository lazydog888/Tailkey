# Tailkey 專案日誌

更新日期：2026-10-01（Asia/Taipei）

本日誌記錄開發決策、問題處理與驗證範圍。未保留確切日期的早期工作按階段記錄，不推定完成日期。內容不包含個人裝置名稱、tailnet 網域、本機帳號路徑、配對碼、控制網址或私密金鑰。

## 專案目標

讓手機或平板成為筆電的外接數字鍵盤，提供數字、運算鍵、NumPad Enter、Backspace，以及手機端中斷連線。

目前接收端為 Windows，按鍵送至前景程式。手機端以瀏覽器為主，盡量減少安裝與外部服務需求。跨網路的主要目標為「筆電接公司有線網路，手機使用 4G」，接受部分網路無法打洞成功。

## 開發紀錄

### 初期：Tailscale 網頁鍵盤

- 以 Python HTTP 服務和 Windows SendInput 實作接收端。
- 透過 Tailscale Serve 提供 HTTPS，手機需能連入相同 tailnet。
- 加入 Backspace、長按重複輸入與手機端停止 Windows 服務。
- `start.cmd` 自動載入本機設定；不需要另外執行設定檔。
- 此版本先前已推送 GitHub。後續 WebRTC、tailcat、PWA 與可攜版工作尚未推送。

### 2026-09-25：允許來源錯誤

**現象：**手機能開啟頁面，但送出按鍵時出現「此網址未列入允許來源」。

**原因：**Tailscale 裝置名稱變更後，HTTPS 網址與本機來源允許清單不一致。頁面載入成功不代表按鍵 API 已通過來源驗證。

**處理：**更新本機設定中的確切來源並重新啟動。使用者之後確認恢復正常。本機設定檔由 Git 排除，問題紀錄省略真實網域。

### WebRTC 同網路原型

- 新增無需手機安裝 Tailscale 的瀏覽器 WebRTC 鍵盤。
- 電腦顯示短效 QR code／邀請網址，手機輸入電腦上的六位配對碼。
- 配對碼輸錯三次結束連線；邀請限時且一次性。
- 手機中斷連線、離開前景或心跳逾時後停止輸入；重新使用需新邀請。
- 加入按鍵序號、時間檢查、速率限制與回應確認。
- 修正連接埠已被占用時的啟動體驗，顯示簡短錯誤並要求先關閉既有服務。
- 使用者回報 iPhone 同網路，以及手機熱點供筆電上網的配對成功。

這些結果不代表「手機 4G 與筆電另一個網路」已成功。

### 跨網路架構探索

- 曾完成可自行架設的配對 broker 原型，未部署外部服務。
- 使用者希望減少依賴，並接受直連不保證成功，因此研究 tailcat 與 WebRTC 組合。
- 原生 Windows helper 與瀏覽器 WASM 透過 tailcat／DERP 交換連線資訊，再嘗試建立 WebRTC DataChannel。
- 配對碼與鍵盤輸入走 WebRTC；tailcat 通道只傳遞受限制的配對訊息。
- 此實驗模式不提供 TURN 候選；直連失敗時停止配對，不自動改用 DERP 傳送按鍵。
- 仍依賴外部 DERP 與 STUN，不是完全無外部服務的架構。
- 使用者暫不公開手機靜態網頁；未發布 GitHub Pages。

### 2026-09-30：離線 PWA 原型與桌面驗證

- 加入 Web App Manifest、圖示與 Service Worker。
- 快取固定的鍵盤與 WASM 資產，不快取控制頁面、API 回應、配對碼或邀請資料。
- 新增貼上新邀請的入口；只擷取配對資訊，保持在 PWA 自身來源，不導航至貼上的電腦網址。
- 更新等待現有頁面關閉，避免配對途中替換版本。

當日已記錄的驗證結果：

| 項目 | 結果與範圍 |
|---|---|
| 既有 WebRTC 整合測試 | 三項通過，涵蓋配對、無效／重複按鍵、邀請與來源驗證、心跳結束 |
| JavaScript 語法檢查 | 當日手機、PWA 與 Service Worker 腳本通過 |
| 關閉頁面伺服器後重新載入 | 桌面瀏覽器仍可從快取開啟鍵盤 |
| 快取 WASM 與真實 tailcat 訊息交換 | 完成，接著建立同一台電腦上的 WebRTC 直連 |
| 配對碼與 Backspace | 測試接收端接受按鍵並增加計數，未注入真實 Windows 按鍵 |
| 手機介面的中斷操作 | 鍵盤停用並返回新邀請表單 |

測試服務已停止。這些是桌面端原型結果，尚未驗證 iPhone 主畫面 PWA、快取保留、電信商 4G 或跨網路打洞。

### 本機 HTTPS 與平台方向討論

- 本機 HTTPS 加上手機明確信任憑證，可作為 PWA 初次取得頁面的候選方案；不一定要公開網站。
- 只略過憑證警告不能視為可靠的 PWA 安裝流程。本機憑證產生、HTTPS 啟動與手機信任引導尚未實作。
- HTTPS 解決網頁信任與安裝，不會自動解決公司網路與 4G 之間的連通性。
- 討論未來 Android／iOS 原生 App：可減少網頁首次載入與快取限制，原生 tailcat 整合仍需研發。
- 現有跨平台基礎主要在瀏覽器介面、配對與傳輸邏輯。macOS／Linux 按鍵注入及原生手機 App 尚未實作。

### 2026-10-01：Windows 可攜式封裝與英文介面

- 新增 `Tailkey.exe` 啟動選單：同 Wi-Fi／手機熱點、tailcat＋WebRTC 實驗模式。
- 使用 PyInstaller 封裝 Windows x64 接收端與所需 Python 執行環境、原生 helper、瀏覽器資產。
- 使用者解壓整個資料夾即可啟動，不需要另外安裝 Python、Node.js、Go 或 Tailscale。
- 新增原始碼入口 `Tailkey.cmd` 與重建腳本 `build-portable.ps1`。
- 電腦配對頁面與手機鍵盤加入繁體中文／English，預設依瀏覽器語言選擇，可儲存選擇。
- 切換語言重新載入頁面；手機需重新配對。電腦控制頁保留本次記憶體內的控制資訊以便重新載入。
- 加入中英文可攜版操作說明。原始 Tailscale 版入口保留。
- Go 建置加入 `-trimpath`，減少在產物中保留本機建置路徑。

**產物：**`release/Tailkey-Windows-x64.zip`，67,336,217 bytes，約 64.2 MiB。需要保留完整解壓資料夾，包括 `_internal`。

**本次檢查：**封裝建置成功；壓縮包有 244 個項目，未包含本機私密設定、憑證或虛擬環境，指定的個人路徑與私有 hostname 掃描無匹配。原始碼差異的空白格式檢查通過。

**驗證限制：**本次未啟動封裝程式做執行測試，未做新版手機／語言切換實測；先前原型測試不能當成新版可攜版的完整驗證。執行檔未做 Windows 程式碼簽署。

**交付與發布：**使用者改為要求先交付本機封裝，暫不推送 GitHub。已提供本機壓縮包連結；未推送此輪變更、未發布 Release，提交暫存已撤回，開發檔案保留本機。

**後續（同日）：**使用者要求建立 PR。上述工作已提交為分支 `webrtc-tailcat-portable` 並推送。本機沒有 GitHub CLI，PR 需由使用者在網頁上建立。專案資料夾擁有者為另一個 Windows 帳號，git 指令需臨時加 `-c safe.directory`；未修改全域 git 設定。

### 2026-10-01：跨網路方向結論

- 嚴格的零外部依賴做不到：兩台都在 NAT 後的裝置需要會合點。電腦有公網 IPv6 時可直連，但需要使用者的路由器放行連入流量，不適合一般使用者。
- 目標改為「使用者零安裝、零設定」。手機頁面託管在 GitHub Pages 屬於開發者一次性負擔，使用者看不到，因此列為必要項目。
- 手機頁面放在 HTTPS、配對資訊走 tailcat（WireGuard，以 QR 中的位址驗證電腦），是不安裝任何東西的方案中最安全的。主要風險收斂為開發者的 GitHub 帳號，建議使用專用組織帳號並啟用 passkey（同時避免與其他 `github.io` 專案共用來源）。
- 面向大眾時必須補上「WebRTC 直連失敗改走 DERP 傳按鍵」，否則對稱型 NAT 的使用者會無法連線。
- 原始 Tailscale 版安全性最高（裝置先經帳號認證），但需要安裝 App，保留為進階選項。

### 2026-10-01：資安強化與自動模式（分支 `security-hardening`）

| 項目 | 變更 |
|---|---|
| 監聽範圍 | 不再綁定 `0.0.0.0`。同 Wi-Fi 與 tailcat 模式只監聽 `127.0.0.1` 與偵測到的區網 IP；tailcat 搭配 `--web-url` 時只監聽 `127.0.0.1`；broker 模式維持只監聽 loopback |
| 閒置斷線 | 配對後 5 分鐘沒有成功按鍵即由電腦端中斷，手機顯示原因並需重新掃碼 |
| CSP | tailcat 模式的 `connect-src` 由任意 `wss:` 收窄為 `https://tailcat.dev https://*.ipn.dev wss://*.ipn.dev`。匯出的靜態頁面加上相同的 `<meta>` CSP，供 GitHub Pages 這類無法設定標頭的託管使用 |
| 發布驗證 | `build-portable.ps1` 另產生 `release/SHA256SUMS.txt`；可攜版說明加入 `Get-FileHash` 比對方式 |
| 配對通知 | 手機輸入正確配對碼後，Windows 跳出通知（PowerShell WinRT toast，失敗不影響配對） |
| 依賴鎖定 | `webrtc/requirements.txt`、`packaging-requirements.txt`、`webrtc/broker-requirements.txt` 改為含 SHA-256 的完整鎖定檔，版本與既有環境一致；人工維護的頂層需求移到對應的 `.in` 檔，重產指令寫在鎖定檔第一行 |
| 自動模式 | `Tailkey.exe` 不再顯示選單，預設 `--auto`：有 tailcat 檔案且 DERP 可連時用 tailcat，否則用同 Wi-Fi；tailcat helper 中途失效也會自動改為同 Wi-Fi 模式。`Tailkey.exe --lan` 可強制同 Wi-Fi |

**驗證：**

| 項目 | 結果 |
|---|---|
| 整合測試 | 4 項通過，新增「配對通知與閒置斷線」測試 |
| 鎖定檔 | 在全新虛擬環境以雜湊檢查安裝成功，並於該環境跑完 4 項測試 |
| 監聽位址 | 自動模式實測只監聽 loopback 與區網 IP；`--tailcat --web-url` 只監聽 loopback |
| 收窄後的 CSP | 桌面瀏覽器實測：經 DERP 舊金山節點（`tc302a.ipn.dev`）完成 tailcat 配對、WebRTC 直連、輸入配對碼並送出 Backspace（測試模式計數 +1），主控台無 CSP 錯誤 |
| 自動退回 | 中途終止 tailcat helper 後，服務改為同 Wi-Fi 模式，新邀請不含 tailcat 位址，手機經區網 HTTP 完成配對前置流程 |
| Windows 通知 | 指令執行成功（結束碼 0）；是否實際顯示需使用者確認 |
| JavaScript／Python 語法 | 通過 |

**限制：**未重新建置可攜版 zip，現有 `release/` 內仍是舊版。閒置時間固定 5 分鐘。CSP 綁定 tailcat 目前的 DERP 網域；若上游更換網域，tailcat 模式會連不上（自動模式會退回同 Wi-Fi）。

### 2026-10-01：研究「不可信網路警告」（資安第 1 項，未實作）

**問題：**同 Wi-Fi 模式的網頁與配對資訊走明文 HTTP。同一網路上的攻擊者可替換手機端 JavaScript，看到使用者輸入的配對碼，再冒充手機送出數字鍵、Backspace 與 NumPad Enter。

**評估過的做法：**

| 做法 | 結論 |
|---|---|
| 依 Windows 網路類型（公用／私人）警告 | 不採用。Windows 新加入的網路預設為「公用」，家用網路也常是公用，警告會頻繁誤報，使用者很快會忽略 |
| 解析 `netsh wlan show interfaces` 判斷是否為開放 Wi-Fi | 不採用。輸出文字依系統語言而變（中文系統欄位為中文），無法穩定解析 |
| 以 Windows WLAN API 讀取目前連線的驗證方式 | 可行。開放（無密碼）Wi-Fi 是風險最高的情況，可以可靠判斷。但咖啡廳常見的共用密碼 WPA2 同樣可被同網路的人攻擊，無法涵蓋 |
| 手機與電腦比對驗證碼、或在 QR 放入電腦憑證指紋 | 無效。頁面本身走明文 HTTP，攻擊者換掉 JavaScript 就能跳過任何手機端檢查 |
| 本機自簽 HTTPS | 不採用。略過憑證警告沒有實際保護；讓手機信任自製根憑證的風險比問題本身更大 |
| 比對 HTTP 來源 IP 與 WebRTC 對端 IP | 效果弱。能做 ARP 欺騙的攻擊者也能偽造 IP，且 IPv4／IPv6 並存時會誤判 |
| 手機頁面改由 HTTPS（GitHub Pages）提供 | **根本解法**。頁面無法被竄改，配對資訊走 tailcat 加密且驗證電腦身分；同一個 Wi-Fi 下 WebRTC 仍會直連，速度不受影響 |

**建議：**

1. 根本解：部署 GitHub Pages 靜態頁，讓自動模式預設使用 HTTPS 頁面加 tailcat；明文 HTTP 只在沒有網路時作為退回選項。這也同時是跨網路所需的步驟。
2. 過渡措施：退回明文模式時，以 WLAN API 偵測開放 Wi-Fi 並拒絕產生邀請，其餘情況在電腦配對頁常駐一行「只在自己家或信任的網路使用」。
3. 已完成的配對通知與閒置斷線，可降低被冒充時未被察覺、以及手機被他人拿走使用的風險。

## 目前狀態

| 功能／情境 | 狀態 |
|---|---|
| Windows Tailscale 鍵盤 | 先前使用者確認可用 |
| WebRTC 同 Wi-Fi／手機熱點 | 原型使用者確認成功；新封裝待回歸 |
| 繁體中文／英文介面 | 已實作、已封裝，待操作驗證 |
| 桌面 PWA 快取與 tailcat→WebRTC | 原型已驗證，範圍為單一電腦；收窄 CSP 後重新驗證通過 |
| 自動模式與資安強化 | 已實作並在桌面驗證，位於本機分支 `security-hardening`，尚未推送、尚未重新封裝 |
| 手機頁面 GitHub Pages 託管 | 已決定採用，尚未部署 |
| 直連失敗改走 DERP 傳按鍵 | 面向大眾前必要，尚未實作 |
| 公司有線＋手機 4G | 主要研發目標，尚未實測成功 |
| Android／iOS 原生 App | 討論階段 |
| macOS／Linux 接收端 | 尚未實作 |
| GitHub 發布 | `webrtc-tailcat-portable` 已推送，PR 待使用者在網頁建立；未發布 Release |

## 下一步

1. 使用者確認配對時是否看到 Windows 通知，並試用自動模式。
2. 重新建置可攜版，連同 `SHA256SUMS.txt` 一起發布。
3. 部署 GitHub Pages 靜態頁（建議專用組織帳號並啟用 passkey），可攜版內建該網址。
4. 實作直連失敗時改走 DERP 傳按鍵。
5. 完成「筆電另一條網路＋手機 4G」實機測試，分別記錄頁面載入、訊息交換、直連與按鍵結果。
6. 明文退回模式的開放 Wi-Fi 偵測（WLAN API）。
7. 依成功率與安裝體驗決定是否投入 Android 原生版本。

## 相關文件

- [專案說明](README.md)
- [可攜版中英文操作](PORTABLE.md)
- [WebRTC 原型](webrtc/README.md)
- [tailcat 架構與限制](webrtc/TAILCAT.md)
- [PWA 與既有驗證紀錄](webrtc/PWA.md)
- [自行架設 broker 原型](webrtc/INTERNET.md)
