# Peak Detection Context Handoff

## 1. Original goal of the project

The original project goal was to automate X-ray diffraction image analysis for UOTe high-pressure measurements.

The user first wanted automatic 2D image processing:

- detect bright diffraction spots;
- identify and mask/filter powder rings;
- protect real spots that lie on rings so they are not masked away;
- use Dioptas/pyFAI calibration (`.poni`) where possible;
- produce filtered images, overlays, masks, spot CSVs, and review plots.

The project then expanded into 1D integrated `.xy` pattern analysis:

- detect peak candidates from integrated XRD patterns;
- compare frames/scans/pressures using multiple correlation maps;
- identify static/non-moving peaks that may be diamond or cell artifacts;
- use correlation to identify reproducible material-related features without knowing peak positions in advance.

## 2. Current repository structure and relevant file names

Workspace root:

- `/Users/stanley/x-ray`

Important data folders:

- `Data/Cell_14_integrated`
- `Data/Cell_29_integrated`
- `Data/Cell_*/*/*.tif`
- `raw_data/`
- `notebooks/`

Important scripts:

- `scripts/auto_spot_ring_filter.py`
  - 2D ring and spot filtering.
- `scripts/batch_auto_spot_ring_filter.py`
  - Batch 2D filtering.
- `scripts/find_xray_files.py`
  - Browse/classify X-ray data files.
- `scripts/compare_integrated_peaks.py`
  - Core 1D `.xy` peak detection and correlation utilities.
- `scripts/per_peak_correlation_maps.py`
  - Per-peak frame-vs-frame correlation maps.
- `scripts/window_autocorrelation_correlations.py`
  - Window autocorrelation correlation methods.
- `scripts/static_peak_and_overall_correlation.py`
  - Static peak detection and weighted overall correlation maps.
- `scripts/run_correlation_suite.py`
  - Runs the organized correlation suite.
- `scripts/xrd_results_dashboard.py`
  - Streamlit local dashboard for browsing outputs.

Important output folders:

- `outputs/auto_ring_filter_batch_poni_microz4p2_ringw3`
  - latest useful automated ring filtering output.
- `outputs/auto_ring_filter_batch_radius_groups_cell29_10deg_by_pressure_legend_outside`
  - same-radius spot/ring grouping output.
- `outputs/correlation_suite_20260617`
  - older conservative correlation suite.
- `outputs/correlation_suite_20260619_ultra_peaks`
  - ultra-sensitive but no raw-local-max suite.
- `outputs/correlation_suite_20260619_raw_ultra_peaks`
  - raw-local-max suite.
- `outputs/correlation_suite_20260621_exhaustive_shoulders`
  - current exhaustive shoulder suite.
- `outputs/README_CURRENT.md`
  - current useful output summary.

Dashboard:

- `scripts/xrd_results_dashboard.py`
- current default suite:
  - `outputs/correlation_suite_20260621_exhaustive_shoulders`
- local URL:
  - `http://localhost:8501`

## 3. Old peak-detection algorithm

See `docs/algorithm_changes.md`.

In short, the old algorithm used `find_peaks` on:

- baseline-subtracted smoothed residual;
- smoothed signal;
- micro-smoothed signal.

It filtered by height, prominence, local rise, SNR, and merged nearby detections.

It missed visible tiny peaks.

## 4. New peak-detection algorithm

The newest completed/validated suite uses:

- residual peaks;
- smoothed bumps;
- micro-smoothed peaks;
- raw local maxima;
- curvature shoulder candidates from negative second derivative.

It is high recall but too noisy.

A newer matched-filter/shape-score idea was partially implemented but not fully wired or validated:

- multi-scale Mexican-hat matched filter;
- local detrended peak-shape score;
- robust local SNR;
- local two-sided contrast.

This is likely the right direction for the next iteration.

## 5. Every parameter changed

See `docs/algorithm_changes.md` for detailed parameter history.

