# analysis — Beat the Bell (AI 導論期末專案)

程式與結果都在這裡；`data/` 仍然只放紀錄器的原始快照。

## 資料來源

| 校區 | 資料 | 來源 | 解析度 |
|---|---|---|---|
| 中山 (NSYSU) | 站點庫存快照，309 站，2026-10-01 起 | 本 repo `data/kaohsiung/` | 10 分鐘 |
| 台大 (NTU) | 騎乘紀錄 2024-09 ~ 2025-06（10 個月） | 臺北市政府開放資料 YouBike 2.0 票證刷卡資料 | 1 小時 |
| 台大 (NTU) | 站點庫存快照 2024-09-01 ~ 2025-06-22（295 天） | github.com/tses89214/youbike-historical-data | 10 分鐘 |

台大研究區 = 距臺大公館校區中心 1.2 km 內的 144 站（其中 59 站在校內），定義在 `results/ntu/ntu_stations.csv`。

## 程式（`code/`）

| 檔案 | 功能 |
|---|---|
| `nsysu_data.py` | 讀取紀錄器 CSV → 10 分鐘面板；校內 8 站與周邊 11 站的定義 |
| `nsysu_analysis.py` | 中山下課缺車量化：日內曲線、鐘響對齊、缺車事件、圖 |
| `ntu_pipeline.py` | 台大管線：站點表 → 騎乘紀錄擷取 → 快照面板 → 小時對帳（需求 vs 庫存變化） |
| `ntu_demand.py` | 截斷需求校正（Poisson 曝險）與業者調度推論 |
| `features.py` | 預測模型特徵（時間、鐘響距離、庫存狀態、鄰站、流量）與標籤 |
| `train_predictor.py` | 訓練 LightGBM 缺車預測器、基準線、Brier/AUC/ECE、可靠度曲線 |
| `horizon_sweep.py` | 時距掃描 30/60/90/120 分鐘：提案的 Poisson 推演（精確生滅鏈 + MC 抽樣對照）、logistic 基準、堆疊模型 |
| `validate_moves.py` | 調度推論的四項檢查：守恆、門檻/視窗敏感度、10 分鐘跳變、費率校正驗證 |
| `bootstrap_ci.py` | 區塊拔靴信賴區間：台大（日）、中山（站×日）、模擬器（日，成對政策差） |
| `ablation_bells.py` | 去掉鐘響特徵的消融 |
| `transfer_nsysu.py` | 台大 → 中山遷移：zero-shot、fine-tune、僅中山、季節基準 |
| `timetable.py` | 中山 115-1 課表 → 每週上課時段、每個節次下課／上課人數、課表強度特徵 |
| `timetable_bells.py` | 每次鐘響放出的學生數 vs 鐘響後 20 分鐘校內流出（含提前 30 分鐘的對照窗） |
| `timetable_nsysu.py` | 課表強度特徵對中山缺車預測的增益：逐日留一（10 個上課日），成對日拔靴 |
| `ablation_transfer.py` | 遷移實驗的補充消融 |
| `replay_sim.py` | 離散事件重播模擬器（真實騎乘、K 台卡車）：三種貪婪政策、路徑搜尋（`route`）與同一套價值的單步版本（`route1`）、業者調度重播；`--period val` 改用 2025-03 的 16 個驗證日 |
| `route_planner.py` | 路徑搜尋規劃器：生滅鏈（截斷校正費率）算出每站每個庫存水準在未來 H 分鐘的預期未滿足租借；給定停靠順序時載量用動態規劃求最佳，順序用貪婪插入、模擬退火與 2-opt 改進；每台車開完前兩站就重新規劃 |
| `tune_route.sh`、`run_route_test.sh` | 在驗證日調整地平線 H、時間成本 β、每次執行幾站；用選定設定跑 28 個測試日（1/3/6 台車） |
| `merge_sim.py`、`sim_numbers.py` | 合併新舊模擬結果；報告用的減少比例與成對日拔靴區間 |
| `nsysu_rates.py` | 中山各站的借還速率：高雄沒有騎乘紀錄，改把紀錄器每 10 分鐘的庫存變化用規劃器的生滅鏈做最大概似估計（空站、滿站的截斷由鏈本身處理，不是下界）；每格（站×上課日／假日×小時）用 3 小時曝險的先驗往全站同時段平均收縮；鏈給的機率低於 1e-5 的轉移視為卡車調度排除；`--holdout 7` 以最後 7 天檢驗 |
| `demo_replays.py` | 維持最近 7 個完整日的重播檔 `docs/replay_*.json` 與清單 `docs/replays.json`，每次最多補一天 |
| `demo_state.py` | 即時 demo 的狀態：最新快照 → 生滅鏈往後推 9 步，算每站每 10 分鐘有車、有空位的機會和預估車數（`ahead`）→ 微調過的臺大模型算 30／60 分缺車機率 → 生滅鏈算各站未來 90 分預期借不到車 → 路線搜尋排一台只補校園走廊 19 站的卡車，寫成 `docs/state.json`；紀錄器每 10 分鐘跑一次。另外寫出走廊各站「每一種可能的車數各自的預估」（`fresh`），讓頁面讀到更新的車數時能換一列用；並呼叫 `demo_track.py` |
| `demo_track.py` | 實測紀錄：每次快照先把頁面對走廊 19 站旁的人會給的建議（去哪一站、把握、預估幾分鐘）寫進 `data/advice/日期.csv`，之後的快照進來再對答案，把每天的結果寫進 `docs/track.json`。建議寫在結果之前，由 git 紀錄作證 |
| `demo_places.py`、`paths.py` | 起點與目的地：校內 14 棟建築、捷運站、輪渡站，以及它們和周邊 69 站兩兩之間的步行、騎車分鐘數（OpenStreetMap 路網距離，上限為直線的 1.7 倍），寫成 `docs/places.json`；`paths.py` 是讀這份表的共用函式 |
| `demo_outlook.py` | 頁面上「平常幾點難借、難還」那一條：上課日與假日每半小時，校內 8 站與山下 11 站沒車、沒空位的比例；另外存每一站自己的比例（站的卡片上「平常這個時段」那一行），寫成 `docs/outlook.json`（由 `demo_replays.py` 在補上新的一天時呼叫） |
| `nsysu_finetune.py` | 把臺大的 inventory-only 模型用紀錄器的全部天數接著訓練（學習率 0.02，最後 3 天決定停在哪一棵樹），產生 `lgb_inv_30_nsysu.txt`、`lgb_inv_60_nsysu.txt` 給 `demo_state.py` 用 |
| `figs_v2.py`, `figs_v3.py`, `figs_v4.py`, `hw3_figs.py`, `report_figs.py` | 報告圖（`figcheck.py` 自動檢查文字是否被裁切或重疊）；`figs_v4.py` 畫方法示意圖（單站一日的對帳、截斷與生滅鏈）、鐘響散佈圖、中山遷移與課表特徵的信賴區間圖、模擬器信賴區間圖 |
| `figstyle.py` | 圖表共用樣式 |
| `final_nsysu.py` | 期末報告：整段紀錄期間（10/2–11/16，29 個上課日）的下課缺車數字與紀錄器的完整度 |
| `final_forecast.py` | 期末報告：下課後 20 分車數預估的檢驗。速率只用到 10/29，之後 12 個上課日當測試；生滅鏈（每 10 分鐘速率、每小時速率）對照持續法與季節平均，含日拔靴區間與可靠度 |
| `final_transfer.py` | 期末報告：臺大模型在中山需要幾週本地資料（1–4 週 fine-tune、僅本地、zero-shot），以及 zero-shot 逐週的 AUC |
| `final_lost_demand.py` | 期末報告：臺大重播日上，空站時段流失的需求有多少（截斷校正速率 × 空站時間） |
| `final_planner.py` | 期末報告：規劃器在中山每個時段預期的缺口與建議路線（由 `demo_state.py --replay` 的輸出彙整），並對照只用每小時速率的版本 |
| `final_time.py` | 期末報告：照建議走，幾分鐘騎得上車（或還完車走到目的地）。12 個測試日逐一重播，第一站撲空就換下一站，最多三站；比較最近的站、官方 App 的即時車數、頁面第一版的規則（九成門檻）與現在的規則（預期分鐘數最少），並檢驗出發前 0–30 分鐘的預估有多準。`--outcome late|early` 是兩種計分方式的敏感度 |
| `final_relay.py` | 期末報告：官方「友愛接力」（滿站借車、空站還車各 5 元）看的是借還那一刻的站況。頁面標出「你到的時候很可能還是空站／滿站」的站，這支程式拿 12 個測試日對答案，和「現在是空站就當它等一下也是」比較；另外數每天有多少台車出現在原本空著的站 |
| `final_city.py` | 期末報告：用縣市公布的見車率算法（06:00–24:00 有車的時間比例）算校內、山下和周邊所有站，對照傍晚三小時；以及早上校內是整體車柱不夠，還是個別站停滿 |
| `final_spread.py` | 期末報告：頁面上每個出發時間的 10 個點（第一站就有車／換一站 8 分鐘內／超過 8 分鐘）準不準。現在出發照建議的站算；晚一點出發假設出發時再看一次車數，各站一起空的程度用 θ 調整（θ = 0.6，留一個測試日選出）。出發前 0–60 分鐘的預告對照實際，算可靠度與 Brier 分數，基準是平常那個時段的比例和常數 |
| `final_docks.py` | 期末報告：早上校內個別站停滿，車柱挪一挪有沒有用。生滅鏈從每三小時的實際車數往後推，算每站每天預期借不到、還不了的次數；容量正負 12 個車柱，一次移一個車柱的貪婪搜尋，以及體育館移 0–10 個車柱到工學院 |
| `final_rider.py` | 期末報告的第一版檢驗，只看第一站：照頁面的建議走，到站時真的有車（有位子）的比例。三個難用的時段各自重播 12 個測試日，對照最近的站、看現在車數挑站（至少 K 台）與生滅鏈門檻；另外輸出三個時段沒車、沒位子的比例（`hard_hours.csv`） |
| `final_avail.py` | 期末報告：生滅鏈的「k 步後有車／有位子」機率，對照保序校正與疊在鏈上的 LightGBM（兩個區塊交叉擬合）；輸出 `avail_oof.npz` 給 `final_rider.py --avail` |
| `nsysu_sim.py` | 期末報告：中山的卡車模擬。需求由後段資料估的速率抽 Poisson，規劃器用前段資料估的速率；早上與傍晚各一個班次，比較不派車、1–3 台只補校園走廊的車、1 或 3 台不限區域的車 |
| `final_figs.py` | 期末報告新增的圖（六週趨勢、遷移、預估檢驗、規劃器、速率、架構圖、幾分鐘騎得上車、卡車模擬） |

