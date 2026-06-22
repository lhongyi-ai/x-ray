#!/usr/bin/env python3
"""Automatically reject powder rings and keep compact diffraction spots.

This script is designed for the UOTe high-pressure TIFFs in this repository.
When pyFAI is available it uses the full Dioptas/PONI geometry to build a
2-theta radial coordinate. Without pyFAI it falls back to a PONI-derived beam
center and pixel-radius geometry.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import tifffile
from scipy import ndimage as ndi
from scipy.signal import find_peaks
from skimage import measure, morphology


PILATUS_CDTE_1M_PIXEL_SIZE_M = 172e-6
warnings.filterwarnings("ignore", category=FutureWarning)


@dataclass
class SpotRecord:
    label: int
    y: float
    x: float
    area_px: int
    major_axis_px: float
    minor_axis_px: float
    eccentricity: float
    orientation_deg: float
    mean_intensity: float
    max_intensity: float
    mean_z: float
    max_z: float
    bbox_min_y: int
    bbox_min_x: int
    bbox_max_y: int
    bbox_max_x: int
    radius_px: float
    ring_index: int
    ring_radius_px: float
    ring_delta_px: float
    radius_group_index: int
    radius_group_radius_px: float
    radius_group_delta_px: float


@dataclass
class FilterConfig:
    geometry: str = "auto"
    ring_half_width: float = 3.0
    ring_prominence: float = 2.4
    ring_mean_prominence: float = 1.5
    ring_density_prominence: float = 2.8
    ring_z_range: tuple[float, float] = (1.5, 25.0)
    min_ring_radius: float = 80.0
    max_ring_radius_fraction: float = 0.92
    spot_z: float = 5.0
    micro_spot_z: float = 4.5
    micro_spot_contrast: float = 2.5
    min_area: int = 2
    max_area: int = 350
    max_eccentricity: float = 0.998
    spot_dilate: int = 2
    micro_spot_dilate: int = 1
    spot_ring_tolerance: float = 10.0
    spot_radius_group_tolerance: float = 10.0
    keep_on_rings: bool = True
    make_plot: bool = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an automatic powder-ring mask and detect compact bright "
            "diffraction spots in a 2D XRD TIFF."
        )
    )
    parser.add_argument("image", type=Path, help="Input TIFF image.")
    parser.add_argument(
        "--poni",
        type=Path,
        default=None,
        help="Optional Dioptas/pyFAI .poni calibration file.",
    )
    parser.add_argument(
        "--center",
        type=float,
        nargs=2,
        metavar=("Y", "X"),
        default=None,
        help="Beam center in pixel coordinates. Overrides --poni center.",
    )
    parser.add_argument(
        "--geometry",
        choices=("auto", "poni", "pixel"),
        default="auto",
        help=(
            "Radial geometry source. 'auto' uses full pyFAI/PONI geometry when "
            "available, otherwise pixel radius; 'poni' requires pyFAI; 'pixel' "
            "uses only the beam center."
        ),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("outputs/auto_ring_filter"),
        help="Directory for masks, CSVs, reports, and diagnostic PNGs.",
    )
    parser.add_argument(
        "--ring-half-width",
        type=float,
        default=3.0,
        help="Half-width in pixels for annular ring masks around detected radii.",
    )
    parser.add_argument(
        "--ring-prominence",
        type=float,
        default=2.4,
        help="Minimum robust prominence for radial ring peak detection.",
    )
    parser.add_argument(
        "--ring-density-prominence",
        type=float,
        default=2.8,
        help=(
            "Minimum prominence for detecting faint partial rings from the "
            "radial density of moderate residual pixels."
        ),
    )
    parser.add_argument(
        "--ring-mean-prominence",
        type=float,
        default=1.5,
        help="Minimum prominence for mean-profile ring peak detection.",
    )
    parser.add_argument(
        "--ring-z-range",
        type=float,
        nargs=2,
        metavar=("LOW", "HIGH"),
        default=(1.5, 25.0),
        help="Residual z-score range used to vote for faint ring pixels.",
    )
    parser.add_argument(
        "--min-ring-radius",
        type=float,
        default=80.0,
        help="Ignore ring candidates closer than this radius in pixels.",
    )
    parser.add_argument(
        "--max-ring-radius-fraction",
        type=float,
        default=0.92,
        help="Ignore ring candidates beyond this fraction of the valid radial range.",
    )
    parser.add_argument(
        "--spot-z",
        type=float,
        default=5.0,
        help="Minimum annular-background z score for spot pixels.",
    )
    parser.add_argument(
        "--micro-spot-z",
        type=float,
        default=4.5,
        help="Minimum high-pass local-maximum z score for tiny spot detection.",
    )
    parser.add_argument(
        "--micro-spot-contrast",
        type=float,
        default=2.5,
        help="Minimum local contrast for tiny spot detection.",
    )
    parser.add_argument(
        "--min-area",
        type=int,
        default=2,
        help="Minimum connected-component area for spot candidates.",
    )
    parser.add_argument(
        "--max-area",
        type=int,
        default=350,
        help="Maximum connected-component area for spot candidates.",
    )
    parser.add_argument(
        "--max-eccentricity",
        type=float,
        default=0.998,
        help="Reject very long arc-like objects above this eccentricity.",
    )
    parser.add_argument(
        "--spot-dilate",
        type=int,
        default=2,
        help="Dilate detected spot mask by this radius for saved masks/PNG marking.",
    )
    parser.add_argument(
        "--micro-spot-dilate",
        type=int,
        default=1,
        help="Dilate micro-spot local maxima by this radius before merging.",
    )
    parser.add_argument(
        "--spot-ring-tolerance",
        type=float,
        default=10.0,
        help="Maximum radius difference in pixels for assigning a spot to a detected ring.",
    )
    parser.add_argument(
        "--spot-radius-group-tolerance",
        type=float,
        default=10.0,
        help="Maximum radius difference in pixels for grouping spots by same radius.",
    )
    parser.add_argument(
        "--keep-on-rings",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Detect and protect spots even if they overlap detected ring bands. "
            "Use --no-keep-on-rings to restore the older behavior."
        ),
    )
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="Skip the diagnostic PNG.",
    )
    parser.add_argument(
        "--output-suffix",
        default="",
        help="Optional suffix inserted into output filenames before the standard ending.",
    )
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
        make_plot=not bool(args.no_plot),
    )


def read_poni_center(path: Path, pixel_size_m: float) -> tuple[float, float]:
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split(":", 1)
        values[key.strip().lower()] = value.strip()

    if "poni1" not in values or "poni2" not in values:
        raise ValueError(f"{path} does not contain Poni1/Poni2 fields")

    center_y = float(values["poni1"]) / pixel_size_m
    center_x = float(values["poni2"]) / pixel_size_m
    return center_y, center_x


def radial_pixels(shape: tuple[int, int], center: tuple[float, float]) -> np.ndarray:
    yy, xx = np.indices(shape, dtype=np.float32)
    cy, cx = center
    return np.hypot(yy - cy, xx - cx)


def pyfai_two_theta_array(shape: tuple[int, int], poni_path: Path) -> np.ndarray:
    try:
        import pyFAI  # type: ignore
    except ImportError as exc:
        raise RuntimeError("pyFAI is not installed in this Python environment") from exc

    ai = pyFAI.load(str(poni_path))
    try:
        two_theta = ai.center_array(shape, unit="2th_rad")
    except Exception:
        two_theta = ai.twoThetaArray(shape)
    return np.asarray(two_theta, dtype=np.float32)


def coordinate_step(coordinate: np.ndarray, valid: np.ndarray) -> float:
    grad_y, grad_x = np.gradient(coordinate.astype(np.float32))
    grad = np.hypot(grad_y, grad_x)
    good = np.isfinite(grad) & np.isfinite(coordinate) & valid & (grad > 0)
    if not np.any(good):
        return 1.0
    return max(float(np.median(grad[good])), np.finfo(np.float32).eps)


def build_radial_coordinate(
    shape: tuple[int, int],
    valid: np.ndarray,
    *,
    poni_path: Path | None,
    center: tuple[float, float] | None,
    geometry: str,
) -> tuple[np.ndarray, tuple[float, float], dict[str, object]]:
    if center is not None:
        center_yx = (float(center[0]), float(center[1]))
        radial = radial_pixels(shape, center_yx)
        return radial, center_yx, {
            "radial_source": "pixel_radius",
            "radial_units": "px",
            "center_source": "cli",
            "coordinate_origin": 0.0,
            "coordinate_step": 1.0,
        }

    center_source = "image midpoint fallback"
    if poni_path is not None:
        center_yx = read_poni_center(poni_path, PILATUS_CDTE_1M_PIXEL_SIZE_M)
        center_source = str(poni_path)
    else:
        center_yx = ((shape[0] - 1) / 2.0, (shape[1] - 1) / 2.0)

    if geometry in {"auto", "poni"} and poni_path is not None:
        try:
            two_theta = pyfai_two_theta_array(shape, poni_path)
            origin = float(np.nanmin(two_theta[valid]))
            step = coordinate_step(two_theta, valid)
            radial = (two_theta - origin) / step
            return radial.astype(np.float32), center_yx, {
                "radial_source": "pyFAI_poni_2theta",
                "radial_units": "2th_rad_scaled_to_pixel_step",
                "center_source": center_source,
                "coordinate_origin": origin,
                "coordinate_step": step,
            }
        except RuntimeError:
            if geometry == "poni":
                raise
        except Exception as exc:
            if geometry == "poni":
                raise RuntimeError(f"Could not build pyFAI coordinate from {poni_path}") from exc

    radial = radial_pixels(shape, center_yx)
    return radial, center_yx, {
        "radial_source": "pixel_radius",
        "radial_units": "px",
        "center_source": center_source,
        "coordinate_origin": 0.0,
        "coordinate_step": 1.0,
    }


def robust_binned_stats(
    image: np.ndarray,
    radial: np.ndarray,
    valid: np.ndarray,
    n_bins: int | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    radial_i = np.rint(radial).astype(np.int32)
    if n_bins is None:
        n_bins = int(radial_i[valid].max()) + 1

    med = np.full(n_bins, np.nan, dtype=np.float32)
    mad = np.full(n_bins, np.nan, dtype=np.float32)
    q90 = np.full(n_bins, np.nan, dtype=np.float32)
    counts = np.bincount(radial_i[valid].ravel(), minlength=n_bins).astype(np.int64)

    flat_img = image[valid].astype(np.float32, copy=False)
    flat_rad = radial_i[valid]
    order = np.argsort(flat_rad)
    flat_rad = flat_rad[order]
    flat_img = flat_img[order]

    starts = np.flatnonzero(np.r_[True, flat_rad[1:] != flat_rad[:-1]])
    stops = np.r_[starts[1:], flat_rad.size]
    for start, stop in zip(starts, stops):
        idx = int(flat_rad[start])
        vals = flat_img[start:stop]
        vals = vals[np.isfinite(vals)]
        if vals.size == 0:
            continue
        med_i = np.median(vals)
        med[idx] = med_i
        mad[idx] = np.median(np.abs(vals - med_i))
        q90[idx] = np.quantile(vals, 0.90)

    med = fill_nan_1d(med)
    mad = fill_nan_1d(mad)
    q90 = fill_nan_1d(q90)
    mad = np.maximum(mad, 1.0)
    return med, mad, q90, counts


def binned_mean_profile(
    image: np.ndarray,
    radial: np.ndarray,
    valid: np.ndarray,
    n_bins: int,
) -> np.ndarray:
    radial_i = np.rint(radial).astype(np.int32)
    radial_i = np.clip(radial_i, 0, n_bins - 1)
    values = image[valid].astype(np.float32, copy=False)
    bins = radial_i[valid]
    sums = np.bincount(bins.ravel(), weights=values.ravel(), minlength=n_bins)
    counts = np.bincount(bins.ravel(), minlength=n_bins)
    mean = np.full(n_bins, np.nan, dtype=np.float32)
    good = counts > 0
    mean[good] = sums[good] / counts[good]
    return fill_nan_1d(mean)


def fill_nan_1d(values: np.ndarray) -> np.ndarray:
    out = values.astype(np.float32, copy=True)
    ok = np.isfinite(out)
    if ok.all():
        return out
    if not ok.any():
        return np.zeros_like(out)
    x = np.arange(out.size)
    out[~ok] = np.interp(x[~ok], x[ok], out[ok])
    return out


def detect_ring_radii(
    q90_profile: np.ndarray,
    counts: np.ndarray,
    min_prominence: float,
    min_radius: float = 0.0,
    max_radius: float | None = None,
) -> tuple[np.ndarray, dict[str, np.ndarray | float]]:
    smooth = ndi.gaussian_filter1d(q90_profile.astype(np.float32), sigma=2.0)
    baseline = ndi.gaussian_filter1d(smooth, sigma=35.0)
    residual = smooth - baseline
    scale = 1.4826 * np.median(np.abs(residual - np.median(residual)))
    scale = max(float(scale), 1.0)
    score = residual / scale

    enough_pixels = counts > max(50, int(np.nanmax(counts) * 0.08))
    score_for_peaks = np.where(enough_pixels, score, 0.0)
    peaks, props = find_peaks(
        score_for_peaks,
        prominence=min_prominence,
        distance=12,
        width=(2, 80),
    )
    peaks = filter_radii(peaks, min_radius, max_radius)
    diagnostics = {
        "smooth_q90": smooth,
        "baseline": baseline,
        "ring_score": score,
        "prominences": props.get("prominences", np.array([], dtype=float)),
        "widths": props.get("widths", np.array([], dtype=float)),
    }
    return peaks.astype(np.float32), diagnostics


def detect_mean_ring_radii(
    mean_profile: np.ndarray,
    counts: np.ndarray,
    min_prominence: float,
    min_radius: float = 0.0,
    max_radius: float | None = None,
) -> tuple[np.ndarray, dict[str, np.ndarray | float]]:
    smooth = ndi.gaussian_filter1d(mean_profile.astype(np.float32), sigma=2.0)
    baseline = ndi.gaussian_filter1d(smooth, sigma=28.0)
    residual = smooth - baseline
    scale = 1.4826 * np.median(np.abs(residual - np.median(residual)))
    scale = max(float(scale), 1.0)
    score = residual / scale

    enough_pixels = counts > max(50, int(np.nanmax(counts) * 0.08))
    score_for_peaks = np.where(enough_pixels, score, 0.0)
    peaks, props = find_peaks(
        score_for_peaks,
        prominence=min_prominence,
        distance=10,
        width=(2, 120),
    )
    peaks = filter_radii(peaks, min_radius, max_radius)
    diagnostics = {
        "smooth_mean": smooth,
        "mean_baseline": baseline,
        "mean_score": score,
        "prominences": props.get("prominences", np.array([], dtype=float)),
        "widths": props.get("widths", np.array([], dtype=float)),
    }
    return peaks.astype(np.float32), diagnostics


def detect_density_ring_radii(
    z: np.ndarray,
    radial: np.ndarray,
    valid: np.ndarray,
    counts: np.ndarray,
    z_range: tuple[float, float],
    min_prominence: float,
    min_radius: float,
    max_radius: float | None,
) -> tuple[np.ndarray, dict[str, np.ndarray | float]]:
    radial_i = np.rint(radial).astype(np.int32)
    low, high = z_range
    votes = (z >= low) & (z <= high) & valid
    hit_counts = np.bincount(radial_i[votes].ravel(), minlength=counts.size)
    density = hit_counts / np.maximum(counts, 1)
    smooth = ndi.gaussian_filter1d(density.astype(np.float32), sigma=2.0)
    baseline = ndi.gaussian_filter1d(smooth, sigma=35.0)
    residual = smooth - baseline
    scale = 1.4826 * np.median(np.abs(residual - np.median(residual)))
    scale = max(float(scale), 1e-6)
    score = residual / scale

    enough_pixels = counts > max(50, int(np.nanmax(counts) * 0.08))
    score_for_peaks = np.where(enough_pixels, score, 0.0)
    peaks, props = find_peaks(
        score_for_peaks,
        prominence=min_prominence,
        distance=12,
        width=(2, 80),
    )
    peaks = filter_radii(peaks, min_radius, max_radius)
    diagnostics = {
        "density": density,
        "smooth_density": smooth,
        "density_score": score,
        "prominences": props.get("prominences", np.array([], dtype=float)),
        "widths": props.get("widths", np.array([], dtype=float)),
    }
    return peaks.astype(np.float32), diagnostics


def filter_radii(
    radii: np.ndarray,
    min_radius: float = 0.0,
    max_radius: float | None = None,
) -> np.ndarray:
    keep = radii >= min_radius
    if max_radius is not None:
        keep &= radii <= max_radius
    return radii[keep]


def merge_close_radii(radii: Iterable[float], tolerance: float = 8.0) -> np.ndarray:
    ordered = sorted(float(radius) for radius in radii)
    if not ordered:
        return np.array([], dtype=np.float32)
    groups: list[list[float]] = [[ordered[0]]]
    for radius in ordered[1:]:
        if radius - groups[-1][-1] <= tolerance:
            groups[-1].append(radius)
        else:
            groups.append([radius])
    merged = [float(np.mean(group)) for group in groups]
    return np.array(merged, dtype=np.float32)


def build_ring_mask(
    radial: np.ndarray,
    ring_radii: Iterable[float],
    half_width: float,
    base_mask: np.ndarray,
) -> np.ndarray:
    mask = np.zeros(radial.shape, dtype=bool)
    for radius in ring_radii:
        mask |= np.abs(radial - float(radius)) <= half_width
    mask &= ~base_mask
    return mask


def detect_spots(
    image: np.ndarray,
    radial: np.ndarray,
    base_mask: np.ndarray,
    ring_mask: np.ndarray,
    med: np.ndarray,
    mad: np.ndarray,
    spot_z: float,
    min_area: int,
    max_area: int,
    max_eccentricity: float,
    keep_on_rings: bool,
) -> tuple[np.ndarray, np.ndarray, list[SpotRecord]]:
    radial_i = np.clip(np.rint(radial).astype(np.int32), 0, med.size - 1)
    background = med[radial_i]
    sigma = np.maximum(1.4826 * mad[radial_i], 1.0)
    z = (image.astype(np.float32) - background) / sigma

    candidate = z >= spot_z
    candidate &= ~base_mask
    if not keep_on_rings:
        candidate &= ~ring_mask

    candidate = morphology.remove_small_objects(candidate, min_size=min_area)
    candidate = morphology.binary_opening(candidate, morphology.disk(1))
    candidate = morphology.binary_closing(candidate, morphology.disk(1))

    labels = measure.label(candidate, connectivity=2)
    clean = np.zeros(candidate.shape, dtype=bool)
    records: list[SpotRecord] = []

    for region in measure.regionprops(labels, intensity_image=image):
        if region.area < min_area or region.area > max_area:
            continue
        if region.eccentricity > max_eccentricity:
            continue

        coords = region.coords
        rr = radial[coords[:, 0], coords[:, 1]]
        zz = z[coords[:, 0], coords[:, 1]]
        clean[coords[:, 0], coords[:, 1]] = True
        cy, cx = region.weighted_centroid
        minr, minc, maxr, maxc = region.bbox
        records.append(
            SpotRecord(
                label=len(records) + 1,
                y=float(cy),
                x=float(cx),
                area_px=int(region.area),
                major_axis_px=float(region.major_axis_length),
                minor_axis_px=float(region.minor_axis_length),
                eccentricity=float(region.eccentricity),
                orientation_deg=float(np.rad2deg(region.orientation)),
                mean_intensity=float(region.mean_intensity),
                max_intensity=float(region.max_intensity),
                mean_z=float(np.mean(zz)),
                max_z=float(np.max(zz)),
                bbox_min_y=int(minr),
                bbox_min_x=int(minc),
                bbox_max_y=int(maxr),
                bbox_max_x=int(maxc),
                radius_px=float(np.mean(rr)),
                ring_index=-1,
                ring_radius_px=float("nan"),
                ring_delta_px=float("nan"),
                radius_group_index=-1,
                radius_group_radius_px=float("nan"),
                radius_group_delta_px=float("nan"),
            )
        )

    return clean, z, records


def detect_micro_spots(
    image: np.ndarray,
    z: np.ndarray,
    base_mask: np.ndarray,
    threshold: float,
    contrast_threshold: float,
    dilate_radius: int,
) -> np.ndarray:
    image_f = np.asarray(image, dtype=np.float32)
    filled = image_f.copy()
    valid = np.isfinite(filled) & ~base_mask
    fill_value = float(np.nanmedian(filled[valid])) if np.any(valid) else 0.0
    filled[~valid] = fill_value

    fine = ndi.gaussian_filter(filled, sigma=0.45)
    coarse = ndi.gaussian_filter(filled, sigma=2.0)
    dog = fine - coarse
    dog_valid = dog[valid]
    dog_scale = 1.4826 * np.median(np.abs(dog_valid - np.median(dog_valid))) if dog_valid.size else 1.0
    dog_scale = max(float(dog_scale), 1.0)
    dog_z = dog / dog_scale

    local_max = dog == ndi.maximum_filter(dog, size=3)
    local_floor = ndi.percentile_filter(filled, percentile=25, size=5)
    local_contrast = (filled - local_floor) / dog_scale
    micro = (
        (z >= threshold)
        & (dog_z >= threshold)
        & (local_contrast >= contrast_threshold)
        & local_max
        & ~base_mask
    )
    if dilate_radius > 0:
        micro = morphology.binary_dilation(micro, morphology.disk(dilate_radius))
    return np.asarray(micro, dtype=bool)


def nearest_ring_group(
    radius_px: float,
    ring_radii: np.ndarray,
    tolerance: float,
) -> tuple[int, float, float]:
    if ring_radii.size == 0:
        return -1, float("nan"), float("nan")
    deltas = np.abs(ring_radii.astype(np.float32) - float(radius_px))
    index = int(np.argmin(deltas))
    delta = float(deltas[index])
    ring_radius = float(ring_radii[index])
    if delta > tolerance:
        return -1, ring_radius, delta
    return index, ring_radius, delta


def records_from_spot_mask(
    spot_mask: np.ndarray,
    image: np.ndarray,
    z: np.ndarray,
    radial: np.ndarray,
    ring_radii: np.ndarray,
    ring_tolerance: float,
    min_area: int,
    max_area: int,
    max_eccentricity: float,
) -> list[SpotRecord]:
    labels = measure.label(spot_mask, connectivity=2)
    records: list[SpotRecord] = []
    for region in measure.regionprops(labels, intensity_image=image):
        if region.area < min_area or region.area > max_area:
            continue
        if region.eccentricity > max_eccentricity:
            continue

        coords = region.coords
        rr = radial[coords[:, 0], coords[:, 1]]
        zz = z[coords[:, 0], coords[:, 1]]
        mean_radius = float(np.mean(rr))
        ring_index, ring_radius, ring_delta = nearest_ring_group(
            mean_radius,
            ring_radii,
            ring_tolerance,
        )
        cy, cx = region.weighted_centroid
        minr, minc, maxr, maxc = region.bbox
        records.append(
            SpotRecord(
                label=len(records) + 1,
                y=float(cy),
                x=float(cx),
                area_px=int(region.area),
                major_axis_px=float(region.major_axis_length),
                minor_axis_px=float(region.minor_axis_length),
                eccentricity=float(region.eccentricity),
                orientation_deg=float(np.rad2deg(region.orientation)),
                mean_intensity=float(region.mean_intensity),
                max_intensity=float(region.max_intensity),
                mean_z=float(np.mean(zz)),
                max_z=float(np.max(zz)),
                bbox_min_y=int(minr),
                bbox_min_x=int(minc),
                bbox_max_y=int(maxr),
                bbox_max_x=int(maxc),
                radius_px=mean_radius,
                ring_index=ring_index,
                ring_radius_px=ring_radius,
                ring_delta_px=ring_delta,
                radius_group_index=-1,
                radius_group_radius_px=float("nan"),
                radius_group_delta_px=float("nan"),
            )
        )
    return records


def assign_radius_groups(records: list[SpotRecord], tolerance: float) -> list[dict[str, object]]:
    ordered = sorted(records, key=lambda record: record.radius_px)
    groups: list[list[SpotRecord]] = []
    for record in ordered:
        if not groups:
            groups.append([record])
            continue
        current_radius = float(np.mean([item.radius_px for item in groups[-1]]))
        if abs(record.radius_px - current_radius) <= tolerance:
            groups[-1].append(record)
        else:
            groups.append([record])

    summaries: list[dict[str, object]] = []
    for index, group in enumerate(groups):
        radius = float(np.mean([record.radius_px for record in group]))
        for record in group:
            record.radius_group_index = index
            record.radius_group_radius_px = radius
            record.radius_group_delta_px = float(record.radius_px - radius)
        summaries.append(
            {
                "radius_group_index": index,
                "radius_group_radius_px": radius,
                "spot_count": len(group),
            }
        )
    return summaries


def ring_group_counts(records: list[SpotRecord], ring_radii: np.ndarray) -> list[dict[str, object]]:
    counts: list[dict[str, object]] = []
    for index, radius in enumerate(ring_radii):
        group_records = [record for record in records if record.ring_index == index]
        counts.append(
            {
                "ring_index": index,
                "ring_radius_px": float(radius),
                "spot_count": len(group_records),
            }
        )
    off_ring = [record for record in records if record.ring_index < 0]
    if off_ring:
        counts.append(
            {
                "ring_index": -1,
                "ring_radius_px": None,
                "spot_count": len(off_ring),
            }
        )
    return counts


def write_spot_csv(path: Path, records: list[SpotRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(SpotRecord.__dataclass_fields__.keys())
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))


def robust_limits(image: np.ndarray, valid: np.ndarray) -> tuple[float, float]:
    vals = image[valid]
    vals = vals[np.isfinite(vals)]
    vals = vals[vals > 0]
    if vals.size == 0:
        return 0.0, 1.0
    return float(np.percentile(vals, 1)), float(np.percentile(vals, 99.8))


def filtered_image(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = np.asarray(image, dtype=np.float32).copy()
    out[np.asarray(mask, dtype=bool)] = np.nan
    return out


def dilate_mask(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return np.asarray(mask, dtype=bool)
    return morphology.binary_dilation(np.asarray(mask, dtype=bool), morphology.disk(radius))


def prepare_matplotlib_cache(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mpl_cache = path.parent / ".matplotlib"
    mpl_cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(mpl_cache))


def save_filtered_image_png(
    path: Path,
    image: np.ndarray,
    combined_mask: np.ndarray,
    spot_mask: np.ndarray | None = None,
) -> None:
    prepare_matplotlib_cache(path)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm

    filtered = filtered_image(image, combined_mask)
    valid = np.isfinite(filtered) & (filtered > 0)
    vmin, vmax = robust_limits(image, valid)

    cmap = plt.get_cmap("gray").copy()
    cmap.set_bad(color="black")
    fig, ax = plt.subplots(figsize=(8, 8), constrained_layout=True)
    ax.imshow(
        filtered,
        origin="upper",
        cmap=cmap,
        norm=LogNorm(vmin=max(vmin, 1), vmax=vmax),
        interpolation="nearest",
    )
    if spot_mask is not None:
        overlay = np.zeros((*image.shape, 4), dtype=np.float32)
        overlay[spot_mask] = (0.0, 0.85, 1.0, 0.85)
        ax.imshow(overlay, origin="upper", interpolation="nearest")
    ax.set_title("Ring-filtered image")
    ax.set_xticks([])
    ax.set_yticks([])
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_diagnostic_png(
    path: Path,
    image: np.ndarray,
    base_mask: np.ndarray,
    ring_mask: np.ndarray,
    spot_mask: np.ndarray,
    z: np.ndarray,
    q90: np.ndarray,
    ring_diag: dict[str, np.ndarray | float],
    mean_diag: dict[str, np.ndarray | float],
    density_diag: dict[str, np.ndarray | float],
    ring_radii: np.ndarray,
) -> None:
    prepare_matplotlib_cache(path)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm

    valid = ~base_mask
    vmin, vmax = robust_limits(image, valid)

    fig, axes = plt.subplots(2, 3, figsize=(15, 9), constrained_layout=True)
    ax = axes.ravel()
    ax[0].imshow(image, origin="upper", cmap="gray", norm=LogNorm(vmin=max(vmin, 1), vmax=vmax))
    ax[0].set_title("Raw TIFF")

    overlay = np.zeros((*image.shape, 4), dtype=np.float32)
    overlay[ring_mask] = (1.0, 0.55, 0.0, 0.50)
    overlay[spot_mask] = (0.0, 0.85, 1.0, 0.90)
    overlay[base_mask] = (1.0, 0.0, 0.0, 0.35)
    ax[1].imshow(image, origin="upper", cmap="gray", norm=LogNorm(vmin=max(vmin, 1), vmax=vmax))
    ax[1].imshow(overlay, origin="upper")
    ax[1].set_title("Overlay: rings orange, spots cyan, bad red")

    ax[2].imshow(ring_mask, origin="upper", cmap="gray_r", interpolation="nearest")
    ax[2].set_title("Auto ring mask")

    z_show = np.clip(z, -3, 25)
    im = ax[3].imshow(z_show, origin="upper", cmap="magma", vmin=-3, vmax=25)
    ax[3].set_title("Annular residual z score")
    fig.colorbar(im, ax=ax[3], shrink=0.8)

    ax[4].imshow(spot_mask, origin="upper", cmap="gray_r", interpolation="nearest")
    ax[4].set_title("Detected spot pixels")

    score = ring_diag["ring_score"]
    ax[5].plot(q90, color="0.45", lw=1, label="radial q90")
    ax[5].plot(ring_diag["smooth_q90"], color="black", lw=1, label="smoothed q90")
    ax_t = ax[5].twinx()
    ax_t.plot(score, color="tab:orange", lw=1, label="ring score")
    ax_t.plot(
        mean_diag["mean_score"],
        color="tab:green",
        lw=1,
        alpha=0.75,
        label="mean score",
    )
    ax_t.plot(
        density_diag["density_score"],
        color="tab:blue",
        lw=1,
        alpha=0.75,
        label="density score",
    )
    for radius in ring_radii:
        ax[5].axvline(radius, color="tab:orange", alpha=0.35)
    ax[5].set_xlabel("Radius from beam center (px)")
    ax[5].set_title("Ring candidates")
    ax[5].legend(loc="upper left", fontsize=8)
    ax_t.legend(loc="upper right", fontsize=8)

    for axis in ax[:5]:
        axis.set_xticks([])
        axis.set_yticks([])

    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_grouped_ring_spot_overlay_png(
    path: Path,
    image: np.ndarray,
    radial: np.ndarray,
    base_mask: np.ndarray,
    ring_radii: np.ndarray,
    records: list[SpotRecord],
) -> None:
    prepare_matplotlib_cache(path)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm

    valid = ~base_mask
    vmin, vmax = robust_limits(image, valid)
    cmap = plt.get_cmap("gray").copy()
    ring_colors = plt.get_cmap("turbo")(np.linspace(0.05, 0.95, max(len(ring_radii), 1)))
    spot_colors = plt.get_cmap("tab20")(np.linspace(0, 1, 20))
    markers = ["o", "D", "x", "+", "s", "^", "v", "P", "*", "X", "<", ">"]

    fig, ax = plt.subplots(figsize=(12.5, 9), constrained_layout=True)
    ax.imshow(
        image,
        origin="upper",
        cmap=cmap,
        norm=LogNorm(vmin=max(vmin, 1), vmax=vmax),
        interpolation="nearest",
    )

    for index, radius in enumerate(ring_radii):
        color = ring_colors[index % len(ring_colors)]
        ax.contour(
            radial,
            levels=[float(radius)],
            colors=[color],
            linewidths=1.2,
            alpha=0.95,
        )
        if index < 12:
            ax.plot(
                [],
                [],
                color=color,
                lw=1.4,
                label=f"ring {index + 1}: r={radius:.1f}px",
            )

    radius_groups: dict[int, list[SpotRecord]] = {}
    for record in records:
        radius_groups.setdefault(record.radius_group_index, []).append(record)

    labelled_groups = 0
    for index in sorted(radius_groups):
        if index < 0:
            continue
        group = radius_groups[index]
        if not group:
            continue
        radius = float(np.mean([record.radius_group_radius_px for record in group]))
        marker = markers[index % len(markers)]
        color = spot_colors[index % len(spot_colors)]
        label = None
        if len(group) > 1 and labelled_groups < 16:
            label = f"spot radius group {index + 1}: r={radius:.1f}px, n={len(group)}"
            labelled_groups += 1
        scatter_kwargs = {
            "s": 48,
            "marker": marker,
            "linewidths": 1.3,
        }
        if label is not None:
            scatter_kwargs["label"] = label
        if marker in {"x", "+", "*"}:
            scatter_kwargs["color"] = color
        else:
            scatter_kwargs["facecolors"] = "none"
            scatter_kwargs["edgecolors"] = color
        ax.scatter(
            [record.x for record in group],
            [record.y for record in group],
            **scatter_kwargs,
        )

    ax.set_title("Colored rings and all-spot same-radius groups")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.legend(
        loc="upper left",
        bbox_to_anchor=(1.01, 1.0),
        borderaxespad=0.0,
        fontsize=7,
        framealpha=0.9,
        ncol=1,
    )
    fig.savefig(path, dpi=180)
    plt.close(fig)


def process_image(
    image_path: Path,
    out_dir: Path,
    *,
    poni_path: Path | None = None,
    center: tuple[float, float] | None = None,
    config: FilterConfig | None = None,
    output_suffix: str = "",
) -> dict:
    if config is None:
        config = FilterConfig()
    image_path = Path(image_path)
    stem = f"{image_path.stem}{output_suffix}"
    out_dir.mkdir(parents=True, exist_ok=True)

    image = tifffile.imread(image_path)
    image = np.asarray(image, dtype=np.float32)

    base_mask = ~np.isfinite(image) | (image <= 0)
    valid = ~base_mask
    radial, center, geometry_info = build_radial_coordinate(
        image.shape,
        valid,
        poni_path=poni_path,
        center=center,
        geometry=config.geometry,
    )
    med, mad, q90, counts = robust_binned_stats(image, radial, valid)
    mean_profile = binned_mean_profile(image, radial, valid, n_bins=len(counts))
    radial_i = np.clip(np.rint(radial).astype(np.int32), 0, med.size - 1)
    z = (image.astype(np.float32) - med[radial_i]) / np.maximum(
        1.4826 * mad[radial_i],
        1.0,
    )
    max_ring_radius = float(np.nanmax(radial[valid])) * config.max_ring_radius_fraction
    profile_ring_radii, ring_diag = detect_ring_radii(
        q90,
        counts,
        config.ring_prominence,
        min_radius=config.min_ring_radius,
        max_radius=max_ring_radius,
    )
    mean_ring_radii, mean_diag = detect_mean_ring_radii(
        mean_profile,
        counts,
        config.ring_mean_prominence,
        min_radius=config.min_ring_radius,
        max_radius=max_ring_radius,
    )
    density_ring_radii, density_diag = detect_density_ring_radii(
        z,
        radial,
        valid,
        counts,
        z_range=config.ring_z_range,
        min_prominence=config.ring_density_prominence,
        min_radius=config.min_ring_radius,
        max_radius=max_ring_radius,
    )
    ring_radii = merge_close_radii(
        np.r_[profile_ring_radii, mean_ring_radii, density_ring_radii],
        tolerance=max(6.0, config.ring_half_width * 2.0),
    )
    ring_mask = build_ring_mask(radial, ring_radii, config.ring_half_width, base_mask)

    spot_mask, z, _primary_records = detect_spots(
        image=image,
        radial=radial,
        base_mask=base_mask,
        ring_mask=ring_mask,
        med=med,
        mad=mad,
        spot_z=config.spot_z,
        min_area=config.min_area,
        max_area=config.max_area,
        max_eccentricity=config.max_eccentricity,
        keep_on_rings=config.keep_on_rings,
    )
    micro_spot_mask = detect_micro_spots(
        image,
        z,
        base_mask,
        threshold=config.micro_spot_z,
        contrast_threshold=config.micro_spot_contrast,
        dilate_radius=config.micro_spot_dilate,
    )
    spot_core_mask = spot_mask | micro_spot_mask
    records = records_from_spot_mask(
        spot_core_mask,
        image,
        z,
        radial,
        ring_radii,
        ring_tolerance=config.spot_ring_tolerance,
        min_area=config.min_area,
        max_area=config.max_area,
        max_eccentricity=config.max_eccentricity,
    )
    radius_spot_groups = assign_radius_groups(
        records,
        tolerance=config.spot_radius_group_tolerance,
    )
    spot_display_mask = dilate_mask(spot_core_mask, config.spot_dilate)
    protected_ring_mask = ring_mask & ~spot_display_mask

    combined_mask = base_mask | protected_ring_mask
    raw_ring_mask_path = out_dir / f"{stem}_raw_auto_ring_mask.npy"
    ring_mask_path = out_dir / f"{stem}_auto_ring_mask.npy"
    micro_spot_mask_path = out_dir / f"{stem}_micro_spot_mask.npy"
    spot_mask_path = out_dir / f"{stem}_auto_spot_mask.npy"
    combined_mask_path = out_dir / f"{stem}_base_plus_ring_mask.npy"
    filtered_image_path = out_dir / f"{stem}_ring_filtered_image.npy"
    csv_path = out_dir / f"{stem}_spots.csv"
    report_path = out_dir / f"{stem}_auto_ring_filter_report.json"
    png_path = out_dir / f"{stem}_auto_ring_filter_overlay.png"
    filtered_png_path = out_dir / f"{stem}_ring_filtered_image.png"
    grouped_png_path = out_dir / f"{stem}_ring_spot_groups.png"

    np.save(raw_ring_mask_path, ring_mask)
    np.save(ring_mask_path, protected_ring_mask)
    np.save(micro_spot_mask_path, micro_spot_mask)
    np.save(spot_mask_path, spot_display_mask)
    np.save(combined_mask_path, combined_mask)
    np.save(filtered_image_path, filtered_image(image, combined_mask))
    write_spot_csv(csv_path, records)

    report = {
        "image": str(image_path),
        "shape": list(image.shape),
        "center_yx_px": [float(center[0]), float(center[1])],
        "center_source": geometry_info["center_source"],
        "radial_source": geometry_info["radial_source"],
        "radial_units": geometry_info["radial_units"],
        "coordinate_origin": geometry_info["coordinate_origin"],
        "coordinate_step": geometry_info["coordinate_step"],
        "ring_positions_coordinate": [
            float(geometry_info["coordinate_origin"]) + float(x) * float(geometry_info["coordinate_step"])
            for x in ring_radii
        ],
        "profile_ring_radii_px": [float(x) for x in profile_ring_radii],
        "mean_ring_radii_px": [float(x) for x in mean_ring_radii],
        "density_ring_radii_px": [float(x) for x in density_ring_radii],
        "ring_radii_px": [float(x) for x in ring_radii],
        "ring_half_width_px": float(config.ring_half_width),
        "spot_ring_tolerance_px": float(config.spot_ring_tolerance),
        "spot_radius_group_tolerance_px": float(config.spot_radius_group_tolerance),
        "ring_spot_groups": ring_group_counts(records, ring_radii),
        "radius_spot_groups": radius_spot_groups,
        "base_mask_pixels": int(base_mask.sum()),
        "raw_ring_mask_pixels": int(ring_mask.sum()),
        "ring_mask_pixels": int(protected_ring_mask.sum()),
        "combined_mask_pixels": int(combined_mask.sum()),
        "spot_pixels": int(spot_mask.sum()),
        "micro_spot_pixels": int(micro_spot_mask.sum()),
        "merged_spot_core_pixels": int(spot_core_mask.sum()),
        "spot_display_pixels": int(spot_display_mask.sum()),
        "spot_display_pixels_on_raw_ring": int((spot_display_mask & ring_mask).sum()),
        "spot_count": len(records),
        "outputs": {
            "raw_ring_mask_npy": str(raw_ring_mask_path),
            "ring_mask_npy": str(ring_mask_path),
            "micro_spot_mask_npy": str(micro_spot_mask_path),
            "spot_mask_npy": str(spot_mask_path),
            "combined_mask_npy": str(combined_mask_path),
            "filtered_image_npy": str(filtered_image_path),
            "spots_csv": str(csv_path),
            "diagnostic_png": str(png_path) if config.make_plot else None,
            "filtered_image_png": str(filtered_png_path) if config.make_plot else None,
            "grouped_overlay_png": str(grouped_png_path) if config.make_plot else None,
        },
    }
    report_path.write_text(json.dumps(report, indent=2))

    if config.make_plot:
        save_diagnostic_png(
            png_path,
            image,
            base_mask,
            protected_ring_mask,
            spot_display_mask,
            z,
            q90,
            ring_diag,
            mean_diag,
            density_diag,
            ring_radii,
        )
        save_filtered_image_png(
            filtered_png_path,
            image,
            combined_mask,
            spot_mask=spot_display_mask,
        )
        save_grouped_ring_spot_overlay_png(
            grouped_png_path,
            image,
            radial,
            base_mask,
            ring_radii,
            records,
        )

    return report


def main() -> None:
    args = parse_args()
    center = None
    if args.center is not None:
        center = (float(args.center[0]), float(args.center[1]))
    report = process_image(
        args.image,
        args.out_dir,
        poni_path=args.poni,
        center=center,
        config=config_from_args(args),
        output_suffix=str(args.output_suffix),
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
