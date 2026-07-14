"""基于已验证 CSV 生成正式图表和文字报告源文件。"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = PROJECT_ROOT / "reports" / "data_exports"
CHART_DIR = PROJECT_ROOT / "reports" / "formal_charts"
REPORT_DIR = PROJECT_ROOT / "reports"

BLUE = "#2F5D8A"
ORANGE = "#D8873B"
GOLD = "#C6A15B"
INK = "#24313D"
MUTED = "#7A8793"
LIGHT = "#E8EDF2"
PINK = "#C86B85"


def configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#B8C1CA",
            "axes.labelcolor": INK,
            "text.color": INK,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "axes.titleweight": "bold",
        }
    )


def save_figure(fig: plt.Figure, name: str) -> None:
    fig.tight_layout()
    fig.savefig(CHART_DIR / name, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def build_outcome_mix(kpi: pd.Series) -> None:
    labels = ["48小时购买 A", "未明确处置 B", "移除 C"]
    values = np.array(
        [kpi["purchase_rate_pct"], kpi["unresolved_rate_pct"], kpi["remove_rate_pct"]],
        dtype=float,
    )
    colors = [BLUE, LIGHT, ORANGE]
    fig, ax = plt.subplots(figsize=(10.5, 2.4))
    left = 0.0
    for label, value, color in zip(labels, values, colors, strict=True):
        ax.barh([0], [value], left=left, color=color, edgecolor="white", height=0.48)
        text_color = "white" if color in {BLUE, ORANGE} else INK
        ax.text(left + value / 2, 0, f"{label}\n{value:.1f}%", ha="center", va="center", color=text_color, fontsize=10)
        left += value
    ax.set_xlim(0, 100)
    ax.set_yticks([])
    ax.set_xlabel("占完整 48 小时加购样本的比例")
    ax.set_title("首次观测加购后的 48 小时结果构成", loc="left", fontsize=14)
    ax.grid(axis="x", color="#E4E9EE", linewidth=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    save_figure(fig, "11_outcome_mix_48h.png")


def build_window_sensitivity(sensitivity: pd.DataFrame) -> None:
    data = sensitivity.sort_values("window_hours")
    windows = data["window_hours"].astype(int).astype(str) + "小时"
    series = [
        ("购买率", "purchase_rate_pct", BLUE),
        ("未明确处置率", "unresolved_rate_pct", LIGHT),
        ("移除率", "remove_rate_pct", ORANGE),
    ]
    x = np.arange(len(data))
    width = 0.23
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    for index, (label, column, color) in enumerate(series):
        values = data[column].astype(float).to_numpy()
        positions = x + (index - 1) * width
        bars = ax.bar(positions, values, width, label=label, color=color, edgecolor="#FFFFFF")
        for bar, value in zip(bars, values, strict=True):
            ax.text(bar.get_x() + bar.get_width() / 2, value + 1.0, f"{value:.2f}%", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x, windows)
    ax.set_ylim(0, 74)
    ax.set_ylabel("占同一批 72 小时完整样本的比例")
    ax.set_title("24/48/72 小时时间窗口敏感性", loc="left", fontsize=14)
    ax.legend(frameon=False, ncol=3, loc="upper center")
    ax.grid(axis="y", color="#E4E9EE", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    save_figure(fig, "12_window_sensitivity.png")


def build_brand_matrix(brands: pd.DataFrame) -> None:
    data = brands.copy()
    data["brand_cohort_count"] = pd.to_numeric(data["brand_cohort_count"])
    data["remove_to_purchase_ratio"] = pd.to_numeric(data["remove_to_purchase_ratio"])
    data["clear_outcome_count"] = pd.to_numeric(data["clear_outcome_count"])
    volume_threshold = float(data["volume_median_count"].iloc[0])
    ratio_threshold = float(data["remove_to_purchase_threshold"].iloc[0])
    colors = {
        "优先核查": ORANGE,
        "规模优势/维护": BLUE,
        "监控并补样本": PINK,
        "常规观察": MUTED,
    }
    fig, ax = plt.subplots(figsize=(10.5, 7.2))
    for quadrant in ["常规观察", "监控并补样本", "规模优势/维护", "优先核查"]:
        subset = data.loc[data["priority_quadrant"].eq(quadrant)]
        sizes = 22 + 1.8 * np.sqrt(subset["clear_outcome_count"].to_numpy())
        ax.scatter(
            subset["brand_cohort_count"],
            subset["remove_to_purchase_ratio"],
            s=sizes,
            color=colors[quadrant],
            alpha=0.78,
            edgecolor="white",
            linewidth=0.7,
            label=f"{quadrant}（{len(subset)}）",
        )
    ax.axvline(volume_threshold, color=INK, linewidth=1.1, linestyle="--")
    ax.axhline(ratio_threshold, color=INK, linewidth=1.1, linestyle="--")
    ax.text(volume_threshold * 1.05, 3.0, f"覆盖量中位数 {volume_threshold:,.0f}", fontsize=9, color=INK)
    ax.text(150, ratio_threshold + 0.05, "启发式筛选线 1.5", fontsize=9, color=INK)

    priority = data.loc[data["priority_quadrant"].eq("优先核查")].nlargest(8, "brand_cohort_count")
    for _, row in priority.iterrows():
        ax.annotate(
            row["brand"],
            (row["brand_cohort_count"], row["remove_to_purchase_ratio"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8,
        )
    ax.set_xscale("log")
    ax.set_xlim(100, max(data["brand_cohort_count"]) * 1.4)
    ax.set_ylim(0.4, 3.25)
    ax.set_xlabel("品牌完整 48 小时加购样本数（对数刻度）")
    ax.set_ylabel("移除/购买比（C/A）")
    ax.set_title("已知品牌运营排查优先级矩阵", loc="left", fontsize=14)
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    ax.grid(color="#E4E9EE", linewidth=0.7, which="both")
    ax.spines[["top", "right"]].set_visible(False)
    save_figure(fig, "13_brand_priority_matrix.png")


def build_data_quality_report(
    source: pd.Series,
    quality: pd.Series,
    kpi: pd.Series,
    reconciliation: pd.DataFrame,
) -> None:
    failed_errors = reconciliation.loc[
        ~reconciliation["passed"].astype(bool) & reconciliation["severity"].eq("error")
    ]
    warning_count = int(
        (~reconciliation["passed"].astype(bool) & reconciliation["severity"].eq("warning")).sum()
    )
    source_rows = int(source["source_row_count"])
    duplicate_rate = 100 * float(source["exact_duplicate_excess_rows"]) / source_rows
    invalid_key_share = 100 * float(quality["invalid_cart_key_event_rows"]) / float(quality["cart_event_rows"])
    excluded_tail_share = 100 * float(quality["incomplete_tail_rows_excluded"]) / float(quality["first_observed_cart_rows"])
    brand_missing_share = 100 * float(quality["missing_brand_rows"]) / float(quality["complete_48h_rows"])
    category_missing_share = 100 * float(quality["missing_category_code_rows"]) / float(quality["complete_48h_rows"])
    text = f"""# 数据质量报告

