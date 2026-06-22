# Scientific Peak Group Validation

## Executive Summary

- Analyzed `outputs/correlation_suite_20260621_high_recall_scored_v2` with 17 scans and 625 peak groups.
- This report does not retune the detector; it interprets the existing high-recall candidates using cross-pressure behavior.
- Category counts: {'recurring': 208, 'appearing/disappearing': 26, 'systematic_shift': 0, 'isolated_strong': 28, 'likely_static_background': 206, 'uncertain': 321}.
- Top persistent groups include: 578, 36, 347, 49, 38.
- Top shifting groups include: none.
- Labels are cautious: recurring/static/shift candidates are priorities for inspection, not phase assignments.

## 1. Dataset and Suite Analyzed

- Suite: `outputs/correlation_suite_20260621_high_recall_scored_v2`
- Output folder: `outputs/correlation_suite_20260621_high_recall_scored_v2/06_scientific_peak_group_validation`
- Pressure order used: 0.7GPa (compression), 1GPa (compression), 1.3GPa (compression), 1.5GPa (compression), 2.3GPa (compression), 3.9GPa (compression), 5GPa (compression), 6.2GPa (compression), 6.6GPa (compression), 7.4GPa (compression), 8.5GPa (compression), 9.8GPa (compression), 10.4GPa (compression), 12.8GPa (compression), 13.3GPa (compression), 15.6GPa (compression), 2.4GPa_decomp (decompression)
- Compression and decompression are distinguishable; decompression is not automatically connected to compression trajectories.

## 2. Review-Plot Sanity Check

| frame         |   total_candidates |   tier_a_count |   tier_b_count |   tier_c_count | visually_retained_weak_features                                                     | obvious_artifacts_remaining_in_A+B                                                                              | conclusion                                                             |
|:--------------|-------------------:|---------------:|---------------:|---------------:|:------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------|
| 10.4GPa       |                338 |            149 |             99 |             90 | weak shoulder/small features around 8-9 deg and 12-16 deg remain marked in Tier A/B | some high-angle and broad-tail markers remain in A+B, consistent with high-recall setting                       | passes high-recall sanity check; no top-peaks truncation               |
| 2.4GPa_decomp |                527 |            171 |             73 |            283 | plausible protrusions remain in A/B across the broad decomp background              | many obvious slope/plateau/tail candidates were downgraded to Tier C, but A/B is still intentionally permissive | usable for cross-scan prioritization, not single-scan phase assignment |

## 3. Pressure Ordering and Methodology

Pressure labels were parsed numerically from the frame label. Compression scans are ordered by increasing pressure. Decompression scans are kept as a separate branch after compression for plotting and coverage, but global position fits use compression points unless otherwise noted.

Correlation maps in this suite are per-peak frame-pair similarity maps: for each peak group, the implementation compares the local/ROI peak signal across frames. Strong correlation means similar behavior for that grouped candidate in those frames; it does not prove that the peak is real or belongs to the sample.

## 4. Most Persistent Peak Groups

|   peak_group |   median_2theta |   frame_count |   coverage_fraction |   longest_consecutive_run |   tier_a_count |   tier_b_count |   max_roi_area | notes                                                                                                                                                                                                                     |
|-------------:|----------------:|--------------:|--------------------:|--------------------------:|---------------:|---------------:|---------------:|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|          578 |        22.2286  |            14 |            0.823529 |                        10 |             14 |              8 |    0.000730056 | appears in many scans; recurrence alone does not identify phase | nearly fixed 2theta across pressure; possible static/background/diamond-like candidate                                                                  |
|           36 |         3.38662 |            14 |            0.823529 |                         9 |              6 |             14 |    0.00577826  | appears in many scans; recurrence alone does not identify phase | nearly fixed 2theta across pressure; possible static/background/diamond-like candidate | trajectory depends strongly on weak/shoulder Tier B detections |
|          347 |        14.1311  |            14 |            0.823529 |                         5 |             16 |              4 |    0.0181036   | appears in many scans; recurrence alone does not identify phase | nearly fixed 2theta across pressure; possible static/background/diamond-like candidate                                                                  |
|           49 |         3.80362 |            13 |            0.764706 |                         8 |             16 |              2 |    0.0112731   | appears in many scans; recurrence alone does not identify phase | nearly fixed 2theta across pressure; possible static/background/diamond-like candidate                                                                  |
|           38 |         3.43986 |            13 |            0.764706 |                         7 |             10 |              9 |    0.000613584 | appears in many scans; recurrence alone does not identify phase | nearly fixed 2theta across pressure; possible static/background/diamond-like candidate                                                                  |
|          321 |        13.1691  |            13 |            0.764706 |                         6 |             14 |              5 |    0.00601679  | appears in many scans; recurrence alone does not identify phase | nearly fixed 2theta across pressure; possible static/background/diamond-like candidate                                                                  |
|          621 |        23.6702  |            13 |            0.764706 |                         6 |              9 |              5 |    0.00289931  | appears in many scans; recurrence alone does not identify phase | nearly fixed 2theta across pressure; possible static/background/diamond-like candidate                                                                  |
|          501 |        19.6112  |            13 |            0.764706 |                         6 |             14 |              2 |    0.00140683  | appears in many scans; recurrence alone does not identify phase | nearly fixed 2theta across pressure; possible static/background/diamond-like candidate                                                                  |

