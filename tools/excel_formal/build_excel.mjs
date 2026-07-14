import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";


const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(SCRIPT_DIR, "..", "..");
const EXPORT_DIR = path.join(PROJECT_ROOT, "reports", "data_exports");
const OUTPUT_DIR = path.join(PROJECT_ROOT, "outputs", "formal_delivery");
const PREVIEW_DIR = path.join(OUTPUT_DIR, "qa_previews");
const OUTPUT_PATH = path.join(OUTPUT_DIR, "eCommerce_brand_priority_formal.xlsx");

const NAVY = "#243B53";
const BLUE = "#2F5D8A";
const ORANGE = "#D8873B";
const LIGHT_BLUE = "#E8F0F7";
const LIGHT_ORANGE = "#F8EBDD";
const LIGHT_GRAY = "#EEF2F5";
const MID_GRAY = "#B8C4CE";
const WHITE = "#FFFFFF";
const INK = "#24313D";


function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;
  const clean = text.replace(/^\uFEFF/, "");
  for (let index = 0; index < clean.length; index += 1) {
    const char = clean[index];
    if (inQuotes) {
      if (char === '"' && clean[index + 1] === '"') {
        field += '"';
        index += 1;
      } else if (char === '"') {
        inQuotes = false;
      } else {
        field += char;
      }
    } else if (char === '"') {
      inQuotes = true;
    } else if (char === ",") {
      row.push(field);
      field = "";
    } else if (char === "\n") {
      row.push(field.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      field = "";
    } else {
      field += char;
    }
  }
  if (field.length || row.length) {
    row.push(field.replace(/\r$/, ""));
    rows.push(row);
  }
  return rows.filter((item) => item.some((value) => value !== ""));
}


function coerce(value) {
  if (value === "") return null;
  if (value === "True" || value === "true") return true;
  if (value === "False" || value === "false") return false;
  if (/^-?\d+(\.\d+)?$/.test(value)) return Number(value);
  return value;
}


async function readCsv(name) {
  const text = await fs.readFile(path.join(EXPORT_DIR, name), "utf8");
  const rows = parseCsv(text);
  const headers = rows[0];
  return rows.slice(1).map((values) => Object.fromEntries(headers.map((header, index) => [header, coerce(values[index] ?? "")])))
}


function styleTitle(sheet, range, title) {
  sheet.getRange(range).merge();
  const cell = sheet.getRange(range.split(":")[0]);
  cell.values = [[title]];
  cell.format = {
    fill: NAVY,
    font: { bold: true, color: WHITE, size: 18 },
    verticalAlignment: "center",
    horizontalAlignment: "left",
  };
}


function styleHeader(range) {
  range.format = {
    fill: BLUE,
    font: { bold: true, color: WHITE },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "bottom", style: "thin", color: NAVY },
  };
}


function styleKpiCard(sheet, labelRange, valueRange, label, formula, numberFormat, fill) {
  sheet.getRange(labelRange).merge();
  sheet.getRange(valueRange).merge();
  const labelCell = sheet.getRange(labelRange.split(":")[0]);
  const valueCell = sheet.getRange(valueRange.split(":")[0]);
  labelCell.values = [[label]];
  valueCell.formulas = [[formula]];
  sheet.getRange(labelRange).format = {
    fill,
    font: { bold: true, color: NAVY, size: 11 },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    borders: { preset: "outside", style: "thin", color: MID_GRAY },
  };
  sheet.getRange(valueRange).format = {
    fill,
    font: { bold: true, color: INK, size: 19 },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    numberFormat,
    borders: { preset: "outside", style: "thin", color: MID_GRAY },
  };
}


function writeObjectTable(sheet, startCell, rows, columns) {
  const startMatch = /^([A-Z]+)(\d+)$/.exec(startCell);
  if (!startMatch) throw new Error(`Invalid start cell: ${startCell}`);
  const startRow = Number(startMatch[2]) - 1;
  const startCol = startMatch[1].split("").reduce((acc, char) => acc * 26 + char.charCodeAt(0) - 64, 0) - 1;
  const matrix = [columns.map((item) => item.label), ...rows.map((row) => columns.map((item) => row[item.key] ?? null))];
  sheet.getRangeByIndexes(startRow, startCol, matrix.length, columns.length).values = matrix;
  return {
    matrix,
    range: sheet.getRangeByIndexes(startRow, startCol, matrix.length, columns.length),
    header: sheet.getRangeByIndexes(startRow, startCol, 1, columns.length),
    data: sheet.getRangeByIndexes(startRow + 1, startCol, rows.length, columns.length),
  };
}