## 结论

当前数据足以支持“已发生加购后的会话—商品结果描述”和“已知品牌运营排查优先级”，但不适合直接推断品牌因果、销售额损失或本地时段策略。正式 SQL 与 Python 重新聚合共 {len(reconciliation)} 项检查，错误 {len(failed_errors)} 项、历史版本警告 {warning_count} 项。

## 数据范围与粒度

- 原始事件：{source_rows:,} 行，UTC 时间范围 {source['source_min_time_utc']} 至 {source['source_max_time_utc']}。
- 主队列：{int(quality['complete_48h_rows']):,} 个有效 `user_session × product_id` 首次观测加购样本。
- 完整性处理：排除月末无法完整观察 48 小时的 {int(quality['incomplete_tail_rows_excluded']):,} 个样本（{excluded_tail_share:.2f}%）。
- 无效会话键：{int(quality['invalid_cart_key_event_rows']):,} 条加购事件使用空值或 `NaN/null/none` 占位符（{invalid_key_share:.3f}%）；正式会话队列排除，避免跨用户串联。

## 关键质量问题

| 问题 | 证据 | 正式处理 | 剩余风险 |
|---|---:|---|---|
| 未知品牌 | {int(quality['missing_brand_rows']):,} 个主队列样本（{brand_missing_share:.2f}%） | `NaN/null/none` 标准化为缺失，品牌榜只保留已知品牌 | 已知品牌榜可能存在选择偏差，不能外推到全部样本 |
| 品类文本缺失 | {int(quality['missing_category_code_rows']):,} 个样本（{category_missing_share:.2f}%） | 不把 `category_code` 用作正式主分析维度 | 当前数据不足以完成可靠的品类归因 |
| 非正价格 | 原始 {int(source['nonpositive_price_rows']):,} 行；主队列 {int(quality['nonpositive_price_rows']):,} 行 | 当前正式品牌 KPI 不使用价格 | 后续价格分析前需确认 0/负值业务含义和币种 |
| 完全相同业务字段记录 | 超额 {int(source['exact_duplicate_excess_rows']):,} 行（{duplicate_rate:.2f}%） | 不自动删除，因为没有事件 ID，无法区分重复上报与真实重复操作 | 事件次数指标需谨慎；会话—商品首事件队列可降低影响但不能完全消除 |
| 旧 48 小时 CSV 漂移 | 369 个无效会话样本与正式队列不同 | 旧文件保留为历史版本，不再作为正式数据源 | 面试或展示时必须明确版本 |

