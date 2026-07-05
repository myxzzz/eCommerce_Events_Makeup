from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_INPUT = Path("data/raw/Dec.csv")
DEFAULT_OUTPUT = Path("data/interim/11_user_behavior_groups_window_48h.csv")


def build_windowed_groups(
    input_path: Path,
    output_path: Path,
    window_hours: int = 48,
    cutoff: str = "2019-12-30 00:00:00+00:00",
) -> pd.DataFrame:
    usecols = [
        "event_time",
        "event_type",
        "product_id",
        "category_id",
        "category_code",
        "brand",
        "price",
        "user_id",
        "user_session",
    ]

    df = pd.read_csv(input_path, usecols=usecols)
    df["event_time"] = pd.to_datetime(df["event_time"], utc=True)

    cart_events = df[df["event_type"] == "cart"].copy()
    cart_events = cart_events.sort_values("event_time")

    first_cart = (
        cart_events.drop_duplicates(["user_session", "product_id"], keep="first")
        .rename(columns={"event_time": "first_cart_time"})
        .copy()
    )
    first_cart["window_end_time"] = first_cart["first_cart_time"] + pd.Timedelta(hours=window_hours)

    cutoff_ts = pd.Timestamp(cutoff)
    cohort = first_cart[first_cart["first_cart_time"] < cutoff_ts].copy()

    cohort_keys = cohort[["user_session", "product_id", "first_cart_time", "window_end_time"]]
    events_after_cart = df.merge(cohort_keys, on=["user_session", "product_id"], how="inner")
    events_after_cart = events_after_cart[
        (events_after_cart["event_time"] > events_after_cart["first_cart_time"])
        & (events_after_cart["event_time"] <= events_after_cart["window_end_time"])
    ].copy()

    event_summary = (
        events_after_cart.groupby(["user_session", "product_id"], as_index=False)
        .agg(
            has_purchase_48h=("event_type", lambda x: bool((x == "purchase").any())),
            has_remove_48h=("event_type", lambda x: bool((x == "remove_from_cart").any())),
            event_type_window=("event_type", lambda x: str(sorted(set(x.tolist())))),
            first_followup_time=("event_time", "min"),
        )
    )

    result = cohort.merge(event_summary, on=["user_session", "product_id"], how="left")
    result["has_purchase_48h"] = result["has_purchase_48h"].fillna(False).astype(bool)
    result["has_remove_48h"] = result["has_remove_48h"].fillna(False).astype(bool)
    result["event_type_window"] = result["event_type_window"].fillna("[]")

    result["group_type"] = np.select(
        [
            result["has_purchase_48h"],
            ~result["has_purchase_48h"] & result["has_remove_48h"],
        ],
        ["A", "C"],
        default="B",
    )

    result["event_time"] = result["first_cart_time"]
    result = result[
        [
            "user_session",
            "product_id",
            "event_type",
            "price",
            "user_id",
            "brand",
            "category_code",
            "category_id",
            "event_time",
            "group_type",
            "first_cart_time",
            "window_end_time",
            "has_purchase_48h",
            "has_remove_48h",
            "event_type_window",
            "first_followup_time",
        ]
    ].sort_values(["first_cart_time", "user_session", "product_id"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False, encoding="utf-8-sig")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build user_session x product_id groups using a fixed post-cart observation window."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--window-hours", type=int, default=48)
    parser.add_argument("--cutoff", default="2019-12-30 00:00:00+00:00")
    args = parser.parse_args()

    result = build_windowed_groups(
        input_path=args.input,
        output_path=args.output,
        window_hours=args.window_hours,
        cutoff=args.cutoff,
    )

    print(f"output: {args.output}")
    print(f"rows: {len(result):,}")
    print("group_type distribution:")
    print(result["group_type"].value_counts().sort_index().to_string())
    print("first_cart_time range:")
    print(result["first_cart_time"].min(), "->", result["first_cart_time"].max())


if __name__ == "__main__":
    main()
