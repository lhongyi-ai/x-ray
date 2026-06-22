XRD correlation suite
=====================

01_per_peak_frame_correlation:
  One lower-triangle frame-vs-frame map per detected peak group.

  Peak detector parameters:
    micro-prominence: 0.005
    raw-prominence: 0
    shoulder-prominence: 0
    matched-filter-prominence: 0.2
    matched-filter-widths: 2,3,5,8 samples
    min-shape-snr: 0.15
    min-shape-contrast: 0.0005
    shape-half-window: 0.16 deg
    merge-tolerance: 0.015 deg
    include-tier-c: 0

02_same_window_acf_across_frames:
  One lower-triangle frame-vs-frame ACF map per 5 degree window.
  Handles up to +/-1 degree pressure shift by comparing neighboring windows and taking the best match.

03_single_frame_window_acf:
  For each frame, compares all 5 degree windows within that single frame.

04_all_window_to_all_window_acf:
  One large lower-triangle map comparing every frame-window against every other frame-window.

05_static_peaks_and_overall_correlation:
  Identifies high-coverage non-moving peak groups and writes overall frame correlation maps.
