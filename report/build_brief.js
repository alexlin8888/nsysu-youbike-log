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
const LINE = 264;                          // 1.1 lines

const run = (text, o = {}) => new TextRun({ text, font: FONT, size: 19, ...o });
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
const COLS = [4426, 1440, 1440, 1440, 1440];   // sums to WIDTH
const R = AlignmentType.RIGHT;
const row = (cells, o = {}) => new TableRow({ cantSplit: true, children: cells.map((t, k) => cell(t, COLS[k], { align: k ? R : AlignmentType.LEFT, ...o })) });
const line = { style: BorderStyle.SINGLE, size: 4, color: "8A96A3" };
const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const grid = new Table({
  width: { size: WIDTH, type: WidthType.DXA }, columnWidths: COLS,
  borders: { top: line, bottom: line, left: none, right: none, insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: "C9D1D9" }, insideVertical: none },
  rows: [
    row(["做法（12 個上課日，模型估計）", "傍晚借不到車\n15:00–20:00", "早上還不了車\n08:00–11:00", "多騎的趟數\n傍晚／早上", "多送的時數\n傍晚／早上"], { bold: true, fill: "E8ECEF" }),
    row(["現況（每天人次）", "204", "75", "—", "—"]),
    row(["預測型友愛接力，還車（早上為借車）多 25%", "−5%", "−3%", "12／3", "58／13 小時"]),
    row(["同上，多 50%", "−11%", "−6%", "25／5", "69／14 小時"]),
    row(["同上，多一倍", "−22%", "−11%", "50／10", "89／17 小時"]),
    row(["下課前補車（傍晚兩趟、早上一趟，各 20 台）", "−16%", "−20%", "—", "—"]),
    row(["補車加上預測型友愛接力（多 50%）", "−27%", "−25%", "26／5", "65／10 小時"]),
  ],
});

function sourceTable(list) {
  const half = Math.ceil(list.length / 2), w = WIDTH / 2;
  const nb = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  const col = (items) => new TableCell({ width: { size: w, type: WidthType.DXA }, margins: { top: 0, bottom: 0, left: 0, right: 120 },
    children: items.map((t) => new Paragraph({ spacing: { after: 0, line: 200 }, indent: { left: 280, hanging: 280 }, children: [run(t, { size: 15 })] })) });
  return new Table({ width: { size: WIDTH, type: WidthType.DXA }, columnWidths: [w, w],
    borders: { top: nb, bottom: nb, left: nb, right: nb, insideHorizontal: nb, insideVertical: nb },
    rows: [new TableRow({ children: [col(list.slice(0, half)), col(list.slice(half))] })] });
}