重跑台大管線（騎乘紀錄的 zip 約 75 MB/月，不放進 repo）：

```bash
pip install pandas numpy pyarrow matplotlib lightgbm scikit-learn
# 1. 站點表（sites.csv 取自 tses89214 repo 的 data/sites/ 最新版）
python code/ntu_pipeline.py stations sites.csv work/ntu
# 2. 騎乘紀錄：把 YYYYMM.zip 放到 raw/ 後
python code/ntu_pipeline.py trips raw work/ntu
# 3. 快照面板（需要 tses89214/youbike-historical-data 的 clone）
python code/ntu_pipeline.py snapshots path/to/youbike-historical-data work/ntu 2024-09-01 2025-06-22
# 4. 對帳、需求與調度推論、預測模型
python code/ntu_pipeline.py reconcile work/ntu
python code/ntu_demand.py work/ntu work/ntu/demand
python code/train_predictor.py work/ntu work/model
python code/validate_moves.py work/ntu work/ntu/demand
# 5. 時距掃描、遷移、模擬、信賴區間
python code/horizon_sweep.py work/ntu work/model work/model/sweep
python code/transfer_nsysu.py ../data work/model work/model/transfer
for k in 1 3 6; do python code/replay_sim.py work/ntu work/model work/sim/k$k --trucks $k; done
bash code/tune_route.sh work/ntu work/model work/sim_tune          # 只用 2025-03 的驗證日
bash code/run_route_test.sh work/ntu work/model work/sim_route
python code/merge_sim.py work/sim work/sim_route work/sim_v2
python code/sim_numbers.py work/sim_v2 work/sim_v2/sim_numbers.json
python code/bootstrap_ci.py work/model/sweep work/model/transfer work/sim_v2 work/model/ci
# 中山的借還速率與即時 demo
python code/nsysu_rates.py ../data results/nsysu/rates --holdout 7 --slots --tune-slots    # --slots：走廊 19 站上課日每 10 分鐘一組速率
python code/demo_state.py ../data results ../docs/state.json --trucks 1            # --at "2026-10-28 15:30" 可重播過去的時刻
python code/demo_replays.py ../data results ../docs --days 7                                   # 最近 7 天的重播檔，給頁面的重播模式
# 中山
python code/nsysu_analysis.py ../data results/nsysu
# 期末報告新增的實驗（速率先只估到 10/29，放在 work/rates_1029）
python code/final_nsysu.py ../data results/final
python code/nsysu_rates.py ../data work/rates_1029 --until 2026-10-29 --slots --tune-slots
python code/final_forecast.py ../data work/rates_1029 results/final/forecast
python code/final_transfer.py ../data results/model results/final/transfer --boot 200
python code/final_lost_demand.py work/ntu work/sim_v2 results/final/lost_demand.json
python code/final_planner.py work/replays results/final/planner work/replays_hourly   # work/replays：每個上課日跑 demo_state.py --replay
# 建議的成效、疊加模型、卡車模擬（世界的速率只用 10/30 之後的資料估）
python code/final_avail.py ../data results/final/rates_fit_to_1029 results/final/avail
python code/final_rider.py ../data results/final/rates_fit_to_1029 results/final/rider --avail results/final/avail/avail_oof.npz
python code/final_relay.py ../data results/final/rates_fit_to_1029 results/final/relay
python code/final_city.py ../data results/final/city
python code/final_spread.py ../data results/final/rates_fit_to_1029 ../docs/places.json results/final/spread
python code/final_docks.py ../data results/final/rates_fit_to_1029 results/final/docks
python code/demo_places.py ../data ../docs/places.json                            # 需要網路；地點或站有變動時才重跑
python code/final_time.py ../data results/final/rates_fit_to_1029 ../docs/places.json results/final/time
python code/final_time.py ../data results/final/rates_fit_to_1029 ../docs/places.json results/final/time_late --outcome late --only leave,arrive,dock
python code/final_time.py ../data results/final/rates_fit_to_1029 ../docs/places.json results/final/time_early --outcome early --only leave,arrive,dock
python code/nsysu_rates.py ../data results/final/rates_fit_from_1030 --since 2026-10-30 --until 2026-11-16 --slots
python code/nsysu_sim.py ../data results/final/rates_fit_to_1029 results/final/rates_fit_from_1030 results/final/sim --seeds 5
python code/nsysu_finetune.py ../data results/model results/model                 # 即時頁面用的微調模型
python code/final_figs.py results/final ../report/figs
# 課表：courses_115-1.tsv 由公開課程查詢系統逐日（星期一～日）查詢匯出（需人工通過驗證碼）
python code/timetable.py results/nsysu/timetable/courses_115-1.tsv results/nsysu/timetable
python code/timetable_bells.py ../data results/nsysu/timetable/sessions.csv results/nsysu/timetable
python code/timetable_nsysu.py ../data work/model results/nsysu/timetable/sessions.csv work/model/timetable
TT_SPLIT=week python code/timetable_nsysu.py ../data work/model results/nsysu/timetable/sessions.csv work/model/timetable/week
```

