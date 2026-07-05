from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_INPUT = Path("data/interim/11_user_behavior_groups_window_48h.csv")
DEFAULT_OUTPUT_CSV = Path("data/interim/11_brand_quadrant_matrix_window_48h_median.csv")
DEFAULT_FIXED_OUTPUT_CSV = Path("data/interim/11_brand_quadrant_matrix_window_48h_fixed_risk_1_5.csv")


def clean_brand(series: pd.Series) -> pd.Series:
    brand = series.astype("string").str.strip()
    unknown_mask = brand.isna() | (brand == "") | brand.str.lower().isin(["nan", "null", "none"])
    return brand.mask(unknown_mask, "Unknown Brand")


def assign_quadrant(row: pd.Series, share_threshold: float, risk_threshold: float) -> str:
    high_share = row["brand_share_in_clear_outcome"] >= share_threshold
    high_risk = row["c_to_a_ratio"] >= risk_threshold

    if high_share and high_risk:
        return "priority_fix"
    if high_share and not high_risk:
        return "core_healthy"
    if not high_share and high_risk:
        return "problem_long_tail"
    return "potential_long_tail"


def build_brand_stats(input_path: Path, min_clear_outcome_count: int) -> pd.DataFrame:
    df = pd.read_csv(input_path)
    df_ac = df[df["group_type"].isin(["A", "C"])].copy()
    df_ac["brand_clean"] = clean_brand(df_ac["brand"])

    brand_stats = (
        df_ac.groupby("brand_clean")
        .agg(
            A_count=("group_type", lambda x: int((x == "A").sum())),
            C_count=("group_type", lambda x: int((x == "C").sum())),
        )
        .reset_index()
    )
    brand_stats["clear_outcome_count"] = brand_stats["A_count"] + brand_stats["C_count"]
    brand_stats["ac_purchase_share"] = brand_stats["A_count"] / brand_stats["clear_outcome_count"]
    brand_stats["ac_loss_share"] = brand_stats["C_count"] / brand_stats["clear_outcome_count"]
    brand_stats["c_to_a_ratio"] = np.where(
        brand_stats["A_count"] > 0,
        brand_stats["C_count"] / brand_stats["A_count"],
        np.inf,
    )
    brand_stats["brand_share_in_clear_outcome"] = (
        brand_stats["clear_outcome_count"] / brand_stats["clear_outcome_count"].sum()
    )

    qualified = brand_stats[
        (brand_stats["brand_clean"] != "Unknown Brand")
        & (brand_stats["clear_outcome_count"] >= min_clear_outcome_count)
        & (brand_stats["A_count"] > 0)
        & np.isfinite(brand_stats["c_to_a_ratio"])
    ].copy()

    return qualified


def build_quadrant_version(
    qualified: pd.DataFrame,
    output_csv: Path,
    share_threshold: float,
    risk_threshold: float,
    threshold_method: str,
) -> pd.DataFrame:
    result = qualified.copy()
    result["quadrant"] = result.apply(
        assign_quadrant,
        axis=1,
        share_threshold=share_threshold,
        risk_threshold=risk_threshold,
    )
    result["share_threshold"] = share_threshold
    result["risk_threshold"] = risk_threshold
    result["threshold_method"] = threshold_method

    output_cols = [
        "brand_clean",
        "quadrant",
        "A_count",
        "C_count",
        "clear_outcome_count",
        "ac_purchase_share",
        "ac_loss_share",
        "c_to_a_ratio",
        "brand_share_in_clear_outcome",
        "share_threshold",
        "risk_threshold",
        "threshold_method",
    ]
    result = result[output_cols].sort_values(["quadrant", "clear_outcome_count"], ascending=[True, False])
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_csv, index=False, encoding="utf-8-sig")
    return result


def print_summary(name: str, result: pd.DataFrame, output_csv: Path) -> None:
    print(f"\n{name}")
    print("-" * len(name))
    print("quadrant counts:")
    print(result["quadrant"].value_counts().to_string())
    print("top brands by quadrant:")
    for quadrant in ["core_healthy", "priority_fix", "potential_long_tail", "problem_long_tail"]:
        top = result[result["quadrant"] == quadrant].nlargest(5, "clear_outcome_count")["brand_clean"].tolist()
        print(f"{quadrant}: {', '.join(top)}")
    print(f"output csv: {output_csv}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build median and fixed-threshold brand quadrant matrices.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--fixed-output-csv", type=Path, default=DEFAULT_FIXED_OUTPUT_CSV)
    parser.add_argument("--min-clear-outcome-count", type=int, default=100)
    parser.add_argument("--fixed-risk-threshold", type=float, default=1.5)
    args = parser.parse_args()

    qualified = build_brand_stats(args.input, args.min_clear_outcome_count)
    share_threshold = qualified["brand_share_in_clear_outcome"].median()
    median_risk_threshold = qualified["c_to_a_ratio"].median()

    median_result = build_quadrant_version(
        qualified=qualified,
        output_csv=args.output_csv,
        share_threshold=share_threshold,
        risk_threshold=median_risk_threshold,
        threshold_method="median_share_median_risk",
    )
    fixed_result = build_quadrant_version(
        qualified=qualified,
        output_csv=args.fixed_output_csv,
        share_threshold=share_threshold,
        risk_threshold=args.fixed_risk_threshold,
        threshold_method="median_share_fixed_risk_1_5",
    )

    print(f"input: {args.input}")
    print(f"qualified brands: {len(qualified):,}")
    print(f"share threshold: {share_threshold:.6f}")
    print(f"median risk threshold: {median_risk_threshold:.6f}")
    print(f"fixed risk threshold: {args.fixed_risk_threshold:.6f}")
    print_summary("median threshold version", median_result, args.output_csv)
    print_summary("fixed risk threshold version", fixed_result, args.fixed_output_csv)


if __name__ == "__main__":
    main()
