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
| `replay_sim.py` | 離散事件重播模擬器（真實騎乘、K 台卡車、四種政策） |
| `figs_v2.py`, `figs_v3.py`, `figs_v4.py`, `hw3_figs.py`, `report_figs.py` | 報告圖（`figcheck.py` 自動檢查文字是否被裁切或重疊）；`figs_v4.py` 畫方法示意圖（單站一日的對帳、截斷與生滅鏈）、鐘響散佈圖、中山遷移與課表特徵的信賴區間圖、模擬器信賴區間圖 |
| `figstyle.py` | 圖表共用樣式 |

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
python code/bootstrap_ci.py work/model/sweep work/model/transfer work/sim work/model/ci
# 中山
python code/nsysu_analysis.py ../data results/nsysu
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
- `sim/k1,k3,k6/`：重播模擬每日結果與摘要。

執行環境：Python 3.11、pandas 3.0、numpy 2.4、LightGBM 4.7、scikit-learn 1.8、2 vCPU / 7 GB RAM。
