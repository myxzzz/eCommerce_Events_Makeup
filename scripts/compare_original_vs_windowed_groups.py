from __future__ import annotations

from pathlib import Path

import pandas as pd


OLD_PATH = Path("data/interim/03_user_behavior_groups.csv")
NEW_PATH = Path("data/interim/11_user_behavior_groups_window_48h.csv")


def print_section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def load_new() -> pd.DataFrame:
    df = pd.read_csv(NEW_PATH)
    df["first_cart_time"] = pd.to_datetime(df["first_cart_time"], utc=True)
    df["window_end_time"] = pd.to_datetime(df["window_end_time"], utc=True)
    return df


def validate_windowed_table(df: pd.DataFrame) -> None:
    print_section("1. 48小时窗口新表质检")

    duplicated_keys = df.duplicated(["user_session", "product_id"]).sum()
    late_first_cart = (df["first_cart_time"] >= pd.Timestamp("2019-12-30 00:00:00+00:00")).sum()
    wrong_window = ((df["window_end_time"] - df["first_cart_time"]) != pd.Timedelta(hours=48)).sum()
    non_cart_seed = (df["event_type"] != "cart").sum()

    a_invalid = df[(df["group_type"] == "A") & (~df["has_purchase_48h"].astype(bool))]
    c_invalid = df[
        (df["group_type"] == "C")
        & (df["has_purchase_48h"].astype(bool) | ~df["has_remove_48h"].astype(bool))
    ]
    b_invalid = df[
        (df["group_type"] == "B")
        & (df["has_purchase_48h"].astype(bool) | df["has_remove_48h"].astype(bool))
    ]

    checks = pd.DataFrame(
        [
            ("duplicate user_session + product_id", duplicated_keys),
            ("first_cart_time >= 2019-12-30", late_first_cart),
            ("window_end_time - first_cart_time != 48h", wrong_window),
            ("seed event_type is not cart", non_cart_seed),
            ("A without purchase in 48h", len(a_invalid)),
            ("C with purchase or without remove in 48h", len(c_invalid)),
            ("B with purchase/remove in 48h", len(b_invalid)),
        ],
        columns=["check", "bad_rows"],
    )
    print(checks.to_string(index=False))

    print("\nfirst_cart_time range:")
    print(df["first_cart_time"].min(), "->", df["first_cart_time"].max())

    print("\ngroup_type x purchase/remove flags:")
    print(
        pd.crosstab(
            df["group_type"],
            [df["has_purchase_48h"].astype(bool), df["has_remove_48h"].astype(bool)],
        ).to_string()
    )


def compare_group_distribution(new_df: pd.DataFrame) -> None:
    print_section("2. 旧口径 vs 48小时窗口口径：A/B/C整体分布")

    old_counts = pd.read_csv(OLD_PATH, usecols=["group_type"])["group_type"].value_counts().rename("old_count")
    new_counts = new_df["group_type"].value_counts().rename("new_count")

    compare = pd.concat([old_counts, new_counts], axis=1).fillna(0).astype(int)
    compare = compare.reindex(["A", "B", "C"])
    compare["old_share"] = compare["old_count"] / compare["old_count"].sum()
    compare["new_share"] = compare["new_count"] / compare["new_count"].sum()
    compare["count_change"] = compare["new_count"] - compare["old_count"]
    compare["share_change_pp"] = (compare["new_share"] - compare["old_share"]) * 100

    print(compare.to_string(float_format=lambda x: f"{x:.4f}"))

    print("\n48小时窗口内 event_type_window 分布（辅助复查，不是主分组口径）:")
    print(new_df["event_type_window"].value_counts().head(15).to_string())


def compare_daily_distribution(new_df: pd.DataFrame) -> None:
    print_section("3. 48小时窗口新表：末尾日期分布")

    daily = pd.crosstab(new_df["first_cart_time"].dt.date, new_df["group_type"])
    print(daily.tail(10).to_string())


def clean_brand(series: pd.Series) -> pd.Series:
    brand = series.astype("string").str.strip()
    unknown_mask = brand.isna() | (brand == "") | brand.str.lower().isin(["nan", "null", "none"])
    return brand.mask(unknown_mask, "Unknown Brand")


