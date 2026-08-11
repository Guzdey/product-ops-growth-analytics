import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = process.argv[2];
if (!outputDir) throw new Error("Usage: node build_retailrocket_workbook.mjs <output-dir>");

const payload = JSON.parse(await fs.readFile(path.join(outputDir, "workbook_data.json"), "utf8"));
const workbook = Workbook.create();
workbook.comments.setSelf({ displayName: "User" });

const colors = {
  navy: "#12304A",
  teal: "#147D73",
  paleTeal: "#DFF3F0",
  paleBlue: "#EAF2F8",
  paleGold: "#FFF3CD",
  text: "#24323D",
  muted: "#5B6B78",
  white: "#FFFFFF",
  line: "#D7E0E7",
};

const guide = workbook.worksheets.add("使用说明");
guide.showGridLines = false;
guide.mergeCells("A1:H2");
guide.getRange("A1").values = [["Retailrocket 电商行为数据小样例"]];
guide.getRange("A1:H2").format = {
  fill: colors.navy,
  font: { bold: true, color: colors.white, size: 20 },
  verticalAlignment: "center",
  horizontalAlignment: "left",
};

guide.getRange("A4:B4").values = [["项目", "说明"]];
guide.getRange("A5:B16").values = [
  ["数据来源", payload.metadata.source_url],
  ["许可", `${payload.metadata.license} · ${payload.metadata.license_url}`],
  ["随机种子", payload.metadata.seed],
  ["会话示例规则", `同一 visitorid 相邻事件间隔超过 ${payload.metadata.session_gap_minutes} 分钟则开始新会话`],
  ["随机事件样例", `${payload.metadata.counts.random_events} 行；接近真实事件分布，仅用于观察结构`],
  ["完整行为路径", `${payload.metadata.counts.journey_visitors} 位访客，${payload.metadata.counts.journey_events} 行；有目的选择，不可用于总体转化率`],
  ["商品属性", `${payload.metadata.counts.property_rows} 行；categoryid/available 可解释，其余匿名属性不可擅自解释`],
  ["分类树", `${payload.metadata.counts.category_rows} 行；仅包含样例商品相关分类及祖先节点`],
  ["原始字段", "timestamp、visitorid、event、itemid、transactionid；保持原值"],
  ["衍生字段", "event_time、event_cn、has_transaction_id、event_sequence、session_number；浅黄色标识"],
  ["关联覆盖率", `路径商品中 ${(payload.metadata.journey_item_property_coverage * 100).toFixed(1)}% 有属性记录；已提取分类中 ${(payload.metadata.category_tree_coverage * 100).toFixed(1)}% 可关联分类树`],
  ["时间说明", "timestamp 为 Unix 毫秒时间戳；event_time / property_time 按 UTC 转换"],
];

guide.getRange("D4:E4").values = [["行为类型", "随机样例条数"]];
const eventOrder = ["view", "addtocart", "transaction"];
guide.getRange("D5:E7").values = eventOrder.map((event) => [event, payload.metadata.event_counts_random[event] ?? 0]);

guide.getRange("D9:H9").merge();
guide.getRange("D9").values = [["建议阅读顺序"]];
guide.getRange("D10:H14").merge(true);
guide.getRange("D10:D14").values = [
  ["1. 先看“随机事件样例”，认识原始埋点结构。"],
  ["2. 再看“完整行为路径”，按 visitorid、session_number、event_sequence 追踪购买过程。"],
  ["3. 用 itemid 连接“商品属性”。"],
  ["4. 通过 property=categoryid 的 value 连接“分类树”。"],
  ["5. 样例不可代替完整数据做留存率或转化率结论。"],
];

guide.getRange("A4:B4").format = guide.getRange("D4:E4").format = {
  fill: colors.teal,
  font: { bold: true, color: colors.white },
};
guide.getRange("A5:A16").format = { fill: colors.paleBlue, font: { bold: true, color: colors.text } };
guide.getRange("A4:B16").format.borders = { preset: "inside", style: "thin", color: colors.line };
guide.getRange("D4:E7").format.borders = { preset: "inside", style: "thin", color: colors.line };
guide.getRange("D9:H9").format = { fill: colors.teal, font: { bold: true, color: colors.white } };
guide.getRange("D10:H14").format = { fill: colors.paleTeal, font: { color: colors.text }, wrapText: true };
guide.getRange("A1:H16").format.font = { name: "Microsoft YaHei", color: colors.text };
guide.getRange("A1:H2").format.font = { name: "Microsoft YaHei", bold: true, color: colors.white, size: 20 };
guide.getRange("A1:H16").format.verticalAlignment = "center";
guide.getRange("A:A").format.columnWidth = 18;
guide.getRange("B:B").format.columnWidth = 62;
guide.getRange("C:C").format.columnWidth = 3;
guide.getRange("D:D").format.columnWidth = 20;
guide.getRange("E:E").format.columnWidth = 18;
guide.getRange("F:H").format.columnWidth = 14;
guide.getRange("5:16").format.rowHeight = 26;
guide.getRange("A5:B16").format.wrapText = true;
guide.freezePanes.freezeRows(4);