const children = [
  new Paragraph({ spacing: { after: 60, line: 300 }, children: [b("中山大學傍晚借不到 YouBike：友愛接力改在下課前就送", { size: 30 })] }),
  new Paragraph({ spacing: { after: 0, line: 260 }, children: [run("給：國立中山大學總務處、高雄市政府交通局、微笑單車高雄營運團隊", { size: 18 })] }),
  new Paragraph({ spacing: { after: 0, line: 260 }, children: [run("提出：國立中山大學「人工智慧導論」第 54 組　林沛霆、陳佳晨、林詩穎　2026 年 11 月", { size: 18 })] }),
  new Paragraph({ spacing: { after: 90, line: 260 }, border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "10202F", space: 4 } },
    children: [run("即時網站：", { size: 18 }), link("https://alexlin8888.github.io/nsysu-youbike-log/", "alexlin8888.github.io/nsysu-youbike-log"),
      run("　報告、程式與資料：", { size: 18 }), link("https://github.com/alexlin8888/nsysu-youbike-log", "github.com/alexlin8888/nsysu-youbike-log")] }),

  head("一、問題"),
  para([run("我們從 2026 年 10 月 1 日起每 10 分鐘記錄一次 YouBike 官方開放資料。29 個上課日裡，校內 8 站在 17:00 到 20:00 有 40% 的時間沒車，07:00 到 17:00 只有 2%；早上 09:00 到 11:00 則有 28% 的時間停滿。傍晚缺車時校內各站同時沒車，換一站也借不到，車必須在下課前就回到校內。")]),

  head("二、現行友愛接力付錢太晚"),
  para([run("2026 年 7 月起，高雄 YouBike 在滿站借車或把一般車還到空站可得 5 元騎乘券，以借還當下的站況為準 [1]。依我們的模型估計，下午兩點到晚上八點還到校內的車有 69% 在 17:00 前到站，這時校內多半還有車，現行規則只付給其中 3%。這些車並非用不到：16:30 還回校內的車，兩小時內平均讓 0.92 人借到車，和 17:30 還的車（0.94）相當。")]),

  new Paragraph({ spacing: { before: 40, after: 40 }, alignment: AlignmentType.CENTER, keepNext: true,   // no line rule: an exact line height would clip the picture
    children: [new ImageRun({ type: "png", data: fs.readFileSync(FIG + "fig_brief_timing.png"), transformation: { width: 626, height: 119 } })] }),
  head("三、建議"),
  item(1, "預測型友愛接力：站快被借光時就送。", "系統每 10 分鐘預測一次，校內哪一站 40 分鐘內被借光的機會超過一半，把車還到那一站就有獎勵，不必等站空；早上反過來，快停滿的站借車就有獎勵。紐約 Citi Bike 也依各站接下來需要多少車給點數 [2]。在 12 個未參與模型訓練的上課日，219 次借空中有 91% 事先被標出，中位數提早 40 分鐘；被標出的站有 62% 真的在 40 分鐘內借空，其他有車的站只有 25%。若騎回校內的人因此多一半，傍晚借不到車少 11%，每天多 25 趟騎車回校，多送約 69 次獎勵。"),
  item(2, "獎勵先用現行的 5 元券，一小時騎乘時數是第二個選項。", "刷一卡通數位學生證的學生和有 TPASS、MeNGo 月票的人，前 30 分鐘本來就免費，一般會員付 5 元 [3]，騎乘時數只對超過 30 分鐘的那一段有用。11/24 訪談 10 位每週騎 YouBike 的中山同學：最想要 5 元券和一小時的各 4 位，30 分鐘 1 位，有月票的 1 位都不要；8 位一個月幾乎不曾騎超過 30 分鐘，選 5 元券的人說它能抵電輔車費。提案改的是什麼時候送；送什麼可以沿用現行的 5 元券，每天約 24 次（120 元）就能獎勵 17:00 前騎回校內的車。想一併鼓勵多騎再改送一小時：世界衛生組織建議每週 150 分鐘身體活動 [4]，近五成國人不到 [5]，騎車通勤者死亡風險低 41% [6]。"),
  item(3, "下課前補車。", "16:50 與 17:50 各送 20 台到校內，傍晚借不到車少 16%；早上 09:00 從校內載走 20 台，還不了車少 20%。補車再加上預測型友愛接力，傍晚少 27%。"),
  item(4, "不必為此錯開下課。", "一半的課提早 10 分鐘下課，傍晚借不到車只少 2%，因為傍晚整個校園的車本來就不夠。"),
  new Paragraph({ spacing: { before: 50, after: 30, line: 230 }, keepNext: true, children: [run("試算：百分比和現況相比；趟數和時數是每天比現行規則多出的部分，時數以每次送一小時計，送 5 元券時金額是次數 × 5 元。", { size: 17 })] }),
  grid,

  head("四、試辦與限制"),
  para([run("建議在校內 8 站試辦四週，單雙週輪流使用現行的友愛接力和預測型友愛接力，用我們的紀錄器比較兩種週次的沒車時間。以上數字來自生滅鏈模型：從實際記錄的 15:00 車數出發，沒有算營運商之後的卡車，所以人次偏高，請看百分比；獎勵能讓多少人改變還車地點還沒有資料，表中列出三種情況（訪談裡 7 位說每週至少會為 5 元券這樣還一次車，5 位為一小時）。多送的獎勵若是 5 元券，傍晚每天約 345 元；若是一小時，以一般票價計面額上限約 1,380 元，其中約 44 次付給本來就會在那時還車的人。預測每 10 分鐘自動產生並公開在網站上；營運商提供試辦期間的借還與獎勵紀錄，就能直接量到反應比例。")]),

  new Paragraph({ spacing: { before: 50, after: 10, line: 220 }, children: [b("資料來源", { size: 16 })] }),
  // the sources in two columns of a borderless table, to keep the brief on one page
  sourceTable([
    "[1] 中央社，〈高雄YouBike推「友愛接力」〉，2026-06-24。",
    "[2] Citi Bike, Bike Angels points and rewards, citibikenyc.com, 2026-11-22.",
    "[3] YouBike 微笑單車，高雄市收費方式，youbike.com.tw，2026-11-22。",
    "[4] WHO, “Every move counts towards better health,” 2020-11-25.",
    "[5] 公視新聞網，〈國健署：國人每天久坐5.9小時〉，2020-06-11。",
    "[6] C. A. Celis-Morales et al., BMJ 357:j1456, 2017.",
  ]),
];

const doc = new Document({
  creator: "NSYSU Group 54",
  title: "中山大學傍晚借不到 YouBike：友愛接力改在下課前就送",
  styles: { default: { document: { run: { font: FONT, size: 20 } } } },
  sections: [{ properties: { page: { margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN } } }, children }],
});
const OUT = process.env.OUT_DOCX || "policy_brief.docx";
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log("wrote", OUT, buf.length, "bytes"); });
