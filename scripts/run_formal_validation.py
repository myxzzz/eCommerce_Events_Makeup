"""运行正式只读 SQL，并用本地 48 小时 CSV 独立复核关键结果。

业务目标：为品牌运营优先级提供可审计的证据，而不是修改数据库。
输入：PostgreSQL 原始事件表、已有 48 小时中间表、本地对应 CSV。
输出：reports/data_exports 下的 SQL 结果、Python 复核结果与对账摘要。
"""

from __future__ import annotations

import os
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import psycopg2


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = PROJECT_ROOT / "sql" / "formal"
EXPORT_DIR = PROJECT_ROOT / "reports" / "data_exports"
LOCAL_COHORT_PATH = (
    PROJECT_ROOT / "data" / "interim" / "11_user_behavior_groups_window_48h.csv"
)

QUERY_OUTPUTS = {
    "00_source_profile.sql": "source_profile.csv",
    "01_cohort_quality.sql": "cohort_quality.csv",
    "02_kpi_summary_48h.sql": "kpi_summary_48h.csv",
    "03_brand_metrics_48h.sql": "brand_metrics_48h.csv",
    "04_funnel_metrics.sql": "funnel_metrics.csv",
    "05_window_sensitivity.sql": "window_sensitivity.csv",
    "06_cohort_detail_48h.sql": "cohort_detail_48h.csv",
}


def connection_kwargs() -> dict[str, Any]:
    """只从环境或本机 PostgreSQL 默认认证读取连接信息。"""
    kwargs: dict[str, Any] = {
        "host": os.getenv("PGHOST", "localhost"),
        "port": int(os.getenv("PGPORT", "5432")),
        "dbname": os.getenv("PGDATABASE", "postgres"),
        "user": os.getenv("PGUSER", "postgres"),
        "connect_timeout": 10,
        "application_name": "ecommerce_formal_validation_readonly",
    }
    password = os.getenv("PGPASSWORD")
    if password:
        kwargs["password"] = password
    return kwargs


def execute_select(conn: psycopg2.extensions.connection, sql_path: Path) -> pd.DataFrame:
    """执行一个以 SELECT 结尾的 SQL 文件并返回最后一个结果集。"""
    sql = sql_path.read_text(encoding="utf-8")
    started = time.perf_counter()
    with conn.cursor() as cursor:
        cursor.execute(sql)
        if cursor.description is None:
            raise RuntimeError(f"{sql_path.name} 没有返回结果集")
        columns = [item.name for item in cursor.description]
        rows = cursor.fetchall()
    elapsed = time.perf_counter() - started
    print(f"[SQL] {sql_path.name}: {len(rows):,} rows, {elapsed:.1f}s")
    return pd.DataFrame(rows, columns=columns)


def normalize_numeric(frame: pd.DataFrame) -> pd.DataFrame:
    """将 psycopg2 Decimal 转成普通数值，便于 CSV 和跨工具读取。"""
    result = frame.copy()
    for column in result.columns:
        non_null_values = result[column].dropna()
        if pd.api.types.is_datetime64_any_dtype(result[column]):
            continue
        if not non_null_values.empty and isinstance(non_null_values.iloc[0], (datetime, date)):
            continue
        converted = pd.to_numeric(result[column], errors="coerce")
        non_null = result[column].notna().sum()
        if non_null > 0 and converted.notna().sum() == non_null:
            result[column] = converted
    return result


