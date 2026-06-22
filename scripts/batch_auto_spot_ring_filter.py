#!/usr/bin/env python3
"""Batch automation for UOTe ring rejection and spot extraction."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from pathlib import Path

import numpy as np

from auto_spot_ring_filter import FilterConfig, process_image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Automatically process a folder of 2D XRD TIFFs: detect powder "
            "rings, write masks, extract spots, and create batch summaries."
        )
    )
    parser.add_argument(
        "input",
        type=Path,
        help="A TIFF file, a directory to scan recursively, or a glob pattern.",
    )
    parser.add_argument(
        "--poni",
        type=Path,
        default=Path("raw_data/High_Pressure_PXRD/Data/Calibration/CeO2_30keV_168mm_0deg_001.poni"),
        help="Dioptas/pyFAI .poni file used for the beam center.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("outputs/auto_ring_filter_batch"),
        help="Batch output directory.",
    )
    parser.add_argument(
        "--pattern",
        default="*.tif",
        help="Recursive file pattern when input is a directory.",
    )
    parser.add_argument(
        "--geometry",
        choices=("auto", "poni", "pixel"),
        default="auto",
        help="Use full pyFAI/PONI geometry when available, or pixel-radius fallback.",
    )
    parser.add_argument(
        "--include",
        default=None,
        help="Optional regex that filenames must match.",
    )
    parser.add_argument(
        "--exclude",
        default=None,
        help="Optional regex that filenames must not match.",
    )
    parser.add_argument("--ring-half-width", type=float, default=3.0)
    parser.add_argument("--ring-prominence", type=float, default=2.4)
    parser.add_argument("--ring-mean-prominence", type=float, default=1.5)
    parser.add_argument("--ring-density-prominence", type=float, default=2.8)
    parser.add_argument("--ring-z-range", type=float, nargs=2, default=(1.5, 25.0))
    parser.add_argument("--min-ring-radius", type=float, default=80.0)
    parser.add_argument("--max-ring-radius-fraction", type=float, default=0.92)
    parser.add_argument("--spot-z", type=float, default=5.0)
    parser.add_argument("--micro-spot-z", type=float, default=4.5)
    parser.add_argument("--micro-spot-contrast", type=float, default=2.5)
    parser.add_argument("--min-area", type=int, default=2)
    parser.add_argument("--max-area", type=int, default=350)
    parser.add_argument("--max-eccentricity", type=float, default=0.998)
    parser.add_argument("--spot-dilate", type=int, default=2)
    parser.add_argument("--micro-spot-dilate", type=int, default=1)
    parser.add_argument("--spot-ring-tolerance", type=float, default=10.0)
    parser.add_argument("--spot-radius-group-tolerance", type=float, default=10.0)
    parser.add_argument(
        "--output-suffix",
        default="",
        help="Optional suffix inserted into output filenames and batch summary names.",
    )
    parser.add_argument(
        "--flat-output",
        action="store_true",
        help="Write all per-image outputs directly into --out-dir instead of one subfolder per image.",
    )
    parser.add_argument(
        "--pressure-output",
        action="store_true",
        help="Write per-image outputs into pressure folders under --out-dir.",
    )
    parser.add_argument(
        "--keep-on-rings",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Detect and protect spots that overlap ring bands.",
    )
    parser.add_argument("--no-plots", action="store_true", help="Skip per-image diagnostic PNGs.")
    parser.add_argument("--no-summary-plot", action="store_true", help="Skip batch summary PNG.")
    return parser.parse_args()


def config_from_args(args: argparse.Namespace) -> FilterConfig:
    return FilterConfig(
        geometry=str(args.geometry),
        ring_half_width=float(args.ring_half_width),
        ring_prominence=float(args.ring_prominence),
        ring_mean_prominence=float(args.ring_mean_prominence),
        ring_density_prominence=float(args.ring_density_prominence),
        ring_z_range=(float(args.ring_z_range[0]), float(args.ring_z_range[1])),
        min_ring_radius=float(args.min_ring_radius),
        max_ring_radius_fraction=float(args.max_ring_radius_fraction),
        spot_z=float(args.spot_z),
        micro_spot_z=float(args.micro_spot_z),
        micro_spot_contrast=float(args.micro_spot_contrast),
        min_area=int(args.min_area),
        max_area=int(args.max_area),
        max_eccentricity=float(args.max_eccentricity),
        spot_dilate=int(args.spot_dilate),
        micro_spot_dilate=int(args.micro_spot_dilate),
        spot_ring_tolerance=float(args.spot_ring_tolerance),
        spot_radius_group_tolerance=float(args.spot_radius_group_tolerance),
        keep_on_rings=bool(args.keep_on_rings),
        make_plot=not bool(args.no_plots),
    )


def discover_images(input_path: Path, pattern: str, include: str | None, exclude: str | None) -> list[Path]:
    if input_path.is_file():
        candidates = [input_path]
    elif input_path.is_dir():
        candidates = sorted(input_path.rglob(pattern))
    else:
        candidates = sorted(Path(".").glob(str(input_path)))

    include_re = re.compile(include) if include else None
    exclude_re = re.compile(exclude) if exclude else None
    images: list[Path] = []
    for path in candidates:
        if path.suffix.lower() not in {".tif", ".tiff"}:
            continue
        name = path.name
        if include_re and not include_re.search(name):
            continue
        if exclude_re and exclude_re.search(name):
            continue
        images.append(path)
    return images


def safe_output_name(path: Path) -> str:
    parent = path.parent.name.replace(" ", "_")
    return f"{parent}__{path.stem}"


def safe_pressure_name(path: Path) -> str:
    text = " ".join([path.name, path.parent.name])
    match = re.search(r"(\d+(?:p\d+|\.\d+)?)\s*G[PpOo][Aa]", text, flags=re.IGNORECASE)
    if match:
        value = match.group(1).replace(".", "p")
        return f"{value}_GPa"
    return path.parent.name.replace(" ", "_")


def suffixed_name(base: str, suffix: str, extension: str) -> str:
    return f"{base}{suffix}{extension}" if suffix else f"{base}{extension}"


def parse_pressure_gpa(path: Path) -> float | None:
    text = " ".join([path.parent.name, path.name])
    match = re.search(r"(\d+(?:p\d+|\.\d+)?)\s*G[PpOo][Aa]", text, flags=re.IGNORECASE)
    if not match:
        return None
    return float(match.group(1).replace("p", "."))


def write_summary_csv(path: Path, reports: list[dict]) -> None:
    fields = [
        "image",
        "pressure_gpa",
        "shape_y",
        "shape_x",
        "spot_count",
        "spot_pixels",
        "micro_spot_pixels",
        "merged_spot_core_pixels",
        "spot_display_pixels",
        "spot_display_pixels_on_raw_ring",
        "ring_count",
        "radius_group_count",
        "radial_source",
        "radial_units",
        "ring_radii_px",
        "ring_positions_coordinate",
        "profile_ring_radii_px",
        "mean_ring_radii_px",
        "density_ring_radii_px",
        "base_mask_fraction",
        "raw_ring_mask_fraction",
        "ring_mask_fraction",
        "combined_mask_fraction",
        "raw_ring_mask_npy",
        "combined_mask_npy",
        "filtered_image_npy",
        "micro_spot_mask_npy",
        "spot_mask_npy",
        "spots_csv",
        "diagnostic_png",
        "filtered_image_png",
        "grouped_overlay_png",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for report in reports:
            total = int(report["shape"][0]) * int(report["shape"][1])
            writer.writerow(
                {
                    "image": report["image"],
                    "pressure_gpa": report.get("pressure_gpa"),
                    "shape_y": report["shape"][0],
                    "shape_x": report["shape"][1],
                    "spot_count": report["spot_count"],
                    "spot_pixels": report["spot_pixels"],
                    "micro_spot_pixels": report["micro_spot_pixels"],
                    "merged_spot_core_pixels": report["merged_spot_core_pixels"],
                    "spot_display_pixels": report["spot_display_pixels"],
                    "spot_display_pixels_on_raw_ring": report["spot_display_pixels_on_raw_ring"],
                    "ring_count": len(report["ring_radii_px"]),
                    "radius_group_count": len(report["radius_spot_groups"]),
                    "radial_source": report["radial_source"],
                    "radial_units": report["radial_units"],
                    "ring_radii_px": " ".join(f"{x:.1f}" for x in report["ring_radii_px"]),
                    "ring_positions_coordinate": " ".join(
                        f"{x:.8g}" for x in report["ring_positions_coordinate"]
                    ),
                    "profile_ring_radii_px": " ".join(f"{x:.1f}" for x in report["profile_ring_radii_px"]),
                    "mean_ring_radii_px": " ".join(f"{x:.1f}" for x in report["mean_ring_radii_px"]),
                    "density_ring_radii_px": " ".join(f"{x:.1f}" for x in report["density_ring_radii_px"]),
                    "base_mask_fraction": report["base_mask_pixels"] / total,
                    "raw_ring_mask_fraction": report["raw_ring_mask_pixels"] / total,
                    "ring_mask_fraction": report["ring_mask_pixels"] / total,
                    "combined_mask_fraction": report["combined_mask_pixels"] / total,
                    "raw_ring_mask_npy": report["outputs"]["raw_ring_mask_npy"],
                    "combined_mask_npy": report["outputs"]["combined_mask_npy"],
                    "filtered_image_npy": report["outputs"]["filtered_image_npy"],
                    "micro_spot_mask_npy": report["outputs"]["micro_spot_mask_npy"],
                    "spot_mask_npy": report["outputs"]["spot_mask_npy"],
                    "spots_csv": report["outputs"]["spots_csv"],
                    "diagnostic_png": report["outputs"]["diagnostic_png"],
                    "filtered_image_png": report["outputs"]["filtered_image_png"],
                    "grouped_overlay_png": report["outputs"]["grouped_overlay_png"],
                }
            )


def write_all_spots_csv(path: Path, reports: list[dict]) -> None:
    wrote_header = False
    with path.open("w", newline="") as out_handle:
        writer: csv.DictWriter | None = None
        for report in reports:
            spots_csv = Path(report["outputs"]["spots_csv"])
            if not spots_csv.exists():
                continue
            with spots_csv.open(newline="") as in_handle:
                reader = csv.DictReader(in_handle)
                fields = ["image", "pressure_gpa"] + list(reader.fieldnames or [])
                if writer is None:
                    writer = csv.DictWriter(out_handle, fieldnames=fields)
                if not wrote_header:
                    writer.writeheader()
                    wrote_header = True
                for row in reader:
                    row_out = {"image": report["image"], "pressure_gpa": report.get("pressure_gpa")}
                    row_out.update(row)
                    writer.writerow(row_out)


def save_summary_plot(path: Path, reports: list[dict]) -> None:
    mpl_cache = path.parent / ".matplotlib"
    mpl_cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(mpl_cache))

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [Path(r["image"]).stem for r in reports]
    x = np.arange(len(reports))
    spot_counts = [r["spot_count"] for r in reports]
    ring_counts = [len(r["ring_radii_px"]) for r in reports]
    total_px = [r["shape"][0] * r["shape"][1] for r in reports]
    mask_frac = [r["combined_mask_pixels"] / total for r, total in zip(reports, total_px)]

    fig, axes = plt.subplots(3, 1, figsize=(12, 9), constrained_layout=True, sharex=True)
    axes[0].bar(x, spot_counts, color="tab:blue")
    axes[0].set_ylabel("spot count")
    axes[1].bar(x, ring_counts, color="tab:orange")
    axes[1].set_ylabel("ring count")
    axes[2].plot(x, mask_frac, marker="o", color="black")
    axes[2].set_ylabel("combined mask fraction")
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(labels, rotation=35, ha="right", fontsize=8)
    fig.suptitle("Batch auto ring filter summary")
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    images = discover_images(args.input, args.pattern, args.include, args.exclude)
    if not images:
        raise SystemExit(f"No TIFF images found for {args.input}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    config = config_from_args(args)
    output_suffix = str(args.output_suffix)
    reports: list[dict] = []

    for idx, image in enumerate(images, start=1):
        if args.flat_output:
            per_image_dir = args.out_dir
        elif args.pressure_output:
            per_image_dir = args.out_dir / safe_pressure_name(image)
        else:
            per_image_dir = args.out_dir / safe_output_name(image)
        print(f"[{idx}/{len(images)}] {image}")
        report = process_image(
            image,
            per_image_dir,
            poni_path=args.poni,
            config=config,
            output_suffix=output_suffix,
        )
        report["pressure_gpa"] = parse_pressure_gpa(image)
        reports.append(report)

    summary_csv = args.out_dir / suffixed_name("summary", output_suffix, ".csv")
    all_spots_csv = args.out_dir / suffixed_name("all_spots", output_suffix, ".csv")
    manifest_json = args.out_dir / suffixed_name("manifest", output_suffix, ".json")
    write_summary_csv(summary_csv, reports)
    write_all_spots_csv(all_spots_csv, reports)
    manifest_json.write_text(json.dumps({"reports": reports}, indent=2))

    summary_png = None
    if not args.no_summary_plot:
        summary_png = args.out_dir / suffixed_name("batch_summary", output_suffix, ".png")
        save_summary_plot(summary_png, reports)

    print(
        json.dumps(
            {
                "image_count": len(reports),
                "summary_csv": str(summary_csv),
                "all_spots_csv": str(all_spots_csv),
                "manifest_json": str(manifest_json),
                "summary_png": str(summary_png) if summary_png else None,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