const [kpiRows, qualityRows, sourceRows, brandRows, sensitivityRows, reconciliationRows] = await Promise.all([
  readCsv("kpi_summary_48h.csv"),
  readCsv("cohort_quality.csv"),
  readCsv("source_profile.csv"),
  readCsv("brand_metrics_48h.csv"),
  readCsv("window_sensitivity.csv"),
  readCsv("reconciliation_summary.csv"),
]);

const workbook = Workbook.create();
const summary = workbook.worksheets.add("01_管理层总览");
const brand = workbook.worksheets.add("02_品牌优先级");
const sensitivity = workbook.worksheets.add("03_窗口敏感性");
const quality = workbook.worksheets.add("04_对账与质量");
const parameters = workbook.worksheets.add("00_口径与参数");
const kpiData = workbook.worksheets.add("05_KPI数据");

for (const sheet of [summary, brand, sensitivity, quality, parameters, kpiData]) {
  sheet.showGridLines = false;
}

// KPI source sheet.
const kpiEntries = Object.entries(kpiRows[0]);
kpiData.getRangeByIndexes(0, 0, kpiEntries.length + 1, 2).values = [["指标", "数值"], ...kpiEntries];
styleHeader(kpiData.getRange("A1:B1"));
kpiData.getRange("A:B").format.columnWidth = 26;
kpiData.freezePanes.freezeRows(1);

// Parameters and metric definitions.
styleTitle(parameters, "A1:F2", "品牌运营优先级：口径与可调参数");
parameters.getRange("A4:B6").values = [
  ["参数", "当前值"],
  ["高覆盖量阈值（品牌样本数中位数）", null],
  ["移除/购买比筛选线", 1.5],
];
const firstBrandRow = 3;
const lastBrandRow = brandRows.length + 2;

parameters.getRange("B5").formulas = [[
  `=MEDIAN('02_品牌优先级'!$B$${firstBrandRow}:$B$${lastBrandRow})`
]];
styleHeader(parameters.getRange("A4:B4"));
parameters.getRange("B5:B6").format.numberFormat = "0.00";
parameters.getRange("A8:F14").values = [
  ["口径", "定义", "粒度", "分母", "用途", "限制"],
  ["48小时购买率", "A/(A+B+C)", "会话×商品", "完整48小时首次观测加购", "主转化指标", "不是用户购买率"],
  ["未明确处置率", "B/(A+B+C)", "会话×商品", "完整48小时首次观测加购", "保留未购买也未移除样本", "B不是已确认流失"],
  ["移除率", "C/(A+B+C)", "会话×商品", "完整48小时首次观测加购", "描述移除结果", "购买优先"],
  ["明确结果购买率", "A/(A+C)", "会话×商品", "仅A+C", "比较明确结果", "不能代替整体购买率"],
  ["移除/购买比", "C/A", "品牌", "A>0且A+C≥100", "品牌排查信号", "不是概率或因果风险"],
  ["已知品牌覆盖率", "已知品牌样本/全队列", "会话×商品", "完整48小时队列", "判断品牌榜覆盖", "未知品牌不参与排名"],
];
styleHeader(parameters.getRange("A8:F8"));
parameters.getRange("A4:F14").format.wrapText = true;
parameters.getRange("A:A").format.columnWidth = 30;
parameters.getRange("B:B").format.columnWidth = 23;
parameters.getRange("C:F").format.columnWidth = 22;
parameters.freezePanes.freezeRows(4);

