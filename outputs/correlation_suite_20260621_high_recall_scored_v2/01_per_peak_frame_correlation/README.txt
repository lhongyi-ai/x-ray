Per-peak frame correlation maps
================================

Each heatmap is one peak group. The score compares the ROI area of that peak between two frames.
If both frames have the peak: score = 1 - abs(area_a-area_b)/max(area_a,area_b).
If only one frame has the peak: score = 0.
If neither frame has the peak: blank/NaN.
The diagonal and upper triangle are blank because they are redundant.

Input files: 17
All generated candidates: 7227
Detected peaks used in this suite: 4893
Tier A candidates used: 2687
Tier B candidates used: 2206
Tier C candidates generated: 2334
Tier C included in correlation maps: 0
Small-peak candidates: 4893
Peak groups: 625
Peak match tolerance: 0.02 deg
ROI half-width: 0.06 deg
micro-prominence: 0.005
raw-prominence: 0
shoulder-prominence: 0
matched-filter-prominence: 0.2
matched-filter-widths: 2,3,5,8
min-micro-snr: 0
min-shape-snr: 0.15
min-shape-contrast: 0.0005
shape-half-window: 0.16
merge-tolerance: 0.015
top-peaks: 4000
Top-peaks truncation occurred: 0
