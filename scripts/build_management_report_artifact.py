"""Build the validated, source-backed management report artifact.

This script only reads reviewed CSV exports and formal SQL files. It does not
connect to PostgreSQL or modify source data.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = PROJECT_ROOT / "reports" / "data_exports"
SQL_DIR = PROJECT_ROOT / "sql" / "formal"
OUTPUT_PATH = PROJECT_ROOT / "reports" / "management_report_artifact.json"


def read_rows(name: str) -> list[dict[str, str]]:
    with (EXPORT_DIR / name).open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def read_sql(name: str) -> str:
    return (SQL_DIR / name).read_text(encoding="utf-8")


def number(row: dict[str, str], field: str) -> float:
    return float(row[field])


def integer(row: dict[str, str], field: str) -> int:
    return int(float(row[field]))


def rate(row: dict[str, str], field: str) -> float:
    """Convert an exported percentage-point value to a fractional rate."""
    return number(row, field) / 100


def build_sources(generated_at: str) -> list[dict[str, object]]:
    common_filters = [
        "event_time interpreted in UTC",
        "valid user_session excludes NULL, blank, 'nan', 'null', and 'none'",
        "one sample per user_session × product_id at first observed cart event",
        "only samples with a complete follow-up window are retained",
    ]
    return [
        {
            "id": "src_kpi_48h",
            "label": "48 小时正式 KPI SQL",
            "path": "sql/formal/02_kpi_summary_48h.sql",
            "query": {
                "engine": "PostgreSQL",
                "language": "sql",
                "id": "formal_kpi_summary_48h",
                "description": "从原始事件表构建完整 48 小时会话—商品队列并汇总 KPI。",
                "sql": read_sql("02_kpi_summary_48h.sql"),
                "executed_at": generated_at,
                "tables_used": ["makeup_consumer_events.dec"],
                "filters": common_filters + [
                    "follow-up window = [first_cart_time, first_cart_time + 48 hours]",
                    "A = purchase observed; C = no purchase but remove_from_cart observed; B = neither",
                ],
                "metric_definitions": [
                    "总体购买率 = A 组会话—商品样本数 / 完整 48 小时队列样本数",
                    "未明确处置率 = B 组会话—商品样本数 / 完整 48 小时队列样本数",
                    "移除率 = C 组会话—商品样本数 / 完整 48 小时队列样本数",
                    "明确结果购买率 = A / (A + C)，只作辅助诊断，不代替总体购买率",
                    "已知品牌覆盖率 = 品牌非空队列样本数 / 完整 48 小时队列样本数",
                ],
            },
        },
        {
            "id": "src_brand_48h",
            "label": "48 小时品牌优先级 SQL",
            "path": "sql/formal/03_brand_metrics_48h.sql",
            "query": {
                "engine": "PostgreSQL",
                "language": "sql",
                "id": "formal_brand_metrics_48h",
                "description": "对已知品牌队列按覆盖量和移除/购买比构造描述性排查优先级。",
                "sql": read_sql("03_brand_metrics_48h.sql"),
                "executed_at": generated_at,
                "tables_used": ["makeup_consumer_events.dec"],
                "filters": common_filters + [
                    "follow-up window = 48 hours",
                    "brand must be known after placeholder normalization",
                    "eligible brands satisfy the formal SQL sample threshold",
                    "priority quadrant = volume above eligible-brand median and remove/purchase ratio >= 1.5",
                ],
                "metric_definitions": [
                    "品牌样本数 = 该品牌的会话—商品队列行数",
                    "移除/购买比 = C 组样本数 / A 组样本数；不是流失概率",
                    "优先核查是启发式运营排序，不是因果风险标签或行业标准",
                ],
            },
        },
        {
            "id": "src_window_sensitivity",
            "label": "窗口敏感性 SQL",
            "path": "sql/formal/05_window_sensitivity.sql",
            "query": {
                "engine": "PostgreSQL",
                "language": "sql",
                "id": "formal_window_sensitivity",
                "description": "在同一批具备完整 72 小时观察期的样本上比较 24、48、72 小时标签。",
                "sql": read_sql("05_window_sensitivity.sql"),
                "executed_at": generated_at,
                "tables_used": ["makeup_consumer_events.dec"],
                "filters": common_filters + [
                    "common cohort requires a complete 72-hour follow-up window",
                    "windows compared = 24, 48, and 72 hours",
                ],
                "metric_definitions": [
                    "窗口购买率 = 对应窗口 A 组数 / 共同 72 小时完整队列数",
                    "跨窗口差异只反映标签窗口敏感性，不证明用户行为机制",
                ],
            },
        },
        {
            "id": "src_quality",
            "label": "数据质量检查 SQL",
            "path": "sql/formal/00_source_profile.sql; sql/formal/01_cohort_quality.sql",
            "query": {
                "engine": "PostgreSQL",
                "language": "sql",
                "id": "formal_data_quality",
                "description": "原始事件层与正式 48 小时队列层的数据质量检查。",
                "sql": read_sql("00_source_profile.sql") + "\n\n" + read_sql("01_cohort_quality.sql"),
                "executed_at": generated_at,
                "tables_used": ["makeup_consumer_events.dec"],
                "filters": [
                    "source period = full available December 2019 extract",
                    "duplicate count uses business fields because the extract has no event_id",
                    "duplicates are reported but not automatically deleted",
                ],
                "metric_definitions": [
                    "精确重复超额行 = 按全部业务字段分组后 SUM(count - 1)",
                    "不完整尾部样本 = 首次加购后无法获得完整 48 小时观察期的队列候选",
                    "缺失品牌在正式品牌榜中排除，但在覆盖率和局限性中保留",
                ],
            },
        },
    ]


def build_artifact() -> dict[str, object]:
    generated_at = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")

    kpi_raw = read_rows("kpi_summary_48h.csv")[0]
    quality_raw = read_rows("cohort_quality.csv")[0]
    source_raw = read_rows("source_profile.csv")[0]
    brand_raw = read_rows("brand_metrics_48h.csv")
    sensitivity_raw = read_rows("window_sensitivity.csv")

    kpi = {
        "cohort_count": integer(kpi_raw, "cohort_count"),
        "purchase_count": integer(kpi_raw, "purchase_count"),
        "unresolved_count": integer(kpi_raw, "unresolved_count"),
        "remove_count": integer(kpi_raw, "remove_count"),
        "purchase_rate": rate(kpi_raw, "purchase_rate_pct"),
        "unresolved_rate": rate(kpi_raw, "unresolved_rate_pct"),
        "remove_rate": rate(kpi_raw, "remove_rate_pct"),
        "clear_purchase_rate": rate(kpi_raw, "clear_purchase_rate_pct"),
        "remove_to_purchase_ratio": number(kpi_raw, "remove_to_purchase_ratio"),
        "known_brand_coverage": rate(kpi_raw, "known_brand_coverage_pct"),
    }

    outcome_rows = [
        {
            "result_code": "A",
            "result": "48小时内购买",
            "stage_order": 1,
            "count": kpi["purchase_count"],
            "rate": kpi["purchase_rate"],
            "numerator": kpi["purchase_count"],
            "denominator": kpi["cohort_count"],
            "definition": "窗口内观察到 purchase；购买优先于移除",
        },
        {
            "result_code": "B",
            "result": "无购买且无移除",
            "stage_order": 2,
            "count": kpi["unresolved_count"],
            "rate": kpi["unresolved_rate"],
            "numerator": kpi["unresolved_count"],
            "denominator": kpi["cohort_count"],
            "definition": "窗口内既未观察到 purchase，也未观察到 remove_from_cart",
        },
        {
            "result_code": "C",
            "result": "未购买但移除",
            "stage_order": 3,
            "count": kpi["remove_count"],
            "rate": kpi["remove_rate"],
            "numerator": kpi["remove_count"],
            "denominator": kpi["cohort_count"],
            "definition": "窗口内无 purchase，但观察到 remove_from_cart",
        },
    ]

    brand_rows: list[dict[str, object]] = []
    for rank, row in enumerate(brand_raw, start=1):
        brand_rows.append(
            {
                "rank_by_volume": rank,
                "brand": row["brand"],
                "brand_cohort_count": integer(row, "brand_cohort_count"),
                "purchase_count": integer(row, "purchase_count"),
                "unresolved_count": integer(row, "unresolved_count"),
                "remove_count": integer(row, "remove_count"),
                "clear_outcome_count": integer(row, "clear_outcome_count"),
                "distinct_users": integer(row, "distinct_users"),
                "distinct_sessions": integer(row, "distinct_sessions"),
                "distinct_products": integer(row, "distinct_products"),
                "brand_share": rate(row, "brand_share_pct"),
                "purchase_rate": rate(row, "purchase_rate_pct"),
                "unresolved_rate": rate(row, "unresolved_rate_pct"),
                "remove_rate": rate(row, "remove_rate_pct"),
                "clear_purchase_rate": rate(row, "clear_purchase_rate_pct"),
                "remove_to_purchase_ratio": number(row, "remove_to_purchase_ratio"),
                "volume_median_count": integer(row, "volume_median_count"),
                "remove_to_purchase_threshold": number(row, "remove_to_purchase_threshold"),
                "volume_band": row["volume_band"],
                "risk_band": row["risk_band"],
                "priority_quadrant": row["priority_quadrant"],
            }
        )

    priority_rows = [row for row in brand_rows if row["priority_quadrant"] == "优先核查"]
    priority_rows.sort(key=lambda row: (-int(row["brand_cohort_count"]), str(row["brand"])))

    sensitivity_rows: list[dict[str, object]] = []
    outcome_columns = [
        ("购买", "purchase_count", "purchase_rate_pct"),
        ("无购买且无移除", "unresolved_count", "unresolved_rate_pct"),
        ("未购买但移除", "remove_count", "remove_rate_pct"),
    ]
    for row in sensitivity_raw:
        for outcome, count_field, rate_field in outcome_columns:
            sensitivity_rows.append(
                {
                    "window_hours": integer(row, "window_hours"),
                    "window": f"{integer(row, 'window_hours')}小时",
                    "outcome": outcome,
                    "count": integer(row, count_field),
                    "rate": rate(row, rate_field),
                    "common_cohort_count": integer(row, "common_cohort_count"),
                    "purchase_count": integer(row, "purchase_count"),
                    "unresolved_count": integer(row, "unresolved_count"),
                    "remove_count": integer(row, "remove_count"),
                    "clear_purchase_rate": rate(row, "clear_purchase_rate_pct"),
                    "remove_to_purchase_ratio": number(row, "remove_to_purchase_ratio"),
                }
            )

    quality_rows = [
        {
            "scope": "原始事件",
            "row_count": integer(source_raw, "source_row_count"),
            "missing_session_rows": integer(source_raw, "missing_session_rows"),
            "missing_brand_rows": integer(source_raw, "missing_brand_rows"),
            "missing_category_code_rows": integer(source_raw, "missing_category_code_rows"),
            "nonpositive_price_rows": integer(source_raw, "nonpositive_price_rows"),
            "exact_duplicate_excess_rows": integer(source_raw, "exact_duplicate_excess_rows"),
            "incomplete_tail_rows": 0,
            "label_inconsistency_rows": 0,
        },
        {
            "scope": "正式48小时队列",
            "row_count": integer(quality_raw, "complete_48h_rows"),
            "missing_session_rows": integer(quality_raw, "invalid_cart_key_event_rows"),
            "missing_brand_rows": integer(quality_raw, "missing_brand_rows"),
            "missing_category_code_rows": integer(quality_raw, "missing_category_code_rows"),
            "nonpositive_price_rows": integer(quality_raw, "nonpositive_price_rows"),
            "exact_duplicate_excess_rows": integer(quality_raw, "duplicate_session_product_excess_rows"),
            "incomplete_tail_rows": integer(quality_raw, "incomplete_tail_rows_excluded"),
            "label_inconsistency_rows": integer(quality_raw, "inconsistent_label_rows"),
        },
    ]

    sources = build_sources(generated_at)
    title = "品牌运营排查优先级"

    manifest = {
        "version": 1,
        "surface": "report",
        "title": title,
        "description": "基于完整 48 小时会话—商品队列的品牌运营排查优先级与数据质量说明。",
        "generatedAt": generated_at,
        "sources": sources,
        "cards": [
            {
                "id": "card_cohort",
                "description": "具有完整 48 小时观察期的首次观测加购会话—商品样本。",
                "dataset": "kpi_48h",
                "sourceId": "src_kpi_48h",
                "metrics": [{"label": "正式队列样本", "field": "cohort_count", "format": "compact"}],
            },
            {
                "id": "card_purchase_rate",
                "description": "48 小时内观察到购买的队列样本占比。",
                "dataset": "kpi_48h",
                "sourceId": "src_kpi_48h",
                "metrics": [{"label": "总体购买率", "field": "purchase_rate", "format": "percent"}],
            },
            {
                "id": "card_unresolved_rate",
                "description": "48 小时内既未购买也未移除的队列样本占比。",
                "dataset": "kpi_48h",
                "sourceId": "src_kpi_48h",
                "metrics": [{"label": "未明确处置率", "field": "unresolved_rate", "format": "percent"}],
            },
            {
                "id": "card_remove_rate",
                "description": "48 小时内没有购买但发生移除的队列样本占比。",
                "dataset": "kpi_48h",
                "sourceId": "src_kpi_48h",
                "metrics": [{"label": "移除率", "field": "remove_rate", "format": "percent"}],
            },
            {
                "id": "card_brand_coverage",
                "description": "正式队列中品牌非空、可以进入品牌比较的样本占比。",
                "dataset": "kpi_48h",
                "sourceId": "src_kpi_48h",
                "metrics": [{"label": "已知品牌覆盖率", "field": "known_brand_coverage", "format": "percent"}],
            },
        ],
        "charts": [
            {
                "id": "chart_outcome_mix",
                "title": "48 小时结果构成",
                "subtitle": "多数加购样本在观察窗口内既未购买也未移除。",
                "intent": "composition",
                "question": "完整 48 小时队列最终落入 A、B、C 的样本量分别是多少？",
                "rationale": "横向条形图便于比较三个互斥结果的数量差异。",
                "type": "bar",
                "dataset": "outcome_mix",
                "sourceId": "src_kpi_48h",
                "encodings": {
                    "x": {"field": "result", "type": "nominal", "label": "48 小时结果"},
                    "y": {"field": "count", "type": "quantitative", "label": "会话—商品样本", "format": "compact"},
                    "tooltip": [
                        {"field": "rate", "type": "quantitative", "label": "占比", "format": "percent"},
                        {"field": "numerator", "type": "quantitative", "label": "分子", "format": "number"},
                        {"field": "denominator", "type": "quantitative", "label": "分母", "format": "number"},
                    ],
                },
                "settings": {"orientation": "horizontal", "sort": "descending", "showValues": True},
                "valueFormat": "compact",
                "layout": "full",
            },
            {
                "id": "chart_brand_priority",
                "title": "已知品牌覆盖量与移除/购买比",
                "subtitle": "右上区域用于确定第一批运营排查对象，不代表品牌导致流失。",
                "intent": "relationship",
                "question": "哪些已知品牌同时具有较高覆盖量和较高移除/购买比？",
                "rationale": "散点图同时呈现覆盖量、结果比值与启发式优先象限。",
                "type": "scatter",
                "dataset": "brand_metrics",
                "sourceId": "src_brand_48h",
                "encodings": {
                    "x": {"field": "brand_cohort_count", "type": "quantitative", "label": "品牌样本数", "format": "compact"},
                    "y": {"field": "remove_to_purchase_ratio", "type": "quantitative", "label": "移除/购买比", "format": "number"},
                    "color": {"field": "priority_quadrant", "type": "nominal", "label": "排查象限"},
                    "size": {"field": "distinct_products", "type": "quantitative", "label": "商品数"},
                    "tooltip": [
                        {"field": "brand", "type": "text", "label": "品牌"},
                        {"field": "purchase_rate", "type": "quantitative", "label": "购买率", "format": "percent"},
                        {"field": "unresolved_rate", "type": "quantitative", "label": "未明确处置率", "format": "percent"},
                        {"field": "remove_rate", "type": "quantitative", "label": "移除率", "format": "percent"},
                    ],
                },
                "legend": {"position": "bottom", "title": "排查象限"},
                "referenceLines": [
                    {"axis": "x", "value": 1342, "label": "覆盖量中位数"},
                    {"axis": "y", "value": 1.5, "label": "启发式比值线"},
                ],
                "layout": "full",
            },
            {
                "id": "chart_window_sensitivity",
                "title": "共同队列的窗口敏感性",
                "subtitle": "24—72 小时总体比例变化很小，但不能替代跨月份稳定性验证。",
                "intent": "comparison",
                "question": "同一批样本在不同观察窗口下的 A、B、C 比例是否明显变化？",
                "rationale": "分组条形图适合比较三个离散窗口下的三类互斥结果。",
                "type": "bar",
                "dataset": "window_sensitivity",
                "sourceId": "src_window_sensitivity",
                "encodings": {
                    "x": {"field": "window", "type": "ordinal", "label": "观察窗口"},
                    "y": {"field": "rate", "type": "quantitative", "label": "结果占比", "format": "percent"},
                    "color": {"field": "outcome", "type": "nominal", "label": "结果"},
                    "tooltip": [
                        {"field": "count", "type": "quantitative", "label": "样本数", "format": "number"},
                        {"field": "common_cohort_count", "type": "quantitative", "label": "共同队列", "format": "number"},
                    ],
                },
                "settings": {"groupMode": "grouped", "orientation": "vertical", "sort": "custom"},
                "legend": {"position": "bottom", "title": "结果"},
                "layout": "full",
            },
        ],
        "tables": [
            {
                "id": "table_priority_brands",
                "title": "第一批优先核查品牌",
                "subtitle": "仅展示达到高覆盖量与高比值启发式条件的已知品牌。",
                "dataset": "priority_brands",
                "sourceId": "src_brand_48h",
                "defaultSort": {"field": "brand_cohort_count", "direction": "desc"},
                "density": "dense",
                "columns": [
                    {"field": "brand", "label": "品牌", "type": "text"},
                    {"field": "brand_cohort_count", "label": "样本数", "type": "number", "format": "number"},
                    {"field": "purchase_rate", "label": "购买率", "type": "percent", "format": "percent"},
                    {"field": "unresolved_rate", "label": "未明确处置率", "type": "percent", "format": "percent"},
                    {"field": "remove_rate", "label": "移除率", "type": "percent", "format": "percent"},
                    {"field": "remove_to_purchase_ratio", "label": "移除/购买比", "type": "number", "format": "number"},
                    {"field": "distinct_products", "label": "商品数", "type": "number", "format": "number"},
                ],
                "layout": "full",
            },
            {
                "id": "table_quality",
                "title": "关键数据质量事实",
                "subtitle": "重复只报告不自动删除；无 event_id 时不能确认哪些重复是技术重复。",
                "dataset": "quality_summary",
                "sourceId": "src_quality",
                "defaultSort": {"field": "row_count", "direction": "desc"},
                "density": "dense",
                "columns": [
                    {"field": "scope", "label": "检查层级", "type": "text"},
                    {"field": "row_count", "label": "行数", "type": "number", "format": "number"},
                    {"field": "missing_session_rows", "label": "无效会话相关行", "type": "number", "format": "number"},
                    {"field": "missing_brand_rows", "label": "品牌缺失", "type": "number", "format": "number"},
                    {"field": "nonpositive_price_rows", "label": "非正价格", "type": "number", "format": "number"},
                    {"field": "exact_duplicate_excess_rows", "label": "重复超额行", "type": "number", "format": "number"},
                    {"field": "incomplete_tail_rows", "label": "尾部排除", "type": "number", "format": "number"},
                    {"field": "label_inconsistency_rows", "label": "标签矛盾", "type": "number", "format": "number"},
                ],
                "layout": "full",
            },
        ],
        "blocks": [
            {"id": "title", "type": "markdown", "body": f"# {title}", "layout": "full"},
            {
                "id": "executive_summary",
                "type": "markdown",
                "body": "## Executive Summary\n\n本项目把问题从‘给品牌贴风险标签’改为‘在数据证据有限时确定运营排查顺序’。正式结论基于完整观察窗口、互斥 A/B/C 标签和 SQL/Python 对账；现有数据只能支持描述性优先级，不能证明库存、运费、促销或品牌本身造成流失。",
                "layout": "full",
            },
            {
                "id": "kpis",
                "type": "metric-strip",
                "cardIds": ["card_cohort", "card_purchase_rate", "card_unresolved_rate", "card_remove_rate", "card_brand_coverage"],
                "layout": "full",
            },
            {
                "id": "outcome_heading",
                "type": "markdown",
                "body": "## 多数加购在 48 小时内没有明确结果\n\n正式队列中，购买率为 13.56%，移除率为 20.22%，另有 66.22% 既未购买也未移除。因此，A/(A+C) 的 40.14% 只能作为‘已有明确结果样本’的辅助指标，不能写成总体转化率。",
                "sourceId": "src_kpi_48h",
                "layout": "full",
            },
            {"id": "outcome_chart", "type": "chart", "chartId": "chart_outcome_mix", "layout": "full"},
            {
                "id": "brand_heading",
                "type": "markdown",
                "body": "## 品牌结论应当是排查优先级，而不是因果归因\n\n已知品牌只覆盖 55.99% 的正式样本。优先核查象限用覆盖量中位数和 1.5 的移除/购买比作为启发式筛选线，适合决定先查哪些品牌，不适合宣称这些品牌‘导致流失’。下一步应继续下钻到 SKU，并补充库存、促销、费用、渠道和结账错误数据。",
                "layout": "full",
            },
            {"id": "brand_chart", "type": "chart", "chartId": "chart_brand_priority", "layout": "full"},
            {"id": "brand_table", "type": "table", "tableId": "table_priority_brands", "layout": "full"},
            {
                "id": "window_heading",
                "type": "markdown",
                "body": "## 48 小时口径对总体结论较稳健\n\n在同一批 756,116 个具备完整 72 小时观察期的样本上，购买率从 24 小时的 13.5758% 变为 72 小时的 13.6188%，相差 0.043 个百分点。这个结果支持用 48 小时作为本项目主口径，但品牌级稳定性仍需跨月份验证。",
                "sourceId": "src_window_sensitivity",
                "layout": "full",
            },
            {"id": "window_chart", "type": "chart", "chartId": "chart_window_sensitivity", "layout": "full"},
            {
                "id": "quality_heading",
                "type": "markdown",
                "body": "## 数据质量决定了结论边界\n\n原始数据存在品牌与品类文本大量缺失、779 行无效会话值、7,607 行非正价格和 183,860 个业务字段重复超额行。正式流程排除了 19,231 个观察期不完整的尾部队列候选，并验证标签矛盾为 0；由于没有 event_id，重复行只做披露，不自动删除。",
                "sourceId": "src_quality",
                "layout": "full",
            },
            {"id": "quality_table", "type": "table", "tableId": "table_quality", "layout": "full"},
            {
                "id": "actions",
                "type": "markdown",
                "body": "## 建议动作\n\n1. 先对优先品牌按 SKU 下钻，检查问题是否由少数商品集中贡献。\n2. 联查库存、配送/费用展示、促销一致性和结账错误日志；未补充这些数据前，不写根因结论。\n3. 将更清晰的库存、费用或配送提示设计为实验，以 48 小时总体购买率为主指标，移除率和投诉为护栏。\n4. 看板同时展示 A/B/C 与已知品牌覆盖率，防止只看明确结果样本或把未知品牌当作一个品牌。",
                "layout": "full",
            },
            {
                "id": "further_questions",
                "type": "markdown",
                "body": "## 后续应回答的问题\n\n- 优先品牌的问题是否集中在少数 SKU、价格带或时间段？\n- 未知品牌样本与已知品牌样本的行为分布是否系统不同？\n- 跨月份、渠道和活动期的品牌排序是否稳定？\n- 补充库存、促销、运费和错误日志后，哪些机制最值得进入实验？",
                "layout": "full",
            },
            {
                "id": "caveats",
                "type": "markdown",
                "body": "## 口径与局限\n\n一行正式样本代表一个会话—商品在数据窗口内的首次观测加购，不代表一个用户，也不代表用户历史上的真正首次加购。报告使用 2019 年 12 月单月事件数据，品牌结论存在缺失覆盖与时间代表性限制。所有品牌结果均为描述性相关，建议通过补充字段、跨期验证或 A/B 实验确认。",
                "layout": "full",
            },
        ],
    }

    snapshot = {
        "version": 1,
        "generatedAt": generated_at,
        "status": "ready",
        "datasets": {
            "kpi_48h": [kpi],
            "outcome_mix": outcome_rows,
            "brand_metrics": brand_rows,
            "priority_brands": priority_rows,
            "window_sensitivity": sensitivity_rows,
            "quality_summary": quality_rows,
        },
    }
    return {"surface": "report", "manifest": manifest, "snapshot": snapshot, "sources": sources}


def main() -> None:
    artifact = build_artifact()
    OUTPUT_PATH.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Datasets: {len(artifact['snapshot']['datasets'])}")
    print(f"Priority brands: {len(artifact['snapshot']['datasets']['priority_brands'])}")


if __name__ == "__main__":
    main()