// Brand detail with formula-driven priority columns.
styleTitle(brand, "A1:Q1", "已知品牌 48 小时运营排查优先级（A+B+C）");
const brandColumns = [
  ["brand", "品牌"],
  ["brand_cohort_count", "完整样本数"],
  ["purchase_count", "购买A"],
  ["unresolved_count", "未明确B"],
  ["remove_count", "移除C"],
  ["clear_outcome_count", "明确结果A+C"],
  ["distinct_users", "用户数"],
  ["distinct_products", "商品数"],
  ["purchase_rate_pct", "购买率"],
  ["unresolved_rate_pct", "未明确处置率"],
  ["remove_rate_pct", "移除率"],
  ["clear_purchase_rate_pct", "明确结果购买率"],
  ["remove_to_purchase_ratio", "移除/购买比"],
];
const brandMatrix = [brandColumns.map((item) => item[1])];
for (const row of brandRows) brandMatrix.push(brandColumns.map((item) => row[item[0]]));
brandMatrix[0].push("覆盖量层", "比值层", "优先级", "建议动作");
for (let index = 1; index < brandMatrix.length; index += 1) brandMatrix[index].push(null, null, null, null);
brand.getRangeByIndexes(1, 0, brandMatrix.length, 17).values = brandMatrix;
styleHeader(brand.getRange("A2:Q2"));
brand.getRange("N3").formulas = [["=IF(B3>='00_口径与参数'!$B$5,\"高覆盖量\",\"低覆盖量\")"]];
brand.getRange(`N3:N${lastBrandRow}`).fillDown();
brand.getRange("O3").formulas = [["=IF(M3>='00_口径与参数'!$B$6,\"高比值\",\"低比值\")"]];
brand.getRange(`O3:O${lastBrandRow}`).fillDown();
brand.getRange("P3").formulas = [["=IF(AND(N3=\"高覆盖量\",O3=\"高比值\"),\"优先核查\",IF(N3=\"高覆盖量\",\"规模优势/维护\",IF(O3=\"高比值\",\"监控并补样本\",\"常规观察\")))"]];
brand.getRange(`P3:P${lastBrandRow}`).fillDown();
brand.getRange("Q3").formulas = [["=IF(P3=\"优先核查\",\"拆分至SKU并核查库存/费用/配送/结账\",IF(P3=\"监控并补样本\",\"补样本后再判断\",IF(P3=\"规模优势/维护\",\"维持并监控异常\",\"常规观察\")))"]];
brand.getRange(`Q3:Q${lastBrandRow}`).fillDown();
brand.tables.add(`A2:Q${lastBrandRow}`, true, "BrandPriorityTable");
brand.getRange(`B3:H${lastBrandRow}`).format.numberFormat = "#,##0";
brand.getRange(`I3:L${lastBrandRow}`).format.numberFormat = "0.00\"%\"";
brand.getRange(`M3:M${lastBrandRow}`).format.numberFormat = "0.00";
brand.getRange(`A2:Q${lastBrandRow}`).format.wrapText = false;
brand.getRange("A:A").format.columnWidth = 17;
brand.getRange("B:H").format.columnWidth = 14;
brand.getRange("I:M").format.columnWidth = 17;
brand.getRange("N:P").format.columnWidth = 16;
brand.getRange("Q:Q").format.columnWidth = 36;
brand.freezePanes.freezeRows(2);
brand.freezePanes.freezeColumns(1);
brand.getRange(`P3:P${lastBrandRow}`).conditionalFormats.add("containsText", { text: "优先核查", format: { fill: LIGHT_ORANGE, font: { bold: true, color: ORANGE } } });
brand.getRange(`P3:P${lastBrandRow}`).conditionalFormats.add("containsText", { text: "规模优势", format: { fill: LIGHT_BLUE, font: { color: BLUE } } });