function writeDataSheet(name, spec) {
  const sheet = workbook.worksheets.add(name);
  sheet.showGridLines = false;
  const matrix = [spec.headers, ...spec.rows];
  const range = sheet.getRangeByIndexes(0, 0, matrix.length, spec.headers.length);
  range.values = matrix;
  const table = sheet.tables.add(range, true, `${name.replace(/[^A-Za-z0-9]/g, "") || "Data"}Table${workbook.worksheets.items.length}`);
  table.style = "TableStyleMedium2";
  table.showFilterButton = true;
  sheet.getRangeByIndexes(0, 0, 1, spec.headers.length).format = {
    fill: colors.navy,
    font: { bold: true, color: colors.white, name: "Microsoft YaHei" },
    wrapText: true,
    verticalAlignment: "center",
  };
  sheet.getRangeByIndexes(1, 0, Math.max(1, spec.rows.length), spec.headers.length).format.font = {
    name: "Microsoft YaHei",
    color: colors.text,
  };
  const derivedStart = spec.headers.findIndex((header) => ["event_time", "property_time"].includes(header));
  if (derivedStart >= 0) {
    sheet.getRangeByIndexes(0, derivedStart, matrix.length, spec.headers.length - derivedStart).format.fill = colors.paleGold;
    sheet.getRangeByIndexes(0, derivedStart, 1, spec.headers.length - derivedStart).format.font = {
      bold: true,
      color: colors.text,
      name: "Microsoft YaHei",
    };
  }
  for (const timestampHeader of ["event_time", "property_time"]) {
    const idx = spec.headers.indexOf(timestampHeader);
    if (idx >= 0 && spec.rows.length > 0) {
      sheet.getRangeByIndexes(1, idx, spec.rows.length, 1).setNumberFormat("yyyy-mm-dd hh:mm:ss");
    }
  }
  for (const integerHeader of [
    "timestamp",
    "visitorid",
    "itemid",
    "transactionid",
    "event_sequence",
    "session_number",
    "categoryid",
    "parentid",
  ]) {
    const idx = spec.headers.indexOf(integerHeader);
    if (idx >= 0 && spec.rows.length > 0) {
      sheet.getRangeByIndexes(1, idx, spec.rows.length, 1).setNumberFormat("0");
    }
  }
  sheet.freezePanes.freezeRows(1);
  sheet.getUsedRange().format.autofitColumns();
  sheet.getUsedRange().format.autofitRows();
  for (let col = 0; col < spec.headers.length; col += 1) {
    const column = sheet.getRangeByIndexes(0, col, matrix.length, 1);
    const header = spec.headers[col];
    if (["timestamp", "visitorid", "itemid", "transactionid"].includes(header)) column.format.columnWidth = 18;
    else if (["event_time", "property_time"].includes(header)) column.format.columnWidth = 21;
    else if (header === "property_meaning_cn") column.format.columnWidth = 30;
    else if (header === "value") column.format.columnWidth = 26;
    else column.format.columnWidth = Math.min(18, Math.max(12, header.length + 3));
  }
  return sheet;
}

for (const [name, spec] of Object.entries(payload.sheets)) writeDataSheet(name, spec);

await fs.mkdir(outputDir, { recursive: true });
const workbookPath = path.join(outputDir, "Retailrocket_数据样例.xlsx");
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(workbookPath);

const inspections = [];
inspections.push((await workbook.inspect({ kind: "sheet", include: "id,name", maxChars: 3000 })).ndjson);
inspections.push((await workbook.inspect({
  kind: "table",
  sheetId: "使用说明",
  range: "A1:H16",
  include: "values,formulas",
  tableMaxRows: 16,
  tableMaxCols: 8,
  maxChars: 6000,
})).ndjson);
inspections.push((await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
  maxChars: 3000,
})).ndjson);
await fs.writeFile(path.join(outputDir, "workbook_inspection.ndjson"), inspections.join("\n"), "utf8");

const previewRanges = {
  "使用说明": "A1:H16",
  "随机事件样例": "A1:J24",
  "完整行为路径": "A1:J30",
  "商品属性": "A1:F30",
  "分类树": "A1:B30",
};
for (const [sheetName, range] of Object.entries(previewRanges)) {
  const preview = await workbook.render({ sheetName, range, scale: 1.5, format: "png" });
  await fs.writeFile(path.join(outputDir, `preview_${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
}

console.log(JSON.stringify({ workbookPath, sheets: Object.keys(payload.sheets).length + 1 }));