Important current values in `scripts/per_peak_correlation_maps.py`:

- `peak-match-tolerance = 0.02`
- `prominence = 0.2`
- `bump-prominence = 0.05`
- `micro-prominence = 0.005`
- `raw-prominence = 0.0`
- `shoulder-prominence = 0.0`
- `min-micro-snr = 0.0`
- `top-peaks = 4000`
- `distance = 1`
- `min-peak-height = 0.0`
- `min-bump-rise = 0.0`
- `merge-tolerance = 0.0`
- `small-peak-max-prominence = 999.0`
- `small-peak-max-width = 999.0`

New but not fully wired parameters in `scripts/compare_integrated_peaks.py`:

- `matched-filter-prominence = 0.0`
- `matched-filter-widths = "2,3,5,8"`
- `min-shape-snr = 0.0`
- `min-shape-contrast = 0.0`
- `shape-half-window = 0.16`

Overall/reliable correlation parameters in `scripts/static_peak_and_overall_correlation.py`:

- `min-static-frame-fraction = 0.65`
- `max-static-mad-deg = 0.045`
- `max-static-abs-slope = 0.005`
- `min-static-position-frames = 5`
- `min-static-max-roi-area = 5e-4`
- `min-reliable-frame-fraction = 0.24`
- `min-reliable-max-roi-area = 1e-4`
- `roi-presence-fraction-of-max = 0.10`
- `min-roi-presence-area = 1e-4`
- overall weights:
  - `peak_presence = 0.35`
  - `peak_area = 0.30`
  - `same_window_acf = 0.20`
  - `all_window_acf = 0.15`

## 6. What problems remain

Main unresolved problem:

- The detector still does not match human intuition.
- Conservative versions miss small visible peaks.
- Exhaustive versions mark too many false peaks on slopes, tails, shoulders, baseline ripples, and noise.

Specific unresolved examples:

- The older 10.4GPa plot missed black-circled small peaks.
- The newest 2.4GPa_decomp / exhaustive plot marks red-circled non-peaks on sloped/broad regions.

Technical unresolved issues:

- Matched-filter/shape-score code exists but is not fully wired into suite CLI.
- No validated threshold has been chosen for `min-shape-snr` or `min-shape-contrast`.
- No labeled ground truth exists.
- Peak definition is ambiguous for shoulders and broad features.
- Current review plots use the same visual marker for all candidate quality levels; there is no confidence/color coding.

Recommended next direction:

- Use high-recall candidate generation, then score/filter candidates by local peak shape.
- Keep full candidate table, but create filtered candidate classes:
  - strong peaks;
  - weak plausible peaks;
  - shoulder candidates;
  - likely noise/background.
- Use correlation recurrence to decide scientific relevance.

## 7. Collaborator feedback and scientific goal

See `docs/collaborator_feedback.md`.

Most important point:

The collaborator wants many plausible peaks plotted because fake/random peaks should not recur across many scans. The correlation plot is meant to identify recurring peaks precisely because we do not know ahead of time which peak positions matter.

## 8. Important assumptions and decisions already made

Assumptions:

- `.xy` files are integrated 1D diffraction patterns with columns `2theta` and intensity.
- Pressure labels are parsed from filenames/folders, e.g. `0.7GPa`, `1GPa`, `2.4GPa_decomp`.
- Static/non-moving peaks across pressure are likely diamond/cell/artifact candidates.
- Material peaks may shift with pressure, sometimes up to around 1 degree.
- Same-window ACF allows shift tolerance.
- Single-frame window ACF is not used in overall frame-vs-frame correlation because it compares windows within one frame.

Decisions:

- Keep multiple result suites instead of deleting all old versions.
- Dashboard defaults to the newest suite.
- Lower triangle heatmaps are used because frame correlation matrices are symmetric and diagonal is trivial.
- Both all-peaks and static-removed overall maps are generated.
- Added reliable peak maps to reduce single-frame noise impact:
  - `overall_reliable_peaks_*`
  - `overall_reliable_static_removed_*`