## 5. Pressure-Induced Appearance/Disappearance

|   peak_group |   median_2theta | transition_category                  | pressure_interval   |   frame_count | evidence                               |
|-------------:|----------------:|:-------------------------------------|:--------------------|--------------:|:---------------------------------------|
|           51 |         3.87865 | high-pressure-only / onset candidate | 10.4-13.3 GPa       |             2 | first detected near 10.4 GPa           |
|           67 |         4.43257 | high-pressure-only / onset candidate | 10.4-15.6 GPa       |             3 | first detected near 10.4 GPa           |
|          146 |         7.09324 | high-pressure-only / onset candidate | 9.8-12.8 GPa        |             2 | first detected near 9.8 GPa            |
|          348 |        14.1638  | high-pressure-only / onset candidate | 9.8-13.3 GPa        |             3 | first detected near 9.8 GPa            |
|          369 |        14.908   | high-pressure-only / onset candidate | 8.5-12.8 GPa        |             3 | first detected near 8.5 GPa            |
|          442 |        17.5379  | high-pressure-only / onset candidate | 9.8-13.3 GPa        |             3 | first detected near 9.8 GPa            |
|          457 |        18.118   | high-pressure-only / onset candidate | 8.5-10.4 GPa        |             2 | first detected near 8.5 GPa            |
|          216 |         9.45294 | isolated strong / possible transient | 2.3-8.5 GPa         |             3 | few detections but high ROI/prominence |

## 6. Systematically Shifting Peak Groups

_None found by current heuristic._

## 7. Isolated Strong Candidates

|   peak_group |   median_2theta |   frame_count |   max_roi_area |   tier_a_count |   tier_b_count | frames_present       | notes                                                                                                                                                                                |
|-------------:|----------------:|--------------:|---------------:|---------------:|---------------:|:---------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|          264 |        11.1894  |             2 |      0.222228  |              3 |              0 | 3.9GPa;5GPa          | few-scan candidate with strong Tier/ROI evidence; may be transient or grouping failure                                                                                               |
|          268 |        11.3634  |             1 |      0.209812  |              1 |              0 | 1.5GPa               | few-scan candidate with strong Tier/ROI evidence; may be transient or grouping failure                                                                                               |
|          225 |         9.77396 |             1 |      0.148968  |              2 |              0 | 3.9GPa               | few-scan candidate with strong Tier/ROI evidence; may be transient or grouping failure                                                                                               |
|          219 |         9.56045 |             1 |      0.117914  |              1 |              0 | 5GPa                 | few-scan candidate with strong Tier/ROI evidence; may be transient or grouping failure                                                                                               |
|          269 |        11.403   |             1 |      0.102171  |              2 |              0 | 2.3GPa               | few-scan candidate with strong Tier/ROI evidence; may be transient or grouping failure                                                                                               |
|          245 |        10.514   |             2 |      0.0935342 |              1 |              1 | 1GPa;15.6GPa         | few-scan candidate with strong Tier/ROI evidence; may be transient or grouping failure                                                                                               |
|          246 |        10.5509  |             2 |      0.0933062 |              2 |              0 | 1.5GPa;15.6GPa       | few-scan candidate with strong Tier/ROI evidence; may be transient or grouping failure                                                                                               |
|          262 |        11.1262  |             2 |      0.0819865 |              1 |              1 | 6.2GPa;2.4GPa_decomp | limited detections across compression/decompression; inspect before connecting trajectories | few-scan candidate with strong Tier/ROI evidence; may be transient or grouping failure |

