#!/usr/bin/env python3
"""Compare Figure 4 results with a five-method historical reference."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image


METHODS = ["KSSD-Array", "XXH3", "XXH64", "MurmurHash3", "Wyhash"]
RESAMPLE_LANCZOS = getattr(Image, "Resampling", Image).LANCZOS
RAW_KEYS = ["method", "k", "sequence_length", "bins", "repeat"]
SUMMARY_KEYS = ["method", "k", "sequence_length", "bins"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_historical(data: pd.DataFrame, exclude_method: str,
                         legacy_kssd_label: str,
                         new_kssd_label: str) -> pd.DataFrame:
    result = data[data["method"] != exclude_method].copy()
    result["method"] = result["method"].replace(
        {legacy_kssd_label: new_kssd_label})
    if "seq_len" in result.columns:
        result = result.rename(columns={"seq_len": "sequence_length"})
    if set(result["method"]) != set(METHODS):
        raise RuntimeError(
            f"filtered historical method set is {sorted(result['method'].unique())}")
    return result


def prepare_raw(new: pd.DataFrame, historical: pd.DataFrame) -> pd.DataFrame:
    historical = historical.rename(columns={
        "total_kmers": "mapped_value_count",
        "chi2_stat": "chi_square",
        "passed_p_gt_0.05": "non_reject",
        "num_buckets": "historical_num_buckets",
    })
    if "bucket_count_sum" not in historical:
        historical["bucket_count_sum"] = historical["mapped_value_count"]
    if "degrees_of_freedom" not in historical:
        historical["degrees_of_freedom"] = historical["bins"] - 1
    columns = RAW_KEYS + [
        "seed", "mapped_value_count", "bucket_count_sum",
        "degrees_of_freedom", "chi_square", "p_value", "non_reject",
    ]
    left = new[columns].copy()
    right = historical[columns].copy()
    merged = left.merge(
        right, on=RAW_KEYS, how="outer", suffixes=("_new", "_historical"),
        indicator=True, validate="one_to_one",
    )
    exact_columns = [
        "seed", "mapped_value_count", "bucket_count_sum",
        "degrees_of_freedom", "non_reject",
    ]
    float_columns = ["chi_square", "p_value"]
    merged["key_match"] = merged["_merge"] == "both"
    for column in exact_columns:
        merged[f"{column}_match"] = (
            merged[f"{column}_new"] == merged[f"{column}_historical"])
    for column in float_columns:
        merged[f"{column}_absolute_difference"] = np.abs(
            merged[f"{column}_new"] - merged[f"{column}_historical"])
        denominator = np.maximum(
            np.abs(merged[f"{column}_historical"]),
            np.finfo(float).tiny,
        )
        merged[f"{column}_relative_difference"] = (
            merged[f"{column}_absolute_difference"] / denominator)
        merged[f"{column}_within_1e_12"] = (
            merged[f"{column}_absolute_difference"] <= 1e-12)
    match_columns = ["key_match"] + [f"{column}_match" for column in exact_columns]
    match_columns += [f"{column}_within_1e_12" for column in float_columns]
    merged["exact_or_tolerance_match"] = merged[match_columns].all(axis=1)
    return merged


def prepare_summary(new: pd.DataFrame,
                    historical: pd.DataFrame) -> pd.DataFrame:
    historical = historical.rename(columns={
        "pass_count": "non_reject_count",
        "pass_probability": "non_rejection_rate",
    })
    if "non_rejection_rate_percent" not in historical:
        historical["non_rejection_rate_percent"] = (
            100.0 * historical["non_rejection_rate"])
    columns = SUMMARY_KEYS + [
        "repeats", "non_reject_count", "non_rejection_rate",
        "non_rejection_rate_percent",
    ]
    merged = new[columns].merge(
        historical[columns], on=SUMMARY_KEYS, how="outer",
        suffixes=("_new", "_historical"), indicator=True,
        validate="one_to_one",
    )
    merged["key_match"] = merged["_merge"] == "both"
    merged["repeat_match"] = (
        merged["repeats_new"] == merged["repeats_historical"])
    merged["non_reject_count_match"] = (
        merged["non_reject_count_new"] ==
        merged["non_reject_count_historical"])
    merged["percentage_point_difference"] = (
        merged["non_rejection_rate_percent_new"] -
        merged["non_rejection_rate_percent_historical"])
    merged["rate_match"] = (
        np.abs(merged["percentage_point_difference"]) <= 1e-12)
    merged["exact_or_tolerance_match"] = merged[[
        "key_match", "repeat_match", "non_reject_count_match", "rate_match",
    ]].all(axis=1)
    return merged


def safe_correlation(left: pd.Series, right: pd.Series) -> float:
    if left.nunique() <= 1 or right.nunique() <= 1:
        return 1.0 if np.allclose(left, right) else 0.0
    return float(left.corr(right))


def trend_metrics(summary: pd.DataFrame) -> tuple[dict[str, float], pd.DataFrame]:
    complete = summary[summary["_merge"] == "both"].copy()
    new = complete["non_rejection_rate_percent_new"]
    old = complete["non_rejection_rate_percent_historical"]
    differences = new - old
    method_rows = []
    for method in METHODS:
        subset = complete[complete["method"] == method]
        method_rows.append({
            "method": method,
            "pearson": safe_correlation(
                subset["non_rejection_rate_percent_new"],
                subset["non_rejection_rate_percent_historical"]),
            "mean_absolute_percentage_point_difference": float(
                np.abs(subset["percentage_point_difference"]).mean()),
            "maximum_absolute_percentage_point_difference": float(
                np.abs(subset["percentage_point_difference"]).max()),
        })

    direction_matches = []
    for _, group in complete.groupby(
            ["method", "sequence_length", "bins"], sort=True):
        ordered = group.sort_values("k")
        new_direction = np.sign(np.diff(
            ordered["non_rejection_rate_percent_new"].to_numpy()))
        old_direction = np.sign(np.diff(
            ordered["non_rejection_rate_percent_historical"].to_numpy()))
        direction_matches.extend((new_direction == old_direction).tolist())
    metrics = {
        "overall_pearson": safe_correlation(new, old),
        "mean_absolute_percentage_point_difference": float(np.abs(differences).mean()),
        "root_mean_square_percentage_point_difference": float(
            np.sqrt(np.mean(np.square(differences)))),
        "maximum_absolute_percentage_point_difference": float(np.abs(differences).max()),
        "adjacent_direction_agreement": float(np.mean(direction_matches)),
    }
    return metrics, pd.DataFrame(method_rows)


def difference_hash(image: Image.Image) -> str:
    gray = image.convert("L").resize((9, 8), RESAMPLE_LANCZOS)
    values = np.asarray(gray)
    bits = values[:, 1:] > values[:, :-1]
    return f"{sum(int(bit) << index for index, bit in enumerate(bits.flat)):016x}"


def hash_distance(left: str, right: str) -> int:
    return bin(int(left, 16) ^ int(right, 16)).count("1")


def image_metrics(new_path: Path, historical_path: Path) -> dict[str, object]:
    new_image = Image.open(new_path).convert("RGB")
    historical_image = Image.open(historical_path).convert("RGB")
    resized_historical = historical_image.resize(
        new_image.size, RESAMPLE_LANCZOS)
    new_values = np.asarray(new_image, dtype=np.float64)
    old_values = np.asarray(resized_historical, dtype=np.float64)
    result: dict[str, object] = {
        "new_dimensions": list(new_image.size),
        "historical_dimensions": list(historical_image.size),
        "pixel_correlation_after_resize": float(
            np.corrcoef(new_values.ravel(), old_values.ravel())[0, 1]),
        "new_difference_hash": difference_hash(new_image),
        "historical_difference_hash": difference_hash(historical_image),
    }
    result["difference_hash_distance"] = hash_distance(
        result["new_difference_hash"], result["historical_difference_hash"])
    try:
        from skimage.metrics import structural_similarity
        result["ssim_after_resize"] = float(structural_similarity(
            new_values, old_values, channel_axis=2, data_range=255.0))
    except (ImportError, ValueError) as error:
        result["ssim_after_resize"] = None
        result["ssim_note"] = str(error)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--new-raw", type=Path, required=True)
    parser.add_argument("--new-summary", type=Path, required=True)
    parser.add_argument("--historical-raw", type=Path, required=True)
    parser.add_argument("--historical-summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--exclude-method", required=True)
    parser.add_argument("--legacy-kssd-label", required=True)
    parser.add_argument("--new-kssd-label", default="KSSD-Array")
    parser.add_argument("--new-figure", type=Path)
    parser.add_argument("--historical-figure", type=Path)
    parser.add_argument("--minimum-pearson", type=float, default=0.9)
    parser.add_argument("--maximum-mae", type=float, default=15.0)
    parser.add_argument("--minimum-direction-agreement", type=float, default=0.7)
    args = parser.parse_args()

    if bool(args.new_figure) != bool(args.historical_figure):
        parser.error("new and historical figure paths must be supplied together")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    new_raw = pd.read_csv(args.new_raw)
    new_summary = pd.read_csv(args.new_summary)
    historical_raw = normalize_historical(
        pd.read_csv(args.historical_raw), args.exclude_method,
        args.legacy_kssd_label, args.new_kssd_label)
    historical_summary = normalize_historical(
        pd.read_csv(args.historical_summary), args.exclude_method,
        args.legacy_kssd_label, args.new_kssd_label)
    raw_comparison = prepare_raw(new_raw, historical_raw)
    summary_comparison = prepare_summary(new_summary, historical_summary)
    raw_mismatches = raw_comparison[
        ~raw_comparison["exact_or_tolerance_match"]]
    summary_mismatches = summary_comparison[
        ~summary_comparison["exact_or_tolerance_match"]]

    raw_comparison.to_csv(
        args.output_dir / "figure4_raw_comparison.csv", index=False)
    raw_mismatches.to_csv(
        args.output_dir / "figure4_raw_mismatches.csv", index=False)
    summary_comparison.to_csv(
        args.output_dir / "figure4_summary_comparison.csv", index=False)
    summary_mismatches.to_csv(
        args.output_dir / "figure4_summary_mismatches.csv", index=False)
    summary_comparison.to_csv(
        args.output_dir / "figure4_trend_comparison.csv", index=False)

    metrics, method_metrics = trend_metrics(summary_comparison)
    method_metrics.to_csv(
        args.output_dir / "figure4_trend_metrics_by_method.csv", index=False)
    trend_similar = (
        metrics["overall_pearson"] >= args.minimum_pearson and
        metrics["mean_absolute_percentage_point_difference"] <= args.maximum_mae and
        metrics["adjacent_direction_agreement"] >= args.minimum_direction_agreement
    )
    max_float_difference = max(
        float(raw_comparison["chi_square_absolute_difference"].max()),
        float(raw_comparison["p_value_absolute_difference"].max()),
    )
    report: dict[str, object] = {
        "new_raw_rows": len(new_raw),
        "new_summary_rows": len(new_summary),
        "filtered_historical_raw_rows": len(historical_raw),
        "filtered_historical_summary_rows": len(historical_summary),
        "raw_mismatch_rows": len(raw_mismatches),
        "summary_mismatch_rows": len(summary_mismatches),
        "maximum_raw_floating_point_absolute_difference": max_float_difference,
        "trend_metrics": metrics,
        "trend_thresholds": {
            "minimum_overall_pearson": args.minimum_pearson,
            "maximum_mean_absolute_percentage_point_difference": args.maximum_mae,
            "minimum_adjacent_direction_agreement": args.minimum_direction_agreement,
        },
        "trend_acceptance": "PASS" if trend_similar else "FAIL",
        "comparison_classification": (
            "plotted_data_exact_visual_equivalent"
            if len(summary_mismatches) == 0 else
            "plotted_data_trend_similar"
            if trend_similar else "plotted_data_mismatch"
        ),
        "source_sha256": {
            "new_raw": sha256(args.new_raw),
            "new_summary": sha256(args.new_summary),
            "historical_raw": sha256(args.historical_raw),
            "historical_summary": sha256(args.historical_summary),
        },
    }
    if args.new_figure:
        report["image_metrics"] = image_metrics(
            args.new_figure, args.historical_figure)
        report["source_sha256"].update({
            "new_figure": sha256(args.new_figure),
            "historical_figure": sha256(args.historical_figure),
        })
    (args.output_dir / "figure4_comparison_metrics.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if trend_similar else 1


if __name__ == "__main__":
    raise SystemExit(main())