## 結果（`results/`）

- `nsysu/`：`nsysu_summary.json` 關鍵數字、`nsysu_profile.csv` 日內曲線、`nsysu_stations.csv` 站點表、
  `nsysu_bells.csv` 鐘響後每 10 分鐘的變化、`nsysu_episodes.csv` 每次缺車事件、兩張圖；`nsysu/timetable/` 課表
  （`courses_115-1.tsv` 原始匯出、`sessions.csv` 上課時段、`bells.csv` 各節次下課人數、`bell_outflow.csv` 鐘響後流出）。
- `ntu/`：`flows_hourly.parquet` 站×小時借還車、`hourly.parquet` 對帳表（庫存、流量、殘差、調度旗標、曝險）、
  `demand/` 截斷校正與調度推論的結果與圖。
- `model/`：預測模型的指標、可靠度曲線、特徵重要性、測試集預測；`model/sweep/` 時距掃描與 Poisson 推演
  （`sweep_metrics.csv`、`rates_train.csv`、`sweep_setup.json` 含 MC 對照）；`model/transfer/` 遷移；`model/ci/` 信賴區間；`model/timetable/` 課表特徵實驗（逐日留一；`week/` 為第一週訓練、第二週測試）。
- `nsysu/rates/`：中山各站速率 `rates.csv`（`lam_r`、`lam_q` 每小時；`lam_*_gross` 為毛變化量下界）、全站同時段平均 `rates_prior.csv`、最後 7 天的檢驗 `rates_holdout.csv`（每筆轉移的對數概似：鏈估計 −1.51、毛變化量 −1.59、同時段平均 −1.72）。
- `final/`：期末報告新增實驗的結果。`final_nsysu_*.csv/json` 六週的下課缺車數字與紀錄器完整度；`forecast/` 下課後預估的檢驗；`transfer/` 幾週本地資料的遷移；`planner/` 規劃器在中山的時段彙整；`lost_demand.json` 臺大流失需求；`rates_fit_to_1029/` 檢驗用的速率（只估到 10/29）；`rider/` 第一站借不借得到的比例與三個難用時段的比例；`time/` 幾分鐘騎得上車（`time_summary.csv` 各規則的平均與日拔靴區間、`time_by_minute.csv` 依出發時間、`time_foresight_summary.csv` 事前預估的準度；逐筆的 `time_cases.csv` 太大不放進 repo），`time_late/`、`time_early/` 是計分方式的敏感度；`relay/` 友愛接力標記的準度；`city/` 見車率與校內車柱分布；`avail/` 生滅鏈與疊加模型的比較；`sim/` 卡車模擬；`rates_fit_from_1030/` 模擬裡產生需求用的速率（10/30 到 11/16）。
- `nsysu/rates/rates_slots.csv`：走廊 19 站上課日每 10 分鐘的速率（`slot` 0–143）；`rates_slots_tuning.csv` 是先驗權重的驗證。
- `sim/k1,k3,k6/`：重播模擬每日結果與摘要（含 `route`、`route1`）；`sim/route/` 路徑搜尋的原始輸出與設定；`sim/tuning/sim_tune_summary.csv` 驗證日調參結果；`sim/sim_numbers.json` 報告引用的數字與區間。

執行環境：Python 3.11、pandas 3.0、numpy 2.4、LightGBM 4.7、scikit-learn 1.8、2 vCPU / 7 GB RAM。
