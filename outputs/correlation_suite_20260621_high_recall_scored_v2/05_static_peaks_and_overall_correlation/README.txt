Static peak and overall correlation post-processing
===================================================

Static peak identification:
  A suspected static peak group must have high coverage, enough ROI signal, small 2theta MAD, and small pressure slope.
  This intentionally does not allow +/-1 deg shifting; that would hide true pressure-dependent material peak motion.

  min-static-frame-fraction: 0.65
  max-static-mad-deg: 0.045
  max-static-abs-slope: 0.005 deg/GPa
  suspected static groups: 28

Reliable peak set:
  This filters the exhaustive raw-local-max peak list before peak-based overall maps.
  min-reliable-frame-fraction: 0.24
  min-reliable-max-roi-area: 0.0001

Overall frame correlation:
  The overall score is a weighted average of normalized component similarities.
  Components: peak presence Jaccard, peak ROI area cosine, same-window ACF median, all-window ACF frame median.
  single_frame_window_acf is excluded because it compares windows within one frame rather than two frames.

Main outputs:
  suspected_static_peak_groups.csv
  reliable_peak_groups.csv
  all_peak_static_scores.csv
  overall_all_peaks_correlation_heatmap.png/.csv
  overall_reliable_peaks_correlation_heatmap.png/.csv
  overall_static_removed_correlation_heatmap.png/.csv
  overall_reliable_static_removed_correlation_heatmap.png/.csv
  overall_*_pair_components.csv