## 8. Likely Static/Background Candidates

|   peak_group |   median_2theta |   frame_count |   coverage_fraction |   position_mad_deg |   pressure_position_slope_deg_per_gpa | notes                                                                                                                                                                                                                     |
|-------------:|----------------:|--------------:|--------------------:|-------------------:|--------------------------------------:|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|          347 |        14.1311  |            14 |            0.823529 |          0.005625  |                           0.000569017 | appears in many scans; recurrence alone does not identify phase | nearly fixed 2theta across pressure; possible static/background/diamond-like candidate                                                                  |
|           36 |         3.38662 |            14 |            0.823529 |          0.0070115 |                           0.000756031 | appears in many scans; recurrence alone does not identify phase | nearly fixed 2theta across pressure; possible static/background/diamond-like candidate | trajectory depends strongly on weak/shoulder Tier B detections |
|          578 |        22.2286  |            14 |            0.823529 |          0.013617  |                           0.000309989 | appears in many scans; recurrence alone does not identify phase | nearly fixed 2theta across pressure; possible static/background/diamond-like candidate                                                                  |
|           49 |         3.80362 |            13 |            0.764706 |          0.002103  |                          -0.0004015   | appears in many scans; recurrence alone does not identify phase | nearly fixed 2theta across pressure; possible static/background/diamond-like candidate                                                                  |
|          588 |        22.5766  |            13 |            0.764706 |          0.002238  |                           5.48239e-05 | appears in many scans; recurrence alone does not identify phase | nearly fixed 2theta across pressure; possible static/background/diamond-like candidate                                                                  |
|          621 |        23.6702  |            13 |            0.764706 |          0.002397  |                           5.00406e-05 | appears in many scans; recurrence alone does not identify phase | nearly fixed 2theta across pressure; possible static/background/diamond-like candidate                                                                  |
|           38 |         3.43986 |            13 |            0.764706 |          0.002955  |                          -0.000159194 | appears in many scans; recurrence alone does not identify phase | nearly fixed 2theta across pressure; possible static/background/diamond-like candidate                                                                  |
|          547 |        21.1905  |            13 |            0.764706 |          0.0079075 |                          -0.000254594 | appears in many scans; recurrence alone does not identify phase | nearly fixed 2theta across pressure; possible static/background/diamond-like candidate | trajectory depends strongly on weak/shoulder Tier B detections |

## 9. Tier A+B Versus Tier A-Only Findings

|   peak_group |   median_2theta |   tier_ab_frame_count |   tier_a_only_frame_count |   tier_b_contribution |   tier_ab_longest_run |   tier_a_only_longest_run | interpretation                            |
|-------------:|----------------:|----------------------:|--------------------------:|----------------------:|----------------------:|--------------------------:|:------------------------------------------|
|           36 |         3.38662 |                    14 |                         6 |                    14 |                     9 |                         2 | Tier-B-dependent weak trajectory          |
|           37 |         3.40823 |                    12 |                         5 |                    10 |                     8 |                         2 | Tier-B-dependent weak trajectory          |
|          101 |         5.57872 |                    12 |                         5 |                     9 |                     4 |                         2 | Tier-B-dependent weak trajectory          |
|          546 |        21.1532  |                    12 |                         5 |                    11 |                     8 |                         1 | Tier-B-dependent weak trajectory          |
|           68 |         4.47578 |                    11 |                         6 |                     8 |                     5 |                         2 | convincing Tier A-only shifting candidate |
|           73 |         4.63537 |                    11 |                         5 |                     7 |                     5 |                         1 | Tier-B-dependent weak trajectory          |
|           83 |         4.97396 |                    11 |                         5 |                    10 |                     8 |                         2 | Tier-B-dependent weak trajectory          |
|          349 |        14.2102  |                    11 |                         2 |                    13 |                     5 |                         1 | Tier-B-dependent weak trajectory          |

## 10. Possible Grouping Failures, Splits, and Merges

