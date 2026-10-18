# 報告（HW3 期中報告）

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
