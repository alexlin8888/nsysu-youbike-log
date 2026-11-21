# nsysu-youbike-log

每 10 分鐘抓一次 YouBike 官方站點資料（`https://apis.youbike.com.tw/json/station-yb2.json`），
把中山大學周邊 5 km 內約 310 個站的車輛數存成每日 CSV。
給「人工智慧導論」期末專案（Beat the Bell：下課缺車預測與預先調度）當作中山端的在地資料。

全程由 GitHub Actions 執行，不需要任何人的電腦開著。

## 一次性設定（約 5 分鐘）

1. 在 GitHub 建一個 **公開** repo（名稱建議 `nsysu-youbike-log`）。
   要公開的原因：公開 repo 的 Actions 不計分鐘數；私人 repo 每月只有 2,000 分鐘，
   每 10 分鐘跑一次會用到約 1,800 分鐘，很容易被停。
2. 把這個資料夾的內容整包放進 repo 根目錄（含隱藏的 `.github/` 資料夾）：
   ```
   .github/workflows/logger.yml
   logger/fetch_youbike.py
   logger/check_coverage.py
   README.md
   ```
   用 GitHub 網頁「Add file → Upload files」拖進去，或 `git add . && git commit && git push` 都可以。
3. repo 的 **Settings → Actions → General**：
   - Actions permissions：Allow all actions and reusable workflows
   - Workflow permissions：選 **Read and write permissions**，Save
4. 到 **Actions** 分頁 → 左邊點 `youbike-logger` → 右邊 **Run workflow** 手動跑一次。
   約 30 秒後 repo 裡應出現 `data/kaohsiung/YYYY-MM-DD.csv`、`data/stations.csv`、`data/latest.json`。
5. 之後就自動每 10 分鐘跑一次，什麼都不用做。

## 維護

- 一個 run 會連續記錄約 5 小時 40 分（`logger/loop.sh`），結束前自己啟動下一個。Actions 分頁正常的樣子是：
  一個跑很久的黃色 run，加上每 20 分鐘一個幾秒就結束的綠色備援 run。
- YouBike 的 API 會對某些 GitHub 機器整段回 HTTP 503。碰到時該 run 會記一行到 `data/errors.log`、
  立刻交棒給下一個 run（換一台機器），通常幾分鐘內恢復。`fetch failed …` 的 commit 就是這種情況。
- 偶爾會收到 GitHub 寄的失敗通知，原因多半是「The hosted runner lost communication」，是 GitHub 的機器斷線。
  備援排程看到 25 分鐘沒有新資料就會接手，不用處理。
- GitHub 規定公開 repo 若 60 天內沒有人為活動，會自動停掉排程。
  **每隔一個多月請任何一位組員隨便改一下 README 並 commit**，保險起見。
- 想看目前累積了多少：clone 下來後執行
  `python3 logger/check_coverage.py`，會列出每天的快照數、最大間隔、缺車列數。
- 快照不一定落在整 10 分鐘（交棒時會多一兩筆），分析時會把資料重新對齊到 10 分鐘格。

## 資料格式

`data/kaohsiung/YYYY-MM-DD.csv`（台灣時間的日期；前一天的檔會自動壓成 `.csv.gz`）

| 欄位 | 意義 |
|---|---|
| time | 抓取時間 HH:MM:SS（UTC+8） |
| sno | 站號，對照 `data/stations.csv` |
| bikes | 可借車輛數（含電輔車） |
| ebikes | 其中電輔車數 |
| empty | 可還空位數 |
| status | 1 = 營運中、2 = 暫停服務（此時 0/0 不是缺車） |
| age | 該站自己的 updated_at 距抓取時間幾分鐘（判斷資料是否過期） |

`data/stations.csv`：高雄全部 1,512 站的站號、中英文名、行政區、座標、車柱數、距中山距離（公尺）、
是否在記錄範圍內（`logged`）。內容有變才會重寫。

`data/latest.json`：最新一次快照。

## 即時 demo

`docs/index.html` 是即時頁面，有「借車」「還車」「政策」「調度」「說明」五個分頁。借車選起點和目的地，頁面告訴你現在出發幾分鐘騎得上車、晚一點出發會不會更久、騎車和走路哪個快；還車告訴你騎到的時候哪一站還有位子。站名後面的「+5 元」標的是你到的時候有 60% 以上機率符合官方「友愛接力」獎勵的站。紀錄器每 10 分鐘也會把頁面當下的建議寫進 `data/advice/`，之後再對答案（`docs/track.json`）。政策寫給學校、市府和營運商看：傍晚整個校園一起沒車時查詢幫不上，而還到校內的車有將近七成在 17:00 前到，現行友愛接力只付給其中 3%；分頁的提案是在預測會空的站提前送一小時騎乘時數（現行獎勵是 5 元騎乘券；有月票或學生卡的人前 30 分鐘本來就免費，所以送一小時，也鼓勵多騎一點），列出每一站 40 分鐘內借空的機率、這個做法和下課前補車的試算，以及一頁的建議書（`docs/policy_brief.pdf`）。調度給派卡車的人看：校園到捷運之間 19 站未來 90 分鐘預估借不到車的人次，和一台校園專車的建議路線。頁面的讀法、可以直接開到某個畫面的連結寫在 `docs/DEMO.md`。期末影片是一支動畫（`video/`），旁白稿、錄旁白和合成的步驟在 `docs/VIDEO.md`。頁面由 `site/src` 組成，改版流程見 `site/README.md`。

公開網址要在 repo 的 **Settings → Pages** 設定一次：Source 選 *Deploy from a branch*，Branch 選 `main`、資料夾選 `/docs`，Save。之後網址是 `https://alexlin8888.github.io/nsysu-youbike-log/`，每次 commit 後約一分鐘更新。

## 改設定

在 `.github/workflows/logger.yml` 的 `env:` 區塊：

- `RADIUS_KM: "5"` → 改成 `"0"` 就記錄高雄全部站（每天約 4.7 MB，repo 會大很多）
- `CENTER` → 參考點座標（目前是中山大學）
- `AREA_CODES` → `12` 是高雄；台北是 `00`，新北 `01`，台中 `05`
