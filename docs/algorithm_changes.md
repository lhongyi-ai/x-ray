# Algorithm Changes

## Old algorithm

The first peak detection approach used `scipy.signal.find_peaks` on processed 1D integrated `.xy` patterns.

Main file:

- `scripts/compare_integrated_peaks.py`

Main function:

- `detect_peaks(pattern, args)`

Original stages:

1. Load `.xy` two-column diffraction pattern.
2. Normalize intensity by subtracting the 5th percentile and dividing by the 99th percentile.
3. Smooth the normalized pattern using Savitzky-Golay.
4. Estimate broad background/baseline using a wider Savitzky-Golay window.
5. Compute residual: `smoothed - baseline`.
6. Run `find_peaks` on residual for sharp peaks.
7. Run `find_peaks` on smoothed signal for broader bumps.
8. Run `find_peaks` on narrow micro-smoothed signal for tiny local protrusions.
9. Filter by residual height, bump rise, micro SNR, and local height.
10. Merge nearby detections with `merge_tolerance`.
11. Keep only top N peaks.

This old version missed small visible peaks, especially:

- tiny bumps on sloped background;
- shoulders next to larger peaks;
- weak peaks in noisy regions;
- local features that did not become strict local maxima after smoothing.

## Parameter changes over time

Earlier/balanced-ish values used in the suite:

- `peak-match-tolerance`: `0.08`
- `prominence`: `1.0`
- `bump-prominence`: `0.3`
- `micro-prominence`: `0.2`
- `min-micro-snr`: `0`
- `top-peaks`: `240`
- `distance`: `5`
- `min-peak-height`: `0.2`
- `min-bump-rise`: `0.2`
- `merge-tolerance`: `0.04`
- `small-peak-max-prominence`: `0.5`
- `small-peak-max-width`: `2.0`

Ultra-sensitive version:

- `micro-prominence`: `0.02`
- `top-peaks`: `1000`
- `prominence`: `0.2`
- `bump-prominence`: `0.05`
- `min-peak-height`: `0`
- `min-bump-rise`: `0`
- `distance`: `1`
- `merge-tolerance`: `0.005`
- `small-peak-max-prominence`: `999`
- `small-peak-max-width`: `999`

Raw-ultra version:

- Added raw local maxima detector with `raw-prominence=0`
- `peak-match-tolerance`: `0.03`
- `micro-prominence`: `0.005`
- `top-peaks`: `2000`
- `merge-tolerance`: `0`

Exhaustive shoulder version:

- Added curvature shoulder detector:
  - `shoulder_signal = -np.gradient(np.gradient(micro_smoothed))`
  - `shoulder-prominence=0`
- `peak-match-tolerance`: `0.02`
- `top-peaks`: `4000`
- raw/shoulder candidates bypassed residual-height filtering.

Latest partially implemented idea:

- Add multi-scale matched filter using a Mexican-hat-like kernel.
- Add local detrended peak-shape scoring:
  - fit local sideband slope;
  - subtract local slope;
  - compute center-vs-side contrast;
  - compute robust local SNR;
  - filter raw/shoulder/matched candidates using `min-shape-snr` and `min-shape-contrast`.

Important: the matched-filter/shape-score code was written into `scripts/compare_integrated_peaks.py` but was interrupted before it was fully wired into `scripts/per_peak_correlation_maps.py` and `scripts/run_correlation_suite.py`, and before a new suite was run/validated.

## Current algorithm state

The current checked-in/working-tree `compare_integrated_peaks.py` contains candidate sources:

- `residual`: `find_peaks(residual)`
- `bump`: `find_peaks(smoothed)`
- `micro`: `find_peaks(micro_smoothed)`
- `raw`: `find_peaks(y)`
- `shoulder`: `find_peaks(-second_derivative(micro_smoothed))`
- `matched`: multi-scale convolution with Mexican-hat-like kernels, then `find_peaks(response)`

But only some CLI parameters are exposed in downstream scripts:

- `per_peak_correlation_maps.py` currently exposes raw and shoulder parameters, but not the newly added matched-filter and shape-score parameters.
- `run_correlation_suite.py` currently passes raw and shoulder parameters, but not matched-filter and shape-score parameters.

## Important functions to inspect

Inspect these functions in `scripts/compare_integrated_peaks.py`:

- `detect_peaks(pattern, args)`
- `filter_peak_candidates(...)`
- `merge_close_peak_candidates(...)`
- `group_peaks(...)`
- `build_peak_roi_area_vectors(...)`
- `parse_width_list(text)`
- `mexican_hat_kernel(width)`
- `local_shape_score(two_theta, signal, index, half_window_deg)`

Inspect these files for suite wiring:

- `scripts/per_peak_correlation_maps.py`
- `scripts/run_correlation_suite.py`
- `scripts/static_peak_and_overall_correlation.py`
- `scripts/xrd_results_dashboard.py`

## Output evolution

Known generated correlation suites:

- `outputs/correlation_suite_20260617`
  - earlier/conservative baseline
  - about 977 detected peaks and 136 peak groups in one recorded comparison

- `outputs/correlation_suite_20260619_ultra_peaks`
  - ultra-sensitive residual/bump/micro detector
  - 2047 detected peaks
  - 136 peak groups/maps

- `outputs/correlation_suite_20260619_raw_ultra_peaks`
  - added raw local maxima
  - 3033 detected peaks
  - 384 peak groups/maps

- `outputs/correlation_suite_20260621_exhaustive_shoulders`
  - added raw local maxima plus curvature shoulders
  - 6605 detected peaks
  - 621 peak groups/maps
  - current dashboard default in `scripts/xrd_results_dashboard.py`

## Why the newest result is not satisfactory

The newest exhaustive shoulder version marks too many points:

- sloped background;
- broad tails after strong peaks;
- plateaus;
- baseline undulations;
- high-angle noisy regions;
- non-peak curvature changes.

The user provided examples:

- older 10.4GPa plot missed a visible small peak around the black-circled region near roughly 8.5-9 degrees;
- newer exhaustive plot marks many red-circled regions that should not count as meaningful peaks, especially shoulders/tails/flat slope changes.

The next algorithm should be a balanced high-recall detector, not an unfiltered exhaustive detector.

