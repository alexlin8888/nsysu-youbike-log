# 報告

## 期末報告（HW5_54）

期末報告（HW5）以期中報告 HW3 為底，新增或修改的地方用藍字，期中已經有的內容（不論當時是黑字或藍字）一律黑字。繳交檔名是 `HW5_54.pdf`，YouTube 連結印在標題下方、作者上方。

| 檔案 | 用途 |
|---|---|
| `build_final.js` | 產生 `HW5_54.docx`。由 `build_hw3.js` 改寫而來：`BLUE` 設成不上色，新內容用 `fb`、`bodyF`、`capM` 等函式或字串裡的 `{{…}}` 標成藍色。3.8、3.10 節與第 4 節中「評估定案後新記錄的上課日」那幾句的數字讀自 `analysis/results/final/prospective/prospective.json` |
| `layout_final.json`、`layout_final_space.py` | 期末報告每張圖的位置，以及搜尋時每張圖可以放的段落 |
| `make_app_figure.py` | Fig. 19 的兩張手機截圖：用 Playwright 開頁面的英文版，重播 2026-11-11 的 16:40（從圖資大樓借車）和 17:30（管理學院到捷運站），併成 `figs/fig_demo_app.png` |
| `build_brief.js` | 產生一頁的建議書 `policy_brief.docx`（給學校、市府和營運商；中文用標楷體），轉成 PDF 後放到 `docs/policy_brief.pdf`，政策分頁的按鈕連到這個檔。圖讀 `figs/fig_brief_timing.png`（`analysis/code/final_policy_figs.py` 產生） |
| `video_url.txt`（自行新增） | 放 YouTube 連結。標題下方、作者上方那一行會印出這個連結；沒有這個檔時印「link to be added after upload」 |

重建：

```
cd ../analysis && python code/final_prospective.py ../data ../docs results/final/prospective && cd ../report   # 繳交前重跑，納入到截止日為止的上課日
echo "https://youtu.be/影片代號" > video_url.txt          # 影片上傳後
node build_final.js                                       # -> HW5_54.docx
soffice --headless --convert-to pdf HW5_54.docx
python check_black.py HW5_54.docx HW3_54.docx             # 黑字必須和期中報告一字不差
python whitespace.py HW5_54.pdf
BUILD_JS=build_final.js DOC=HW5_54 LAYOUT_OUT=layout_final.json LAYOUT_SPACE=layout_final_space python layout_seq.py   # 內容長度變了才需要重排圖
node build_brief.js && soffice --headless --convert-to pdf policy_brief.docx && mv policy_brief.pdf ../docs/   # 建議書
```

繳交用的 PDF 建議在 Windows 的 Word 開 `HW5_54.docx` 再匯出，中文才會是真正的標楷體。

## 期中報告（HW3_54）

| 檔案 | 用途 |
|---|---|
| `build_hw3.js` | 用 docx-js 產生 `HW3_54.docx`（CVPR 雙欄；藍字 = HW1 之後新增或修改的內容）。圖檔讀自 `figs/`，圖的位置與大小讀自 `layout.json` |
| `layout.json` | 每張圖接在哪個段落之後（`after`，段落編號用 `DUMP=1 node build_hw3.js` 列出）以及寬度比例（`frac`） |
| `layout_seq.py` | 依閱讀順序逐張決定圖的位置：每個候選位置都完整建一次 PDF，量每欄底部的空白，取空白最少者 |
| `layout_tail.py` | 對最後幾張圖與 Table 4 做聯合搜尋，讓欄底不留大片空白 |
| `layout_v14_space.py`、`layout_lib.py`、`layout_all.py` | 搜尋用的候選位置（段落編號）與共用函式 |
| `check_black.py` | 檢查所有黑字是否與 HW1 原文逐字相同：`python check_black.py HW3_54.docx HW1_54.docx` |
| `whitespace.py` | 列出 PDF 每欄中超過一行高的空白 |

重建：

```
node build_hw3.js                      # -> HW3_54.docx
python soffice.py --headless --convert-to pdf HW3_54.docx
python check_black.py HW3_54.docx HW1_54.docx
python whitespace.py HW3_54.pdf
```

`soffice.py` 是 LibreOffice 的轉檔包裝，路徑可用環境變數 `SOFFICE` 指定。

中文一律用標楷體（docx 內的東亞字型設為「標楷體」）。標楷體是 Windows 字型；在 Linux 上轉 PDF 時以教育部標準楷書（`apt install fonts-moe-standard-kai`）代替，對應規則見 `fontconfig/30-dfkai-alias.conf`（放到 `/etc/fonts/conf.d/` 後執行 `fc-cache -f`）。在 Windows 的 Word 開啟 docx 再匯出 PDF，會直接用真正的標楷體。