// Sensitivity sheet.
styleTitle(sensitivity, "A1:J2", "同一批 72 小时完整样本：24/48/72 小时敏感性");
const sensitivityColumns = [
  { key: "window_hours", label: "窗口（小时）" },
  { key: "common_cohort_count", label: "共同样本数" },
  { key: "purchase_count", label: "购买A" },
  { key: "unresolved_count", label: "未明确B" },
  { key: "remove_count", label: "移除C" },
  { key: "purchase_rate_pct", label: "购买率" },
  { key: "unresolved_rate_pct", label: "未明确处置率" },
  { key: "remove_rate_pct", label: "移除率" },
  { key: "clear_purchase_rate_pct", label: "明确结果购买率" },
  { key: "remove_to_purchase_ratio", label: "移除/购买比" },
];
writeObjectTable(sensitivity, "A4", sensitivityRows, sensitivityColumns);
styleHeader(sensitivity.getRange("A4:J4"));
sensitivity.getRange("B5:E7").format.numberFormat = "#,##0";
sensitivity.getRange("F5:I7").format.numberFormat = "0.00\"%\"";
sensitivity.getRange("J5:J7").format.numberFormat = "0.00";
sensitivity.getRange("A:J").format.columnWidth = 18;
// Use a compact helper range for three outcome-rate series.
sensitivity.getRange("L4:O7").values = [
  ["窗口", "购买率", "未明确处置率", "移除率"],
  ...sensitivityRows.map((row) => [`${row.window_hours}小时`, row.purchase_rate_pct, row.unresolved_rate_pct, row.remove_rate_pct]),
];
const chart = sensitivity.charts.add("bar", sensitivity.getRange("L4:O7"));
chart.title = "24/48/72 小时结果率比较（%）";
chart.hasLegend = true;
chart.yAxis = { numberFormatCode: "0.00" };
chart.setPosition("A10", "J27");
sensitivity.freezePanes.freezeRows(4);

// Quality and reconciliation.
styleTitle(quality, "A1:H2", "数据质量与跨工具对账");
quality.getRange("A4:B4").values = [["主队列质量指标", "数值"]];
styleHeader(quality.getRange("A4:B4"));
const qualityEntries = Object.entries(qualityRows[0]);
quality.getRangeByIndexes(4, 0, qualityEntries.length, 2).values = qualityEntries;
quality.getRange("D4:E4").values = [["原始表质量指标", "数值"]];
styleHeader(quality.getRange("D4:E4"));
const sourceEntries = Object.entries(sourceRows[0]);
quality.getRangeByIndexes(4, 3, sourceEntries.length, 2).values = sourceEntries;
const reconciliationStart = Math.max(qualityEntries.length, sourceEntries.length) + 7;
quality.getRangeByIndexes(reconciliationStart - 1, 0, 1, 7).values = [["检查", "SQL", "Python", "差异", "容差", "通过", "严重级别"]];
styleHeader(quality.getRangeByIndexes(reconciliationStart - 1, 0, 1, 7));
quality.getRangeByIndexes(reconciliationStart, 0, reconciliationRows.length, 7).values = reconciliationRows.map((row) => [
  row.check_name, row.sql_value, row.python_value, row.difference, row.tolerance, row.passed, row.severity,
]);
quality.getRange(`A${reconciliationStart + 1}:A${reconciliationStart + reconciliationRows.length}`).format.columnWidth = 42;
quality.getRange("A:A").format.columnWidth = 34;
quality.getRange("B:B").format.columnWidth = 22;
quality.getRange("D:D").format.columnWidth = 34;
quality.getRange("E:E").format.columnWidth = 22;
quality.getRange("F:G").format.columnWidth = 15;
quality.freezePanes.freezeRows(4);

