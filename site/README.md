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

`test_page.py` 會在桌機、平板和三種手機尺寸各跑一次：搜尋、建議的站、我的站、起點、調度分頁、重播、
複製路線、中英文切換、資料過期與讀取失敗的提示、手機底部面板的拖拉。任何一項沒過，結束碼不是 0。

網址可以帶參數，方便錄影或貼連結：

- `?tab=ops`（或 `about`）直接開某個分頁
- `?replay=2026-11-13&t=16:00` 開某一天某個時間的重播
- `?lang=en` 英文
- `#501209069` 直接打開某一站（站號）
