Current useful outputs
======================

Updated on 2026-06-21 after adding high-recall scored peak candidates.

- `correlation_suite_20260621_high_recall_scored_v2`
  - Current recommended/default correlation suite.
  - Uses Tier A + Tier B peak candidates in the scientific per-peak correlation maps.
  - Keeps Tier C likely-artifact candidates in `tier_c_candidate_table.csv` for diagnostics.
  - Used by `scripts/xrd_results_dashboard.py` as the default suite.
  - Counts: 7227 generated candidates, 4893 A+B candidates used, 2334 Tier C candidates, 625 peak groups.
  - `top-peaks=4000` did not truncate any frame.

- `correlation_suite_20260621_all_candidate_diagnostic_v2`
  - Diagnostic companion suite.
  - Uses Tier A + Tier B + Tier C candidates in correlation maps.
  - Useful for checking candidates that were intentionally excluded from the standard A+B view.
  - Counts: 7227 candidates used, 645 peak groups.

- `correlation_suite_20260621_scored_comparison_v2`
  - Comparison folder for old and new peak-detection suites.
  - Contains `suite_comparison_metrics.csv` and stacked review plots for 10.4GPa, 2.4GPa_decomp, and representative scans.

- `correlation_suite_20260621_exhaustive_shoulders`
  - Previous exhaustive raw-local-maximum plus shoulder detection suite.
  - Useful as the aggressive baseline that marked many slope/tail/platform artifacts.

- `correlation_suite_20260619_raw_ultra_peaks`
  - Previous aggressive raw-local-maximum suite before shoulder candidates were added.
  - Useful for comparing against the cleaner 384-map version.

- `correlation_suite_20260619_ultra_peaks`
  - Previous ultra-sensitive suite before raw local maxima were added.
  - Useful for comparing against the cleaner 136-map version.

- `correlation_suite_20260617`
  - Previous, more conservative consolidated correlation suite.
  - Useful as a cleaner baseline for comparison.

- `auto_ring_filter_batch_poni_microz4p2_ringw3`
  - Latest automated ring filtering result with micro-spot threshold 4.2 and narrower ring band.
  - Useful for checking ring-filtered images, masks, overlays, and per-image spot CSV files.

- `auto_ring_filter_batch_radius_groups_cell29_10deg_by_pressure_legend_outside`
  - Latest same-radius spot/ring grouping output organized by pressure.
  - Keeps ring/spot group visualizations and `all_spots.csv` for 2D spot radius/azimuth analyses.

Peak detector parameters used in the current v2 suites
------------------------------------------------------

- `micro-prominence`: 0.005
- `raw-prominence`: 0
- `shoulder-prominence`: 0
- `matched-filter-prominence`: 0.2
- `matched-filter-widths`: 2,3,5,8 samples
- `min-micro-snr`: 0
- `min-shape-snr`: 0.15
- `min-shape-contrast`: 0.0005
- `shape-half-window`: 0.16 deg
- `merge-tolerance`: 0.015 deg
- `top-peaks`: 4000

Interpretation
--------------

The detector is intentionally high recall. Tier A and Tier B are used for the standard exploratory correlation outputs. Tier C candidates are not erased; they are preserved as diagnostics because a future dashboard view or human review may still need them.