def build_python_brand_metrics(cohort: pd.DataFrame) -> pd.DataFrame:
    """不复用 SQL 聚合，独立计算品牌指标。"""
    known = cohort.loc[cohort["brand"].notna()].copy()
    known["brand"] = known["brand"].astype(str).str.strip()
    known = known.loc[known["brand"].ne("")]

    grouped = known.groupby("brand", as_index=False).agg(
        brand_cohort_count=("group_type", "size"),
        purchase_count=("group_type", lambda x: int((x == "A").sum())),
        unresolved_count=("group_type", lambda x: int((x == "B").sum())),
        remove_count=("group_type", lambda x: int((x == "C").sum())),
        distinct_users=("user_id", "nunique"),
        distinct_sessions=("user_session", "nunique"),
        distinct_products=("product_id", "nunique"),
    )
    grouped["clear_outcome_count"] = grouped["purchase_count"] + grouped["remove_count"]
    eligible = grouped.loc[
        grouped["clear_outcome_count"].ge(100) & grouped["purchase_count"].gt(0)
    ].copy()

    total_count = len(cohort)
    volume_median = float(eligible["brand_cohort_count"].median())
    risk_threshold = 1.5
    eligible["brand_share_pct"] = 100 * eligible["brand_cohort_count"] / total_count
    eligible["purchase_rate_pct"] = 100 * eligible["purchase_count"] / eligible["brand_cohort_count"]
    eligible["unresolved_rate_pct"] = 100 * eligible["unresolved_count"] / eligible["brand_cohort_count"]
    eligible["remove_rate_pct"] = 100 * eligible["remove_count"] / eligible["brand_cohort_count"]
    eligible["clear_purchase_rate_pct"] = (
        100 * eligible["purchase_count"] / eligible["clear_outcome_count"]
    )
    eligible["remove_to_purchase_ratio"] = eligible["remove_count"] / eligible["purchase_count"]
    eligible["volume_median_count"] = volume_median
    eligible["remove_to_purchase_threshold"] = risk_threshold
    eligible["volume_band"] = np.where(
        eligible["brand_cohort_count"].ge(volume_median), "高覆盖量", "低覆盖量"
    )
    eligible["risk_band"] = np.where(
        eligible["remove_to_purchase_ratio"].ge(risk_threshold), "高比值", "低比值"
    )
    eligible["priority_quadrant"] = np.select(
        [
            eligible["volume_band"].eq("高覆盖量") & eligible["risk_band"].eq("高比值"),
            eligible["volume_band"].eq("高覆盖量"),
            eligible["risk_band"].eq("高比值"),
        ],
        ["优先核查", "规模优势/维护", "监控并补样本"],
        default="常规观察",
    )
    numeric_metrics = [
        "brand_share_pct",
        "purchase_rate_pct",
        "unresolved_rate_pct",
        "remove_rate_pct",
        "clear_purchase_rate_pct",
        "remove_to_purchase_ratio",
    ]
    eligible[numeric_metrics] = eligible[numeric_metrics].round(4)
    return eligible.sort_values(
        ["priority_quadrant", "brand_cohort_count", "remove_to_purchase_ratio", "brand"],
        ascending=[True, False, False, True],
    ).reset_index(drop=True)


def append_check(
    checks: list[dict[str, Any]],
    check_name: str,
    sql_value: float,
    python_value: float,
    tolerance: float = 0.0,
    severity: str = "error",
) -> None:
    difference = float(python_value) - float(sql_value)
    checks.append(
        {
            "check_name": check_name,
            "sql_value": sql_value,
            "python_value": python_value,
            "difference": difference,
            "tolerance": tolerance,
            "passed": abs(difference) <= tolerance + 1e-12,
            "severity": severity,
        }
    )


