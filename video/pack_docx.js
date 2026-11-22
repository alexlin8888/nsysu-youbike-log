// Word copy of the team brief: the HW5 tasks (docs/HW5_TASKS.md), then the narration script on a new page
// (build/NARRATION.md). Chinese is set in 標楷體, Latin in Times New Roman, as in the report.
//
// Usage: node video/pack_docx.js [OUT_DOCX]   (default video/out/HW5分工與旁白稿.docx; pack.py runs it too)
// Reads only the markdown these two files use: headings, paragraphs, pipe tables, numbered and bulleted lists,
// fenced blocks, inline code and <https://...> links.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, BorderStyle, ShadingType,
  AlignmentType, LevelFormat, ExternalHyperlink, Footer, PageNumber, HeadingLevel, TableLayoutType,
} = require("docx");

const HERE = __dirname;
const OUT = process.argv[2] || path.join(HERE, "out", "HW5分工與旁白稿.docx");
const KAI = "標楷體";
const FONT = { ascii: "Times New Roman", hAnsi: "Times New Roman", cs: "Times New Roman", eastAsia: KAI };
const ACCENT = "1F5FAE", LINE = "A9B6C4", TINT = "EEF3F8", MUTED = "4B5868";
const PAGE_W = 11906, MARGIN = 1134, TEXT_W = PAGE_W - 2 * MARGIN;   // A4, 2 cm margins (DXA)