// Management summary with formula-backed KPI cards.
styleTitle(summary, "A1:L2", "品牌运营排查优先级｜管理层总览");
summary.getRange("A3:L3").merge();
summary.getRange("A3").values = [["主口径：有效会话×商品首次观测加购后48小时；UTC；购买优先；未知品牌不参与排名"]];
summary.getRange("A3:L3").format = { fill: LIGHT_GRAY, font: { color: INK, italic: true }, horizontalAlignment: "left" };
styleKpiCard(summary, "A5:C5", "A6:C8", "完整48小时样本", "='05_KPI数据'!$B$2", "#,##0", LIGHT_BLUE);
styleKpiCard(summary, "D5:F5", "D6:F8", "48小时购买率", "='05_KPI数据'!$B$11/100", "0.00%", LIGHT_BLUE);
styleKpiCard(summary, "G5:I5", "G6:I8", "未明确处置率", "='05_KPI数据'!$B$12/100", "0.00%", LIGHT_GRAY);
styleKpiCard(summary, "J5:L5", "J6:L8", "移除率", "='05_KPI数据'!$B$13/100", "0.00%", LIGHT_ORANGE);
styleKpiCard(summary, "A10:C10", "A11:C13", "明确结果购买率", "='05_KPI数据'!$B$14/100", "0.00%", LIGHT_BLUE);
styleKpiCard(summary, "D10:F10", "D11:F13", "总体移除/购买比", "='05_KPI数据'!$B$15", "0.00", LIGHT_ORANGE);
styleKpiCard(summary, "G10:I10", "G11:I13", "已知品牌覆盖率", "='05_KPI数据'!$B$16/100", "0.00%", LIGHT_GRAY);
styleKpiCard(summary, "J10:L10", "J11:L13", "优先核查品牌数", `=COUNTIF('02_品牌优先级'!$P$3:$P$${lastBrandRow},\"优先核查\")`, "#,##0", LIGHT_ORANGE);

summary.getRange("A16:B19").values = [
  ["结果", "样本数"],
  ["购买A", kpiRows[0].purchase_count],
  ["未明确B", kpiRows[0].unresolved_count],
  ["移除C", kpiRows[0].remove_count],
];
styleHeader(summary.getRange("A16:B16"));
const outcomeChart = summary.charts.add("doughnut", summary.getRange("A16:B19"));
outcomeChart.title = "48小时结果构成";
outcomeChart.hasLegend = true;
outcomeChart.setPosition("D16", "L29");
summary.getRange("A31:G31").values = [["品牌", "完整样本", "购买率", "未明确处置率", "移除率", "移除/购买比", "行动"]];
styleHeader(summary.getRange("A31:G31"));
for (let offset = 0; offset < 10; offset += 1) {
  const sourceRow = 3 + offset;
  const targetRow = 32 + offset;
  summary.getRange(`A${targetRow}:G${targetRow}`).formulas = [[
    `='02_品牌优先级'!A${sourceRow}`,
    `='02_品牌优先级'!B${sourceRow}`,
    `='02_品牌优先级'!I${sourceRow}/100`,
    `='02_品牌优先级'!J${sourceRow}/100`,
    `='02_品牌优先级'!K${sourceRow}/100`,
    `='02_品牌优先级'!M${sourceRow}`,
    `='02_品牌优先级'!Q${sourceRow}`,
  ]];
}
summary.getRange("B32:B41").format.numberFormat = "#,##0";
summary.getRange("C32:E41").format.numberFormat = "0.00%";
summary.getRange("F32:F41").format.numberFormat = "0.00";
summary.getRange("A31:G41").format.wrapText = true;
summary.getRange("A:A").format.columnWidth = 18;
summary.getRange("B:F").format.columnWidth = 17;
summary.getRange("G:G").format.columnWidth = 42;
summary.getRange("H:L").format.columnWidth = 13;
summary.freezePanes.freezeRows(3);

await fs.mkdir(PREVIEW_DIR, { recursive: true });
const previews = [
  ["01_管理层总览", "A1:L42", "01_summary.png"],
  ["00_口径与参数", "A1:F14", "00_parameters.png"],
  ["02_品牌优先级", "A1:Q24", "02_brand.png"],
  ["03_窗口敏感性", "A1:J27", "03_sensitivity.png"],
  ["04_对账与质量", `A1:G${reconciliationStart + Math.min(reconciliationRows.length, 18)}`, "04_quality.png"],
];
for (const [sheetName, range, fileName] of previews) {
  const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
  await fs.writeFile(path.join(PREVIEW_DIR, fileName), new Uint8Array(await preview.arrayBuffer()));
}

const summaryCheck = await workbook.inspect({
  kind: "table",
  range: "01_管理层总览!A1:L42",
  include: "values,formulas",
  tableMaxRows: 42,
  tableMaxCols: 12,
  maxChars: 5000,
});
console.log(summaryCheck.ndjson);
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

await fs.mkdir(OUTPUT_DIR, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(OUTPUT_PATH);
console.log(OUTPUT_PATH);