## 9. Code snippets/functions to inspect

Inspect:

- `scripts/compare_integrated_peaks.py`
  - `detect_peaks`
  - `filter_peak_candidates`
  - `parse_width_list`
  - `mexican_hat_kernel`
  - `local_shape_score`
  - `group_peaks`
  - `build_peak_roi_area_vectors`

- `scripts/per_peak_correlation_maps.py`
  - CLI parameters near top.
  - construction of `detector_args`.
  - output of `peak_table.csv`, `small_peak_table.csv`, `peak_group_table.csv`, `peak_presence_features.csv`, `peak_roi_area_features.csv`, review plots, and per-peak maps.

- `scripts/run_correlation_suite.py`
  - currently passes raw/shoulder parameters, but not matched-filter/shape-score parameters.

- `scripts/static_peak_and_overall_correlation.py`
  - `identify_static_peaks`
  - `peak_group_reliability_mask`
  - `build_overall_correlations`

- `scripts/xrd_results_dashboard.py`
  - `DEFAULT_SUITE`
  - automatic overall mode discovery.

## 10. Exact next task prompt to formulate

Use this as the next Codex/ChatGPT prompt:

> We need a balanced high-recall peak detector for integrated XRD `.xy` scans. The old detector missed visible tiny peaks; the newest exhaustive detector marks too many false peaks on slopes/tails/noise. Please inspect `scripts/compare_integrated_peaks.py`, especially `detect_peaks`, `filter_peak_candidates`, `local_shape_score`, and the partially implemented matched-filter code. Finish wiring matched-filter and local shape-score parameters into `scripts/per_peak_correlation_maps.py` and `scripts/run_correlation_suite.py`. Then implement a candidate scoring system that keeps high recall but filters obvious non-peaks using local detrended shape contrast/SNR and multi-scale matched-filter response. Generate a new output suite, compare it against `outputs/correlation_suite_20260619_raw_ultra_peaks` and `outputs/correlation_suite_20260621_exhaustive_shoulders`, especially the `10.4GPa` and `2.4GPa_decomp` review plots. The goal is to keep the small black-circled peaks missed by the older version while removing red-circled false positives from the exhaustive version. Do not delete old outputs. Report peak counts, peak-group counts, and show where the new review plots and correlation maps are saved.

## Suggested files/images to attach to another ChatGPT session

Code:

- `scripts/compare_integrated_peaks.py`
- `scripts/per_peak_correlation_maps.py`
- `scripts/run_correlation_suite.py`
- `scripts/static_peak_and_overall_correlation.py`
- `scripts/xrd_results_dashboard.py`

Documentation:

- `docs/peak_detection_context.md`
- `docs/algorithm_changes.md`
- `docs/collaborator_feedback.md`
- `outputs/README_CURRENT.md`

Correlation plot screenshots:

- `outputs/correlation_suite_20260621_exhaustive_shoulders/05_static_peaks_and_overall_correlation/overall_reliable_static_removed_correlation_heatmap.png`
- `outputs/correlation_suite_20260621_exhaustive_shoulders/05_static_peaks_and_overall_correlation/overall_static_removed_correlation_heatmap.png`
- `outputs/correlation_suite_20260621_exhaustive_shoulders/01_per_peak_frame_correlation/xy_peak_review/10.4GPa_xy_peak_review.png`
- `outputs/correlation_suite_20260621_exhaustive_shoulders/01_per_peak_frame_correlation/xy_peak_review/2.4GPa_decomp_xy_peak_review.png`

Raw scan data examples:

- one or two `.xy` files from `Data/Cell_14_integrated`
- one or two `.xy` files from `Data/Cell_29_integrated`
- useful examples likely include files corresponding to `10.4GPa` and `2.4GPa_decomp`.

