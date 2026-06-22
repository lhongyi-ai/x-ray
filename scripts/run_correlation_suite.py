#!/usr/bin/env python3
"""Run the four current XRD correlation workflows into one organized folder."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the organized XRD correlation suite.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("outputs/correlation_suite_20260617"),
        help="Main output folder containing four correlation subfolders.",
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        default=["Data/Cell_14_integrated", "Data/Cell_29_integrated"],
        help="Integrated .xy directories/files.",
    )
    parser.add_argument(
        "--include-tier-c",
        action="store_true",
        help="Include likely-artifact Tier C candidates in the per-peak correlation output.",
    )
    return parser.parse_args()


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    python = sys.executable

    common_inputs = [str(item) for item in args.inputs]

    per_peak_dir = args.out_dir / "01_per_peak_frame_correlation"
    same_window_dir = args.out_dir / "02_same_window_acf_across_frames"
    single_frame_dir = args.out_dir / "03_single_frame_window_acf"
    all_window_dir = args.out_dir / "04_all_window_to_all_window_acf"
    static_overall_dir = args.out_dir / "05_static_peaks_and_overall_correlation"

    per_peak_cmd = [
            python,
            "scripts/per_peak_correlation_maps.py",
            *common_inputs,
            "--out-dir",
            str(per_peak_dir),
            "--review-plots",
            "--peak-match-tolerance",
            "0.02",
            "--micro-prominence",
            "0.005",
            "--raw-prominence",
            "0",
            "--shoulder-prominence",
            "0",
            "--matched-filter-prominence",
            "0.2",
            "--matched-filter-widths",
            "2,3,5,8",
            "--min-micro-snr",
            "0",
            "--min-shape-snr",
            "0.15",
            "--min-shape-contrast",
            "0.0005",
            "--shape-half-window",
            "0.16",
            "--top-peaks",
            "4000",
            "--prominence",
            "0.2",
            "--bump-prominence",
            "0.05",
            "--min-peak-height",
            "0",
            "--min-bump-rise",
            "0",
            "--distance",
            "1",
            "--merge-tolerance",
            "0.015",
            "--small-peak-max-prominence",
            "999",
            "--small-peak-max-width",
            "999",
    ]
    if args.include_tier_c:
        per_peak_cmd.append("--include-tier-c")
    run(per_peak_cmd)

    for mode, out_dir in [
        ("same-window", same_window_dir),
        ("single-frame", single_frame_dir),
        ("all-window", all_window_dir),
    ]:
        run(
            [
                python,
                "scripts/window_autocorrelation_correlations.py",
                *common_inputs,
                "--out-dir",
                str(out_dir),
                "--mode",
                mode,
                "--window-width",
                "5",
                "--window-step",
                "1",
                "--shift-tolerance",
                "1",
            ]
        )

    run(
        [
            python,
            "scripts/static_peak_and_overall_correlation.py",
            "--suite-dir",
            str(args.out_dir),
            "--out-dir",
            str(static_overall_dir),
        ]
    )

    with (args.out_dir / "README.txt").open("w") as handle:
        handle.write("XRD correlation suite\n")
        handle.write("=====================\n\n")
        handle.write("01_per_peak_frame_correlation:\n")
        handle.write("  One lower-triangle frame-vs-frame map per detected peak group.\n\n")
        handle.write("  Peak detector parameters:\n")
        handle.write("    micro-prominence: 0.005\n")
        handle.write("    raw-prominence: 0\n")
        handle.write("    shoulder-prominence: 0\n")
        handle.write("    matched-filter-prominence: 0.2\n")
        handle.write("    matched-filter-widths: 2,3,5,8 samples\n")
        handle.write("    min-shape-snr: 0.15\n")
        handle.write("    min-shape-contrast: 0.0005\n")
        handle.write("    shape-half-window: 0.16 deg\n")
        handle.write("    merge-tolerance: 0.015 deg\n")
        handle.write(f"    include-tier-c: {int(bool(args.include_tier_c))}\n\n")
        handle.write("02_same_window_acf_across_frames:\n")
        handle.write("  One lower-triangle frame-vs-frame ACF map per 5 degree window.\n")
        handle.write("  Handles up to +/-1 degree pressure shift by comparing neighboring windows and taking the best match.\n\n")
        handle.write("03_single_frame_window_acf:\n")
        handle.write("  For each frame, compares all 5 degree windows within that single frame.\n\n")
        handle.write("04_all_window_to_all_window_acf:\n")
        handle.write("  One large lower-triangle map comparing every frame-window against every other frame-window.\n")
        handle.write("\n05_static_peaks_and_overall_correlation:\n")
        handle.write("  Identifies high-coverage non-moving peak groups and writes overall frame correlation maps.\n")

    print(f"Wrote correlation suite to {args.out_dir}")


if __name__ == "__main__":
    main()