def reconcile_with_local_csv(
    outputs: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """用正式 SQL 明细复核聚合，并量化旧 CSV 的版本漂移。"""
    if not LOCAL_COHORT_PATH.exists():
        raise FileNotFoundError(f"缺少本地复核文件：{LOCAL_COHORT_PATH}")

    usecols = [
        "user_session",
        "product_id",
        "user_id",
        "brand",
        "group_type",
        "first_cart_time",
        "window_end_time",
    ]
    legacy_cohort = pd.read_csv(
        LOCAL_COHORT_PATH,
        usecols=usecols,
        parse_dates=["first_cart_time", "window_end_time"],
        low_memory=False,
    )
    source_max = pd.to_datetime(outputs["source_profile.csv"].loc[0, "source_max_time_utc"], utc=True)
    legacy_cohort["window_end_time"] = pd.to_datetime(legacy_cohort["window_end_time"], utc=True)
    legacy_cohort = legacy_cohort.loc[legacy_cohort["window_end_time"].le(source_max)].copy()
    cohort = outputs["cohort_detail_48h.csv"].copy()

    kpi = outputs["kpi_summary_48h.csv"].iloc[0]
    checks: list[dict[str, Any]] = []
    append_check(checks, "完整48小时样本数", kpi["cohort_count"], len(cohort))
    for group_type, metric in [
        ("A", "purchase_count"),
        ("B", "unresolved_count"),
        ("C", "remove_count"),
    ]:
        append_check(
            checks,
            f"{group_type}组数量",
            kpi[metric],
            int(cohort["group_type"].eq(group_type).sum()),
        )

    python_brand = build_python_brand_metrics(cohort)
    sql_brand = outputs["brand_metrics_48h.csv"].copy()
    merged = sql_brand.merge(
        python_brand,
        on="brand",
        how="outer",
        suffixes=("_sql", "_python"),
        indicator=True,
    )
    append_check(
        checks,
        "符合条件品牌数",
        len(sql_brand),
        len(python_brand),
    )

    exact_columns = [
        "brand_cohort_count",
        "purchase_count",
        "unresolved_count",
        "remove_count",
        "clear_outcome_count",
        "distinct_users",
        "distinct_sessions",
        "distinct_products",
    ]
    rate_columns = [
        "brand_share_pct",
        "purchase_rate_pct",
        "unresolved_rate_pct",
        "remove_rate_pct",
        "clear_purchase_rate_pct",
        "remove_to_purchase_ratio",
    ]
    for column in exact_columns:
        mismatches = (
            merged[f"{column}_sql"].fillna(-1).astype(float)
            != merged[f"{column}_python"].fillna(-1).astype(float)
        ).sum()
        append_check(checks, f"品牌字段一致：{column}", 0, int(mismatches))
    for column in rate_columns:
        difference = (
            merged[f"{column}_sql"].astype(float)
            - merged[f"{column}_python"].astype(float)
        ).abs()
        max_difference = float(difference.max()) if len(difference) else 0.0
        append_check(checks, f"品牌字段最大差：{column}", 0.0, max_difference, 0.0001)

    label_mismatches = 0
    for column in ["volume_band", "risk_band", "priority_quadrant"]:
        label_mismatches += int(
            (merged[f"{column}_sql"].fillna("<NA>") != merged[f"{column}_python"].fillna("<NA>"))
            .sum()
        )
    append_check(checks, "品牌优先级标签差异数", 0, label_mismatches)
    append_check(checks, "品牌集合差异数", 0, int(merged["_merge"].ne("both").sum()))

    legacy_compare = cohort[
        ["user_session", "product_id", "group_type", "first_cart_time"]
    ].merge(
        legacy_cohort[["user_session", "product_id", "group_type", "first_cart_time"]],
        on=["user_session", "product_id"],
        how="outer",
        suffixes=("_formal", "_legacy"),
        indicator=True,
    )
    legacy_differences = legacy_compare.loc[
        legacy_compare["_merge"].ne("both")
        | legacy_compare["group_type_formal"].ne(legacy_compare["group_type_legacy"])
        | pd.to_datetime(legacy_compare["first_cart_time_formal"], utc=True).ne(
            pd.to_datetime(legacy_compare["first_cart_time_legacy"], utc=True)
        )
    ].copy()
    append_check(
        checks,
        "旧48小时CSV与正式重建的差异行",
        0,
        len(legacy_differences),
        severity="warning",
    )

    return python_brand, pd.DataFrame(checks), legacy_differences


def validate_sensitivity(sensitivity: pd.DataFrame) -> pd.DataFrame:
    """验证固定队列下购买数单调上升、未明确处置数单调下降。"""
    ordered = sensitivity.sort_values("window_hours")
    checks = [
        {
            "check_name": "敏感性分析使用同一队列",
            "sql_value": 1,
            "python_value": int(ordered["common_cohort_count"].nunique() == 1),
            "difference": int(ordered["common_cohort_count"].nunique() == 1) - 1,
            "tolerance": 0,
            "passed": ordered["common_cohort_count"].nunique() == 1,
            "severity": "error",
        },
        {
            "check_name": "购买数量随窗口不下降",
            "sql_value": 1,
            "python_value": int(ordered["purchase_count"].is_monotonic_increasing),
            "difference": int(ordered["purchase_count"].is_monotonic_increasing) - 1,
            "tolerance": 0,
            "passed": ordered["purchase_count"].is_monotonic_increasing,
            "severity": "error",
        },
        {
            "check_name": "未明确处置数量随窗口不上升",
            "sql_value": 1,
            "python_value": int(ordered["unresolved_count"].is_monotonic_decreasing),
            "difference": int(ordered["unresolved_count"].is_monotonic_decreasing) - 1,
            "tolerance": 0,
            "passed": ordered["unresolved_count"].is_monotonic_decreasing,
            "severity": "error",
        },
    ]
    return pd.DataFrame(checks)


def main() -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, pd.DataFrame] = {}

    with psycopg2.connect(**connection_kwargs()) as conn:
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor() as cursor:
            cursor.execute("SET statement_timeout = '15min'; SET TIME ZONE 'UTC';")
        for sql_name, output_name in QUERY_OUTPUTS.items():
            frame = normalize_numeric(execute_select(conn, SQL_DIR / sql_name))
            frame.to_csv(EXPORT_DIR / output_name, index=False, encoding="utf-8-sig")
            outputs[output_name] = frame

    python_brand, reconciliation, legacy_differences = reconcile_with_local_csv(outputs)
    sensitivity_checks = validate_sensitivity(outputs["window_sensitivity.csv"])
    reconciliation = pd.concat([reconciliation, sensitivity_checks], ignore_index=True)

    python_brand.to_csv(
        EXPORT_DIR / "python_brand_metrics_48h.csv", index=False, encoding="utf-8-sig"
    )
    reconciliation.to_csv(
        EXPORT_DIR / "reconciliation_summary.csv", index=False, encoding="utf-8-sig"
    )
    legacy_differences.to_csv(
        EXPORT_DIR / "legacy_cohort_differences.csv", index=False, encoding="utf-8-sig"
    )

    failed = reconciliation.loc[
        ~reconciliation["passed"].astype(bool) & reconciliation["severity"].eq("error")
    ]
    warnings = reconciliation.loc[
        ~reconciliation["passed"].astype(bool) & reconciliation["severity"].eq("warning")
    ]
    print(f"[QA] {len(reconciliation)} checks, {len(failed)} errors, {len(warnings)} warnings")
    if not warnings.empty:
        print(warnings.to_string(index=False))
    if not failed.empty:
        print(failed.to_string(index=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