|   group_id_1 |   group_id_2 | reason                      |   end_pressure_group_1 |   start_pressure_group_2 |   implied_shift | confidence   | possible_event_type                   |
|-------------:|-------------:|:----------------------------|-----------------------:|-------------------------:|----------------:|:-------------|:--------------------------------------|
|          216 |          218 | overlapping pressure ranges |                    8.5 |                      1.5 |       0.060066  | low          | possible fragmented moving trajectory |
|           69 |           71 | overlapping pressure ranges |                   13.3 |                      0.7 |       0.060076  | low          | possible fragmented moving trajectory |
|          200 |          202 | overlapping pressure ranges |                   15.6 |                      2.3 |       0.0601415 | low          | possible fragmented moving trajectory |
|          422 |          424 | overlapping pressure ranges |                    8.5 |                      1   |       0.060201  | low          | possible fragmented moving trajectory |
|           58 |           60 | overlapping pressure ranges |                   13.3 |                      1.3 |       0.060219  | low          | possible fragmented moving trajectory |
|          321 |          323 | overlapping pressure ranges |                   13.3 |                      0.7 |       0.060506  | low          | possible fragmented moving trajectory |
|          166 |          168 | overlapping pressure ranges |                   12.8 |                      1   |       0.060523  | low          | possible fragmented moving trajectory |
|          529 |          531 | overlapping pressure ranges |                   15.6 |                      1.3 |       0.0605325 | low          | possible fragmented moving trajectory |

## 11. Manual-Review Shortlist

|   peak_group | selection_category   |   median_2theta |   pressure_min |   pressure_max |   frame_count | human_review_question                                                                         | contact_sheet                                                                                                                                         |
|-------------:|:---------------------|----------------:|---------------:|---------------:|--------------:|:----------------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------|
|          347 | recurring            |        14.1311  |            0.7 |           15.6 |            14 | Does a real local peak exist at this position in each relevant scan?                          | outputs/correlation_suite_20260621_high_recall_scored_v2/06_scientific_peak_group_validation/manual_review_contact_sheets/group_347_contact_sheet.png |
|           36 | recurring            |         3.38662 |            0.7 |           13.3 |            14 | Does a real local peak exist at this position in each relevant scan?                          | outputs/correlation_suite_20260621_high_recall_scored_v2/06_scientific_peak_group_validation/manual_review_contact_sheets/group_036_contact_sheet.png |
|          282 | low-pressure-only    |        11.8379  |            1   |            2.3 |             2 | Does a real local peak exist at this position in each relevant scan?                          | outputs/correlation_suite_20260621_high_recall_scored_v2/06_scientific_peak_group_validation/manual_review_contact_sheets/group_282_contact_sheet.png |
|          398 | low-pressure-only    |        16.0132  |            1.3 |            2.3 |             3 | Does a real local peak exist at this position in each relevant scan?                          | outputs/correlation_suite_20260621_high_recall_scored_v2/06_scientific_peak_group_validation/manual_review_contact_sheets/group_398_contact_sheet.png |
|          146 | high-pressure-only   |         7.09324 |            9.8 |           12.8 |             2 | Does a real local peak exist at this position in each relevant scan?                          | outputs/correlation_suite_20260621_high_recall_scored_v2/06_scientific_peak_group_validation/manual_review_contact_sheets/group_146_contact_sheet.png |
|          348 | high-pressure-only   |        14.1638  |            9.8 |           13.3 |             3 | Does a real local peak exist at this position in each relevant scan?                          | outputs/correlation_suite_20260621_high_recall_scored_v2/06_scientific_peak_group_validation/manual_review_contact_sheets/group_348_contact_sheet.png |
|          264 | isolated-strong      |        11.1894  |            3.9 |            5   |             2 | Is this a real local peak in the raw .xy and 2D image, or a spotty artifact/grouping failure? | outputs/correlation_suite_20260621_high_recall_scored_v2/06_scientific_peak_group_validation/manual_review_contact_sheets/group_264_contact_sheet.png |

## 12. Main Limitations

- ROI area is taken from available suite peak/prominence-style fields where exact integrated ROI area is not present for every table.
- Fixed-tolerance grouping may fragment moving peaks or merge nearby peaks; `possible_group_linkages.csv` is a warning list, not an automatic correction.
- Static/background labels are hypotheses for prioritization, not definite diamond or gasket assignments.
- Decompression has only one labeled scan in this suite, so hysteresis claims are especially uncertain.

## 13. Recommended Next Experimental Checks

- Open the manual-review contact sheets and original `.xy` review plots for the shortlisted groups.
- For shifting candidates, verify continuity in local windows and inspect possible neighboring group linkages.
- For likely static/background candidates, compare against raw 2D images and known diamond/gasket/reference peak positions.
- For isolated strong candidates, check raw TIFFs for spotty diffraction, masking artifacts, or peak movement beyond the grouping tolerance.
