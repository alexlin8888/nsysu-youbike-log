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

- 每週看一次 Actions 分頁有沒有一整排紅色；偶爾一兩次紅的是 API 逾時，不用管。
  連續三次抓不到才會把 job 標成失敗（GitHub 會寄信）。
- GitHub 規定公開 repo 若 60 天內沒有人為活動，會自動停掉排程。
  **11 月中旬請任何一位組員隨便改一下 README 並 commit**，保險起見。
- 想看目前累積了多少：clone 下來後執行
  `python3 logger/check_coverage.py`，會列出每天的快照數、最大間隔、缺車列數。
- GitHub 的排程在尖峰時段會延遲幾分鐘、偶爾漏一次，這是正常的；
  分析時會把資料重新對齊到 10 分鐘格。

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

`data/latest.json`：最新一次快照，之後 demo 網頁直接讀這個檔。

## 改設定

在 `.github/workflows/logger.yml` 的 `env:` 區塊：

- `RADIUS_KM: "5"` → 改成 `"0"` 就記錄高雄全部站（每天約 4.7 MB，repo 會大很多）
- `CENTER` → 參考點座標（目前是中山大學）
- `AREA_CODES` → `12` 是高雄；台北是 `00`，新北 `01`，台中 `05`
