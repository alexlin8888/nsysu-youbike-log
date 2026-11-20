// One-page policy brief for the school, the city and the operator: report/policy_brief.docx, converted to
// docs/policy_brief.pdf, which the page's Policy tab links to. Every number comes from the report (Secs. 3.8-3.10)
// or from analysis/results/final/reward and analysis/results/final/policy; the sources are listed at the end.
// Chinese text is set in 標楷體 (DFKai-SB), Latin text and numbers in Times New Roman.
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, ExternalHyperlink, Table, TableRow, TableCell, WidthType, AlignmentType,
  BorderStyle, ShadingType, VerticalAlign,
} = require("docx");
const FIG = process.env.FIG_DIR || "figs/";

const KAI = "標楷體";
const FONT = { ascii: "Times New Roman", hAnsi: "Times New Roman", cs: "Times New Roman", eastAsia: KAI };
const MARGIN = 860;                        // 1.52 cm on every side of an A4 page
const WIDTH = 11906 - 2 * MARGIN;          // text width in DXA
const LINE = 278;                          // about 1.16 lines

const run = (text, o = {}) => new TextRun({ text, font: FONT, size: 20, ...o });
const b = (text, o = {}) => run(text, { bold: true, ...o });
const para = (children, o = {}) => new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 30, line: LINE }, children, ...o });
const head = (text) => new Paragraph({ keepNext: true, spacing: { before: 90, after: 20, line: LINE }, children: [b(text, { size: 22 })] });
// a numbered recommendation: the number hangs, the text wraps under the text
const item = (n, lead, rest) => para([b(`${n}. ${lead}`), run(rest)], { indent: { left: 300, hanging: 300 } });
const link = (url, text) => new ExternalHyperlink({ link: url, children: [run(text, { size: 18, color: "1F4E9A", underline: {} })] });

const cell = (text, w, o = {}) => new TableCell({
  width: { size: w, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
  margins: { top: 30, bottom: 30, left: 90, right: 90 },
  shading: o.fill ? { type: ShadingType.CLEAR, color: "auto", fill: o.fill } : undefined,
  // "\n" in a cell's text starts a new line inside the cell
  children: [new Paragraph({ alignment: o.align || AlignmentType.LEFT, spacing: { after: 0, line: 240 },
    children: text.split("\n").map((part, k) => run(part, { size: 18, bold: !!o.bold, break: k ? 1 : 0 })) })],
});
const COLS = [5086, 1700, 1700, 1700];   // sums to WIDTH
const R = AlignmentType.RIGHT;
const row = (cells, o = {}) => new TableRow({ cantSplit: true, children: cells.map((t, k) => cell(t, COLS[k], { align: k ? R : AlignmentType.LEFT, ...o })) });
const line = { style: BorderStyle.SINGLE, size: 4, color: "8A96A3" };
const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const grid = new Table({
  width: { size: WIDTH, type: WidthType.DXA }, columnWidths: COLS,
  borders: { top: line, bottom: line, left: none, right: none, insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: "C9D1D9" }, insideVertical: none },
  rows: [
    row(["做法（12 個上課日，模型估計）", "傍晚 15:00–20:00\n借不到車", "早上 08:00–11:00\n還不了車", "每天多發的券\n傍晚／早上"], { bold: true, fill: "E8ECEF" }),
    row(["現況（每天人次）", "204", "75", "—"]),
    row(["預測型友愛接力，還車（早上為借車）多 25%", "−5%", "−3%", "58／13"]),
    row(["同上，多 50%", "−11%", "−6%", "69／14"]),
    row(["同上，多一倍", "−22%", "−11%", "89／17"]),
    row(["下課前補車（傍晚兩趟、早上一趟，各 20 台）", "−16%", "−20%", "—"]),
    row(["補車加上預測型友愛接力（多 50%）", "−27%", "−25%", "65／10"]),
    row(["一半的課提早 10 分鐘下課", "−2%", "—", "—"]),
  ],
});