## 标签与时间检查

- 主队列联合键重复超额：{int(quality['duplicate_session_product_excess_rows']):,}。
- 标签与布尔结果不一致：{int(quality['inconsistent_label_rows']):,}。
- 后续事件早于或等于首次加购：{int(quality['invalid_followup_order_rows']):,}。
- 时间全部按 UTC 解释；业务时区未知，因此不输出早晚时段运营结论。

## 可用性判断

- **可用于：** 48 小时 A/B/C 结果构成、同口径品牌比较、运营排查队列、24/48/72 小时总体敏感性。
- **需带限制使用：** 品牌榜（已知品牌覆盖率 {float(kpi['known_brand_coverage_pct']):.2f}%）。
- **不可直接用于：** GMV、利润、库存、营销 ROI、品牌因果根因、跨月长期转化和本地时段策略。
"""
    (REPORT_DIR / "data_quality_report.md").write_text(text, encoding="utf-8")


def build_management_source(kpi: pd.Series, brands: pd.DataFrame, sensitivity: pd.DataFrame) -> None:
    priority = brands.loc[brands["priority_quadrant"].eq("优先核查")].copy()
    priority["brand_cohort_count"] = pd.to_numeric(priority["brand_cohort_count"])
    priority = priority.nlargest(8, "brand_cohort_count")
    brand_lines = "\n".join(
        f"- **{row.brand}**：样本 {int(row.brand_cohort_count):,}，购买率 {float(row.purchase_rate_pct):.2f}%，未明确处置率 {float(row.unresolved_rate_pct):.2f}%，移除/购买比 {float(row.remove_to_purchase_ratio):.2f}。"
        for row in priority.itertuples()
    )
    sensitivity = sensitivity.sort_values("window_hours")
    purchase_delta = float(sensitivity.iloc[-1]["purchase_rate_pct"]) - float(
        sensitivity.iloc[0]["purchase_rate_pct"]
    )
    text = f"""# 品牌运营排查优先级：管理层一页结论

## Executive Summary

