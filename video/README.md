# 期末影片的原始檔

這個資料夾用程式畫出整支影片，說明和錄旁白的步驟在 `docs/VIDEO.md`。

| 檔案 | 做什麼 |
|---|---|
| `data.py` | 從網站的重播資料和報告的分析結果取出畫面要用的數字，寫成 `build/data.json` |
| `script.py` | 旁白的句子和時間軸，寫出 `build/cues.json`、字幕（`.srt`、`.ass`）和旁白稿 `build/NARRATION.md` |
| `engine/` | 畫面：`lib.js` 是角色、腳踏車、站、手機等畫法，`scenes.js` 是十一場動畫，`stage.html` 依場景和時間畫出一格 |
| `shots.py` | 網站截圖（11 月 11 日的重播）和建議書第一頁，放在 `assets/` |
| `audio.py` | 合成音樂和音效，寫出 `build/music.wav`、`sfx.wav`、`mix.wav` |
| `render.py` | 每一場各輸出一個 mp4，接起來、配上聲音、燒字幕，放在 `out/` |
| `preview.py` | 只畫某幾格來檢查 |
| `mix_voice.py` | 錄好旁白之後，把旁白放進影片 |

`out/` 和 `build/*.wav` 太大，不放進 git，照 `docs/VIDEO.md` 的步驟可以重新產生。
