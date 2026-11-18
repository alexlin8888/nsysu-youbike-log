# 即時頁面的原始檔

`docs/index.html` 是組出來的，不要直接改它。要改的檔案在 `site/src/`：

| 檔案 | 內容 |
|---|---|
| `strings.js` | 頁面上所有的字，中文和英文各一份 |
| `style.css` | 版面與顏色；手機、平板、桌機的差別都在這裡 |
| `body.html` | 頁面骨架 |
| `app.js` | 讀 `state.json`／`replay_*.json`、畫地圖和清單 |
| `leaflet.css` | 地圖函式庫的樣式（Leaflet 1.9.4，程式放在 `docs/vendor/`） |

改完之後：

```
python3 site/build.py                                  # 重新產生 docs/index.html 和 manifest
python3 -m http.server 8770 --directory docs &         # 在本機開起來看
python3 site/test_page.py                              # 用真的瀏覽器跑一遍功能檢查（需要 playwright）
```

`test_page.py` 會在桌機、筆電、平板和三種手機尺寸各跑一次：搜尋、建議的站、起點與目的地、全程時間與走路的比較、
即時車數、我的站、調度分頁、重播、複製路線、中英文切換、建議的紀錄、資料過期與讀取失敗的提示、手機底部面板的拖拉。
地圖圖磚和官方 API 在檢查時用假的回應代替（`BTB_REAL_TILES=1` 改用真的圖磚）。任何一項沒過，結束碼不是 0。
`BTB_SIZES="phone 390"` 可以只跑一種尺寸。

網址可以帶參數，方便錄影或貼連結：

- `?tab=dock`（或 `ops`、`about`）直接開某個分頁
- `?from=cm&to=krt` 設定起點和目的地（代號列在 `docs/DEMO.md`），`to=` 留空是不指定目的地
- `?fresh=0` 不向官方讀即時車數，只用紀錄器的快照
- `?replay=2026-11-13&t=16:00` 開某一天某個時間的重播
- `?lang=en` 英文
- `#501209069` 直接打開某一站（站號）