- **主问题不是“移除最多的品牌”，而是先找覆盖量大且移除/购买比高的已知品牌。** 正式 48 小时队列共有 {int(kpi['cohort_count']):,} 个会话—商品样本，购买率 {float(kpi['purchase_rate_pct']):.2f}%，移除率 {float(kpi['remove_rate_pct']):.2f}%。
- **{float(kpi['unresolved_rate_pct']):.2f}% 的样本在 48 小时内既未购买也未移除。** 因此只看 A/C 的“明确结果购买率”会忽略多数样本；正式看板同时保留整体购买率和 B 类。
- **品牌榜只能覆盖 {float(kpi['known_brand_coverage_pct']):.2f}% 的样本。** 未知品牌不能当作名为 `NaN` 的最大品牌，品牌排序只用于已知品牌排查，不代表全站结论。
- **总体窗口结论较稳定。** 在同一批 72 小时完整样本上，购买率从 24 小时到 72 小时仅变化 {purchase_delta:.3f} 个百分点；但品牌级稳定性仍需更长时间数据验证。

## 第一批优先核查品牌

{brand_lines}

以上品牌同时超过已知品牌覆盖量中位数，并达到移除/购买比 1.5 的启发式筛选线。1.5 不是行业标准，也不是流失概率。

## 建议动作

1. 先核对优先品牌的商品可售状态、详情页承诺、配送/费用展示、促销一致性和结账失败日志。
2. 对 `grattol`、`masura` 等高覆盖品牌按商品拆分，确认问题是否集中在少数 SKU，而非直接归因于品牌。
3. 把“更清晰的费用/库存/配送提示”设计成 A/B 实验，以 48 小时购买率为主指标，同时监控移除率和投诉等护栏。
4. 补采业务时区、库存、促销、运费、渠道和结账错误字段，再判断机制；现有数据不能证明原因。

## 关键限制

- 一行是会话—商品，不是用户；同一用户可贡献多行。
- “首次加购”是 2019 年 12 月数据窗口内首次观测，不是用户历史首次。
- 未知品牌占比较高，品类文本几乎不可用；品牌结论可能有选择偏差。
- 这是描述性优先级，不是因果结论，建议必须通过补充数据或实验验证。
"""
    (REPORT_DIR / "management_onepager_source.md").write_text(text, encoding="utf-8")


def build_chart_map() -> None:
    text = """# 正式图表映射

| 报告段落 | 分析问题 | 图表类型 | 字段 | 支持的结论 | 配色策略 |
|---|---|---|---|---|---|
| 48 小时结果 | 加购后结果如何构成 | 100% 堆叠横条 | A/B/C 占比 | B 是最大结果组，不能只看 A/C | 蓝/浅灰/橙三类 |
| 窗口敏感性 | 24/48/72 小时是否改变总体结论 | 分组柱状图 | 三类结果率 × 窗口 | 总体购买率变化很小 | 与结果组一致 |
| 品牌优先级 | 哪些已知品牌覆盖量大且移除/购买比高 | 对数横轴散点 | 品牌样本数、C/A、明确结果样本数 | 四象限用于排查顺序，不用于因果归因 | 蓝/橙/粉/中性灰 |
"""
    (REPORT_DIR / "chart_map.md").write_text(text, encoding="utf-8")


def main() -> None:
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    configure_matplotlib()
    source = pd.read_csv(EXPORT_DIR / "source_profile.csv").iloc[0]
    quality = pd.read_csv(EXPORT_DIR / "cohort_quality.csv").iloc[0]
    kpi = pd.read_csv(EXPORT_DIR / "kpi_summary_48h.csv").iloc[0]
    brands = pd.read_csv(EXPORT_DIR / "brand_metrics_48h.csv")
    sensitivity = pd.read_csv(EXPORT_DIR / "window_sensitivity.csv")
    reconciliation = pd.read_csv(EXPORT_DIR / "reconciliation_summary.csv")

    build_outcome_mix(kpi)
    build_window_sensitivity(sensitivity)
    build_brand_matrix(brands)
    build_data_quality_report(source, quality, kpi, reconciliation)
    build_management_source(kpi, brands, sensitivity)
    build_chart_map()
    print(f"charts: {CHART_DIR}")
    print(f"reports: {REPORT_DIR}")


if __name__ == "__main__":
    main()