def brand_ac_stats(df: pd.DataFrame, label: str) -> pd.DataFrame:
    df_ac = df[df["group_type"].isin(["A", "C"])].copy()
    df_ac["brand_clean"] = clean_brand(df_ac["brand"])
    stats = (
        df_ac.groupby("brand_clean")
        .agg(
            **{
                f"{label}_A_count": ("group_type", lambda x: int((x == "A").sum())),
                f"{label}_C_count": ("group_type", lambda x: int((x == "C").sum())),
            }
        )
        .reset_index()
    )
    stats[f"{label}_clear_outcome_count"] = stats[f"{label}_A_count"] + stats[f"{label}_C_count"]
    stats[f"{label}_c_to_a_ratio"] = stats[f"{label}_C_count"] / stats[f"{label}_A_count"].replace(0, pd.NA)
    stats[f"{label}_brand_share"] = (
        stats[f"{label}_clear_outcome_count"] / stats[f"{label}_clear_outcome_count"].sum()
    )
    return stats


def compare_brand_ac_metrics(new_df: pd.DataFrame) -> None:
    print_section("4. 旧口径 vs 48小时窗口口径：品牌A/C风险对比")

    old_df = pd.read_csv(OLD_PATH, usecols=["brand", "group_type"])
    old_stats = brand_ac_stats(old_df, "old")
    new_stats = brand_ac_stats(new_df[["brand", "group_type"]], "new")
    compare = old_stats.merge(new_stats, on="brand_clean", how="inner")
    compare = compare[
        (compare["brand_clean"] != "Unknown Brand")
        & (compare["old_A_count"] > 0)
        & (compare["new_A_count"] > 0)
    ].copy()
    numeric_cols = [
        "old_c_to_a_ratio",
        "new_c_to_a_ratio",
        "old_clear_outcome_count",
        "new_clear_outcome_count",
    ]
    for col in numeric_cols:
        compare[col] = pd.to_numeric(compare[col], errors="coerce")
    compare["ratio_change"] = compare["new_c_to_a_ratio"] - compare["old_c_to_a_ratio"]
    compare["ratio_change_pct"] = pd.NA
    nonzero_old_ratio = compare["old_c_to_a_ratio"] > 0
    compare.loc[nonzero_old_ratio, "ratio_change_pct"] = (
        compare.loc[nonzero_old_ratio, "ratio_change"]
        / compare.loc[nonzero_old_ratio, "old_c_to_a_ratio"]
        * 100
    )
    compare["clear_outcome_count_change"] = (
        compare["new_clear_outcome_count"] - compare["old_clear_outcome_count"]
    )

    focus_brands = [
        "runail",
        "irisk",
        "bpw.style",
        "estel",
        "kapous",
        "masura",
        "grattol",
        "ingarden",
        "pole",
        "bluesky",
    ]
    focus = compare[compare["brand_clean"].isin(focus_brands)].sort_values(
        "old_clear_outcome_count", ascending=False
    )
    cols = [
        "brand_clean",
        "old_A_count",
        "old_C_count",
        "old_c_to_a_ratio",
        "new_A_count",
        "new_C_count",
        "new_c_to_a_ratio",
        "ratio_change",
        "ratio_change_pct",
    ]
    print("\n核心品牌对比:")
    print(focus[cols].to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    print("\n旧口径体量Top15品牌的新旧C/A变化:")
    top15 = compare.nlargest(15, "old_clear_outcome_count")
    print(top15[cols].to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    print("\n新口径C/A下降最多的Top15品牌（旧体量>=500）:")
    decreased = compare[compare["old_clear_outcome_count"] >= 500].nsmallest(15, "ratio_change")
    print(decreased[cols].to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    print("\n新口径C/A上升最多的Top15品牌（旧体量>=500）:")
    increased = compare[compare["old_clear_outcome_count"] >= 500].nlargest(15, "ratio_change")
    print(increased[cols].to_string(index=False, float_format=lambda x: f"{x:.4f}"))


def main() -> None:
    new_df = load_new()
    validate_windowed_table(new_df)
    compare_group_distribution(new_df)
    compare_daily_distribution(new_df)
    compare_brand_ac_metrics(new_df)


if __name__ == "__main__":
    main()