const children = [
  new Paragraph({ spacing: { after: 60, line: 300 }, children: [b("中山大學傍晚借不到 YouBike：把友愛接力提前到下課前", { size: 30 })] }),
  new Paragraph({ spacing: { after: 0, line: 260 }, children: [run("給：國立中山大學總務處、高雄市政府交通局、微笑單車高雄營運團隊", { size: 18 })] }),
  new Paragraph({ spacing: { after: 0, line: 260 }, children: [run("提出：國立中山大學「人工智慧導論」第 54 組　林沛霆、陳佳晨、林詩穎　2026 年 11 月", { size: 18 })] }),
  new Paragraph({ spacing: { after: 90, line: 260 }, border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "10202F", space: 4 } },
    children: [run("即時網站：", { size: 18 }), link("https://alexlin8888.github.io/nsysu-youbike-log/", "alexlin8888.github.io/nsysu-youbike-log"),
      run("　程式與資料：", { size: 18 }), link("https://github.com/alexlin8888/nsysu-youbike-log", "github.com/alexlin8888/nsysu-youbike-log")] }),

  head("一、問題"),
  para([run("我們從 2026 年 10 月 1 日起每 10 分鐘記錄一次 YouBike 官方開放資料。29 個上課日裡，校內 8 站在 17:00 到 20:00 有 40% 的時間沒車，07:00 到 17:00 只有 2%；早上 09:00 到 11:00 則有 28% 的時間停滿、還不了車。傍晚缺車時校內各站同時沒車，換一站也借不到，查詢 App 再準也只能顯示沒車，車必須在下課前就回到校內。")]),

  head("二、現行友愛接力付錢太晚"),
  para([run("2026 年 7 月起，全台 YouBike 在滿站借車或把一般車還到空站可得 5 元騎乘券，以借還當下的站況為準 [1, 2]。依我們的模型估計，下午兩點到晚上八點還到校內的車有 69% 在 17:00 前到站，這時校內多半還有車，現行規則只付給其中 3%。這些車並非用不到：16:30 還回校內的車，兩小時內平均讓 0.92 人借到車，和 17:30 還的車（0.94）相當。")]),

  new Paragraph({ spacing: { before: 40, after: 40 }, alignment: AlignmentType.CENTER, keepNext: true,   // no line rule: an exact line height would clip the picture
    children: [new ImageRun({ type: "png", data: fs.readFileSync(FIG + "fig_brief_timing.png"), transformation: { width: 668, height: 141 } })] }),
  head("三、建議"),
  item(1, "友愛接力改成預測型。", "在模型算出 40 分鐘內借空機率達一半的校內站，提前開放「還車送 5 元」；早上對快停滿的站提前開放「借車送 5 元」。紐約 Citi Bike 的 Bike Angels 也是依各站接下來需要多少車給點數，地圖每 15 分鐘更新 [3, 4]。在 12 個未參與模型訓練的上課日，219 次借空中有 91% 事先被標出，中位數提早 40 分鐘；被標出的站有 62% 真的在 40 分鐘內借空，其他有車的站只有 25%。預測型付錢的車，每台在兩小時內平均讓 0.98 人借到車，和現行規則付錢的車（0.99）相同。若騎回校內的人因此多一半，傍晚借不到車少 11%，每天多發約 69 張券（面額約 345 元），其中約 40 張付給本來就會在那時還車的人。"),
  item(2, "下課前補車。", "16:50 與 17:50 各送 20 台到校內，傍晚借不到車少 16%；早上 09:00 從校內載走 20 台，還不了車少 20%。補車再加上預測型友愛接力，傍晚少 27%。若卡車依同一套預測整晚調度，模擬中一台讓 17:00 到 20:00 借不到車少 34%，兩台少 54% [5]。"),
  item(3, "不必為此錯開下課。", "一半的課提早 10 分鐘下課，傍晚借不到車只少 2%，因為傍晚整個校園的車本來就不夠。"),
  new Paragraph({ spacing: { before: 60, after: 40, line: 240 }, keepNext: true, children: [run("試算結果（百分比是和現況相比；券數是每天比現行規則多發的張數）", { size: 18 })] }),
  grid,

  head("四、試辦與限制"),
  para([run("建議在校內 8 站試辦四週，單雙週輪流使用現行與預測型規則，用我們的紀錄器比較兩種週次的沒車時間。預測每 10 分鐘自動產生，公開在網站的 state.json（reward 欄位），營運商可以直接讀取。以上數字來自生滅鏈模型：從實際記錄的 15:00 車數出發，沒有算營運商之後的卡車，所以人次偏高，請看百分比；5 元能讓多少人改變還車地點還沒有資料，表中列出三種情況。營運商若能提供試辦期間的借還與發券紀錄，就能直接量到這一項。")]),

  new Paragraph({ spacing: { before: 100, after: 10, line: 220 }, children: [b("資料來源", { size: 16 })] }),
  ...[
    "[1] 中央社，〈高雄YouBike推「友愛接力」 單次最高可獲10元回饋〉，2026-06-24。",
    "[2] 林育萱，〈騎YouBike也能賺錢？「紅站借、橘站還」拿10元，騎乘券怎麼領？〉，數位時代，2026-08-19。",
    "[3] Citi Bike, “Bike Angels: Points,” citibikenyc.com/bike-angels/points，2026-11-21 讀取。",
    "[4] H. Chung, D. Freund, and D. B. Shmoys, “Bike Angels: An analysis of Citi Bike’s incentive program,” ACM COMPASS, 2018.",
    "[5] 第 54 組期末報告第 3.8–3.10 節；程式 final_reward.py、final_policy.py、nsysu_sim.py（見上方連結）。",
  ].map((t) => new Paragraph({ spacing: { after: 0, line: 220 }, indent: { left: 280, hanging: 280 }, children: [run(t, { size: 16 })] })),
];

const doc = new Document({
  creator: "NSYSU Group 54",
  title: "中山大學傍晚借不到 YouBike：把友愛接力提前到下課前",
  styles: { default: { document: { run: { font: FONT, size: 20 } } } },
  sections: [{ properties: { page: { margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN } } }, children }],
});
const OUT = process.env.OUT_DOCX || "policy_brief.docx";
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log("wrote", OUT, buf.length, "bytes"); });