function parse(md) {
  const lines = md.replace(/\r/g, "").split("\n");
  const blocks = [];
  let i = 0;
  const starts = /^(#{1,3} |\||```|- |\d+\. )/;
  while (i < lines.length) {
    const l = lines[i];
    if (!l.trim()) { i++; continue; }
    let m;
    if (l.startsWith("```")) {
      const body = []; i++;
      while (i < lines.length && !lines[i].startsWith("```")) body.push(lines[i++]);
      i++; blocks.push({ t: "code", lines: body }); continue;
    }
    if ((m = l.match(/^(#{1,3}) (.*)$/))) { blocks.push({ t: "h", level: m[1].length, text: m[2] }); i++; continue; }
    if (l.startsWith("|")) {
      const rows = [];
      while (i < lines.length && lines[i].startsWith("|")) rows.push(lines[i++]);
      const cells = (r) => r.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());
      blocks.push({ t: "table", head: cells(rows[0]), body: rows.slice(2).map(cells) }); continue;
    }
    if (/^\d+\. /.test(l) || /^- /.test(l)) {
      const ordered = /^\d+\. /.test(l), re = ordered ? /^\d+\. / : /^- /, items = [];
      while (i < lines.length && re.test(lines[i])) {
        let s = lines[i++].replace(re, "");
        while (i < lines.length && /^\s{2,}\S/.test(lines[i])) s += lines[i++].trim();
        items.push(s);
      }
      blocks.push({ t: ordered ? "ol" : "ul", items }); continue;
    }
    const para = [l]; i++;
    while (i < lines.length && lines[i].trim() && !starts.test(lines[i])) para.push(lines[i++]);
    blocks.push({ t: "p", text: para.join("") });
  }
  return blocks;
}

// inline: `code` gets a light tint, <https://...> becomes a link
function runs(text, size, extra = {}) {
  const out = [];
  for (const part of text.split(/(`[^`]+`|<https?:[^>]+>)/)) {
    if (!part) continue;
    if (part.startsWith("`")) {
      out.push(new TextRun({ text: part.slice(1, -1), font: FONT, size, ...extra, shading: { type: ShadingType.CLEAR, fill: TINT, color: "auto" } }));
    } else if (part.startsWith("<http")) {
      const url = part.slice(1, -1);
      out.push(new ExternalHyperlink({ link: url, children: [new TextRun({ text: url, font: FONT, size, color: ACCENT, underline: {} })] }));
    } else {
      out.push(new TextRun({ text: part, font: FONT, size, ...extra }));
    }
  }
  return out;
}

const vlen = (s) => [...s.replace(/`|<|>/g, "")].reduce((n, ch) => n + (ch.charCodeAt(0) > 0x2e80 ? 2 : 1), 0);
const border = { style: BorderStyle.SINGLE, size: 4, color: LINE };
const borders = { top: border, bottom: border, left: border, right: border };

function table(head, body) {
  const all = [head, ...body];
  const weight = head.map((_, c) => Math.min(50, Math.max(8, ...all.map((r) => vlen(r[c] || "")))));
  const sum = weight.reduce((a, b) => a + b, 0);
  const widths = weight.map((w) => Math.floor((w / sum) * TEXT_W));
  widths[widths.length - 1] += TEXT_W - widths.reduce((a, b) => a + b, 0);
  const cell = (text, c, isHead) => new TableCell({
    width: { size: widths[c], type: WidthType.DXA }, borders,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    shading: isHead ? { type: ShadingType.CLEAR, fill: TINT, color: "auto" } : undefined,
    children: [new Paragraph({ spacing: { before: 0, after: 0, line: 280 }, children: runs(text || "", 22, isHead ? { bold: true } : {}) })],
  });
  return new Table({
    width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: widths, layout: TableLayoutType.FIXED,
    rows: all.map((r, k) => new TableRow({ tableHeader: k === 0, cantSplit: true, children: head.map((_, c) => cell(r[c], c, k === 0)) })),
  });
}

// a fenced block becomes one tinted box, one paragraph per line, to copy from; a short one stays on one page
function box(lines) {
  return new Table({
    width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: [TEXT_W], layout: TableLayoutType.FIXED,
    rows: [new TableRow({ cantSplit: lines.length <= 16, children: [new TableCell({
      width: { size: TEXT_W, type: WidthType.DXA }, borders,
      shading: { type: ShadingType.CLEAR, fill: "F5F7FA", color: "auto" },
      margins: { top: 100, bottom: 100, left: 160, right: 160 },
      children: lines.map((l) => new Paragraph({ spacing: { before: 0, after: 0, line: 300 }, children: [new TextRun({ text: l, font: FONT, size: 22 })] })),
    })] })],
  });
}

let listNo = 0;
function render(blocks, { body = 24, line = 312 } = {}) {
  const out = [];
  blocks.forEach((b, k) => {
    const next = blocks[k + 1];
    if (b.t === "h") {
      out.push(new Paragraph({ heading: b.level === 1 ? HeadingLevel.HEADING_1 : HeadingLevel.HEADING_2, children: [new TextRun({ text: b.text, font: FONT })] }));
    } else if (b.t === "p") {
      // a numbered script line ("01　...") wraps under its text, not under the number
      const hang = /^\d{2}\u3000/.test(b.text) ? { left: 600, hanging: 600 } : undefined;
      // a line that introduces a table or a box stays on the same page as it
      const keepNext = !!next && (next.t === "table" || next.t === "code");
      out.push(new Paragraph({ spacing: { after: 120, line }, indent: hang, keepNext, children: runs(b.text, body) }));
    } else if (b.t === "table") {
      out.push(table(b.head, b.body), new Paragraph({ spacing: { after: 60 }, children: [] }));
    } else if (b.t === "code") {
      out.push(box(b.lines), new Paragraph({ spacing: { after: 60 }, children: [] }));
    } else {
      const ref = b.t === "ol" ? "ol" : "ul", instance = ++listNo;
      for (const it of b.items) {
        out.push(new Paragraph({ numbering: { reference: ref, level: 0, instance }, spacing: { after: 80, line }, children: runs(it, body) }));
      }
    }
  });
  return out;
}

const read = (p) => fs.readFileSync(p, "utf-8");
const tasks = parse(read(path.join(HERE, "..", "docs", "HW5_TASKS.md")));
const script = parse(read(path.join(HERE, "build", "NARRATION.md")));
const today = new Date().toLocaleDateString("sv-SE", { timeZone: "Asia/Taipei" });

const top = new Paragraph({
  spacing: { after: 160 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: LINE, space: 4 } },
  children: [new TextRun({ text: `人工智慧導論 期末專題 第 54 組　Beat the Bell　更新於 ${today}`, font: FONT, size: 18, color: MUTED })],
});
const scriptStart = render(script, { body: 26, line: 360 });
scriptStart[0] = new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [new TextRun({ text: script[0].text, font: FONT })] });

const listLevel = (format, text) => ({
  levels: [{ level: 0, format, text, alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 480, hanging: 360 } } } }],
});
const doc = new Document({
  creator: "Group 54", title: "HW5 分工與旁白稿",
  styles: {
    default: {
      document: { run: { font: FONT, size: 24 }, paragraph: { spacing: { after: 120, line: 312 } } },
      heading1: { run: { font: FONT, size: 34, bold: true, color: "1D2733" }, paragraph: { spacing: { before: 120, after: 160 }, keepNext: true } },
      heading2: { run: { font: FONT, size: 28, bold: true, color: ACCENT }, paragraph: { spacing: { before: 280, after: 100 }, keepNext: true } },
    },
  },
  numbering: { config: [{ reference: "ol", ...listLevel(LevelFormat.DECIMAL, "%1.") }, { reference: "ul", ...listLevel(LevelFormat.BULLET, "•") }] },
  sections: [{
    properties: { page: { size: { width: PAGE_W, height: 16838 }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
      new TextRun({ text: "第 ", font: FONT, size: 18, color: MUTED }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18, color: MUTED }),
      new TextRun({ text: " 頁", font: FONT, size: 18, color: MUTED })] })] }) },
    children: [top, ...render(tasks), ...scriptStart],
  }],
});

fs.mkdirSync(path.dirname(OUT), { recursive: true });
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log(OUT); });
